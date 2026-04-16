"""
Business logic for Task 1 (API Key & Rate Limiting) and Task 2 (Job Processing).
"""

import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import APIKeyDB, JobDB


# ============================================================================
# Task 1: API Key & Rate Limiting Service
# ============================================================================


class APIKeyService:
    """Service for managing API keys and rate limiting."""

    RATE_LIMIT = 5  # requests per minute
    RATE_WINDOW = 60  # seconds

    @staticmethod
    async def generate_api_key(session: AsyncSession, user_id: str | None = None) -> str:
        """Generate a new unique API key."""
        while True:
            key = f"sk_{secrets.token_urlsafe(32)}"

            # Check if key already exists
            stmt = select(APIKeyDB).where(APIKeyDB.key == key)
            result = await session.execute(stmt)
            if result.scalars().first() is None:
                # Key is unique, create it
                api_key_db = APIKeyDB(key=key, user_id=user_id)
                session.add(api_key_db)
                await session.commit()
                return key

    @staticmethod
    async def get_api_key_by_key(session: AsyncSession, key: str) -> Optional[APIKeyDB]:
        """Retrieve API key from database."""
        stmt = select(APIKeyDB).where(APIKeyDB.key == key)
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def check_rate_limit(
        session: AsyncSession, api_key: str
    ) -> tuple[bool, int]:
        """
        Check if API key has exceeded rate limit.

        Returns:
            tuple: (is_allowed: bool, remaining_requests: int)
        """
        api_key_obj = await APIKeyService.get_api_key_by_key(session, api_key)

        if api_key_obj is None:
            return False, 0

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        window_start = now - timedelta(seconds=APIKeyService.RATE_WINDOW)

        # Get current values (handle SQLAlchemy objects)
        current_count = int(api_key_obj.request_count) if api_key_obj.request_count else 0  # type: ignore
        last_reset = api_key_obj.last_reset or datetime.now(timezone.utc).replace(tzinfo=None)  # type: ignore

        # If the last reset was more than a minute ago, reset the count
        if last_reset < window_start:  # type: ignore
            stmt = update(APIKeyDB).where(APIKeyDB.key == api_key).values(
                request_count=0,
                last_reset=now,
            )
            await session.execute(stmt)
            await session.commit()
            current_count = 0

        # Check if under limit
        if current_count < APIKeyService.RATE_LIMIT:
            new_count = current_count + 1
            stmt = update(APIKeyDB).where(APIKeyDB.key == api_key).values(
                request_count=new_count
            )
            await session.execute(stmt)
            await session.commit()
            remaining = APIKeyService.RATE_LIMIT - new_count
            return True, remaining

        return False, 0
    
    @staticmethod
    async def get_usage_stats(
        session: AsyncSession, api_key: str
    ) -> tuple[int, datetime]:
        """
        Get current usage statistics without modifying them.
        Returns: (current_request_count, last_reset)
        """
        api_key_obj = await APIKeyService.get_api_key_by_key(session, api_key)
        
        if not api_key_obj:
            return 0, datetime.now(timezone.utc).replace(tzinfo=None)
            
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        window_start = now - timedelta(seconds=APIKeyService.RATE_WINDOW)
        
        current_count = int(api_key_obj.request_count) if api_key_obj.request_count else 0 # type: ignore
        last_reset = api_key_obj.last_reset or datetime.now(timezone.utc).replace(tzinfo=None) # type: ignore
        
        # If window expired logically, it's 0, even though we haven't updated it yet
        if last_reset < window_start: # type: ignore
            return 0, now
            
        return current_count, last_reset # type: ignore


# ============================================================================
# Task 2: Background Job Processing Service
# ============================================================================


class JobProcessingService:
    """Service for managing background job processing."""

    # In-memory store for job results (for quick access)
    # In production, use Redis or a proper cache
    job_cache: dict[str, dict] = {}

    @staticmethod
    async def create_job(session: AsyncSession, task: str) -> str:
        """Create a new job and return its ID."""
        job_id = str(uuid4())

        job_db = JobDB(id=job_id, task=task, status="pending")
        session.add(job_db)
        await session.commit()

        # Initialize cache entry
        JobProcessingService.job_cache[job_id] = {
            "status": "pending",
            "result": None,
        }

        return job_id

    @staticmethod
    async def get_job_status(session: AsyncSession, job_id: str) -> Optional[JobDB]:
        """Retrieve job status from database."""
        stmt = select(JobDB).where(JobDB.id == job_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def process_job(job_id: str, task: str) -> None:
        """
        Process a job in the background with its own database session.

        Simulates a 5-10 second delay.
        """
        from .database import get_db_session

        async with get_db_session() as session:
            try:
                # Update status to in_progress
                stmt = update(JobDB).where(JobDB.id == job_id).values(status="in_progress")
                await session.execute(stmt)
                await session.commit()
                JobProcessingService.job_cache[job_id]["status"] = "in_progress"

                # Simulate async work with random delay between 5-10 seconds
                delay = 5 + (hash(job_id) % 6)  # Pseudo-random between 5-10
                await asyncio.sleep(delay)

                # Generate result
                result = f"Task '{task}' completed successfully after {delay}s"

                # Update job to completed
                stmt = update(JobDB).where(JobDB.id == job_id).values(
                    status="completed",
                    result=result,
                    completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                await session.execute(stmt)
                await session.commit()
                JobProcessingService.job_cache[job_id] = {
                    "status": "completed",
                    "result": result,
                }

            except Exception as e:
                # Handle errors
                error_msg = f"Error: {str(e)}"
                stmt = update(JobDB).where(JobDB.id == job_id).values(
                    status="completed",
                    result=error_msg,
                    completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                await session.execute(stmt)
                await session.commit()
                JobProcessingService.job_cache[job_id] = {
                    "status": "completed",
                    "result": error_msg,
                }

