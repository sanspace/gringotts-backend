# app/main.py
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db_engine import async_engine #, create_db_and_tables
from app.gauth import get_current_user
from app.gauth import router as auth_router
from app.models import User, UserInfo


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("App startup")
    
    # print("Running create_db_and_tables() [DEV/TEST ONLY]")
    # await create_db_and_tables() # ONLY IN DEVELOPMENT
    # print("Table creation check complete")
    
    print("App Ready to serve requests")
    yield # APP RUNS NOW
    
    print("App shutdown")
    await async_engine.dispose()
    print("Engine disposed")
    

app = FastAPI(
    title="Gringotts Banking Corp",
    lifespan=lifespan
)

origins = [
    settings.FRONTEND_ORIGIN_URL
    # You might add other origins later if needed (e.g., staging URL)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True, # Allows cookies/auth headers
    allow_methods=["*"],    # Allows all standard methods (GET, POST, etc.)
    allow_headers=["*"],    # Allows all headers
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])

# --- Example Protected Endpoint ---
@app.get("/users/me", response_model=UserInfo)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Gets information about the currently authenticated user."""
    return UserInfo.model_validate(current_user)

@app.get('/')
def root():
    """Root endpoint returning a simple message."""
    return {'message': 'Hello World from Gringotts Backend!'}

# Add other endpoints here later