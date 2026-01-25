from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db: DbSession,
) -> User:
    """Create a new user."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=user_in.email,
        sport_profile=user_in.sport_profile.value,
        timezone=user_in.timezone,
        device_sources=[],
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
) -> User:
    """Get current user information."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> User:
    """Update current user information."""
    update_data = user_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "sport_profile" and value is not None:
            setattr(current_user, field, value.value)
        else:
            setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: DbSession,
) -> User:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
