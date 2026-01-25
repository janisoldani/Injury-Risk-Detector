from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models import User


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    user_id: int = 1,  # TODO: Replace with proper auth (JWT/OAuth)
) -> User:
    """
    Temporary: Returns user by ID. Will be replaced with proper authentication.
    For MVP, we use a simple user_id header or default to user 1.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
