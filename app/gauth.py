# app/gauth.py
import traceback
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jose import JWTError, jwt
# --- Import DB requirements ---
from sqlalchemy.ext.asyncio import AsyncSession  # Import AsyncSession

from app.config import settings
# Import DB functions and necessary models
from app.database import create_user, get_user_by_google_sub
from app.db_engine import get_session  # Import session dependency
# Import UserCreate model for creating users
from app.models import BackendToken, GoogleToken, User, UserCreate, UserInfo

# Create an APIRouter instance
router = APIRouter()

# --- JWT Utilities (Backend Token) ---
# (This function remains the same)
def create_backend_access_token(data: dict, expires_delta: timedelta | None = None):
    """Generates a JWT signed by the backend."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.BACKEND_JWT_SECRET_KEY,
        algorithm=settings.BACKEND_JWT_ALGORITHM
    )
    return encoded_jwt

# --- OAuth2 Scheme ---
# Ensure the tokenUrl matches the path where users obtain the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/google")

# --- get_current_user Dependency ---
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session) # <-- Inject Session
) -> User: # Returns the full User DB model
    """
    Dependency to verify backend JWT and get the corresponding
    user from the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.BACKEND_JWT_SECRET_KEY,
            algorithms=[settings.BACKEND_JWT_ALGORITHM]
        )
        # Use google_sub stored in the backend token to identify the user
        google_sub: str | None = payload.get("sub")
        if google_sub is None:
            print("JWT decode error: 'sub' claim missing in token payload.")
            raise credentials_exception

        # --- Fetch user fresh from DB using the session ---
        print(f"get_current_user: Fetching user for sub: {google_sub}")
        user = await get_user_by_google_sub(google_sub, session=session) # <-- Pass session
        if user is None:
             print(f"get_current_user: User not found in DB for sub: {google_sub}")
             raise credentials_exception
        if not user.is_active:
             print(f"get_current_user: User is inactive: {google_sub}")
             # Perhaps 403 Forbidden is more appropriate here
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
        print(f"get_current_user: User authenticated: {user.email}")
        return user # Return the User DB model object
    except JWTError as e:
        print(f"JWT decode error: {e}")
        raise credentials_exception
    except HTTPException as e:
         raise e # Re-raise HTTP exceptions directly
    except Exception as e:
        # Catch potential DB errors or other issues
        print(f"Error getting current user: {e}")
        raise credentials_exception # Raise the standard auth error

# --- Authentication Endpoint ---
@router.post("/google", response_model=BackendToken)
async def login_with_google(
    google_token_data: GoogleToken = Body(...),
    session: AsyncSession = Depends(get_session) # <-- Inject Session
):
    """
    Receives Google ID token from frontend, verifies it with Google,
    finds or creates the corresponding user in the local database,
    and returns a backend-specific JWT access token.
    """
    google_token = google_token_data.token
    request = google_requests.Request()

    try:
        # Verify the Google ID token using client ID from settings
        print("Verifying Google token...")
        id_info = id_token.verify_oauth2_token(
            google_token, request, settings.GOOGLE_CLIENT_ID
        )
        print("Google token verified.")

        # Basic validation of issuer
        if id_info.get('iss') not in ['accounts.google.com', 'https://accounts.google.com']:
            print(f"Invalid token issuer: {id_info.get('iss')}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token issuer")

        # Extract required information
        google_sub = id_info.get('sub')
        email = id_info.get('email')

        if not google_sub or not email:
             print("Missing 'sub' or 'email' in verified Google token.")
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required info (sub, email) in Google token")

        # --- Check if user exists in DB ---
        user = await get_user_by_google_sub(google_sub, session=session) # <-- Pass session

        if not user:
            print(f"User not found for sub {google_sub}, creating new user...")
            # --- Prepare data using UserCreate model ---
            # Create the object expected by the database create function
            user_create_data = UserCreate(
                google_sub=google_sub,
                email=email,
                full_name=id_info.get('name'),
                given_name=id_info.get('given_name'),
                family_name=id_info.get('family_name'),
                picture=id_info.get('picture')
                # address will use the default defined in UserBase/User model for now
            )
            # --- Use DB function with session and UserCreate object ---
            user = await create_user(user_data=user_create_data, session=session) # <-- Pass session & UserCreate

        elif not user.is_active:
            print(f"Login attempt by inactive user: {user.email}")
            # Use 403 Forbidden as the user exists but cannot log in
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")
        else:
            print(f"User found and active: {user.email}")
            # Optional: Update user details (name, picture) from Google if desired
            # user.full_name = id_info.get('name') or user.full_name
            # user.picture = id_info.get('picture') or user.picture
            # session.add(user)
            # await session.commit()
            # await session.refresh(user)

        # --- Create backend access token ---
        # The 'sub' in our backend token refers to the google_sub
        access_token_expires = timedelta(minutes=settings.BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES)
        backend_access_token = create_backend_access_token(
            data={"sub": user.google_sub, "email": user.email}, # Add roles etc. if needed
            expires_delta=access_token_expires
        )
        print("Backend access token created.")

        # --- Prepare response user info ---
        # Convert the User DB model object to the UserInfo API response model
        # This ensures only the fields defined in UserInfo are sent back
        user_info_for_token = UserInfo.model_validate(user)

        return BackendToken(
            access_token=backend_access_token,
            token_type="bearer",
            user=user_info_for_token
        )

    except ValueError as e:
        # Specific error from id_token.verify_oauth2_token (e.g., expired, wrong audience)
        print(f"Google Token verification ValueError: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google Token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException as e:
         # Re-raise HTTP exceptions we raised deliberately
         raise e
    except Exception as e: # Catch-all for unexpected errors
        # --- Temporary Detailed Debugging ---
        print(f"\n!!! UNEXPECTED ERROR DETAILS !!!")
        print(f"Error Type: {type(e)}")
        print(f"Error Args: {e.args}")
        print(f"Error String: {e}")
        print("--- Traceback ---")
        traceback.print_exc() # Print the full traceback to console
        print("-----------------\n")
        # --- End Detailed Debugging ---

        # Original logging and raise
        print(f"An unexpected error occurred during Google auth endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during authentication.",
        )
