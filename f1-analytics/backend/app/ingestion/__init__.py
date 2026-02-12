"""
Data ingestion module for F1 Prediction Analytics.

This module provides data ingestion capabilities for F1 racing data,
including race results, qualifying results, and related metadata from
the official Ergast API and other sources.
"""

from .base import BaseIngestionService
from .race_ingestion import RaceIngestionService
from .qualifying_ingestion import QualifyingIngestionService

__all__ = [
    "BaseIngestionService",
    "RaceIngestionService",
    "QualifyingIngestionService"
]