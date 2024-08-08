from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from jose import JWTError, ExpiredSignatureError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
from os import getenv
import time

# from db_module.db_utilities import retrieve_existing_accounts
from db_module.db_manager import DatabaseManager


load_dotenv()

SECRET_KEY = getenv("SECRET_KEY")
ALGORITHM = getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 600
ROUTER_PREFIX = "/auth"
CRYPTCONTEXT_SCHEME = getenv("CRYPTCONTEXT_SCHEME")


db = DatabaseManager()


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    disabled: bool


class UserInDB(User):
    password_hashed: str


pwd_context = CryptContext(schemes=[CRYPTCONTEXT_SCHEME], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{ROUTER_PREFIX}/token")


def verify_password(plaintext_password, password_hashed):
    return pwd_context.verify(plaintext_password, password_hashed)


def get_password_hash(plaintext_password):
    return pwd_context.hash(plaintext_password)


def get_user(username: str):
    # accounts = retrieve_existing_accounts()
    accounts = db.retrieve_existing_accounts()
    if username in accounts:
        user_data = accounts[username]
        return UserInDB(**user_data)


def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.password_hashed):
        return False

    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()

    # Expiry is compared to UTC time on validation, so it must be set to UTC + delta
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)

    to_encode["exp"] = expire

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """_summary_

    Args:
        token (str, optional): _description_. Defaults to Depends(oauth2_scheme).

    Raises:
        credential_exception: _description_
        HTTPException: _description_
        credential_exception: _description_
        credential_exception: _description_

    Returns:
        _type_: _description_
    """
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        print(f"{token=}")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"{payload=}")

        username: str = payload.get("sub")
        print(f"{username=}")
        if username is None:
            raise credential_exception

        token_data = TokenData(username=username)

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except JWTError:
        raise credential_exception

    user = get_user(username=token_data.username)

    if user is None:
        raise credential_exception

    return user


async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    """_summary_

    Args:
        current_user (UserInDB, optional): _description_. Defaults to Depends(get_current_user).

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Account disabled"
        )

    return current_user


router = APIRouter(prefix=ROUTER_PREFIX)


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    print(f"token issued for {ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/")
def ping():
    return "Auth router is running"


@router.get("/secure")
def ping_secure(current_user: User = Depends(get_current_active_user)):
    return "Secure auth router is running"


@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.get("/users/me/items")
async def read_own_items(current_user: User = Depends(get_current_active_user)):
    return [{"item_id": 1, "owner": current_user}]
