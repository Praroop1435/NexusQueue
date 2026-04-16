"""
FastAPI application for Task 1 (API Key & Rate Limiting) and Task 2 (Job Processing).
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_session, init_db
from .models import APIKeyResponse, JobStatusResponse, JobSubmissionRequest, JobSubmissionResponse, SecureDataResponse, APIUsageResponse, UserCreate, UserLogin, TokenResponse, UserDB
from .services import APIKeyService, JobProcessingService
from .auth import get_password_hash, verify_password, create_access_token, get_current_user
from sqlalchemy.future import select


# ============================================================================
# Lifespan Context Manager
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Job Processing API",
    description="Two-service backend: API Key Rate Limiting & Background Job Processing",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# User Authentication Endpoints
# ============================================================================

@app.post("/auth/register", status_code=201, tags=["Authentication"], summary="Register new user")
async def register(user: UserCreate, session: AsyncSession = Depends(get_session)):
    stmt = select(UserDB).where(UserDB.email == user.email)
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_pwd = get_password_hash(user.password)
    new_user = UserDB(email=user.email, hashed_password=hashed_pwd)
    session.add(new_user)
    await session.commit()
    return {"message": "User registered successfully"}

@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"], summary="Login and get token")
async def login(user: UserLogin, session: AsyncSession = Depends(get_session)):
    stmt = select(UserDB).where(UserDB.email == user.email)
    result = await session.execute(stmt)
    db_user = result.scalar_one_or_none()
    
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    access_token = create_access_token(data={"sub": db_user.email})
    return TokenResponse(access_token=access_token, token_type="bearer")


# ============================================================================
# Task 1: API Key & Rate Limiting Endpoints
# ============================================================================


@app.post(
    "/api-keys",
    response_model=APIKeyResponse,
    status_code=201,
    tags=["Task 1: API Key Management"],
    summary="Generate a new API key",
    description="Generate a new unique API key for rate-limited access.",
)
async def generate_api_key(
    session: AsyncSession = Depends(get_session),
    current_user: UserDB = Depends(get_current_user)
) -> APIKeyResponse:
    """Generate a new API key."""
    api_key = await APIKeyService.generate_api_key(session, current_user.id)
    return APIKeyResponse(
        api_key=api_key,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )


@app.get(
    "/api-keys/{api_key}/usage",
    response_model=APIUsageResponse,
    status_code=200,
    tags=["Task 1: API Key Management"],
    summary="Get API key usage statistics",
    description="Retrieve the current request count out of the rate limit capacity over the sliding window.",
)
async def get_api_key_usage(
    api_key: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserDB = Depends(get_current_user)
) -> APIUsageResponse:
    """Get real-time tracking data for a specific API Key."""
    current_count, last_reset = await APIKeyService.get_usage_stats(session, api_key)
    
    return APIUsageResponse(
        api_key_prefix=api_key[:8] + "...",
        request_count=current_count,
        rate_limit=APIKeyService.RATE_LIMIT,
        window_seconds=APIKeyService.RATE_WINDOW,
        last_reset=last_reset
    )


@app.get(
    "/secure-data",
    response_model=SecureDataResponse,
    status_code=200,
    tags=["Task 1: API Key Management"],
    summary="Access secure data endpoint",
    description="Returns secure data if a valid, non-rate-limited API key is provided in headers.",
    responses={
        200: {
            "description": "Successfully accessed secure data",
            "content": {"application/json": {"example": {"message": "Hello World", "timestamp": "2024-01-01T00:00:00"}}},
        },
        401: {"description": "Missing or invalid API key"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def get_secure_data(
    x_api_key: Optional[str] = Header(None, description="API Key"),
    session: AsyncSession = Depends(get_session),
) -> SecureDataResponse:
    """
    Access secure data with API key validation and rate limiting.

    Requires a valid API key in the X-API-Key header.
    Returns 429 if rate limit (5 requests/minute) is exceeded.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header.",
        )

    # Check rate limit
    is_allowed, remaining = await APIKeyService.check_rate_limit(session, x_api_key)

    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 5 requests per minute allowed.",
        )

    return SecureDataResponse(
        message="Hello World",
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
    )


# ============================================================================
# Task 2: Background Job Processing Endpoints
# ============================================================================


@app.post(
    "/jobs",
    response_model=JobSubmissionResponse,
    status_code=202,
    tags=["Task 2: Job Processing"],
    summary="Submit a new background job",
    description="Submit a new task for background processing and receive a job_id.",
)
async def submit_job(
    request: JobSubmissionRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> JobSubmissionResponse:
    """
    Submit a job for background processing.

    Returns immediately with job_id. The job will be processed asynchronously
    with a simulated 5-10 second delay.
    """
    job_id = await JobProcessingService.create_job(session, request.task)

    # Add background task
    background_tasks.add_task(
        JobProcessingService.process_job, job_id, request.task
    )

    return JobSubmissionResponse(
        job_id=job_id,
        task=request.task,
        status="pending",
    )


@app.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    status_code=200,
    tags=["Task 2: Job Processing"],
    summary="Get job status",
    description="Retrieve the current status and result of a background job.",
    responses={
        200: {"description": "Job status retrieved successfully"},
        404: {"description": "Job not found"},
    },
)
async def get_job_status(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> JobStatusResponse:
    """
    Retrieve the status of a background job.

    Returns the current status (pending, in_progress, completed) and result if available.
    """
    job = await JobProcessingService.get_job_status(session, job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job with ID '{job_id}' not found.",
        )

    return JobStatusResponse(
        job_id=job.id,  # type: ignore
        task=job.task,  # type: ignore
        status=job.status,  # type: ignore
        result=job.result,  # type: ignore
        created_at=job.created_at,  # type: ignore
        completed_at=job.completed_at,  # type: ignore
    )


# ============================================================================
# Health Check
# ============================================================================


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Check if the API is running.",
)
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}

