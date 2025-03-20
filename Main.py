from pyrogram import Client, filters
from pymongo import MongoClient
from config import BOT_TOKEN, API_ID, API_HASH, MONGO_URL

app = Client("UserTrackerBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)
db_client = MongoClient(MONGO_URL)
db = db_client["telegram_tracker"]

# Start command with video
@app.on_message(filters.command("start"))
async def start(_, message):
    video_url = "https://files.catbox.moe/ir15jt.mp4"
    await message.reply_video(video=video_url, caption="I'm Krish Spy Bot")

# Track user activity
@app.on_message(filters.text & ~filters.private)
async def track_activity(client, message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username

    # Store username history
    user_data = db.users.find_one({"user_id": user_id})
    if user_data:
        if username and username not in user_data.get("past_usernames", []):
            db.users.update_one({"user_id": user_id}, {"$push": {"past_usernames": username}})
    else:
        db.users.insert_one({"user_id": user_id, "past_usernames": [username] if username else []})

    # Track message count in group
    db.messages.update_one({"chat_id": chat_id, "user_id": user_id}, {"$inc": {"count": 1}}, upsert=True)

    # Track last active group
    db.users.update_one({"user_id": user_id}, {"$set": {"last_active_group": chat_id}}, upsert=True)

    # Track user interactions (for top friends)
    if message.reply_to_message:
        replied_user_id = message.reply_to_message.from_user.id
        db.interactions.update_one(
            {"user_id": user_id, "friend_id": replied_user_id},
            {"$inc": {"count": 1}}, upsert=True
        )

# Command to get top 10 active users in a group
@app.on_message(filters.command("topusers"))
async def top_users(_, message):
    chat_id = message.chat.id
    top_users = db.messages.find({"chat_id": chat_id}).sort("count", -1).limit(10)

    response = "**Top 10 Active Users:**\n"
    for user in top_users:
        response += f"👤 {user['user_id']} - {user['count']} messages\n"
    
    await message.reply_text(response)

# Command to get a user's top 10 friends
@app.on_message(filters.command("myfriends"))
async def my_friends(_, message):
    user_id = message.from_user.id
    friends = db.interactions.find({"user_id": user_id}).sort("count", -1).limit(10)

    response = "**Your Top 10 Friends:**\n"
    for friend in friends:
        response += f"👤 {friend['friend_id']} - {friend['count']} interactions\n"
    
    await message.reply_text(response)

app.run()
