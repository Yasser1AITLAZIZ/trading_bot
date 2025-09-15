"""Caching module for data and computed features."""

import json
import pickle
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import structlog

from ..core.settings import get_settings
from ..core.types import OHLCVData, TechnicalIndicators
from ..core.utils import create_data_hash

logger = structlog.get_logger(__name__)


class CacheError(Exception):
    """Exception raised during cache operations."""
    pass


class DataCache:
    """Cache for storing and retrieving data and computed features."""
    
    def __init__(self, cache_directory: Optional[Union[str, Path]] = None):
        """Initialize the data cache.
        
        Args:
            cache_directory: Directory for cache files (defaults to settings)
        """
        self.settings = get_settings()
        self.cache_dir = Path(cache_directory or self.settings.data.cache_directory)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = self.settings.data.cache_ttl_seconds
    
    def get_ohlcv_data(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[List[OHLCVData]]:
        """Get cached OHLCV data.
        
        Args:
            symbol: Trading symbol
            start_date: Start date
            end_date: End date
            
        Returns:
            Cached OHLCV data or None if not found/expired
        """
        cache_key = self._generate_ohlcv_cache_key(symbol, start_date, end_date)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "rb") as f:
                cache_data = pickle.load(f)
            
            # Check if cache is expired
            if self._is_cache_expired(cache_data.get("timestamp")):
                self._remove_cache_file(cache_file)
                return None
            
            logger.debug("Cache hit for OHLCV data", symbol=symbol, cache_key=cache_key)
            return cache_data["data"]
        
        except Exception as e:
            logger.warning("Failed to load cached OHLCV data", error=str(e), cache_file=str(cache_file))
            self._remove_cache_file(cache_file)
            return None
    
    def set_ohlcv_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        data: List[OHLCVData],
    ) -> None:
        """Cache OHLCV data.
        
        Args:
            symbol: Trading symbol
            start_date: Start date
            end_date: End date
            data: OHLCV data to cache
        """
        cache_key = self._generate_ohlcv_cache_key(symbol, start_date, end_date)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            cache_data = {
                "timestamp": datetime.now(timezone.utc),
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
                "data": data,
                "data_count": len(data),
            }
            
            with open(cache_file, "wb") as f:
                pickle.dump(cache_data, f)
            
            logger.debug("Cached OHLCV data", symbol=symbol, cache_key=cache_key, data_count=len(data))
        
        except Exception as e:
            logger.error("Failed to cache OHLCV data", error=str(e), cache_file=str(cache_file))
            raise CacheError(f"Failed to cache OHLCV data: {e}")
    
    def get_technical_indicators(self, data_hash: str) -> Optional[TechnicalIndicators]:
        """Get cached technical indicators.
        
        Args:
            data_hash: Hash of the input data
            
        Returns:
            Cached technical indicators or None if not found/expired
        """
        cache_file = self.cache_dir / f"indicators_{data_hash}.pkl"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "rb") as f:
                cache_data = pickle.load(f)
            
            # Check if cache is expired
            if self._is_cache_expired(cache_data.get("timestamp")):
                self._remove_cache_file(cache_file)
                return None
            
            logger.debug("Cache hit for technical indicators", data_hash=data_hash)
            return cache_data["indicators"]
        
        except Exception as e:
            logger.warning("Failed to load cached technical indicators", error=str(e), cache_file=str(cache_file))
            self._remove_cache_file(cache_file)
            return None
    
    def set_technical_indicators(self, data_hash: str, indicators: TechnicalIndicators) -> None:
        """Cache technical indicators.
        
        Args:
            data_hash: Hash of the input data
            indicators: Technical indicators to cache
        """
        cache_file = self.cache_dir / f"indicators_{data_hash}.pkl"
        
        try:
            cache_data = {
                "timestamp": datetime.now(timezone.utc),
                "data_hash": data_hash,
                "indicators": indicators,
            }
            
            with open(cache_file, "wb") as f:
                pickle.dump(cache_data, f)
            
            logger.debug("Cached technical indicators", data_hash=data_hash)
        
        except Exception as e:
            logger.error("Failed to cache technical indicators", error=str(e), cache_file=str(cache_file))
            raise CacheError(f"Failed to cache technical indicators: {e}")
    
    def get_market_signals(self, data_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached market signals.
        
        Args:
            data_hash: Hash of the input data
            
        Returns:
            Cached market signals or None if not found/expired
        """
        cache_file = self.cache_dir / f"signals_{data_hash}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            # Check if cache is expired
            cache_timestamp = datetime.fromisoformat(cache_data.get("timestamp", "").replace("Z", "+00:00"))
            if self._is_cache_expired(cache_timestamp):
                self._remove_cache_file(cache_file)
                return None
            
            logger.debug("Cache hit for market signals", data_hash=data_hash)
            return cache_data["signals"]
        
        except Exception as e:
            logger.warning("Failed to load cached market signals", error=str(e), cache_file=str(cache_file))
            self._remove_cache_file(cache_file)
            return None
    
    def set_market_signals(self, data_hash: str, signals: Dict[str, Any]) -> None:
        """Cache market signals.
        
        Args:
            data_hash: Hash of the input data
            signals: Market signals to cache
        """
        cache_file = self.cache_dir / f"signals_{data_hash}.json"
        
        try:
            cache_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data_hash": data_hash,
                "signals": signals,
            }
            
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, default=str)
            
            logger.debug("Cached market signals", data_hash=data_hash)
        
        except Exception as e:
            logger.error("Failed to cache market signals", error=str(e), cache_file=str(cache_file))
            raise CacheError(f"Failed to cache market signals: {e}")
    
    def clear_expired_cache(self) -> int:
        """Clear expired cache files.
        
        Returns:
            Number of files removed
        """
        removed_count = 0
        
        for cache_file in self.cache_dir.glob("*"):
            try:
                if cache_file.suffix == ".pkl":
                    with open(cache_file, "rb") as f:
                        cache_data = pickle.load(f)
                    cache_timestamp = cache_data.get("timestamp")
                elif cache_file.suffix == ".json":
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cache_data = json.load(f)
                    cache_timestamp_str = cache_data.get("timestamp", "")
                    if cache_timestamp_str:
                        cache_timestamp = datetime.fromisoformat(cache_timestamp_str.replace("Z", "+00:00"))
                    else:
                        cache_timestamp = None
                else:
                    continue
                
                if cache_timestamp and self._is_cache_expired(cache_timestamp):
                    self._remove_cache_file(cache_file)
                    removed_count += 1
            
            except Exception as e:
                logger.warning("Failed to check cache file", cache_file=str(cache_file), error=str(e))
                # Remove corrupted cache files
                self._remove_cache_file(cache_file)
                removed_count += 1
        
        if removed_count > 0:
            logger.info("Cleared expired cache files", removed_count=removed_count)
        
        return removed_count
    
    def clear_all_cache(self) -> int:
        """Clear all cache files.
        
        Returns:
            Number of files removed
        """
        removed_count = 0
        
        for cache_file in self.cache_dir.glob("*"):
            if cache_file.is_file():
                self._remove_cache_file(cache_file)
                removed_count += 1
        
        logger.info("Cleared all cache files", removed_count=removed_count)
        return removed_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_files = 0
        total_size = 0
        expired_files = 0
        
        for cache_file in self.cache_dir.glob("*"):
            if cache_file.is_file():
                total_files += 1
                total_size += cache_file.stat().st_size
                
                try:
                    if cache_file.suffix == ".pkl":
                        with open(cache_file, "rb") as f:
                            cache_data = pickle.load(f)
                        cache_timestamp = cache_data.get("timestamp")
                    elif cache_file.suffix == ".json":
                        with open(cache_file, "r", encoding="utf-8") as f:
                            cache_data = json.load(f)
                        cache_timestamp_str = cache_data.get("timestamp", "")
                        if cache_timestamp_str:
                            cache_timestamp = datetime.fromisoformat(cache_timestamp_str.replace("Z", "+00:00"))
                        else:
                            cache_timestamp = None
                    else:
                        continue
                    
                    if cache_timestamp and self._is_cache_expired(cache_timestamp):
                        expired_files += 1
                
                except Exception:
                    expired_files += 1
        
        return {
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "expired_files": expired_files,
            "cache_directory": str(self.cache_dir),
            "ttl_seconds": self.ttl_seconds,
        }
    
    def _generate_ohlcv_cache_key(self, symbol: str, start_date: datetime, end_date: datetime) -> str:
        """Generate cache key for OHLCV data.
        
        Args:
            symbol: Trading symbol
            start_date: Start date
            end_date: End date
            
        Returns:
            Cache key string
        """
        key_data = f"{symbol}_{start_date.isoformat()}_{end_date.isoformat()}"
        return create_data_hash(key_data)
    
    def _is_cache_expired(self, cache_timestamp: Optional[datetime]) -> bool:
        """Check if cache entry is expired.
        
        Args:
            cache_timestamp: Cache timestamp
            
        Returns:
            True if cache is expired
        """
        if cache_timestamp is None:
            return True
        
        now = datetime.now(timezone.utc)
        age = (now - cache_timestamp).total_seconds()
        return age > self.ttl_seconds
    
    def _remove_cache_file(self, cache_file: Path) -> None:
        """Remove a cache file.
        
        Args:
            cache_file: Path to cache file to remove
        """
        try:
            cache_file.unlink()
            logger.debug("Removed cache file", cache_file=str(cache_file))
        except Exception as e:
            logger.warning("Failed to remove cache file", cache_file=str(cache_file), error=str(e))
