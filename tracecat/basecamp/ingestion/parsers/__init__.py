"""File parsers for Base Camp OS ingestion."""

from tracecat.basecamp.ingestion.parsers.base import BaseParser
from tracecat.basecamp.ingestion.parsers.csv_parser import CSVParser
from tracecat.basecamp.ingestion.parsers.excel_parser import ExcelParser
from tracecat.basecamp.ingestion.parsers.json_parser import JSONParser

__all__ = ["BaseParser", "CSVParser", "ExcelParser", "JSONParser"]
