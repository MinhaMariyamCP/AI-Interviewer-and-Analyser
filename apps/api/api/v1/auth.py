from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from db.session import get_db
from db.models import User
from core.security import get_password_hash, verify_password, create_access_token
import hashlib
import os
import uuid

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "candidate" # candidate or recruiter

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str


def _reset_token(email: str) -> str:
    secret = os.getenv("RESET_SECRET", "ai-interview-reset-secret")
    return hashlib.sha256(f"{email.lower().strip()}:{secret}".encode("utf-8")).hexdigest()[:32]

@router.post("/signup", response_model=Token)
async def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    user_in.email = user_in.email.lower().strip()
    # Check if user exists
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(status_code=409, detail="This email is already registered. Please sign in instead.")
    
    # Create user
    new_user = User(
        id=uuid.uuid4(),
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate token
    token = create_access_token(new_user.id, role=new_user.role)
    return {"access_token": token, "token_type": "bearer", "role": new_user.role}

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username.lower().strip()).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    token = create_access_token(user.id, role=user.role)
    return {"access_token": token, "token_type": "bearer", "role": user.role}

@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    token = _reset_token(email)
    if not user:
        return {"message": "If that email exists, a reset token has been generated for the next step.", "reset_token": token}
    return {
        "message": "Use this reset token on the password reset page to set a new password.",
        "reset_token": token,
    }

@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if payload.token != _reset_token(email):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account was found for that email address.")

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long.")

    user.password_hash = get_password_hash(payload.new_password)
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "Password updated successfully. You can sign in with your new password."}
