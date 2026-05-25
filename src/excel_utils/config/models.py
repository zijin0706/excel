"""Data models for the pipeline configuration."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FileFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"
    PARQUET = "parquet"


class JoinType(str, Enum):
    INNER = "inner"
    LEFT = "left"
    RIGHT = "right"
    ANTI_LEFT = "anti_left"
    ANTI_RIGHT = "anti_right"


@dataclass
class DuckDbSettings:
    memory_limit: str = "8GB"
    threads: int = 4
    temp_directory: Optional[str] = None


@dataclass
class Settings:
    input_dir: str
    output_dir: str
    chunk_size: int = 300_000
    encoding: str = "utf-8"
    duckdb: DuckDbSettings = field(default_factory=DuckDbSettings)


@dataclass
class ColumnMapping:
    source: str
    alias: Optional[str] = None


@dataclass
class SourceConfig:
    name: str
    files: str
    format: FileFormat
    delimiter: str = ","
    has_header: bool = True
    encoding: str = "utf-8"
    sheet: Optional[str] = None


@dataclass
class JoinKey:
    left: str
    right: str


@dataclass
class JoinConfig:
    type: JoinType
    left: str
    right: str
    keys: list = field(default_factory=list)  # list[JoinKey]
    conditions: list[str] = field(default_factory=list)
    filter: Optional[str] = None


@dataclass
class PipelineStep:
    step: str
    from_: Optional[str] = None
    select: Optional[list] = None  # list[ColumnMapping]
    filter: Optional[str] = None
    join: Optional[JoinConfig] = None
    sql: Optional[str] = None  # raw DuckDB SQL for complex operations


@dataclass
class OutputConfig:
    name: str
    from_: str
    path: str
    prefix: str
    format: FileFormat = FileFormat.XLSX
    chunk_size: Optional[int] = None


@dataclass
class PipelineConfig:
    version: int
    settings: Settings
    sources: list[SourceConfig]  # list[SourceConfig]
    pipeline: list[PipelineStep]  # list[PipelineStep]
    outputs: list[OutputConfig]  # list[OutputConfig]
