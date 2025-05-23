from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from jose import jwt
from datetime import datetime, timedelta
import bcrypt
import os
from models import User
from dotenv import load_dotenv
from utils.db import get_db
from models import UserInvite, RoleEnum
import logging


load_dotenv()

if len(logging.getLogger().handlers) > 0:
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.basicConfig(level=logging.INFO)


router = APIRouter()

SECRET_KEY = "your-super-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    
class InviteRequest(BaseModel):
    email: EmailStr
    role: RoleEnum  # only accepts master_admin, admin, user


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    # role: str = "user"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def is_token_valid(user: User) -> bool:
    if not user.access_token or not user.access_token_creation_datetime:
        return False
    expiry_time = user.access_token_creation_datetime + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return datetime.utcnow() < expiry_time

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not bcrypt.checkpw(request.password.encode(), user.password.encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if is_token_valid(user):
        return {
            "access_token": user.access_token,
            "token_type": "bearer",
            "role": user.role
        }

    access_token = create_access_token({"sub": user.email, "role": user.role})
    user.access_token = access_token
    user.access_token_creation_datetime = datetime.utcnow()
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }

@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    # Check if the email is in the user_invite table and marked as invited
    invite = db.query(UserInvite).filter(
        UserInvite.email == request.email,
        UserInvite.invited == True
    ).first()
    logging.info(f"Invite: {invite}")

    if not invite:
        raise HTTPException(status_code=403, detail="Email is not invited to register")

    # Check if the user is already registered
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash the password
    hashed_password = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()

    # Use role from UserInvite table, not from the request
    new_user = User(
        email=request.email,
        password=hashed_password,
        role=invite.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate token
    access_token = create_access_token({"sub": new_user.email, "role": new_user.role})
    new_user.access_token = access_token
    new_user.access_token_creation_datetime = datetime.utcnow()
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": new_user.role
    }

security = HTTPBearer()

@router.get("/verify-token")
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if not email:
            raise HTTPException(status_code=401, detail="Token payload invalid")

        user = db.query(User).filter(User.email == email).first()
        if not user or user.access_token != token:
            raise HTTPException(status_code=401, detail="Invalid token or user not found")

        expiry_time = user.access_token_creation_datetime + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        if datetime.utcnow() > expiry_time:
            raise HTTPException(status_code=401, detail="Token has expired")

        return {"valid": True, "email": email, "role": user.role}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")

    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
@router.post("/invite")
async def invite_user(request: InviteRequest, db: Session = Depends(get_db)):
    # Check if the email is already in the UserInvite table
    invite = db.query(UserInvite).filter(UserInvite.email == request.email).first()

    if invite:
        if invite.invited:
            raise HTTPException(status_code=400, detail="User already invited")
        else:
            invite.role = request.role
            invite.invited = True
    else:
        invite = UserInvite(
            email=request.email,
            role=request.role,
            invited=True
        )
        db.add(invite)

    db.commit()

    # Placeholder: Send an email (replace with your actual mail sending logic)
    print(f"Sent invite to {request.email} with role {request.role}")

    return {"message": f"Invitation sent to {request.email}", "status": "success"}
