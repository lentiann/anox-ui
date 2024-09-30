import socketio
import redis.asyncio as redis
from socketio import AsyncRedisManager

from apps.webui.models.users import Users
from utils.utils import decode_token

# redis_client = redis.Redis(host="localhost", port=6379, db=0)

redis_url = "rediss://default:AVNS_NCOH8RXCRTrfzv5JS0e@db-caching-fra1-71936-do-user-17488949-0.d.db.ondigitalocean.com:25061"

redis_client = redis.Redis(
    host="db-caching-fra1-71936-do-user-17488949-0.d.db.ondigitalocean.com",
    port=25061,
    password="AVNS_NCOH8RXCRTrfzv5JS0e",
    username="default",
    ssl=True,
    ssl_cert_reqs=None,
    # ssl_ca_certs='/path/to/ca-certificate.crt',
)
mgr = AsyncRedisManager(redis_url)

sio = socketio.AsyncServer(
    cors_allowed_origins=["*"],
    client_manager=mgr,
    async_mode="asgi",
)
app = socketio.ASGIApp(sio, socketio_path="/ws/socket.io")

# Timeout duration in seconds
TIMEOUT_DURATION = 3


async def get_user_count():
    count = 0
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(
            cursor=cursor, match="USER_POOL:*", count=100
        )
        count += len(keys)
        if cursor == 0:
            break
    return count


async def get_models_in_use():
    models_in_use = set()
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(
            cursor=cursor, match="USAGE_POOL:*", count=100
        )
        for key in keys:
            key_str = key.decode()
            parts = key_str.split(":")
            if len(parts) >= 2:
                model_id = parts[1]
                models_in_use.add(model_id)
        if cursor == 0:
            break
    return list(models_in_use)


# @sio.event
# async def connect(sid, environ, auth):
#     user = None
#     if auth and "token" in auth:
#         data = decode_token(auth["token"])

#         if data and "id" in data:
#             user = Users.get_user_by_id(data["id"])

#         if user:
#             # Store the session ID and user ID in Redis
#             await redis_client.hset("SESSION_POOL", sid, user.id)

#             # Add the session ID to the set of sessions for the user
#             await redis_client.sadd(f"USER_POOL:{user.id}", sid)

#             # Have the client join a room named after their client_id (user.id)
#             await sio.enter_room(sid, user.id)  # Ensure this matches client_id

#             print(f"user {user.name}({user.id}) connected with session ID {sid}")

#             # Update user count and usage models
#             user_count = await get_user_count()
#             await sio.emit("user-count", {"count": user_count})
#             await sio.emit("usage", {"models": await get_models_in_use()})

#             return True  # Accept the connection
#     print(f"Connection rejected for sid {sid}")
#     return False  # Reject the connection


@sio.event
async def connect(sid, environ, auth):
    user = None
    if auth and "token" in auth and "client_id" in auth:
        data = decode_token(auth["token"])

        if data and "id" in data:
            user = Users.get_user_by_id(data["id"])

        if user and auth["client_id"] == str(
            user.id
        ):  # Ensure client_id matches user.id
            # Store the session ID and user ID in Redis
            await redis_client.hset("SESSION_POOL", sid, user.id)

            # Add the session ID to the set of sessions for the user
            await redis_client.sadd(f"USER_POOL:{user.id}", sid)

            # Have the client join a room named after their client_id (user.id)
            await sio.enter_room(sid, user.id)

            print(f"user {user.name}({user.id}) connected with session ID {sid}")

            # Update user count and usage models
            user_count = await get_user_count()
            await sio.emit("user-count", {"count": user_count})
            await sio.emit("usage", {"models": await get_models_in_use()})

            return True  # Accept the connection

    print(f"Connection rejected for sid {sid}")
    return False  # Reject the connection


