from datetime import datetime, timedelta, timezone
import secrets
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

ALGORITHM = "HS256"
bearer_scheme = HTTPBearer(auto_error=False)


def verify_pin(plain_pin: str) -> bool:
    """Compara o PIN em tempo constante para evitar timing attacks."""
    return secrets.compare_digest(plain_pin.strip(), settings.APP_PIN.strip())


def create_access_token() -> tuple[str, datetime]:
    """Gera um token JWT válido por ACCESS_TOKEN_EXPIRE_DAYS (7 dias)."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": "cashapp_owner",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)
    return token, expires_at


def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Dependência usada nas rotas protegidas para exigir Bearer Token válido."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado. Informe seu PIN.",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET, 
            algorithms=[ALGORITHM],
        )
        subject = payload.get("sub")
        if subject != "cashapp_owner":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido.",
            )
        return subject
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão expirada (7 dias). Digite seu PIN novamente.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
        )