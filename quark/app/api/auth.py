from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token
from app.utils.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)
from app.database import get_session
from app.config import settings

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Authentication failed"},
        403: {"description": "Forbidden"},
        429: {"description": "Too many requests"}
    }
)

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_session)
):
    """
    Register a new user in the QUARK platform.

    Parameters:
    - **username**: Required, 3-50 characters, alphanumeric and underscores only
    - **email**: Required, valid email format
    - **password**: Required, minimum 8 characters, must include:
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one number
        - At least one special character

    Example request:
    ```json
    {
        "username": "john_doe",
        "email": "john@example.com",
        "password": "SecurePass123!"
    }
    ```

    Returns:
    ```json
    {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "created_at": "2024-03-07T10:30:00Z"
    }
    ```

    Raises:
    - **400**: Username already taken or email already registered
    - **422**: Invalid input data format
    """
    # Check if user exists
    existing_user = db.exec(
        select(User).where(
            (User.email == user_data.email) | 
            (User.username == user_data.username)
        )
    ).first()
    
    if existing_user:
        if existing_user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        password=hashed_password  # Note: field name changed from hashed_password to password
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_session)
):
    """
    Authenticate user and return JWT token.

    The token can be used to authenticate future requests by including it in the
    Authorization header: `Bearer <token>`

    Parameters:
    - **username**: Email or username
    - **password**: User's password

    Returns:
    ```json
    {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "token_type": "bearer",
        "expires_in": 1800
    }
    ```

    Raises:
    - **401**: Invalid credentials
    - **429**: Too many login attempts
    """
    # Try to find user by username or email
    user = db.exec(
        select(User).where(
            (User.email == form_data.username) | 
            (User.username == form_data.username)
        )
    ).first()
    
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user 