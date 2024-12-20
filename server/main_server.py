import psutil
import os

# Set CPU affinity for the main process to core 0
p = psutil.Process(os.getpid())
p.cpu_affinity([0])

import asyncio
import logging
from contextlib import asynccontextmanager
from pprint import pprint
import platform

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    status,
)
from pydantic import BaseModel, Field

try:
    from routers.auth import router as auth_router
    from routers.auth import get_current_active_user, get_current_user
except:
    from server.routers.auth import router as auth_router
    from server.routers.auth import get_current_active_user, get_current_user

try:
    from services.db_manager import db
    from services.connection_manager import ConnectionManager
except:
    from server.services.db_manager import db
    from server.services.connection_manager import ConnectionManager

os_name = platform.platform()
if "Windows" in os_name:
    import winloop
elif "Linux" in os_name:
    import uvloop

logger = logging.getLogger('Server')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
formatter.datefmt = '%H:%M:%S'
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    loop = asyncio.get_event_loop()
    # loop_type = "uvloop" if "uvloop" in str(type(loop)).lower() else type(loop).__name__
    print(f"Current event loop: {str(type(loop))}")

    yield

    # Shutdown logic
    if connection_man.listener_task:
        connection_man.listener_task.cancel()
        try:
            await connection_man.listener_task
        except asyncio.CancelledError:
            pass
    # Close all active WebSocket connections
    for connection in connection_man.active_connections.values():
        await connection["ws"].close()
    connection_man.active_connections.clear()
    db.close_all()


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)

# Endpoint to get server health
@app.get("/", status_code=status.HTTP_200_OK)
async def server_health():
    """Verify connection to database and return server health"""
    db_status = await connection_man.db.verify_connection_and_tables()
    if db_status.get("status"):
        return {"status": "ready"}

    error_details = []
    if not db_status["status"]:
        error_details.append(db_status["details"])

    return {"status": ", ".join(error_details)}


# Endpoint to ping server
@app.get("/ping", status_code=status.HTTP_200_OK)
async def ping():
    """Get a static response from server"""
    return {"status": "alive"}


@app.get("/tables")
def tables():
    db.init_database()
    return db.list_tables()


@app.get("/filepath")
def get_filepath():
    db.init_database()
    return db.read_db_filepath()

@app.get("/check-loop")
async def check_loop():
    """Endpoint to confirm the type of event loop being used, for debugging purposes"""
    loop = asyncio.get_event_loop()
    loop_type = type(loop).__name__
    
    if "Windows" in os_name:
        is_winloop = isinstance(loop, winloop.Loop)
        return {
            "os": os_name,
            "loop": loop_type,
            "is_winloop": is_winloop,
            "is_uvloop": False
        }
    elif "Linux" in os_name:
        is_uvloop = isinstance(loop, uvloop.Loop)
        return {
            "os": os_name,
            "loop": loop_type,
            "is_winloop": False,
            "is_uvloop": is_uvloop
        }
    else:
        return {
            "os": os_name,
            "loop": loop_type,
            "is_winloop": False,
            "is_uvloop": False,
            "message": "Unknown operating system"
        }


connection_man = ConnectionManager(logger, db)


class AccountCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=255)


@app.post("/create_account", status_code=status.HTTP_201_CREATED)
async def create_account_endpoint(account: AccountCreate):
    """Endpoint to create an account"""
    return db.create_account(account.username, account.password)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Websocket endpoint to send and receive messages"""
    try:
        auth_header = websocket.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            print("Invalid or missing Authorization header")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        token = auth_header.split("Bearer ")[1]

        try:
            current_user = await get_current_user(token)
            active_user = await get_current_active_user(current_user)
            # print(f"Authenticated user: {active_user.username}")
        except HTTPException as e:
            print(f"Authentication failed: {str(e)}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # User is authenticated and active, proceed with the WebSocket connection
        await connection_man.connect(websocket, active_user.username)

        while True:
            try:
                message: bytes = await websocket.receive_bytes()
            except RuntimeError as e:
                if str(e) == 'WebSocket is not connected. Need to call "accept" first.':
                    pass
                else:
                    logger.warning(f"Websocket endpoint {type(e).__name__}: {e}")
                await connection_man.disconnect(active_user.username)
            try:
                await connection_man.handle_incoming_message(message, active_user.username)
            except Exception as e:
                print(f"Exception during 'while True' loop of main_server websocket endpoint: {type(e).__name__}: {e}")
                await connection_man.disconnect(active_user.username)
    except WebSocketDisconnect:
        await connection_man.disconnect(active_user.username)
    except asyncio.CancelledError:
        await connection_man.disconnect(active_user.username)
    except Exception as e:
        logger.warning(f"Websocket endpoint Exception: {type(e).__name__}: {e}", exc_info=True)
