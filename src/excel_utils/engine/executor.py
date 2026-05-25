"""DuckDB executor: manages connection, executes SQL, streams results."""

import logging
from pathlib import Path
from typing import Generator

import duckdb
import pandas as pd

from ..config.models import Settings

logger = logging.getLogger(__name__)


class Executor:
    """Manages a DuckDB connection and provides execution + streaming."""

    def __init__(self, settings: Settings):
        db_config = settings.duckdb
        if db_config.temp_directory:
            db_path = str(Path(db_config.temp_directory) / "pipeline.db")
            self.conn = duckdb.connect(db_path)
        else:
            self.conn = duckdb.connect(":memory:")

        self.conn.execute(f"SET memory_limit = '{db_config.memory_limit}'")
        self.conn.execute(f"SET threads = {db_config.threads}")
        self.conn.execute("SET enable_progress_bar = false")

    def execute_batch(self, statements: list[str]) -> None:
        for i, sql in enumerate(statements):
            logger.info("Executing statement %s/%s", i + 1, len(statements))
            try:
                self.conn.execute(sql)
            except Exception as e:
                preview = sql[:300].replace("\n", " ")
                raise RuntimeError(
                    f"SQL statement {i + 1} failed:\n  {preview}...\nError: {e}"
                ) from e

    def table_row_count(self, table_name: str) -> int:
        result = self.conn.execute(
            f"SELECT count(*) FROM {table_name}"
        ).fetchone()
        return int(result[0])

    def stream_table(
        self, table_name: str, batch_size: int
    ) -> Generator[pd.DataFrame, None, None]:
        total = self.table_row_count(table_name)
        if total == 0:
            empty_df = self.conn.execute(
                f"SELECT * FROM {table_name} LIMIT 0"
            ).fetchdf()
            yield empty_df
            return

        offset = 0
        while offset < total:
            df = self.conn.execute(
                f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}"
            ).fetchdf()
            yield df
            offset += batch_size

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
