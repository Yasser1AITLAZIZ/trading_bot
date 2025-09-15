#!/usr/bin/env python3
"""Health check script for the trading bot system."""

import asyncio
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Any
import structlog

from src.core.settings import get_settings
from src.data.ingestion import DataIngestionService
from src.llm.factory import get_llm_client
from src.execution.binance_client import BinanceClient
from src.communication.notification_manager import NotificationManager, NotificationPriority

# Initialize structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class HealthCheckResult:
    """Health check result container."""
    
    def __init__(self, component: str, status: str, message: str, details: Dict[str, Any] = None):
        """Initialize health check result.
        
        Args:
            component: Component name
            status: Status (healthy, warning, error)
            message: Status message
            details: Additional details
        """
        self.component = component
        self.status = status
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc)


class SystemHealthChecker:
    """System health checker for the trading bot."""
    
    def __init__(self):
        """Initialize the health checker."""
        self.settings = get_settings()
        self.results: List[HealthCheckResult] = []
        self.notification_manager = NotificationManager()
    
    async def check_all(self) -> List[HealthCheckResult]:
        """Run all health checks.
        
        Returns:
            List of health check results
        """
        logger.info("Starting system health check")
        
        # Clear previous results
        self.results.clear()
        
        # Run all checks
        await self._check_environment()
        await self._check_data_ingestion()
        await self._check_llm_connectivity()
        await self._check_binance_connectivity()
        await self._check_notification_system()
        await self._check_disk_space()
        await self._check_memory_usage()
        
        # Send notification if there are errors
        await self._send_health_notification()
        
        logger.info("System health check completed", results_count=len(self.results))
        return self.results
    
    async def _check_environment(self) -> None:
        """Check environment configuration."""
        try:
            issues = []
            
            # Check required environment variables
            required_vars = [
                "LLM_OPENAI_API_KEY",
                "BINANCE_API_KEY",
                "BINANCE_SECRET_KEY",
            ]
            
            for var in required_vars:
                if not getattr(self.settings, var.lower().replace("_", "_"), None):
                    issues.append(f"Missing {var}")
            
            # Check trading mode
            if self.settings.binance.mode not in ["paper", "testnet", "live"]:
                issues.append(f"Invalid trading mode: {self.settings.binance.mode}")
            
            if issues:
                self.results.append(HealthCheckResult(
                    component="Environment",
                    status="error",
                    message=f"Configuration issues: {', '.join(issues)}",
                    details={"issues": issues}
                ))
            else:
                self.results.append(HealthCheckResult(
                    component="Environment",
                    status="healthy",
                    message="Environment configuration is valid",
                    details={"trading_mode": self.settings.binance.mode}
                ))
        
        except Exception as e:
            self.results.append(HealthCheckResult(
                component="Environment",
                status="error",
                message=f"Environment check failed: {str(e)}",
                details={"error": str(e)}
            ))
    
    async def _check_data_ingestion(self) -> None:
        """Check data ingestion system."""
        try:
            data_service = DataIngestionService()
            
            # Test with sample data
            sample_data = [
                {
                    "timestamp": "2024-01-01T00:00:00Z",
                    "open": 50000.0,
                    "high": 51000.0,
                    "low": 49000.0,
                    "close": 50500.0,
                    "volume": 1000.0,
                    "symbol": "BTCUSDT"
                }
            ]
            
            # Validate data
            quality_metrics = data_service.validate_data_quality(sample_data)
            
            if quality_metrics["valid"]:
                self.results.append(HealthCheckResult(
                    component="Data Ingestion",
                    status="healthy",
                    message="Data ingestion system is working",
                    details={"quality_score": quality_metrics.get("quality_score", 0)}
                ))
            else:
                self.results.append(HealthCheckResult(
                    component="Data Ingestion",
                    status="warning",
                    message=f"Data quality issues: {', '.join(quality_metrics['issues'])}",
                    details=quality_metrics
                ))
        
        except Exception as e:
            self.results.append(HealthCheckResult(
                component="Data Ingestion",
                status="error",
                message=f"Data ingestion check failed: {str(e)}",
                details={"error": str(e)}
            ))
    
    async def _check_llm_connectivity(self) -> None:
        """Check LLM connectivity."""
        try:
            # Test primary provider
            primary_provider = self.settings.llm.primary_provider
            llm_client = get_llm_client(primary_provider)
            
            # Test with simple prompt
            test_prompt = "Hello, this is a health check. Please respond with 'OK'."
            
            start_time = time.time()
            response = llm_client.generate(test_prompt)
            response_time = time.time() - start_time
            
            if response and len(response) > 0:
                self.results.append(HealthCheckResult(
                    component="LLM Connectivity",
                    status="healthy",
                    message=f"LLM {primary_provider} is responding",
                    details={
                        "provider": primary_provider,
                        "response_time": response_time,
                        "response_length": len(response)
                    }
                ))
            else:
                self.results.append(HealthCheckResult(
                    component="LLM Connectivity",
                    status="error",
                    message=f"LLM {primary_provider} returned empty response",
                    details={"provider": primary_provider}
                ))
        
        except Exception as e:
            self.results.append(HealthCheckResult(
                component="LLM Connectivity",
                status="error",
                message=f"LLM connectivity check failed: {str(e)}",
                details={"error": str(e)}
            ))
    
    async def _check_binance_connectivity(self) -> None:
        """Check Binance API connectivity."""
        try:
            binance_client = BinanceClient(self.settings.binance.mode)
            
            # Test API connectivity
            start_time = time.time()
            account_info = binance_client.get_account_info()
            response_time = time.time() - start_time
            
            if account_info:
                self.results.append(HealthCheckResult(
                    component="Binance API",
                    status="healthy",
                    message=f"Binance API is responding (mode: {self.settings.binance.mode})",
                    details={
                        "mode": self.settings.binance.mode,
                        "response_time": response_time,
                        "account_type": account_info.get("accountType", "unknown")
                    }
                ))
            else:
                self.results.append(HealthCheckResult(
                    component="Binance API",
                    status="error",
                    message="Binance API returned empty response",
                    details={"mode": self.settings.binance.mode}
                ))
        
        except Exception as e:
            self.results.append(HealthCheckResult(
                component="Binance API",
                status="error",
                message=f"Binance API check failed: {str(e)}",
                details={"error": str(e)}
            ))
    
    async def _check_notification_system(self) -> None:
        """Check notification system."""
        try:
            # Test notification sending
            test_notification = self.notification_manager.send_system_notification(
                title="Health Check Test",
                message="This is a test notification from the health check system",
                priority=NotificationPriority.LOW
            )
            
            await test_notification
            
            # Get statistics
            stats = self.notification_manager.get_channel_statistics()
            
            self.results.append(HealthCheckResult(
                component="Notification System",
                status="healthy",
                message="Notification system is working",
                details={
                    "total_sent": stats["total_sent"],
                    "success_rate": stats["success_rate"],
                    "registered_channels": stats["registered_channels"]
                }
            ))
        
        except Exception as e:
            self.results.append(HealthCheckResult(
                component="Notification System",
                status="error",
                message=f"Notification system check failed: {str(e)}",
                details={"error": str(e)}
            ))
    
    async def _check_disk_space(self) -> None:
        """Check disk space."""
        try:
            import shutil
            
            # Check current directory disk space
            total, used, free = shutil.disk_usage(".")
            free_percent = (free / total) * 100
            
            if free_percent > 20:
                status = "healthy"
                message = f"Disk space is adequate ({free_percent:.1f}% free)"
            elif free_percent > 10:
                status = "warning"
                message = f"Disk space is low ({free_percent:.1f}% free)"
            else:
                status = "error"
                message = f"Disk space is critically low ({free_percent:.1f}% free)"
            
            self.results.append(HealthCheckResult(
                component="Disk Space",
                status=status,
                message=message,
                details={
                    "free_percent": free_percent,
                    "free_gb": free / (1024**3),
                    "total_gb": total / (1024**3)
                }
            ))
        
        except Exception as e:
            self.results.append(HealthCheckResult(
                component="Disk Space",
                status="error",
                message=f"Disk space check failed: {str(e)}",
                details={"error": str(e)}
            ))
    
    async def _check_memory_usage(self) -> None:
        """Check memory usage."""
        try:
            import psutil
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent < 80:
                status = "healthy"
                message = f"Memory usage is normal ({memory_percent:.1f}%)"
            elif memory_percent < 90:
                status = "warning"
                message = f"Memory usage is high ({memory_percent:.1f}%)"
            else:
                status = "error"
                message = f"Memory usage is critically high ({memory_percent:.1f}%)"
            
            self.results.append(HealthCheckResult(
                component="Memory Usage",
                status=status,
                message=message,
                details={
                    "memory_percent": memory_percent,
                    "available_gb": memory.available / (1024**3),
                    "total_gb": memory.total / (1024**3)
                }
            ))
        
        except ImportError:
            self.results.append(HealthCheckResult(
                component="Memory Usage",
                status="warning",
                message="Memory check skipped (psutil not available)",
                details={"note": "Install psutil for memory monitoring"}
            ))
        except Exception as e:
            self.results.append(HealthCheckResult(
                component="Memory Usage",
                status="error",
                message=f"Memory usage check failed: {str(e)}",
                details={"error": str(e)}
            ))
    
    async def _send_health_notification(self) -> None:
        """Send health check notification if there are errors."""
        try:
            error_count = len([r for r in self.results if r.status == "error"])
            warning_count = len([r for r in self.results if r.status == "warning"])
            
            if error_count > 0 or warning_count > 0:
                # Create summary message
                summary_lines = ["System Health Check Results:"]
                
                for result in self.results:
                    status_emoji = {
                        "healthy": "✅",
                        "warning": "⚠️",
                        "error": "❌"
                    }.get(result.status, "❓")
                    
                    summary_lines.append(f"{status_emoji} {result.component}: {result.message}")
                
                summary_message = "\n".join(summary_lines)
                
                # Determine priority
                if error_count > 0:
                    priority = NotificationPriority.HIGH
                    title = f"System Health Check - {error_count} Errors"
                else:
                    priority = NotificationPriority.NORMAL
                    title = f"System Health Check - {warning_count} Warnings"
                
                # Send notification
                await self.notification_manager.send_system_notification(
                    title=title,
                    message=summary_message,
                    priority=priority
                )
        
        except Exception as e:
            logger.error("Failed to send health notification", error=str(e))
    
    def get_summary(self) -> Dict[str, Any]:
        """Get health check summary.
        
        Returns:
            Dictionary with health check summary
        """
        total_checks = len(self.results)
        healthy_count = len([r for r in self.results if r.status == "healthy"])
        warning_count = len([r for r in self.results if r.status == "warning"])
        error_count = len([r for r in self.results if r.status == "error"])
        
        overall_status = "healthy"
        if error_count > 0:
            overall_status = "error"
        elif warning_count > 0:
            overall_status = "warning"
        
        return {
            "overall_status": overall_status,
            "total_checks": total_checks,
            "healthy_count": healthy_count,
            "warning_count": warning_count,
            "error_count": error_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": [
                {
                    "component": r.component,
                    "status": r.status,
                    "message": r.message,
                    "details": r.details,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in self.results
            ]
        }


async def main():
    """Main health check function."""
    print("🔍 Starting System Health Check...")
    
    checker = SystemHealthChecker()
    results = await checker.check_all()
    
    # Print results
    print("\n📊 Health Check Results:")
    print("=" * 50)
    
    for result in results:
        status_emoji = {
            "healthy": "✅",
            "warning": "⚠️",
            "error": "❌"
        }.get(result.status, "❓")
        
        print(f"{status_emoji} {result.component}: {result.message}")
        
        if result.details:
            for key, value in result.details.items():
                print(f"   {key}: {value}")
    
    # Print summary
    summary = checker.get_summary()
    print("\n📈 Summary:")
    print(f"Overall Status: {summary['overall_status'].upper()}")
    print(f"Total Checks: {summary['total_checks']}")
    print(f"Healthy: {summary['healthy_count']}")
    print(f"Warnings: {summary['warning_count']}")
    print(f"Errors: {summary['error_count']}")
    
    # Exit with appropriate code
    if summary['error_count'] > 0:
        print("\n❌ Health check failed with errors!")
        sys.exit(1)
    elif summary['warning_count'] > 0:
        print("\n⚠️ Health check completed with warnings!")
        sys.exit(0)
    else:
        print("\n✅ All health checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
