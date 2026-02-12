"""
Command-line interface for F1 data ingestion services.

This module provides CLI commands to run data ingestion for races and qualifying
sessions, with options for different seasons and specific rounds.
"""

import asyncio
import argparse
import logging
from typing import Optional
from datetime import datetime

from app.database import db_manager
from app.config import settings
from .race_ingestion import RaceIngestionService
from .qualifying_ingestion import QualifyingIngestionService


# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.app.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def ingest_race_data(
    season: int,
    race_round: Optional[int] = None,
    include_results: bool = True
) -> None:
    """
    Ingest race data for specified season/round.

    Args:
        season: F1 season year
        race_round: Optional specific race round
        include_results: Whether to include race results
    """
    logger.info(f"Starting race ingestion for season {season}")

    race_service = RaceIngestionService()

    try:
        with db_manager.get_session() as session:
            results = await race_service.ingest_data(
                session=session,
                season=season,
                race_round=race_round,
                include_results=include_results
            )

            print(f"\nRace Ingestion Results for {season}:")
            print(f"  Races processed: {results['races_processed']}")
            print(f"  Races created: {results['races_created']}")
            print(f"  Races updated: {results['races_updated']}")

            if include_results:
                print(f"  Results processed: {results['results_processed']}")
                print(f"  Results created: {results['results_created']}")

            print(f"  Circuits created: {results['circuits_created']}")
            print(f"  Drivers created: {results['drivers_created']}")
            print(f"  Teams created: {results['teams_created']}")
            print(f"  Duration: {results['duration_seconds']:.2f} seconds")

            if results['errors']:
                print(f"\nErrors encountered:")
                for error in results['errors']:
                    print(f"  - {error}")

    except Exception as e:
        logger.error(f"Race ingestion failed: {e}")
        raise


async def ingest_qualifying_data(
    season: int,
    race_round: Optional[int] = None
) -> None:
    """
    Ingest qualifying data for specified season/round.

    Args:
        season: F1 season year
        race_round: Optional specific race round
    """
    logger.info(f"Starting qualifying ingestion for season {season}")

    qualifying_service = QualifyingIngestionService()

    try:
        with db_manager.get_session() as session:
            results = await qualifying_service.ingest_data(
                session=session,
                season=season,
                race_round=race_round
            )

            print(f"\nQualifying Ingestion Results for {season}:")
            print(f"  Races processed: {results['races_processed']}")
            print(f"  Qualifying results processed: {results['qualifying_results_processed']}")
            print(f"  Qualifying results created: {results['qualifying_results_created']}")
            print(f"  Qualifying results updated: {results['qualifying_results_updated']}")
            print(f"  Drivers created: {results['drivers_created']}")
            print(f"  Duration: {results['duration_seconds']:.2f} seconds")

            if results['errors']:
                print(f"\nErrors encountered:")
                for error in results['errors']:
                    print(f"  - {error}")

    except Exception as e:
        logger.error(f"Qualifying ingestion failed: {e}")
        raise


async def ingest_full_season(
    season: int,
    include_qualifying: bool = True
) -> None:
    """
    Ingest complete season data (races and optionally qualifying).

    Args:
        season: F1 season year
        include_qualifying: Whether to include qualifying data
    """
    logger.info(f"Starting full season ingestion for {season}")

    try:
        # First ingest race data
        await ingest_race_data(season=season, include_results=True)

        if include_qualifying:
            # Then ingest qualifying data
            await ingest_qualifying_data(season=season)

        print(f"\nFull season ingestion completed for {season}")

    except Exception as e:
        logger.error(f"Full season ingestion failed: {e}")
        raise


async def validate_data(
    season: int,
    race_round: Optional[int] = None
) -> None:
    """
    Validate ingested data for consistency.

    Args:
        season: F1 season year
        race_round: Optional specific race round
    """
    logger.info(f"Starting data validation for season {season}")

    qualifying_service = QualifyingIngestionService()

    try:
        with db_manager.get_session() as session:
            validation_results = await qualifying_service.validate_qualifying_data(
                session=session,
                season=season,
                race_round=race_round
            )

            print(f"\nData Validation Results for {season}:")
            print(f"  Races validated: {validation_results['races_validated']}")
            print(f"  Issues found: {len(validation_results['issues'])}")
            print(f"  Warnings: {len(validation_results['warnings'])}")

            if validation_results['issues']:
                print(f"\nIssues found:")
                for issue_group in validation_results['issues']:
                    print(f"  Race: {issue_group['race_name']}")
                    for issue in issue_group['issues']:
                        print(f"    - {issue}")

            if validation_results['warnings']:
                print(f"\nWarnings:")
                for warning in validation_results['warnings']:
                    print(f"  - {warning}")

    except Exception as e:
        logger.error(f"Data validation failed: {e}")
        raise


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='F1 Data Ingestion CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Race ingestion command
    race_parser = subparsers.add_parser('race', help='Ingest race data')
    race_parser.add_argument('season', type=int, help='F1 season year')
    race_parser.add_argument('--round', type=int, help='Specific race round')
    race_parser.add_argument('--no-results', action='store_true', help='Skip race results')

    # Qualifying ingestion command
    qualifying_parser = subparsers.add_parser('qualifying', help='Ingest qualifying data')
    qualifying_parser.add_argument('season', type=int, help='F1 season year')
    qualifying_parser.add_argument('--round', type=int, help='Specific race round')

    # Full season command
    season_parser = subparsers.add_parser('season', help='Ingest full season data')
    season_parser.add_argument('season', type=int, help='F1 season year')
    season_parser.add_argument('--no-qualifying', action='store_true', help='Skip qualifying data')

    # Validation command
    validate_parser = subparsers.add_parser('validate', help='Validate ingested data')
    validate_parser.add_argument('season', type=int, help='F1 season year')
    validate_parser.add_argument('--round', type=int, help='Specific race round')

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Run the appropriate command
    try:
        if args.command == 'race':
            asyncio.run(ingest_race_data(
                season=args.season,
                race_round=args.round,
                include_results=not args.no_results
            ))
        elif args.command == 'qualifying':
            asyncio.run(ingest_qualifying_data(
                season=args.season,
                race_round=args.round
            ))
        elif args.command == 'season':
            asyncio.run(ingest_full_season(
                season=args.season,
                include_qualifying=not args.no_qualifying
            ))
        elif args.command == 'validate':
            asyncio.run(validate_data(
                season=args.season,
                race_round=args.round
            ))

        print("\nOperation completed successfully!")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"\nOperation failed: {e}")
        logger.exception("CLI operation failed")


if __name__ == '__main__':
    main()