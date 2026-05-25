"""Generate DuckDB SQL statements from a PipelineConfig."""

from pathlib import Path

from ..config.models import (
    FileFormat,
    JoinType,
    PipelineConfig,
    PipelineStep,
    SourceConfig,
)


class SQLGenerator:
    """Converts a validated PipelineConfig into ordered DuckDB SQL statements."""

    def __init__(self, input_dir: Path):
        self.input_dir = input_dir

    def generate(self, config: PipelineConfig) -> list[str]:
        statements: list[str] = []

        for src in config.sources:
            statements.append(self._load_source(src))

        for step in config.pipeline:
            if step.from_ is not None:
                statements.append(self._source_step(step))
            elif step.join is not None:
                statements.append(self._join_step(step))
            elif step.sql is not None:
                statements.append(self._sql_step(step))

        return statements

    def _load_source(self, src: SourceConfig) -> str:
        resolved = sorted(self.input_dir.glob(src.files))
        if not resolved:
            raise ValueError(f"No files matched for source '{src.name}': {src.files}")

        if src.format == FileFormat.CSV:
            paths = ", ".join(f"'{p}'" for p in resolved)
            header_str = "true" if src.has_header else "false"
            return (
                f"CREATE OR REPLACE TABLE {src.name} AS\n"
                f"SELECT * FROM read_csv_auto(\n"
                f"  [{paths}],\n"
                f"  header={header_str},\n"
                f"  delim='{src.delimiter}'\n"
                f")"
            )

        elif src.format == FileFormat.XLSX:
            sheet = src.sheet or "Sheet1"
            paths = ", ".join(f"'{p}'" for p in resolved)
            return (
                f"INSTALL spatial;\n"
                f"LOAD spatial;\n"
                f"CREATE OR REPLACE TABLE {src.name} AS\n"
                f"SELECT * FROM st_read(\n"
                f"  [{paths}],\n"
                f"  layer='{sheet}'\n"
                f")"
            )

        elif src.format == FileFormat.PARQUET:
            paths = ", ".join(f"'{p}'" for p in resolved)
            return (
                f"CREATE OR REPLACE TABLE {src.name} AS\n"
                f"SELECT * FROM read_parquet([{paths}])"
            )

        raise ValueError(f"Unsupported format: {src.format}")

    def _source_step(self, step: PipelineStep) -> str:
        if step.select:
            cols = []
            for cm in step.select:
                if cm.alias:
                    cols.append(f"{cm.source} AS {cm.alias}")
                else:
                    cols.append(cm.source)
            select_clause = ", ".join(cols)
        else:
            select_clause = "*"

        sql = f"CREATE OR REPLACE TABLE {step.step} AS\nSELECT {select_clause}\nFROM {step.from_}"
        if step.filter:
            sql += f"\nWHERE {step.filter}"
        return sql

    def _join_step(self, step: PipelineStep) -> str:
        jc = step.join
        step_name = step.step

        if jc.type in (JoinType.ANTI_LEFT, JoinType.ANTI_RIGHT):
            return self._anti_join_sql(step_name, jc)

        join_kw = jc.type.value.upper()
        on_parts = [f"L.{k.left} = R.{k.right}" for k in jc.keys]
        for cond in jc.conditions:
            on_parts.append(f"({cond})")
        on_clause = "\n  AND ".join(on_parts)

        sql = (
            f"CREATE OR REPLACE TABLE {step_name} AS\n"
            f"SELECT *\n"
            f"FROM {jc.left} L\n"
            f"{join_kw} JOIN {jc.right} R\n"
            f"ON {on_clause}"
        )

        if jc.filter:
            sql += f"\nWHERE {jc.filter}"
        return sql

    def _anti_join_sql(self, step_name: str, jc) -> str:
        if jc.type == JoinType.ANTI_LEFT:
            source = jc.left
            other = jc.right
            key_pairs = [(k.left, k.right) for k in jc.keys]
        else:
            source = jc.right
            other = jc.left
            key_pairs = [(k.right, k.left) for k in jc.keys]

        where_clauses = " AND ".join(
            f"{source}.{s_col} = {other}.{o_col}" for s_col, o_col in key_pairs
        )

        sql = (
            f"CREATE OR REPLACE TABLE {step_name} AS\n"
            f"SELECT {source}.*\n"
            f"FROM {source}\n"
            f"WHERE NOT EXISTS (\n"
            f"  SELECT 1 FROM {other}\n"
            f"  WHERE {where_clauses}\n"
            f")"
        )
        return sql

    def _sql_step(self, step: PipelineStep) -> str:
        return f"CREATE OR REPLACE TABLE {step.step} AS\n{step.sql}"
