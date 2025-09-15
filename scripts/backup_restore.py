#!/usr/bin/env python3
"""Backup and restore script for trading bot data and state."""

import asyncio
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
import structlog
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from src.core.settings import get_settings

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
console = Console()
app = typer.Typer(help="Backup and Restore - Manage trading bot data and state")


class BackupManager:
    """Manager for backup and restore operations."""
    
    def __init__(self):
        """Initialize the backup manager."""
        self.settings = get_settings()
        self.data_dir = Path(self.settings.data.data_directory)
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """Create a backup of trading bot data.
        
        Args:
            backup_name: Optional custom backup name
            
        Returns:
            Backup directory path
        """
        if not backup_name:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_name = f"trading_bot_backup_{timestamp}"
        
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        logger.info("Creating backup", backup_name=backup_name, backup_path=str(backup_path))
        
        # Backup database files
        self._backup_databases(backup_path)
        
        # Backup configuration
        self._backup_configuration(backup_path)
        
        # Backup logs
        self._backup_logs(backup_path)
        
        # Create backup manifest
        self._create_manifest(backup_path, backup_name)
        
        logger.info("Backup created successfully", backup_path=str(backup_path))
        return str(backup_path)
    
    def _backup_databases(self, backup_path: Path) -> None:
        """Backup database files.
        
        Args:
            backup_path: Backup directory path
        """
        db_backup_dir = backup_path / "databases"
        db_backup_dir.mkdir(exist_ok=True)
        
        # Find all database files
        db_files = list(self.data_dir.glob("*.db"))
        
        for db_file in db_files:
            if db_file.exists():
                shutil.copy2(db_file, db_backup_dir / db_file.name)
                logger.debug("Backed up database", file=db_file.name)
    
    def _backup_configuration(self, backup_path: Path) -> None:
        """Backup configuration files.
        
        Args:
            backup_path: Backup directory path
        """
        config_backup_dir = backup_path / "config"
        config_backup_dir.mkdir(exist_ok=True)
        
        # Backup .env file
        env_file = Path(".env")
        if env_file.exists():
            shutil.copy2(env_file, config_backup_dir / ".env")
            logger.debug("Backed up .env file")
        
        # Backup pyproject.toml
        pyproject_file = Path("pyproject.toml")
        if pyproject_file.exists():
            shutil.copy2(pyproject_file, config_backup_dir / "pyproject.toml")
            logger.debug("Backed up pyproject.toml")
        
        # Create settings backup
        settings_backup = {
            "llm": self.settings.llm.dict(),
            "binance": self.settings.binance.dict(),
            "streaming": self.settings.streaming.dict(),
            "trading": self.settings.trading.dict(),
            "data": self.settings.data.dict(),
        }
        
        with open(config_backup_dir / "settings.json", "w") as f:
            json.dump(settings_backup, f, indent=2, default=str)
        
        logger.debug("Backed up settings")
    
    def _backup_logs(self, backup_path: Path) -> None:
        """Backup log files.
        
        Args:
            backup_path: Backup directory path
        """
        log_backup_dir = backup_path / "logs"
        log_backup_dir.mkdir(exist_ok=True)
        
        # Find log files
        log_files = list(Path("logs").glob("*.log")) if Path("logs").exists() else []
        
        for log_file in log_files:
            if log_file.exists():
                shutil.copy2(log_file, log_backup_dir / log_file.name)
                logger.debug("Backed up log file", file=log_file.name)
    
    def _create_manifest(self, backup_path: Path, backup_name: str) -> None:
        """Create backup manifest.
        
        Args:
            backup_path: Backup directory path
            backup_name: Backup name
        """
        manifest = {
            "backup_name": backup_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
            "components": {
                "databases": list((backup_path / "databases").glob("*.db")),
                "config": list((backup_path / "config").glob("*")),
                "logs": list((backup_path / "logs").glob("*.log")),
            },
            "settings": {
                "data_directory": str(self.data_dir),
                "trading_mode": self.settings.binance.mode,
                "llm_provider": self.settings.llm.primary_provider,
            }
        }
        
        # Convert Path objects to strings
        for component in manifest["components"]:
            manifest["components"][component] = [str(p) for p in manifest["components"][component]]
        
        with open(backup_path / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
        
        logger.debug("Created backup manifest")
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore from backup.
        
        Args:
            backup_path: Path to backup directory
            
        Returns:
            True if restore was successful
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            logger.error("Backup path does not exist", backup_path=str(backup_path))
            return False
        
        manifest_file = backup_path / "manifest.json"
        if not manifest_file.exists():
            logger.error("Backup manifest not found", backup_path=str(backup_path))
            return False
        
        # Load manifest
        with open(manifest_file, "r") as f:
            manifest = json.load(f)
        
        logger.info("Restoring backup", backup_name=manifest["backup_name"])
        
        try:
            # Restore databases
            self._restore_databases(backup_path)
            
            # Restore configuration
            self._restore_configuration(backup_path)
            
            # Restore logs
            self._restore_logs(backup_path)
            
            logger.info("Backup restored successfully")
            return True
        
        except Exception as e:
            logger.error("Backup restore failed", error=str(e))
            return False
    
    def _restore_databases(self, backup_path: Path) -> None:
        """Restore database files.
        
        Args:
            backup_path: Backup directory path
        """
        db_backup_dir = backup_path / "databases"
        
        if db_backup_dir.exists():
            for db_file in db_backup_dir.glob("*.db"):
                target_path = self.data_dir / db_file.name
                shutil.copy2(db_file, target_path)
                logger.debug("Restored database", file=db_file.name)
    
    def _restore_configuration(self, backup_path: Path) -> None:
        """Restore configuration files.
        
        Args:
            backup_path: Backup directory path
        """
        config_backup_dir = backup_path / "config"
        
        if config_backup_dir.exists():
            # Restore .env file
            env_file = config_backup_dir / ".env"
            if env_file.exists():
                shutil.copy2(env_file, ".env")
                logger.debug("Restored .env file")
            
            # Restore pyproject.toml
            pyproject_file = config_backup_dir / "pyproject.toml"
            if pyproject_file.exists():
                shutil.copy2(pyproject_file, "pyproject.toml")
                logger.debug("Restored pyproject.toml")
    
    def _restore_logs(self, backup_path: Path) -> None:
        """Restore log files.
        
        Args:
            backup_path: Backup directory path
        """
        log_backup_dir = backup_path / "logs"
        
        if log_backup_dir.exists():
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            
            for log_file in log_backup_dir.glob("*.log"):
                shutil.copy2(log_file, logs_dir / log_file.name)
                logger.debug("Restored log file", file=log_file.name)
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups.
        
        Returns:
            List of backup information
        """
        backups = []
        
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                manifest_file = backup_dir / "manifest.json"
                
                if manifest_file.exists():
                    try:
                        with open(manifest_file, "r") as f:
                            manifest = json.load(f)
                        
                        backups.append({
                            "name": manifest["backup_name"],
                            "path": str(backup_dir),
                            "created_at": manifest["created_at"],
                            "trading_mode": manifest["settings"]["trading_mode"],
                            "llm_provider": manifest["settings"]["llm_provider"],
                        })
                    except Exception as e:
                        logger.warning("Failed to read backup manifest", backup_dir=str(backup_dir), error=str(e))
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        
        return backups
    
    def delete_backup(self, backup_name: str) -> bool:
        """Delete a backup.
        
        Args:
            backup_name: Name of backup to delete
            
        Returns:
            True if deletion was successful
        """
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            logger.error("Backup does not exist", backup_name=backup_name)
            return False
        
        try:
            shutil.rmtree(backup_path)
            logger.info("Backup deleted", backup_name=backup_name)
            return True
        except Exception as e:
            logger.error("Failed to delete backup", backup_name=backup_name, error=str(e))
            return False


@app.command()
def create(
    name: Optional[str] = typer.Option(None, "--name", help="Custom backup name"),
):
    """Create a new backup."""
    
    console.print(Panel.fit(
        f"""
[bold]💾 Creating Backup[/bold]

Backup Name: {name or "Auto-generated"}
Target: backups/
        """,
        title="Backup Creation",
        border_style="blue"
    ))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task = progress.add_task("Creating backup...", total=None)
        
        try:
            backup_manager = BackupManager()
            backup_path = backup_manager.create_backup(name)
            
            progress.update(task, description="✅ Backup created successfully")
            
            console.print(f"[green]✅ Backup created: {backup_path}[/green]")
        
        except Exception as e:
            progress.update(task, description="❌ Backup failed")
            console.print(f"[red]❌ Backup failed: {e}[/red]")
            raise typer.Exit(1)


@app.command()
def restore(
    backup_name: str = typer.Argument(..., help="Name of backup to restore"),
):
    """Restore from a backup."""
    
    console.print(Panel.fit(
        f"""
[bold]🔄 Restoring Backup[/bold]

Backup Name: {backup_name}
Source: backups/{backup_name}/
        """,
        title="Backup Restore",
        border_style="yellow"
    ))
    
    if not typer.confirm("Are you sure you want to restore this backup? This will overwrite current data."):
        console.print("Restore cancelled.")
        raise typer.Abort()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task = progress.add_task("Restoring backup...", total=None)
        
        try:
            backup_manager = BackupManager()
            backup_path = f"backups/{backup_name}"
            success = backup_manager.restore_backup(backup_path)
            
            if success:
                progress.update(task, description="✅ Backup restored successfully")
                console.print(f"[green]✅ Backup restored: {backup_name}[/green]")
            else:
                progress.update(task, description="❌ Restore failed")
                console.print(f"[red]❌ Restore failed: {backup_name}[/red]")
                raise typer.Exit(1)
        
        except Exception as e:
            progress.update(task, description="❌ Restore failed")
            console.print(f"[red]❌ Restore failed: {e}[/red]")
            raise typer.Exit(1)


@app.command()
def list():
    """List available backups."""
    
    console.print(Panel.fit(
        """
[bold]📋 Available Backups[/bold]
        """,
        title="Backup List",
        border_style="green"
    ))
    
    try:
        backup_manager = BackupManager()
        backups = backup_manager.list_backups()
        
        if not backups:
            console.print("[yellow]No backups found.[/yellow]")
            return
        
        for backup in backups:
            created_at = datetime.fromisoformat(backup["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
            
            console.print(f"""
[bold]{backup['name']}[/bold]
  Created: {created_at}
  Mode: {backup['trading_mode']}
  LLM: {backup['llm_provider']}
  Path: {backup['path']}
            """)
    
    except Exception as e:
        console.print(f"[red]❌ Failed to list backups: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def delete(
    backup_name: str = typer.Argument(..., help="Name of backup to delete"),
):
    """Delete a backup."""
    
    console.print(Panel.fit(
        f"""
[bold]🗑️ Delete Backup[/bold]

Backup Name: {backup_name}
        """,
        title="Backup Deletion",
        border_style="red"
    ))
    
    if not typer.confirm("Are you sure you want to delete this backup? This action cannot be undone."):
        console.print("Deletion cancelled.")
        raise typer.Abort()
    
    try:
        backup_manager = BackupManager()
        success = backup_manager.delete_backup(backup_name)
        
        if success:
            console.print(f"[green]✅ Backup deleted: {backup_name}[/green]")
        else:
            console.print(f"[red]❌ Failed to delete backup: {backup_name}[/red]")
            raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"[red]❌ Failed to delete backup: {e}[/red]")
        raise typer.Exit(1)


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