@sio.on("user-join")
async def user_join(sid, data):
    print("user-join", sid, data)

    auth = data.get("auth")
    if not auth or "token" not in auth:
        return

    token_data = decode_token(auth["token"])
    if token_data is None or "id" not in token_data:
        return

    user = Users.get_user_by_id(token_data["id"])
    if not user:
        return

    # Store the session ID and user ID in Redis
    await redis_client.hset("SESSION_POOL", sid, user.id)

    # Add the session ID to the set of sessions for the user
    await redis_client.sadd(f"USER_POOL:{user.id}", sid)

    # Have the client join a room named after their client_id (user.id)
    await sio.enter_room(sid, user.id)  # Ensure consistency

    print(f"user {user.name}({user.id}) connected with session ID {sid}")

    # Update user count
    user_count = await get_user_count()
    await sio.emit("user-count", {"count": user_count})

    # Optionally, emit the models in use
    models_in_use = await get_models_in_use()
    await sio.emit("usage", {"models": models_in_use})


@sio.on("user-count")
async def user_count(sid):
    count = await get_user_count()
    await sio.emit("user-count", {"count": count})


@sio.on("usage")
async def usage(sid, data):
    model_id = data["model"]
    # Create a unique key for the model and session ID
    key = f"USAGE_POOL:{model_id}:{sid}"

    # Set the key with an expiration time
    await redis_client.set(key, 1, ex=TIMEOUT_DURATION)

    # Broadcast the usage data to all clients
    models_in_use = await get_models_in_use()
    await sio.emit("usage", {"models": models_in_use})


# @sio.event
# async def disconnect(sid):
#     user_id = await redis_client.hget("SESSION_POOL", sid)
#     if user_id:
#         user_id = user_id.decode()  # Convert bytes to string

#         # Remove the session ID from SESSION_POOL
#         await redis_client.hdel("SESSION_POOL", sid)

#         # Remove the session ID from the user's set
#         await redis_client.srem(f"USER_POOL:{user_id}", sid)

#         # If the user's session set is empty, delete it
#         user_sids = await redis_client.smembers(f"USER_POOL:{user_id}")
#         if not user_sids:
#             await redis_client.delete(f"USER_POOL:{user_id}")

#         # Remove the client from their room
#         await sio.leave_room(sid, user_id)

#         # Update user count
#         user_count = await get_user_count()
#         await sio.emit("user-count", {"count": user_count})
#     else:
#         print(f"Unknown session ID {sid} disconnected")


@sio.event
async def disconnect(sid):
    user_id = await redis_client.hget("SESSION_POOL", sid)
    if user_id:
        user_id = user_id.decode()  # Convert bytes to string

        # Remove the session ID from SESSION_POOL
        await redis_client.hdel("SESSION_POOL", sid)

        # Remove the session ID from the user's set
        await redis_client.srem(f"USER_POOL:{user_id}", sid)

        # If the user's session set is empty, delete it
        user_sids = await redis_client.smembers(f"USER_POOL:{user_id}")
        if not user_sids:
            await redis_client.delete(f"USER_POOL:{user_id}")

        # Remove the client from their room
        await sio.leave_room(sid, user_id)

        # Update user count
        user_count = await get_user_count()
        await sio.emit("user-count", {"count": user_count})
    else:
        print(f"Unknown session ID {sid} disconnected")


def get_event_emitter(request_info):
    async def __event_emitter__(event_data):
        client_id = request_info.get("client_id")  # Ensure this key exists
        if not client_id:
            print("No client_id in request_info")
            return

        await sio.emit(
            "chat-events",
            {
                "chat_id": request_info["chat_id"],
                "message_id": request_info["message_id"],
                "data": event_data,
            },
            room=client_id,
        )

    return __event_emitter__


def get_event_call(request_info):
    async def __event_call__(event_data):
        client_id = request_info.get("client_id")
        if not client_id:
            print("No client_id in request_info")
            return None

        response = await sio.call(
            "chat-events",
            {
                "chat_id": request_info["chat_id"],
                "message_id": request_info["message_id"],
                "data": event_data,
            },
            to=client_id,
        )
        return response

    return __event_call__
