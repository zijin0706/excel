"""Main entry point: parses config, runs the pipeline, and writes outputs."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Union

from .config.parser import ConfigError, parse
from .engine.executor import Executor
from .engine.sql_generator import SQLGenerator
from .output.writer import OutputWriter

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def run(config_path: Union[str, Path]) -> dict:
    config_path = Path(config_path)

    logger.info("Parsing config: %s", config_path)
    pipeline_config = parse(config_path)

    settings = pipeline_config.settings
    sql_gen = SQLGenerator(Path(settings.input_dir))

    logger.info("Generating SQL for %d sources and %d pipeline steps",
                len(pipeline_config.sources), len(pipeline_config.pipeline))
    statements = sql_gen.generate(pipeline_config)

    results = {}
    with Executor(settings) as executor:
        logger.info("Executing %d SQL statements", len(statements))
        executor.execute_batch(statements)

        writer = OutputWriter(Path(settings.output_dir))

        for out_cfg in pipeline_config.outputs:
            table = out_cfg.from_
            row_count = executor.table_row_count(table)
            logger.info("Output '%s': %s rows in table '%s'",
                        out_cfg.name, f"{row_count:,}", table)

            files = writer.write(executor, out_cfg, settings.chunk_size)
            results[out_cfg.name] = {
                "row_count": row_count,
                "files": [str(f) for f in files],
            }

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Excel Utils - Dynamic Excel/CSV matching pipeline"
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config.yaml",
        help="Path to YAML config file (default: config.yaml)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug output",
    )
    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        results = run(args.config)
    except ConfigError as e:
        logger.error("Configuration error: %s", e)
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        if args.verbose:
            raise
        sys.exit(1)

    print()
    print("=" * 60)
    print("Pipeline completed successfully")
    print("=" * 60)
    for name, info in results.items():
        print(f"\n  {name}:")
        print(f"    Rows: {info['row_count']:,}")
        print(f"    Files ({len(info['files'])}):")
        for f in info["files"]:
            print(f"      {f}")
    print()


if __name__ == "__main__":
    main()
