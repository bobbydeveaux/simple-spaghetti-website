#!/bin/bash
"""
Test runner script for weather ingestion functionality.

This script runs all weather ingestion tests with proper configuration.
"""

set -e

# Get the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# Set up environment
export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"
export F1_WEATHER_API_KEY="test_key_12345"
export F1_WEATHER_BASE_URL="https://api.openweathermap.org/data/2.5"

# Change to the test directory
cd "$SCRIPT_DIR"

echo "Running weather ingestion integration tests..."
echo "Test directory: $SCRIPT_DIR"
echo "Backend directory: $BACKEND_DIR"
echo ""

# Run tests with pytest
python -m pytest tests/ -v --tb=short --disable-warnings

echo ""
echo "✅ All weather ingestion tests completed!"