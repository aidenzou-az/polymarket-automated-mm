"""
Configuration management for the Polymarket trading bot.
Handles environment variables and storage backend configuration.
"""
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class Config:
    """Configuration class for managing environment variables."""

    # Airtable Configuration
    AIRTABLE_API_KEY: Optional[str] = os.getenv("AIRTABLE_API_KEY")
    AIRTABLE_BASE_ID: Optional[str] = os.getenv("AIRTABLE_BASE_ID")

    # Storage Backend Selection
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "hybrid")  # sheets/airtable/hybrid

    # SQLite Configuration
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "data/trading_local.db")

    # Data Retention Policy (days)
    TRADE_RETENTION_DAYS: int = int(os.getenv("TRADE_RETENTION_DAYS", "30"))
    REWARD_SNAPSHOT_RETENTION_DAYS: int = int(os.getenv("REWARD_SNAPSHOT_RETENTION_DAYS", "7"))
    POSITION_HISTORY_RETENTION_DAYS: int = int(os.getenv("POSITION_HISTORY_RETENTION_DAYS", "30"))

    # Google Sheets (legacy, for migration/rollback)
    SPREADSHEET_URL: Optional[str] = os.getenv("SPREADSHEET_URL")

    # Trading Configuration
    PK: Optional[str] = os.getenv("PK")
    DRY_RUN: bool = os.getenv("DRY_RUN", "false").lower() == "true"

    # Alert Configuration
    DISCORD_WEBHOOK_URL: Optional[str] = os.getenv("DISCORD_WEBHOOK_URL")

    @classmethod
    def validate(cls) -> list[str]:
        """
        Validate configuration and return list of missing required variables.

        Returns:
            List of missing configuration keys
        """
        missing = []

        if cls.STORAGE_BACKEND in ("airtable", "hybrid"):
            if not cls.AIRTABLE_API_KEY:
                missing.append("AIRTABLE_API_KEY")
            if not cls.AIRTABLE_BASE_ID:
                missing.append("AIRTABLE_BASE_ID")

        if cls.STORAGE_BACKEND == "sheets":
            if not cls.SPREADSHEET_URL:
                missing.append("SPREADSHEET_URL")

        if not cls.PK:
            missing.append("PK")

        return missing

    @classmethod
    def is_airtable_enabled(cls) -> bool:
        """Check if Airtable storage is enabled."""
        return cls.STORAGE_BACKEND in ("airtable", "hybrid") and bool(cls.AIRTABLE_API_KEY)

    @classmethod
    def is_sheets_enabled(cls) -> bool:
        """Check if Google Sheets storage is enabled."""
        return cls.STORAGE_BACKEND in ("sheets",) and bool(cls.SPREADSHEET_URL)

    @classmethod
    def is_sqlite_enabled(cls) -> bool:
        """Check if SQLite storage is enabled."""
        return cls.STORAGE_BACKEND in ("hybrid", "sqlite")


# Table names in Airtable
AIRTABLE_TABLES = {
    "markets": "Markets",
    "trading_configs": "Trading Configs",
    "trade_summary": "Trade Summary",
    "alerts": "Alerts",
}

# SQLite Schema version for migrations
SQLITE_SCHEMA_VERSION = 1
