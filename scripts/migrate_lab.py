"""Add new lab tables without dropping or rewriting existing registrations."""
import asyncio
from src.backend.infrastructure.database.db_connection import create_tables

if __name__ == "__main__":
    asyncio.run(create_tables())
