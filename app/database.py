from app.models import UserInDB

# --- Database Stub (Replace with your actual DB logic) ---
# In-memory "database" for demonstration purposes
fake_users_db: dict[str, UserInDB] = {}
user_id_counter = 1

async def get_user_by_google_sub(sub: str) -> UserInDB | None:
    """Finds a user by their Google Subject ID."""
    for user in fake_users_db.values():
        if user.google_sub == sub:
            return user
    return None

async def create_user(sub: str, email: str, name: str | None, given_name: str | None, family_name: str | None, picture: str | None) -> UserInDB:
    """Creates a new user in the database."""
    global user_id_counter
    new_user = UserInDB(
        id=user_id_counter,
        google_sub=sub,
        email=email,
        full_name=name,
        given_name=given_name,
        family_name=family_name,
        picture=picture,
        is_active=True
    )
    fake_users_db[sub] = new_user # Using sub as key here for simplicity
    user_id_counter += 1
    print(f"Created new user: {new_user.model_dump_json(indent=2)}") # For debugging
    return new_user
