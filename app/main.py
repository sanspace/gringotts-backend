# app/main.py
import os
from datetime import timedelta

from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.database import create_user, get_user_by_google_sub
from app.gauth import create_backend_access_token, get_current_user
from app.models import BackendToken, GoogleToken, UserInDB

# Load environment variables from .env file (especially for FRONTEND_ORIGIN_URL)
load_dotenv() 

# Load from environment variables or a config file
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
BACKEND_JWT_SECRET_KEY = os.getenv("BACKEND_JWT_SECRET_KEY")
BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


if not all([GOOGLE_CLIENT_ID, BACKEND_JWT_SECRET_KEY]):
    raise ValueError("Missing required environment variables: GOOGLE_CLIENT_ID, BACKEND_JWT_SECRET_KEY")


app = FastAPI(
    title="Gringotts Banking Corp"
)

# Get allowed origin from environment variable - IMPORTANT!
frontend_origin = os.getenv("FRONTEND_ORIGIN_URL", "http://localhost:5173") # Default to local Vite dev server if not set
print(f"Using frontend origin: {frontend_origin}")

origins = [
    frontend_origin,
    # You might add other origins later if needed (e.g., staging URL)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True, # Allows cookies/auth headers
    allow_methods=["*"],    # Allows all standard methods (GET, POST, etc.)
    allow_headers=["*"],    # Allows all headers
)

# --- Authentication Endpoint ---
@app.post("/auth/google", response_model=BackendToken)
async def login_with_google(google_token_data: GoogleToken = Body(...)):
    """
    Receives Google ID token from frontend, verifies it,
    finds/creates user, and returns a backend JWT.
    """
    google_token = google_token_data.token
    request = google_requests.Request()

    try:
        # Verify the Google ID token
        id_info = id_token.verify_oauth2_token(
            google_token, request, GOOGLE_CLIENT_ID
        )

        # --- IMPORTANT: Check if token was issued by Google ---
        # Redundant check as verify_oauth2_token does this, but good practice to know
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise HTTPException(status_code=401, detail="Invalid token issuer")

        google_sub = id_info.get('sub')
        email = id_info.get('email')
        name = id_info.get('name')
        given_name = id_info.get('given_name')
        family_name = id_info.get('family_name')
        picture = id_info.get('picture')

        if not google_sub or not email:
             raise HTTPException(status_code=400, detail="Missing required info (sub, email) in Google token")

        # Check if user exists in DB, otherwise create them
        user = await get_user_by_google_sub(google_sub)
        if not user:
            user = await create_user(sub=google_sub, email=email, name=name, given_name=given_name, family_name=family_name, picture=picture)
        elif not user.is_active:
             raise HTTPException(status_code=400, detail="User account is inactive")
        # Optional: Update user details (name, picture) if they changed in Google

        # Create backend access token containing internal user identifier
        access_token_expires = timedelta(minutes=BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES)
        # Include relevant info in the backend token payload (e.g., internal ID or google sub)
        # Using google_sub as the subject ('sub') of our backend token here:
        backend_access_token = create_backend_access_token(
            data={"sub": user.google_sub, "email": user.email}, # Add roles etc. if needed
            expires_delta=access_token_expires
        )

        # Return the backend token and user info
        return BackendToken(
            access_token=backend_access_token,
            token_type="bearer",
            user={ # Send back data needed by frontend immediately after login
                "id": user.id, # Internal ID
                "google_sub": user.google_sub,
                "email": user.email,
                "full_name": user.full_name,
                "given_name": user.given_name,
                "family_name": user.family_name,
                "picture": user.picture,
            }
        )

    except ValueError as e:
        # This might happen if the token is invalid or expired
        print(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google Token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during authentication.",
        )


# --- Example Protected Endpoint ---
@app.get("/users/me", response_model=UserInDB)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    """Gets information about the currently authenticated user."""
    return current_user

@app.get('/')
def root():
    """Root endpoint returning a simple message."""
    return {'message': 'Hello World from Gringotts Backend!'}

# Add other endpoints here later