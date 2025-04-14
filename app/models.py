# app/models.py
import enum
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, EmailStr
from sqlalchemy import TIMESTAMP
from sqlmodel import Field, Relationship, SQLModel


# Enums
class AccountType(str, enum.Enum):
    SAVINGS = "savings"
    CURRENT = "current"

class AccountStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"
    DORMANT = "dormant"
    CLOSED = "closed"

class TransactionType(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    

# User Models
class UserBase(SQLModel):
    google_sub: str = Field(index=True, unique=True, description="Google User ID (subject claim)")
    email: EmailStr = Field(index=True, unique=True, description="User's Email")
    full_name: str | None = Field(default=None)
    given_name: str | None = Field(default=None)
    family_name: str | None = Field(default=None)
    picture: str | None = Field(default=None, description="URL for profile picture")
    address: str | None = Field(default="10 Janpath, New Delhi 110001", max_length=50)
    
## DB Table Model
class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    is_active: bool = Field(default=True, description="User account status")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=TIMESTAMP(timezone=True), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=TIMESTAMP(timezone=True), nullable=False)

    accounts: list["Account"] = Relationship(back_populates="user")
    
## API I/O
class UserCreate(UserBase):
    pass

class UserInfo(UserBase):
    id: int

# Account Models
class AccountBase(SQLModel):
    account_number: str = Field(index=True, unique=True, max_length=16)
    balance: Decimal = Field(default=0.0, description="Account balance")
    type: AccountType = Field(default=AccountType.SAVINGS, description="Account type")
    status: AccountStatus = Field(default=AccountStatus.ACTIVE, description="Account status")

    user_id: int | None = Field(default=None, foreign_key="user.id", index=True, nullable=False)

class Account(AccountBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=TIMESTAMP(timezone=True), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=TIMESTAMP(timezone=True), nullable=False)

    user: User | None = Relationship(back_populates="accounts")
    transactions: list["Transaction"] = Relationship(back_populates="account")

class AccountCreate(AccountBase):
    pass

class AccountInfo(AccountBase):
    id: int

class AccountInfoWithUser(AccountInfo):
    user: UserInfo | None = None

# Transaction Models
class TransactionBase(SQLModel):
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=TIMESTAMP(timezone=True), index=True, nullable=False)
    description: str = Field(max_length=30)
    amount: Decimal = Field(nullable=False, description="Transaction amount")
    type: TransactionType = Field(default=TransactionType.DEBIT, index=True, description="Transaction type")
    
    account_id: int | None = Field(default=None, foreign_key="account.id", index=True, nullable=False)

class Transaction(TransactionBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    account: Account | None = Relationship(back_populates="transactions")

class TransactionCreate(TransactionBase):
    pass

class TransactionInfo(TransactionBase):
    id: int

class TransactionInfoWithAccount(TransactionInfo):
    account: AccountInfo | None = None


# Token Models

class GoogleToken(BaseModel):
    token: str

class BackendToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo
