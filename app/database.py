# app/database.py
from sqlalchemy.ext.asyncio import AsyncSession  # Import AsyncSession
from sqlmodel import select  # Import select

# Import your table model and create model
from app.models import User, UserCreate


async def get_user_by_google_sub(sub: str, session: AsyncSession) -> User | None:
    """
    Finds a user by their Google Subject ID using an async database session.
    """
    print(f"Database: Querying user with google_sub: {sub}") # Debugging
    statement = select(User).where(User.google_sub == sub)
    result = await session.execute(statement)
    
    user_row = result.first()

    if user_row:
        user: User = user_row[0]
        print(f"Database: Found user: {user.email}")
        return user
    
    print(f"Database: User not found with google_sub: {sub}")
    return None

async def create_user(user_data: UserCreate, session: AsyncSession) -> User:
    """
    Creates a new user in the database using an async session.
    Accepts validated data conforming to the UserCreate model.
    """
    print(f"Database: Creating user with email: {user_data.email}") # Debugging
    # Create a User table model instance from the UserCreate input data
    # SQLModel handles mapping the fields. id, created_at, updated_at use defaults.
    db_user = User.model_validate(user_data)

    # Add the new user object to the session
    session.add(db_user)

    try:
        # Commit the transaction to save the user to the database
        await session.commit()
        # Refresh the object to get the database-generated ID and default values
        await session.refresh(db_user)
        print(f"Database: User created successfully with ID: {db_user.id}") # Debugging
        print(f"Created user details: {db_user.model_dump_json(indent=2)}")
        return db_user
    except Exception as e:
        # If commit fails (e.g., unique constraint violation), rollback
        print(f"Database Error: Failed to create user. Rolling back. Error: {e}")
        await session.rollback()
        # Re-raise the exception so the calling function knows about the failure
        raise e


# --- Add other User related DB functions as needed ---

async def get_user_by_id(user_id: int, session: AsyncSession) -> User | None:
    """Finds a user by their internal primary key ID."""
    print(f"Database: Querying user with ID: {user_id}")
    user = await session.get(User, user_id) # session.get() is efficient for PK lookups
    if user:
        print(f"Database: Found user: {user.email}")
    else:
        print(f"Database: User not found with ID: {user_id}")
    return user

# Example: Function to update user details (you'll need an Update model)
# async def update_user(user_id: int, update_data: UserUpdate, session: AsyncSession) -> User | None:
#     user = await session.get(User, user_id)
#     if not user:
#         return None
#     update_dict = update_data.model_dump(exclude_unset=True) # Get only provided fields
#     for key, value in update_dict.items():
#         setattr(user, key, value)
#     # Mark updated_at maybe? Depends on your strategy
#     user.updated_at = datetime.now(timezone.utc)
#     session.add(user)
#     await session.commit()
#     await session.refresh(user)
#     return user