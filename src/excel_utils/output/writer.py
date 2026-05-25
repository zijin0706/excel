"""Output writer: stream DuckDB tables to chunked Excel/CSV files."""

import logging
from pathlib import Path

import pandas as pd

from ..config.models import FileFormat, OutputConfig
from ..engine.executor import Executor

logger = logging.getLogger(__name__)


class OutputWriter:
    """Writes DuckDB table results to chunked output files."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def write(
        self,
        executor: Executor,
        config: OutputConfig,
        default_chunk_size: int,
    ) -> list[Path]:
        table_name = config.from_
        chunk_size = config.chunk_size or default_chunk_size
        out_dir = self.output_dir / config.path
        out_dir.mkdir(parents=True, exist_ok=True)

        files_written: list[Path] = []

        for idx, df in enumerate(
            executor.stream_table(table_name, chunk_size), start=1
        ):
            suffix = config.format.value
            filepath = out_dir / f"{config.prefix}_{idx:03d}.{suffix}"
            self._write_dataframe(df, filepath, config)
            files_written.append(filepath)
            logger.info("Wrote %s rows to %s", len(df), filepath)

        if not files_written:
            suffix = config.format.value
            filepath = out_dir / f"{config.prefix}_001.{suffix}"
            empty_df = executor.conn.execute(
                f"SELECT * FROM {table_name} LIMIT 0"
            ).fetchdf()
            self._write_dataframe(empty_df, filepath, config)
            files_written.append(filepath)

        return files_written

    def _write_dataframe(
        self, df: pd.DataFrame, filepath: Path, config: OutputConfig
    ) -> None:
        if config.format == FileFormat.XLSX:
            df.to_excel(filepath, index=False, header=True, engine="openpyxl")
        elif config.format == FileFormat.CSV:
            df.to_csv(filepath, index=False, header=True)
        elif config.format == FileFormat.PARQUET:
            df.to_parquet(filepath, index=False)
