from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from jose import JWTError, ExpiredSignatureError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
from os import getenv
try:
    from services.db_manager import db
except:
    from server.services.db_manager import db


load_dotenv()

SECRET_KEY = getenv("SECRET_KEY")
ALGORITHM = getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 600
ROUTER_PREFIX = "/auth"
CRYPTCONTEXT_SCHEME = getenv("CRYPTCONTEXT_SCHEME")


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


def verify_password(plaintext_password: str, password_hashed: str):
    """
    Verify that a plaintext password matches its hashed version.

    Args:
        plaintext_password (str): The plaintext password to verify.
        password_hashed (str): The hashed password to compare against.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    return pwd_context.verify(plaintext_password, password_hashed)


def get_password_hash(plaintext_password: str):
    """
    Hash a plaintext password using the configured hashing algorithm.

    Args:
        plaintext_password (str): The plaintext password to hash.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(plaintext_password)


def get_user(username: str):
    """
    Retrieve a user from the database by username.

    Args:
        username (str): The username of the user to retrieve.

    Returns:
        UserInDB: The user object if found, None otherwise.
    """
    accounts: dict = db.retrieve_existing_accounts()
    if username in accounts:
        user_data = accounts[username]
        return UserInDB(**user_data)


def authenticate_user(username: str, password: str):
    """
    Authenticate a user by verifying their credentials.

    Args:
        username (str): The username of the user.
        password (str): The plaintext password of the user.

    Returns:
        UserInDB: The authenticated user object if successful, False otherwise.
    """
    user: UserInDB = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.password_hashed):
        return False

    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Create a JSON Web Token (JWT) for the authenticated user.

    Args:
        data (dict): The payload data to encode in the token.
        expires_delta (timedelta | None): Optional expiration duration for the token.

    Returns:
        str: The encoded JWT.
    """
    to_encode: dict = data.copy()

    # Expiry is compared to UTC time on validation, so it must be set to UTC + delta
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)

    to_encode["exp"] = expire

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """
    Retrieve the current user based on the provided JWT token.

    Args:
        token (str): The OAuth2 token provided in the request.

    Raises:
        HTTPException: If the token is invalid, expired, or the user cannot be found.

    Returns:
        UserInDB: The current authenticated user.
    """
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        username: str = payload.get("sub")
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

    user: UserInDB = get_user(username=token_data.username)

    if user is None:
        raise credential_exception

    return user


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """
    Retrieve the current active user, ensuring the account is not disabled.

    Args:
        current_user (UserInDB): The authenticated user from the token.

    Raises:
        HTTPException: If the user's account is disabled.

    Returns:
        UserInDB: The current active user.
    """
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Account disabled"
        )

    return current_user


router = APIRouter(prefix=ROUTER_PREFIX)


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> dict:
    """
    Authenticate a user and generate an access token.

    Args:
        form_data (OAuth2PasswordRequestForm): The login form data containing username and password.

    Raises:
        HTTPException: If the credentials are invalid.

    Returns:
        dict: A dictionary containing the access token and token type.
    """
    user: UserInDB = authenticate_user(form_data.username, form_data.password)
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
    # print(f"auth.py Authorized user: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/")
def ping() -> str:
    """
    Health check endpoint for the authentication router.

    Returns:
        str: A simple message indicating the router is running.
    """
    return "Auth router is running"


@router.get("/secure")
def ping_secure(current_user: User = Depends(get_current_active_user)) -> str:
    """
    Secure health check endpoint for the authentication router.

    Args:
        current_user (User): The currently authenticated and active user.

    Returns:
        str: A message indicating the secure endpoint is running.
    """
    return "Secure auth router is running"
