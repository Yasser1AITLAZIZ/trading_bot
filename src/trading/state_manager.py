"""State manager for persisting trading state and decisions."""

import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Any
import structlog

from ..core.settings import get_settings
from ..core.types import TradingDecision, OHLCVData
from ..core.utils import create_data_hash

logger = structlog.get_logger(__name__)


class StateManagerError(Exception):
    """Exception raised during state management operations."""
    pass


class StateManager:
    """Manager for persisting and restoring trading state."""
    
    def __init__(self, symbol: str, db_path: Optional[str] = None):
        """Initialize the state manager.
        
        Args:
            symbol: Trading symbol
            db_path: Path to state database file
        """
        self.symbol = symbol
        self.settings = get_settings()
        
        # Database setup
        if db_path:
            self.db_path = Path(db_path)
        else:
            data_dir = Path(self.settings.data.data_directory)
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = data_dir / f"trading_state_{symbol.lower()}.db"
        
        # State data
        self.current_state: Dict[str, Any] = {}
        self.last_analysis_time: Optional[datetime] = None
        self.last_decision: Optional[TradingDecision] = None
        self.session_start_time: Optional[datetime] = None
        
        # Initialize database
        self._initialize_database()
        
        logger.info(
            "Initialized state manager",
            symbol=symbol,
            db_path=str(self.db_path),
        )
    
    def _initialize_database(self) -> None:
        """Initialize the state database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create state table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trading_state (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        state_key TEXT NOT NULL,
                        state_value TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(symbol, state_key)
                    )
                """)
                
                # Create decisions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trading_decisions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        action TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        price REAL,
                        confidence REAL NOT NULL,
                        reasoning TEXT NOT NULL,
                        risk_score REAL NOT NULL,
                        analysis_data TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create analysis history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS analysis_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        data_points INTEGER NOT NULL,
                        indicators TEXT,
                        signals TEXT,
                        decision_hash TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_decisions_symbol_timestamp 
                    ON trading_decisions(symbol, timestamp)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_analysis_symbol_timestamp 
                    ON analysis_history(symbol, timestamp)
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error("Failed to initialize state database", error=str(e))
            raise StateManagerError(f"Database initialization failed: {e}")
    
    async def load_state(self) -> Dict[str, Any]:
        """Load trading state from database.
        
        Returns:
            Dictionary with loaded state
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Load state data
                cursor.execute("""
                    SELECT state_key, state_value 
                    FROM trading_state 
                    WHERE symbol = ?
                """, (self.symbol,))
                
                state_data = {}
                for row in cursor.fetchall():
                    key, value = row
                    try:
                        state_data[key] = json.loads(value)
                    except json.JSONDecodeError:
                        state_data[key] = value
                
                self.current_state = state_data
                
                # Load last analysis time
                if "last_analysis_time" in state_data:
                    self.last_analysis_time = datetime.fromisoformat(
                        state_data["last_analysis_time"]
                    )
                
                # Load session start time
                if "session_start_time" in state_data:
                    self.session_start_time = datetime.fromisoformat(
                        state_data["session_start_time"]
                    )
                else:
                    self.session_start_time = datetime.now(timezone.utc)
                
                logger.info(
                    "Loaded trading state",
                    symbol=self.symbol,
                    state_keys=list(state_data.keys()),
                )
                
                return state_data
        
        except Exception as e:
            logger.error("Failed to load state", error=str(e))
            raise StateManagerError(f"State loading failed: {e}")
    
    async def save_state(self) -> None:
        """Save current trading state to database."""
        try:
            # Update state data
            self.current_state.update({
                "last_analysis_time": (
                    self.last_analysis_time.isoformat()
                    if self.last_analysis_time else None
                ),
                "session_start_time": (
                    self.session_start_time.isoformat()
                    if self.session_start_time else None
                ),
                "last_save_time": datetime.now(timezone.utc).isoformat(),
            })
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Save state data
                for key, value in self.current_state.items():
                    json_value = json.dumps(value) if not isinstance(value, str) else value
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO trading_state 
                        (symbol, state_key, state_value, timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (self.symbol, key, json_value, datetime.now(timezone.utc)))
                
                conn.commit()
                
                logger.debug("Saved trading state", symbol=self.symbol)
        
        except Exception as e:
            logger.error("Failed to save state", error=str(e))
            raise StateManagerError(f"State saving failed: {e}")
    
    async def record_decision(
        self,
        decision: TradingDecision,
        analysis_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a trading decision.
        
        Args:
            decision: Trading decision to record
            analysis_data: Additional analysis data
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create decision hash for deduplication
                decision_hash = create_data_hash({
                    "timestamp": decision.timestamp.isoformat() if hasattr(decision, 'timestamp') else datetime.now(timezone.utc).isoformat(),
                    "action": decision.action.value if decision.action else "HOLD",
                    "quantity": str(decision.quantity),
                    "confidence": decision.confidence,
                })
                
                # Insert decision
                cursor.execute("""
                    INSERT INTO trading_decisions 
                    (symbol, timestamp, action, quantity, price, confidence, reasoning, risk_score, analysis_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.symbol,
                    datetime.now(timezone.utc),
                    decision.action.value if decision.action else "HOLD",
                    float(decision.quantity),
                    float(decision.price) if decision.price else None,
                    decision.confidence,
                    decision.reasoning,
                    decision.risk_score,
                    json.dumps(analysis_data) if analysis_data else None,
                ))
                
                # Update last decision
                self.last_decision = decision
                self.current_state["last_decision"] = {
                    "action": decision.action.value if decision.action else "HOLD",
                    "quantity": str(decision.quantity),
                    "confidence": decision.confidence,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                
                conn.commit()
                
                logger.info(
                    "Recorded trading decision",
                    symbol=self.symbol,
                    action=decision.action.value if decision.action else "HOLD",
                    confidence=decision.confidence,
                )
        
        except Exception as e:
            logger.error("Failed to record decision", error=str(e))
            raise StateManagerError(f"Decision recording failed: {e}")
    
    async def record_analysis(
        self,
        data_points: int,
        indicators: Optional[Dict[str, Any]] = None,
        signals: Optional[Dict[str, str]] = None,
        decision_hash: Optional[str] = None,
    ) -> None:
        """Record analysis data.
        
        Args:
            data_points: Number of data points analyzed
            indicators: Technical indicators
            signals: Market signals
            decision_hash: Hash of the resulting decision
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO analysis_history 
                    (symbol, timestamp, data_points, indicators, signals, decision_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    self.symbol,
                    datetime.now(timezone.utc),
                    data_points,
                    json.dumps(indicators) if indicators else None,
                    json.dumps(signals) if signals else None,
                    decision_hash,
                ))
                
                # Update last analysis time
                self.last_analysis_time = datetime.now(timezone.utc)
                self.current_state["last_analysis_time"] = self.last_analysis_time.isoformat()
                
                conn.commit()
                
                logger.debug(
                    "Recorded analysis data",
                    symbol=self.symbol,
                    data_points=data_points,
                )
        
        except Exception as e:
            logger.error("Failed to record analysis", error=str(e))
            raise StateManagerError(f"Analysis recording failed: {e}")
    
    def get_decision_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get decision history.
        
        Args:
            limit: Maximum number of decisions to return
            
        Returns:
            List of decision records
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT timestamp, action, quantity, price, confidence, reasoning, risk_score
                    FROM trading_decisions 
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (self.symbol, limit))
                
                decisions = []
                for row in cursor.fetchall():
                    decisions.append({
                        "timestamp": row[0],
                        "action": row[1],
                        "quantity": row[2],
                        "price": row[3],
                        "confidence": row[4],
                        "reasoning": row[5],
                        "risk_score": row[6],
                    })
                
                return decisions
        
        except Exception as e:
            logger.error("Failed to get decision history", error=str(e))
            return []
    
    def get_analysis_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get analysis history.
        
        Args:
            limit: Maximum number of analyses to return
            
        Returns:
            List of analysis records
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT timestamp, data_points, indicators, signals, decision_hash
                    FROM analysis_history 
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (self.symbol, limit))
                
                analyses = []
                for row in cursor.fetchall():
                    analyses.append({
                        "timestamp": row[0],
                        "data_points": row[1],
                        "indicators": json.loads(row[2]) if row[2] else None,
                        "signals": json.loads(row[3]) if row[3] else None,
                        "decision_hash": row[4],
                    })
                
                return analyses
        
        except Exception as e:
            logger.error("Failed to get analysis history", error=str(e))
            return []
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get state summary.
        
        Returns:
            Dictionary with state summary
        """
        return {
            "symbol": self.symbol,
            "session_start_time": (
                self.session_start_time.isoformat()
                if self.session_start_time else None
            ),
            "last_analysis_time": (
                self.last_analysis_time.isoformat()
                if self.last_analysis_time else None
            ),
            "last_decision": self.current_state.get("last_decision"),
            "state_keys": list(self.current_state.keys()),
            "database_path": str(self.db_path),
        }
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """Clean up old data from database.
        
        Args:
            days_to_keep: Number of days of data to keep
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete old decisions
                cursor.execute("""
                    DELETE FROM trading_decisions 
                    WHERE symbol = ? AND timestamp < ?
                """, (self.symbol, cutoff_date))
                decisions_deleted = cursor.rowcount
                
                # Delete old analyses
                cursor.execute("""
                    DELETE FROM analysis_history 
                    WHERE symbol = ? AND timestamp < ?
                """, (self.symbol, cutoff_date))
                analyses_deleted = cursor.rowcount
                
                conn.commit()
                
                total_deleted = decisions_deleted + analyses_deleted
                
                logger.info(
                    "Cleaned up old data",
                    symbol=self.symbol,
                    days_to_keep=days_to_keep,
                    decisions_deleted=decisions_deleted,
                    analyses_deleted=analyses_deleted,
                    total_deleted=total_deleted,
                )
                
                return total_deleted
        
        except Exception as e:
            logger.error("Failed to cleanup old data", error=str(e))
            return 0
