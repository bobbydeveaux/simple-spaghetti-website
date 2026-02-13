#!/usr/bin/env python3
"""
F1 Data Ingestion Script

This script provides convenient access to the F1 data ingestion services
for importing race and qualifying data from external sources.

Usage:
    python scripts/ingest_f1_data.py race 2024           # Ingest 2024 season races
    python scripts/ingest_f1_data.py qualifying 2024    # Ingest 2024 qualifying
    python scripts/ingest_f1_data.py season 2024        # Ingest complete 2024 season
    python scripts/ingest_f1_data.py validate 2024      # Validate 2024 data

Requirements:
    - Run from the f1-analytics/backend directory
    - Ensure database is running and accessible
    - Check that PYTHONPATH includes the backend directory
"""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent / "f1-analytics" / "backend"
sys.path.insert(0, str(backend_dir))

# Import and run the CLI
if __name__ == "__main__":
    try:
        from app.ingestion.cli import main
        main()
    except ImportError as e:
        print(f"Error importing CLI module: {e}")
        print(f"Make sure you're running from the correct directory and dependencies are installed")
        sys.exit(1)