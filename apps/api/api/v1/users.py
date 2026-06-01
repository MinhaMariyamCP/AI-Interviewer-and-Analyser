from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from jose import jwt, JWTError
import os
import uuid

from db.session import get_db
from db.models import User
from core.security import SECRET_KEY, ALGORITHM, get_password_hash

router = APIRouter(prefix="/api/v1/users", tags=["users"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

# --- Pydantic Models ---

class UserProfile(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str]
    role: str

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

# --- Dependency ---

async def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

# --- Endpoints ---

@router.get("/me", response_model=UserProfile)
async def read_user_me(current_user: User = Depends(get_current_user)):
    """
    Get current logged-in user profile.
    """
    return current_user

@router.put("/me", response_model=UserProfile)
async def update_user_me(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update current user profile.
    """
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    
    if user_update.email is not None:
        # Check if email is already taken
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = user_update.email
        
    if user_update.password is not None:
        current_user.password_hash = get_password_hash(user_update.password)
        
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
