import os
import hashlib
from flask import Flask
import telebot
from pymongo import MongoClient
from googletrans import Translator, LANGUAGES
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
API_KEY = os.getenv("API_KEY")
CHANNELS = os.getenv("CHANNELS").split(",")

bot = telebot.TeleBot(BOT_TOKEN)
translator = Translator()
client = MongoClient(MONGO_URI)
db = client["translator_bot"]
users_collection = db["users"]


def hash_key(api_key):
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_credits():
    return (
        "\n\n👨‍💻 Created by [Rahat](https://t.me/RahatMx)"
        "\n🎬 Powered By [RM Movie Flix](https://t.me/RM_Movie_Flix)"
    )


def check_subscription(user_id):
    for channel in CHANNELS:
        status = bot.get_chat_member(channel, user_id)
        if status.status in ["left", "kicked"]:
            return False
    return True


@bot.message_handler(commands=["start"])
def start_handler(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        buttons = telebot.types.InlineKeyboardMarkup()
        for channel in CHANNELS:
            buttons.add(
                telebot.types.InlineKeyboardButton(
                    "Join Channel", url=f"https://t.me/{channel}"
                )
            )
        bot.send_message(
            message.chat.id,
            "🔴 Please join all the required channels to use this bot.",
            reply_markup=buttons,
        )
        return

    user_data = users_collection.find_one({"user_id": user_id})
    if not user_data:
        users_collection.insert_one({"user_id": user_id, "preferred_lang": "en"})

    buttons = telebot.types.InlineKeyboardMarkup()
    buttons.add(
        telebot.types.InlineKeyboardButton("🌍 Set Language", callback_data="set_language"),
        telebot.types.InlineKeyboardButton("📜 View Languages", callback_data="view_languages"),
    )
    bot.send_message(
        message.chat.id,
        "👋 Welcome to the Translator Bot!\n"
        "🌍 Translate text between multiple languages.\n"
        "Use the buttons below to explore options."
        f"{get_credits()}",
        reply_markup=buttons,
        parse_mode="Markdown",
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "set_language":
        bot.send_message(
            call.message.chat.id,
            "🗣️ Send me the language code (e.g., 'en' for English, 'bn' for Bangla) to set your preferred language.",
        )
    elif call.data == "view_languages":
        lang_list = "\n".join([f"{key} - {value}" for key, value in LANGUAGES.items()])
        bot.send_message(call.message.chat.id, f"🌍 Supported Languages:\n{lang_list}")


@bot.message_handler(func=lambda message: True)
def translate_handler(message):
    user_id = message.from_user.id
    user_data = users_collection.find_one({"user_id": user_id})
    preferred_lang = user_data.get("preferred_lang", "en")

    try:
        detected = translator.detect(message.text)
        translated = translator.translate(message.text, dest=preferred_lang)
        buttons = telebot.types.InlineKeyboardMarkup()
        buttons.add(
            telebot.types.InlineKeyboardButton("🔁 Translate Again", callback_data="set_language")
        )
        bot.send_message(
            message.chat.id,
            f"🌐 Detected Language: {LANGUAGES[detected.lang].capitalize()}\n"
            f"📜 Translation ({LANGUAGES[preferred_lang].capitalize()}): {translated.text}"
            f"{get_credits()}",
            reply_markup=buttons,
            parse_mode="Markdown",
        )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ Error: {e}{get_credits()}",
            parse_mode="Markdown",
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
