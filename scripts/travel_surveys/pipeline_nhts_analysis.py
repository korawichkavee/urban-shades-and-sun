# ABOUTME: Master pipeline script for NHTS travel survey analysis.
# ABOUTME: Runs extraction, UTCI annotation, and visualization in sequence.

import subprocess
import sys
from pathlib import Path
import argparse
import logging
from datetime import datetime


def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def run_command(cmd, logger, description):
    """Run a command and handle errors."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Step: {description}")
    logger.info(f"Command: {' '.join(cmd)}")
    logger.info(f"{'='*60}\n")

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        logger.error(f"Step failed with exit code {result.returncode}")
        return False

    logger.info(f"\nStep completed successfully")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Full pipeline for NHTS travel survey analysis'
    )
    parser.add_argument(
        '--survey',
        type=str,
        default='nhts_2017',
        help='Survey name from config (default: nhts_2017)'
    )
    parser.add_argument(
        '--skip-extraction',
        action='store_true',
        help='Skip extraction step (use existing standardized file)'
    )
    parser.add_argument(
        '--skip-utci',
        action='store_true',
        help='Skip UTCI annotation step (use existing UTCI file)'
    )
    parser.add_argument(
        '--sample',
        type=int,
        default=None,
        help='Process only first N trips (for testing)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=20,
        help='Number of parallel workers for UTCI fetching (default: 20)'
    )

    args = parser.parse_args()
    logger = setup_logging()

    project_root = Path(__file__).parent.parent.parent
    python_exe = sys.executable

    logger.info("="*60)
    logger.info("NHTS Travel Survey Analysis Pipeline")
    logger.info(f"Survey: {args.survey}")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)

    # Step 1: Extract and standardize
    if not args.skip_extraction:
        extract_script = project_root / "scripts/travel_surveys/extract_and_standardize.py"
        extract_cmd = [python_exe, str(extract_script), "--survey", args.survey]
        if args.sample:
            extract_cmd.extend(["--sample", str(args.sample)])

        if not run_command(extract_cmd, logger, "Extract and standardize trip data"):
            logger.error("Pipeline failed at extraction step")
            return 1
    else:
        logger.info("Skipping extraction step (--skip-extraction)")

    # Step 2: Add UTCI data
    if not args.skip_utci:
        standardized_file = f"data/transit_surveys/processed/{args.survey}_standardized.csv"
        add_utci_script = project_root / "scripts/travel_surveys/add_utci.py"
        utci_cmd = [
            python_exe, str(add_utci_script),
            "--input", standardized_file,
            "--workers", str(args.workers)
        ]
        if args.sample:
            utci_cmd.extend(["--sample", str(args.sample)])

        if not run_command(utci_cmd, logger, "Add UTCI thermal comfort data"):
            logger.error("Pipeline failed at UTCI annotation step")
            return 1
    else:
        logger.info("Skipping UTCI annotation step (--skip-utci)")

    # Step 3: Create visualizations
    utci_file = f"data/transit_surveys/processed/{args.survey}_standardized_with_utci.csv"
    viz_script = project_root / "scripts/travel_surveys/visualize_pedestrian_vs_temperature.py"
    viz_cmd = [
        python_exe, str(viz_script),
        "--input", utci_file,
        "--output-dir", "outputs/travel_surveys"
    ]

    if not run_command(viz_cmd, logger, "Create visualizations"):
        logger.error("Pipeline failed at visualization step")
        return 1

    # Success!
    logger.info("\n" + "="*60)
    logger.info("PIPELINE COMPLETED SUCCESSFULLY")
    logger.info(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    logger.info("\nOutputs:")
    logger.info(f"  Standardized data: data/transit_surveys/processed/{args.survey}_standardized.csv")
    logger.info(f"  With UTCI data: data/transit_surveys/processed/{args.survey}_standardized_with_utci.csv")
    logger.info(f"  Visualizations: outputs/travel_surveys/")
    logger.info("="*60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
