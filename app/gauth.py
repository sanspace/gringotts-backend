import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.database import get_user_by_google_sub
from app.models import UserInDB

load_dotenv()

BACKEND_JWT_SECRET_KEY = os.getenv("BACKEND_JWT_SECRET_KEY")
BACKEND_JWT_ALGORITHM = os.getenv("BACKEND_JWT_ALGORITHM", "HS256")
BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# --- JWT Utilities (Backend Token) ---
def create_backend_access_token(data: dict, expires_delta: timedelta | None = None):
    """Generates a JWT signed by the backend."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, BACKEND_JWT_SECRET_KEY, algorithm=BACKEND_JWT_ALGORITHM)
    return encoded_jwt

# OAuth2 scheme for backend token verification
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/google") # Adjust tokenUrl if needed

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """Dependency to verify backend JWT and get user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, BACKEND_JWT_SECRET_KEY, algorithms=[BACKEND_JWT_ALGORITHM])
        google_sub: str = payload.get("sub") # Assuming you put google_sub in the backend token's sub
        if google_sub is None:
            raise credentials_exception
        # Here you might want to fetch the user fresh from DB based on the ID/sub in the token
        # For simplicity, we'll assume the sub is enough for now or trust the token data
        user = await get_user_by_google_sub(google_sub) # Or use user_id if stored in token
        if user is None:
             raise credentials_exception
        if not user.is_active:
             raise HTTPException(status_code=400, detail="Inactive user")
        return user # Return your internal user object
    except JWTError:
        raise credentials_exception
    except Exception as e:
        print(f"Error getting current user: {e}") # Debugging
        raise credentials_exception
    