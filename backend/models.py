"""
Pydantic and SQLAlchemy models for Task 1 & Task 2.
"""

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

# Database base for SQLAlchemy models
Base = declarative_base()


# ============================================================================
# User Authentication - SQLAlchemy Models
# ============================================================================

class UserDB(Base):
    """SQLAlchemy model for Users."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    api_keys = relationship("APIKeyDB", back_populates="user")


# ============================================================================
# Task 1: API Key & Rate Limiting - SQLAlchemy Models
# ============================================================================


class APIKeyDB(Base):
    """SQLAlchemy model for API keys."""

    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    key = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    request_count = Column(Integer, default=0, nullable=False)
    last_reset = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    user = relationship("UserDB", back_populates="api_keys")


# ============================================================================
# Task 2: Background Job Processing - SQLAlchemy Models
# ============================================================================


class JobDB(Base):
    """SQLAlchemy model for background jobs."""

    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    task = Column(String, nullable=False)
    status = Column(
        String,
        default="pending",
        nullable=False,
    )  # pending, in_progress, completed
    result = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    completed_at = Column(DateTime, nullable=True)


# ============================================================================
# User Authentication - Pydantic Models
# ============================================================================

class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password (min 6 chars)", min_length=6)

class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

class TokenResponse(BaseModel):
    """Schema for returning JWT token."""
    access_token: str = Field(..., description="JWT Bearer token")
    token_type: str = Field(..., description="Type of token, usually 'bearer'")


# ============================================================================
# Task 1: API Key & Rate Limiting - Pydantic Models
# ============================================================================


class APIKeyRequest(BaseModel):
    """Request model for API key generation."""

    pass


class APIKeyResponse(BaseModel):
    """Response model for API key generation."""

    api_key: str = Field(..., description="The generated API key")
    created_at: datetime = Field(..., description="Timestamp of key creation")

    model_config = {"from_attributes": True}


class APIUsageResponse(BaseModel):
    """Response model for API key usage analytics."""

    api_key_prefix: str = Field(..., description="First few characters of the API key")
    request_count: int = Field(..., description="Number of requests made in the current window")
    rate_limit: int = Field(..., description="Maximum allowed requests per window")
    window_seconds: int = Field(..., description="Duration of the rate limit window in seconds")
    last_reset: datetime = Field(..., description="Timestamp of the last rate limit window reset")

    model_config = {"from_attributes": True}


class SecureDataResponse(BaseModel):
    """Response model for secure data endpoint."""

    message: str = Field(..., description="The secure message")
    timestamp: datetime = Field(..., description="Timestamp of the response")

    model_config = {"from_attributes": True}


# ============================================================================
# Task 2: Background Job Processing - Pydantic Models
# ============================================================================


class JobSubmissionRequest(BaseModel):
    """Request model for job submission."""

    task: str = Field(..., min_length=1, description="The task to process")


class JobStatusResponse(BaseModel):
    """Response model for job status."""

    job_id: str = Field(..., description="The unique job ID")
    task: str = Field(..., description="The task description")
    status: Literal["pending", "in_progress", "completed"] = Field(
        ..., description="Current job status"
    )
    result: str | None = Field(None, description="Job result (if completed)")
    created_at: datetime = Field(..., description="Timestamp of job creation")
    completed_at: datetime | None = Field(
        None, description="Timestamp of job completion"
    )

    model_config = {"from_attributes": True}


class JobSubmissionResponse(BaseModel):
    """Response model for job submission."""

    job_id: str = Field(..., description="The unique job ID")
    task: str = Field(..., description="The task description")
    status: str = Field(default="pending", description="Initial job status")

    model_config = {"from_attributes": True}
