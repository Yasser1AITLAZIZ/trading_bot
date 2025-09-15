"""Data ingestion module for loading historical trading data."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import structlog
from pydantic import ValidationError

from ..core.settings import get_settings
from ..core.types import OHLCVData
from ..core.utils import parse_timestamp, validate_symbol_format

logger = structlog.get_logger(__name__)


class DataIngestionError(Exception):
    """Exception raised during data ingestion."""
    pass


class DataIngestionService:
    """Service for ingesting historical trading data from various sources."""
    
    def __init__(self):
        """Initialize the data ingestion service."""
        self.settings = get_settings()
        self.supported_formats = self.settings.data.supported_formats
    
    def load_from_file(
        self,
        file_path: Union[str, Path],
        symbol: Optional[str] = None,
        **kwargs: Any,
    ) -> List[OHLCVData]:
        """Load OHLCV data from a file.
        
        Args:
            file_path: Path to the data file
            symbol: Trading symbol (if not specified in file)
            **kwargs: Additional parameters for file loading
            
        Returns:
            List of OHLCV data points
            
        Raises:
            DataIngestionError: If file cannot be loaded or data is invalid
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise DataIngestionError(f"File not found: {file_path}")
        
        file_extension = file_path.suffix.lower().lstrip(".")
        
        if file_extension not in self.supported_formats:
            raise DataIngestionError(
                f"Unsupported file format: {file_extension}. "
                f"Supported formats: {self.supported_formats}"
            )
        
        logger.info("Loading data from file", file_path=str(file_path), format=file_extension)
        
        try:
            if file_extension == "csv":
                return self._load_from_csv(file_path, symbol, **kwargs)
            elif file_extension == "json":
                return self._load_from_json(file_path, symbol, **kwargs)
            elif file_extension == "parquet":
                return self._load_from_parquet(file_path, symbol, **kwargs)
            else:
                raise DataIngestionError(f"Unsupported format: {file_extension}")
        
        except Exception as e:
            logger.error("Failed to load data from file", file_path=str(file_path), error=str(e))
            raise DataIngestionError(f"Failed to load data from {file_path}: {e}")
    
    def _load_from_csv(
        self,
        file_path: Path,
        symbol: Optional[str] = None,
        **kwargs: Any,
    ) -> List[OHLCVData]:
        """Load data from CSV file.
        
        Args:
            file_path: Path to CSV file
            symbol: Trading symbol
            **kwargs: Additional parameters for pandas.read_csv
            
        Returns:
            List of OHLCV data points
        """
        # Default CSV parameters
        csv_params = {
            "parse_dates": ["timestamp"],
            "date_parser": lambda x: parse_timestamp(x),
        }
        csv_params.update(kwargs)
        
        df = pd.read_csv(file_path, **csv_params)
        return self._dataframe_to_ohlcv(df, symbol)
    
    def _load_from_json(
        self,
        file_path: Path,
        symbol: Optional[str] = None,
        **kwargs: Any,
    ) -> List[OHLCVData]:
        """Load data from JSON file.
        
        Args:
            file_path: Path to JSON file
            symbol: Trading symbol
            **kwargs: Additional parameters for pandas.read_json
            
        Returns:
            List of OHLCV data points
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict) and "data" in data:
            df = pd.DataFrame(data["data"])
        else:
            raise DataIngestionError("Invalid JSON structure")
        
        # Parse timestamps
        if "timestamp" in df.columns:
            df["timestamp"] = df["timestamp"].apply(parse_timestamp)
        
        return self._dataframe_to_ohlcv(df, symbol)
    
    def _load_from_parquet(
        self,
        file_path: Path,
        symbol: Optional[str] = None,
        **kwargs: Any,
    ) -> List[OHLCVData]:
        """Load data from Parquet file.
        
        Args:
            file_path: Path to Parquet file
            symbol: Trading symbol
            **kwargs: Additional parameters for pandas.read_parquet
            
        Returns:
            List of OHLCV data points
        """
        df = pd.read_parquet(file_path, **kwargs)
        
        # Parse timestamps if needed
        if "timestamp" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = df["timestamp"].apply(parse_timestamp)
        
        return self._dataframe_to_ohlcv(df, symbol)
    
    def _dataframe_to_ohlcv(
        self,
        df: pd.DataFrame,
        symbol: Optional[str] = None,
    ) -> List[OHLCVData]:
        """Convert DataFrame to list of OHLCV data points.
        
        Args:
            df: DataFrame containing OHLCV data
            symbol: Trading symbol
            
        Returns:
            List of OHLCV data points
        """
        # Validate required columns
        required_columns = ["timestamp", "open", "high", "low", "close", "volume"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise DataIngestionError(f"Missing required columns: {missing_columns}")
        
        # Use symbol from data if not provided
        if symbol is None and "symbol" in df.columns:
            symbol = df["symbol"].iloc[0]
        elif symbol is None:
            raise DataIngestionError("Symbol must be provided either as parameter or in data")
        
        # Validate symbol format
        if not validate_symbol_format(symbol):
            raise DataIngestionError(f"Invalid symbol format: {symbol}")
        
        # Convert to OHLCV data points
        ohlcv_data = []
        
        for _, row in df.iterrows():
            try:
                ohlcv_point = OHLCVData(
                    timestamp=row["timestamp"],
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=row["volume"],
                    symbol=symbol,
                )
                ohlcv_data.append(ohlcv_point)
            
            except ValidationError as e:
                logger.warning("Skipping invalid data row", row_index=row.name, error=str(e))
                continue
        
        if not ohlcv_data:
            raise DataIngestionError("No valid data points found")
        
        # Sort by timestamp
        ohlcv_data.sort(key=lambda x: x.timestamp)
        
        logger.info(
            "Successfully loaded OHLCV data",
            symbol=symbol,
            data_points=len(ohlcv_data),
            start_time=ohlcv_data[0].timestamp,
            end_time=ohlcv_data[-1].timestamp,
        )
        
        return ohlcv_data
    
    def validate_data_quality(self, data: List[OHLCVData]) -> Dict[str, Any]:
        """Validate data quality and return quality metrics.
        
        Args:
            data: List of OHLCV data points
            
        Returns:
            Dictionary containing quality metrics
        """
        if not data:
            return {"valid": False, "error": "No data provided"}
        
        quality_metrics = {
            "valid": True,
            "total_points": len(data),
            "symbol": data[0].symbol,
            "start_time": data[0].timestamp,
            "end_time": data[-1].timestamp,
            "issues": [],
        }
        
        # Check for minimum data points
        if len(data) < self.settings.data.min_data_points:
            quality_metrics["valid"] = False
            quality_metrics["issues"].append(
                f"Insufficient data points: {len(data)} < {self.settings.data.min_data_points}"
            )
        
        # Check for data continuity
        missing_periods = 0
        for i in range(1, len(data)):
            time_diff = (data[i].timestamp - data[i-1].timestamp).total_seconds()
            if time_diff > 3600:  # More than 1 hour gap
                missing_periods += 1
        
        if missing_periods > 0:
            quality_metrics["issues"].append(f"Found {missing_periods} time gaps > 1 hour")
        
        # Check for duplicate timestamps
        timestamps = [point.timestamp for point in data]
        if len(timestamps) != len(set(timestamps)):
            quality_metrics["valid"] = False
            quality_metrics["issues"].append("Duplicate timestamps found")
        
        # Check for invalid prices
        invalid_prices = 0
        for point in data:
            if point.open <= 0 or point.high <= 0 or point.low <= 0 or point.close <= 0:
                invalid_prices += 1
            if point.high < point.low or point.high < point.open or point.high < point.close:
                invalid_prices += 1
            if point.low > point.open or point.low > point.close:
                invalid_prices += 1
        
        if invalid_prices > 0:
            quality_metrics["valid"] = False
            quality_metrics["issues"].append(f"Found {invalid_prices} invalid price points")
        
        # Check for negative volumes
        negative_volumes = sum(1 for point in data if point.volume < 0)
        if negative_volumes > 0:
            quality_metrics["valid"] = False
            quality_metrics["issues"].append(f"Found {negative_volumes} negative volume points")
        
        # Check data age
        latest_timestamp = max(point.timestamp for point in data)
        age_hours = (datetime.now(timezone.utc) - latest_timestamp).total_seconds() / 3600
        
        if age_hours > self.settings.data.max_data_age_hours:
            quality_metrics["issues"].append(
                f"Data is {age_hours:.1f} hours old (max: {self.settings.data.max_data_age_hours})"
            )
        
        quality_metrics["age_hours"] = age_hours
        quality_metrics["missing_periods"] = missing_periods
        quality_metrics["invalid_prices"] = invalid_prices
        quality_metrics["negative_volumes"] = negative_volumes
        
        return quality_metrics
    
    def save_data(
        self,
        data: List[OHLCVData],
        file_path: Union[str, Path],
        format: str = "csv",
    ) -> None:
        """Save OHLCV data to a file.
        
        Args:
            data: List of OHLCV data points
            file_path: Path to save the data
            format: File format (csv, json, parquet)
        """
        file_path = Path(file_path)
        
        if format not in self.supported_formats:
            raise DataIngestionError(f"Unsupported format: {format}")
        
        # Convert to DataFrame
        df_data = []
        for point in data:
            df_data.append({
                "timestamp": point.timestamp,
                "open": float(point.open),
                "high": float(point.high),
                "low": float(point.low),
                "close": float(point.close),
                "volume": float(point.volume),
                "symbol": point.symbol,
            })
        
        df = pd.DataFrame(df_data)
        
        # Save based on format
        if format == "csv":
            df.to_csv(file_path, index=False)
        elif format == "json":
            df.to_json(file_path, orient="records", date_format="iso")
        elif format == "parquet":
            df.to_parquet(file_path, index=False)
        
        logger.info("Data saved successfully", file_path=str(file_path), format=format, records=len(data))
