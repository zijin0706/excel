"""YAML config parser: load, validate, and deserialize the pipeline configuration."""

from pathlib import Path
from typing import Any, Union

import yaml

from .models import (
    ColumnMapping,
    DuckDbSettings,
    FileFormat,
    JoinConfig,
    JoinKey,
    JoinType,
    OutputConfig,
    PipelineConfig,
    PipelineStep,
    Settings,
    SourceConfig,
)


class ConfigError(Exception):
    """Raised when the configuration is invalid."""


def parse(config_path: Union[str, Path]) -> PipelineConfig:
    """Parse a YAML config file into a validated PipelineConfig."""
    config_path = Path(config_path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ConfigError("Config file is empty")

    version = raw.get("version", 1)

    settings = _parse_settings(raw.get("settings", {}))
    sources = _parse_sources(raw.get("sources", []))
    pipeline = _parse_pipeline(raw.get("pipeline", []))
    outputs = _parse_outputs(raw.get("outputs", []))

    config = PipelineConfig(
        version=version,
        settings=settings,
        sources=sources,
        pipeline=pipeline,
        outputs=outputs,
    )

    _validate(config)
    return config


def _parse_settings(raw: dict) -> Settings:
    duckdb_raw = raw.get("duckdb", {})
    duckdb = DuckDbSettings(
        memory_limit=duckdb_raw.get("memory_limit", "8GB"),
        threads=duckdb_raw.get("threads", 4),
        temp_directory=duckdb_raw.get("temp_directory"),
    )
    return Settings(
        input_dir=raw.get("input_dir", "./data/input"),
        output_dir=raw.get("output_dir", "./data/output"),
        chunk_size=raw.get("chunk_size", 300_000),
        encoding=raw.get("encoding", "utf-8"),
        duckdb=duckdb,
    )


def _parse_sources(raw_sources: list[dict]) -> list[SourceConfig]:
    sources = []
    for s in raw_sources:
        sources.append(
            SourceConfig(
                name=s["name"],
                files=s["files"],
                format=_parse_format(s.get("format", "csv")),
                delimiter=s.get("delimiter", ","),
                has_header=s.get("has_header", True),
                encoding=s.get("encoding", "utf-8"),
                sheet=s.get("sheet"),
            )
        )
    return sources


def _parse_pipeline(raw_steps: list[dict]) -> list[PipelineStep]:
    steps = []
    for s in raw_steps:
        step = PipelineStep(step=s["step"])

        if "from" in s:
            step.from_ = s["from"]
            step.select = _parse_select(s.get("select"))
            step.filter = s.get("filter")

        elif "join" in s:
            j = s["join"]
            key_pairs = []
            for pair in j.get("keys", []):
                if isinstance(pair, dict):
                    key_pairs.append(JoinKey(left=pair["left"], right=pair["right"]))
                elif isinstance(pair, list):
                    key_pairs.append(JoinKey(left=pair[0], right=pair[1]))

            step.join = JoinConfig(
                type=JoinType(j["type"]),
                left=j["left"],
                right=j["right"],
                keys=key_pairs,
                conditions=j.get("conditions", []),
                filter=j.get("filter"),
            )

        elif "sql" in s:
            step.sql = s["sql"]

        steps.append(step)
    return steps


def _parse_select(raw_select: Any) -> Union[list[ColumnMapping], None]:
    if raw_select is None:
        return None
    mappings = []
    for item in raw_select:
        if isinstance(item, dict):
            mappings.append(
                ColumnMapping(source=item["source"], alias=item.get("alias"))
            )
        elif isinstance(item, str):
            mappings.append(ColumnMapping(source=item))
    return mappings


def _parse_outputs(raw_outputs: list[dict]) -> list[OutputConfig]:
    outputs = []
    for o in raw_outputs:
        outputs.append(
            OutputConfig(
                name=o["name"],
                from_=o["from"],
                path=o.get("path", ""),
                prefix=o.get("prefix", o.get("name", "output")),
                format=_parse_format(o.get("format", "xlsx")),
                chunk_size=o.get("chunk_size"),
            )
        )
    return outputs


def _parse_format(fmt: str) -> FileFormat:
    fmt = fmt.lower().strip()
    if fmt in ("csv",):
        return FileFormat.CSV
    if fmt in ("xlsx", "xls", "excel"):
        return FileFormat.XLSX
    if fmt in ("parquet", "pq"):
        return FileFormat.PARQUET
    raise ConfigError(f"Unsupported file format: {fmt}")


def _validate(config: PipelineConfig) -> None:
    """Validate the pipeline configuration before execution."""

    # 1. Source names must be unique
    source_names = [s.name for s in config.sources]
    seen = set()
    for name in source_names:
        if name in seen:
            raise ConfigError(f"Duplicate source name: {name}")
        seen.add(name)

    # 2. Pipeline step names must be unique
    step_names = [s.step for s in config.pipeline]
    seen = set()
    for name in step_names:
        if name in seen:
            raise ConfigError(f"Duplicate pipeline step name: {name}")
        seen.add(name)

    # 3. Collect all valid table references (sources + prior steps)
    valid_refs: set[str] = set(source_names)

    for step in config.pipeline:
        if step.from_ and step.from_ not in valid_refs:
            raise ConfigError(
                f"Step '{step.step}' references unknown source/step: {step.from_}"
            )

        if step.join:
            if step.join.left not in valid_refs:
                raise ConfigError(
                    f"Step '{step.step}' join.left references unknown table: {step.join.left}"
                )
            if step.join.right not in valid_refs:
                raise ConfigError(
                    f"Step '{step.step}' join.right references unknown table: {step.join.right}"
                )

        valid_refs.add(step.step)

    # 4. Output references must point to valid pipeline steps
    for out in config.outputs:
        if out.from_ not in valid_refs:
            raise ConfigError(
                f"Output '{out.name}' references unknown step: {out.from_}"
            )

    # 5. Validate glob patterns resolve to at least one file
    input_dir = Path(config.settings.input_dir)
    if not input_dir.exists():
        raise ConfigError(f"Input directory does not exist: {input_dir}")

    for src in config.sources:
        resolved = sorted(input_dir.glob(src.files))
        if not resolved:
            raise ConfigError(
                f"Source '{src.name}': glob pattern '{src.files}' "
                f"matched no files in {input_dir}"
            )
