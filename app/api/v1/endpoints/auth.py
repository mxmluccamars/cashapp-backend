from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.security import create_access_token, verify_pin, verify_token

router = APIRouter()


class PinLoginRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=12)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


@router.post("/login", response_model=TokenResponse, summary="Autenticar com PIN")
def login_with_pin(body: PinLoginRequest):
    if not verify_pin(body.pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="PIN incorreto.",
        )

    token, expires_at = create_access_token()
    return TokenResponse(access_token=token, expires_at=expires_at)


@router.get("/verify", summary="Verifica se o token atual ainda é válido")
def check_auth(_: str = Depends(verify_token)):
    return {"authenticated": True}