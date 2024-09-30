# import socketio
# import asyncio


# from apps.webui.models.users import Users
# from utils.utils import decode_token

# sio = socketio.AsyncServer(cors_allowed_origins=[], async_mode="asgi")
# app = socketio.ASGIApp(sio, socketio_path="/ws/socket.io")

# # Dictionary to maintain the user pool

# SESSION_POOL = {}
# USER_POOL = {}
# USAGE_POOL = {}
# # Timeout duration in seconds
# TIMEOUT_DURATION = 3


# @sio.event
# async def connect(sid, environ, auth):
#     user = None
#     if auth and "token" in auth:
#         data = decode_token(auth["token"])

#         if data is not None and "id" in data:
#             user = Users.get_user_by_id(data["id"])

#         if user:
#             SESSION_POOL[sid] = user.id
#             if user.id in USER_POOL:
#                 USER_POOL[user.id].append(sid)
#             else:
#                 USER_POOL[user.id] = [sid]

#             print(f"user {user.name}({user.id}) connected with session ID {sid}")

#             await sio.emit("user-count", {"count": len(set(USER_POOL))})
#             await sio.emit("usage", {"models": get_models_in_use()})


# @sio.on("user-join")
# async def user_join(sid, data):
#     print("user-join", sid, data)

#     auth = data["auth"] if "auth" in data else None
#     if not auth or "token" not in auth:
#         return

#     data = decode_token(auth["token"])
#     if data is None or "id" not in data:
#         return

#     user = Users.get_user_by_id(data["id"])
#     if not user:
#         return

#     SESSION_POOL[sid] = user.id
#     if user.id in USER_POOL:
#         USER_POOL[user.id].append(sid)
#     else:
#         USER_POOL[user.id] = [sid]

#     print(f"user {user.name}({user.id}) connected with session ID {sid}")

#     await sio.emit("user-count", {"count": len(set(USER_POOL))})


# @sio.on("user-count")
# async def user_count(sid):
#     await sio.emit("user-count", {"count": len(set(USER_POOL))})


# def get_models_in_use():
#     # Aggregate all models in use
#     models_in_use = []
#     for model_id, data in USAGE_POOL.items():
#         models_in_use.append(model_id)

#     return models_in_use


# @sio.on("usage")
# async def usage(sid, data):
#     model_id = data["model"]

#     # Cancel previous callback if there is one
#     if model_id in USAGE_POOL:
#         USAGE_POOL[model_id]["callback"].cancel()

#     # Store the new usage data and task

#     if model_id in USAGE_POOL:
#         USAGE_POOL[model_id]["sids"].append(sid)
#         USAGE_POOL[model_id]["sids"] = list(set(USAGE_POOL[model_id]["sids"]))

#     else:
#         USAGE_POOL[model_id] = {"sids": [sid]}

#     # Schedule a task to remove the usage data after TIMEOUT_DURATION
#     USAGE_POOL[model_id]["callback"] = asyncio.create_task(
#         remove_after_timeout(sid, model_id)
#     )

#     # Broadcast the usage data to all clients
#     await sio.emit("usage", {"models": get_models_in_use()})


# async def remove_after_timeout(sid, model_id):
#     try:
#         await asyncio.sleep(TIMEOUT_DURATION)
#         if model_id in USAGE_POOL:
#             print(USAGE_POOL[model_id]["sids"])
#             USAGE_POOL[model_id]["sids"].remove(sid)
#             USAGE_POOL[model_id]["sids"] = list(set(USAGE_POOL[model_id]["sids"]))

#             if len(USAGE_POOL[model_id]["sids"]) == 0:
#                 del USAGE_POOL[model_id]

#             # Broadcast the usage data to all clients
#             await sio.emit("usage", {"models": get_models_in_use()})
#     except asyncio.CancelledError:
#         # Task was cancelled due to new 'usage' event
#         pass


# @sio.event
# async def disconnect(sid):
#     if sid in SESSION_POOL:
#         user_id = SESSION_POOL[sid]
#         del SESSION_POOL[sid]

#         USER_POOL[user_id].remove(sid)

#         if len(USER_POOL[user_id]) == 0:
#             del USER_POOL[user_id]

#         await sio.emit("user-count", {"count": len(USER_POOL)})
#     else:
#         print(f"Unknown session ID {sid} disconnected")


# def get_event_emitter(request_info):
#     async def __event_emitter__(event_data):
#         await sio.emit(
#             "chat-events",
#             {
#                 "chat_id": request_info["chat_id"],
#                 "message_id": request_info["message_id"],
#                 "data": event_data,
#             },
#             to=request_info["session_id"],
#         )

#     return __event_emitter__


# def get_event_call(request_info):
#     async def __event_call__(event_data):
#         response = await sio.call(
#             "chat-events",
#             {
#                 "chat_id": request_info["chat_id"],
#                 "message_id": request_info["message_id"],
#                 "data": event_data,
#             },
#             to=request_info["session_id"],
#         )
#         return response

#     return __event_call__

from env import REDIS_URL
import socketio

from socketio import AsyncRedisManager

from apps.webui.models.users import Users
from utils.utils import decode_token
from redis_client import redis_client


mgr = AsyncRedisManager(REDIS_URL)

sio = socketio.AsyncServer(
    cors_allowed_origins=[],
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
        data = await decode_token(auth["token"])

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

    token_data = await decode_token(auth["token"])
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
