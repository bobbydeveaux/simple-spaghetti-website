#!/usr/bin/env python3
"""
Weather Data Ingestion CLI Script

This script provides command-line interfaces for weather data ingestion operations
including historical backfilling, current weather updates, and coordinate validation.

Usage:
    python ingest_weather.py backfill [--season 2024] [--limit 10]
    python ingest_weather.py update-upcoming [--days 7]
    python ingest_weather.py validate-circuits
    python ingest_weather.py ingest-race --race-id 123
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db_session
from data_ingestion.services.weather_service import create_weather_service


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('weather_ingestion.log')
    ]
)
logger = logging.getLogger(__name__)


async def backfill_historical_weather(season_year: int = None, limit: int = None):
    """Backfill historical weather data for races without weather data."""
    logger.info(f"Starting historical weather backfill...")
    logger.info(f"Season: {season_year or 'all'}, Limit: {limit or 'unlimited'}")

    try:
        # Create service with database session
        db_session = next(get_db_session())
        weather_service = create_weather_service(db_session=db_session)

        # Run backfill
        results = await weather_service.backfill_historical_weather(
            season_year=season_year,
            limit=limit
        )

        # Print results
        print(f"\n=== Historical Weather Backfill Results ===")
        print(f"Total races processed: {results['total_races']}")
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")
        print(f"Skipped: {results['skipped']}")

        if results['errors']:
            print(f"\nErrors encountered:")
            for error in results['errors']:
                print(f"  - {error}")

        success_rate = (results['successful'] / results['total_races'] * 100) if results['total_races'] > 0 else 0
        print(f"\nSuccess rate: {success_rate:.1f}%")

    except Exception as e:
        logger.error(f"Error during backfill: {e}")
        print(f"Error: {e}")
        sys.exit(1)

    finally:
        if 'db_session' in locals():
            db_session.close()


async def update_upcoming_weather(days_ahead: int = 7):
    """Update weather data for upcoming races."""
    logger.info(f"Updating weather for upcoming races in next {days_ahead} days...")

    try:
        # Create service with database session
        db_session = next(get_db_session())
        weather_service = create_weather_service(db_session=db_session)

        # Run update
        results = await weather_service.update_upcoming_race_weather(days_ahead=days_ahead)

        # Print results
        print(f"\n=== Upcoming Race Weather Update Results ===")
        print(f"Total races processed: {results['total_races']}")
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")

        if results['errors']:
            print(f"\nErrors encountered:")
            for error in results['errors']:
                print(f"  - {error}")

        success_rate = (results['successful'] / results['total_races'] * 100) if results['total_races'] > 0 else 0
        print(f"\nSuccess rate: {success_rate:.1f}%")

    except Exception as e:
        logger.error(f"Error during upcoming weather update: {e}")
        print(f"Error: {e}")
        sys.exit(1)

    finally:
        if 'db_session' in locals():
            db_session.close()


async def validate_circuit_coordinates():
    """Validate that all circuits have proper coordinates."""
    logger.info("Validating circuit coordinates...")

    try:
        # Create service with database session
        db_session = next(get_db_session())
        weather_service = create_weather_service(db_session=db_session)

        # Run validation
        results = await weather_service.validate_circuit_coordinates()

        # Print results
        print(f"\n=== Circuit Coordinate Validation Results ===")
        print(f"Total circuits: {results['total_circuits']}")
        print(f"With valid coordinates: {results['with_coordinates']}")
        print(f"Missing coordinates: {results['missing_coordinates']}")
        print(f"Invalid coordinates: {results['invalid_coordinates']}")

        if results['circuits_missing_coords']:
            print(f"\nCircuits missing coordinates:")
            for circuit in results['circuits_missing_coords']:
                print(f"  - {circuit['name']} ({circuit['country']}) [ID: {circuit['circuit_id']}]")

        if results['circuits_invalid_coords']:
            print(f"\nCircuits with invalid coordinates:")
            for circuit in results['circuits_invalid_coords']:
                print(f"  - {circuit['name']}: {circuit['latitude']}, {circuit['longitude']} [ID: {circuit['circuit_id']}]")

        completion_rate = (results['with_coordinates'] / results['total_circuits'] * 100) if results['total_circuits'] > 0 else 0
        print(f"\nCoordinate completion rate: {completion_rate:.1f}%")

    except Exception as e:
        logger.error(f"Error during validation: {e}")
        print(f"Error: {e}")
        sys.exit(1)

    finally:
        if 'db_session' in locals():
            db_session.close()


async def ingest_race_weather(race_id: int):
    """Ingest weather data for a specific race."""
    logger.info(f"Ingesting weather data for race {race_id}...")

    try:
        # Create service with database session
        db_session = next(get_db_session())
        weather_service = create_weather_service(db_session=db_session)

        # Run ingestion for specific race
        success = await weather_service.ingest_weather_for_race(race_id)

        # Print results
        print(f"\n=== Race Weather Ingestion Results ===")
        print(f"Race ID: {race_id}")
        print(f"Status: {'Success' if success else 'Failed'}")

        if not success:
            print("Check logs for detailed error information.")

    except Exception as e:
        logger.error(f"Error during race weather ingestion: {e}")
        print(f"Error: {e}")
        sys.exit(1)

    finally:
        if 'db_session' in locals():
            db_session.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="F1 Analytics Weather Data Ingestion CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s backfill --season 2024 --limit 10
  %(prog)s update-upcoming --days 7
  %(prog)s validate-circuits
  %(prog)s ingest-race --race-id 123
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Backfill command
    backfill_parser = subparsers.add_parser(
        'backfill',
        help='Backfill historical weather data'
    )
    backfill_parser.add_argument(
        '--season',
        type=int,
        help='Specific season year to backfill (default: all seasons)'
    )
    backfill_parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of races to process (default: unlimited)'
    )

    # Update upcoming command
    update_parser = subparsers.add_parser(
        'update-upcoming',
        help='Update weather for upcoming races'
    )
    update_parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days ahead to look for races (default: 7)'
    )

    # Validate circuits command
    subparsers.add_parser(
        'validate-circuits',
        help='Validate circuit coordinates'
    )

    # Ingest specific race command
    race_parser = subparsers.add_parser(
        'ingest-race',
        help='Ingest weather for a specific race'
    )
    race_parser.add_argument(
        '--race-id',
        type=int,
        required=True,
        help='Race ID to ingest weather for'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Run appropriate command
    try:
        if args.command == 'backfill':
            asyncio.run(backfill_historical_weather(
                season_year=args.season,
                limit=args.limit
            ))

        elif args.command == 'update-upcoming':
            asyncio.run(update_upcoming_weather(days_ahead=args.days))

        elif args.command == 'validate-circuits':
            asyncio.run(validate_circuit_coordinates())

        elif args.command == 'ingest-race':
            asyncio.run(ingest_race_weather(race_id=args.race_id))

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()