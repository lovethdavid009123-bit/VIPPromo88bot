import os
import re
import random
import logging
from io import BytesIO

from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from gtts import gTTS

# ---------- Config ----------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_URL = "https://t.me/cryptocum4"
CHANNEL_HANDLE = "@cryptocum4"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# In-memory stores
promo_drafts = {}       # user_id -> {"stage": ..., "text": ...}
game_sessions = {}      # user_id -> {"number": int, "attempts": int, "active": bool}

# ---------- Grammar Rules ----------
COMMON_FIXES = {
    r"\bi\b": "I",
    r"\bteh\b": "the",
    r"\brecieve\b": "receive",
    r"\bdefinately\b": "definitely",
    r"\bseperate\b": "separate",
    r"\boccured\b": "occurred",
    r"\bwich\b": "which",
    r"\bthier\b": "their",
    r"\bwierd\b": "weird",
    r"\bbecuase\b": "because",
    r"\bdont\b": "don't",
    r"\bcant\b": "can't",
    r"\bwont\b": "won't",
    r"\bim\b": "I'm",
    r"\bive\b": "I've",
    r"\bdoesnt\b": "doesn't",
    r"\bisnt\b": "isn't",
    r"\byoure\b": "you're",
    r"\balot\b": "a lot",
    r"\buntill\b": "until",
}


def correct_grammar(text: str) -> str:
    corrected = text
    for pattern, replacement in COMMON_FIXES.items():
        corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
    # Capitalize start of sentences
    corrected = re.sub(
        r"(^\s*|[.!?]\s+)([a-z])",
        lambda m: m.group(1) + m.group(2).upper(),
        corrected,
    )
    # Spacing fixes
    corrected = re.sub(r"\s+([,.!?;:])", r"\1", corrected)
    corrected = re.sub(r"([,.!?;:])(?=\S)", r"\1 ", corrected)
    corrected = re.sub(r"\s{2,}", " ", corrected).strip()
    return corrected


# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📣 Join Our Channel", url=CHANNEL_URL)],
        [InlineKeyboardButton("🎮 Play Games", callback_data="menu_games")],
        [InlineKeyboardButton("📢 Promo Bot", callback_data="menu_promo")],
    ]
    text = (
        "🤖 *VIPPromo88bot* — Your All-in-One Assistant\n\n"
        "✨ *Features:*\n"
        "✍️ Grammar Correction — just send any text\n"
        "🔊 Text-to-Speech — /tts your text\n"
        "🔢 Word Counter — /count your text\n"
        "📢 Promo Bot — /promo\n"
        "📣 Channel Redirect — /channel\n"
        "🎮 Gaming — /games\n\n"
        "👇 Choose an option below:"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ---------- Channel Redirect ----------
async def channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📣 Join @cryptocum4", url=CHANNEL_URL)]]
    await update.message.reply_text(
        "📣 *Join our official channel for exclusive updates, signals, and promos!*\n\n"
        f"👉 {CHANNEL_URL}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True,
    )


# ---------- Grammar Correction ----------
async def grammar_correction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    original = update.message.text or ""
    if not original.strip():
        return
    corrected = correct_grammar(original)
    if corrected == original:
        reply = "✅ *No grammar issues found!*"
    else:
        reply = (
            "✍️ *Grammar Correction*\n\n"
            f"*Original:*\n{original}\n\n"
            f"*Corrected:*\n{corrected}"
        )
    await update.message.reply_text(reply, parse_mode="Markdown")


# ---------- Text-to-Speech ----------
async def tts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔊 Usage: `/tts your text here`", parse_mode="Markdown")
        return
    text = " ".join(context.args)
    if len(text) > 500:
        await update.message.reply_text("⚠️ Keep TTS text under 500 characters.")
        return
    await update.message.reply_text("🎙️ Generating voice message...")
    try:
        tts_obj = gTTS(text=text, lang="en")
        buf = BytesIO()
        tts_obj.write_to_fp(buf)
        buf.seek(0)
        buf.name = "voice.mp3"
        await update.message.reply_voice(voice=buf)
    except Exception as e:
        logger.error(f"TTS error: {e}")
        await update.message.reply_text("❌ Failed to generate voice message.")


# ---------- Word Counter ----------
async def count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        text = " ".join(context.args)
    elif update.message.reply_to_message and update.message.reply_to_message.text:
        text = update.message.reply_to_message.text
    else:
        await update.message.reply_text(
            "🔢 Usage: `/count your text here`\nOr reply to any message with /count",
            parse_mode="Markdown",
        )
        return
    words = len(text.split())
    chars = len(text)
    chars_ns = len(text.replace(" ", ""))
    sentences = len(re.findall(r"[.!?]+", text)) or (1 if text.strip() else 0)
    paragraphs = len([p for p in text.split("\n") if p.strip()])
    reply = (
        "🔢 *Word Counter Results*\n\n"
        f"📝 Words: `{words}`\n"
        f"🔤 Characters (with spaces): `{chars}`\n"
        f"🔡 Characters (no spaces): `{chars_ns}`\n"
        f"📄 Sentences: `{sentences}`\n"
        f"📑 Paragraphs: `{paragraphs}`"
    )
    await update.message.reply_text(reply, parse_mode="Markdown")


# ---------- Promo Bot ----------
async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Create Promo", callback_data="promo_create")],
        [InlineKeyboardButton("📤 Send Promo", callback_data="promo_send")],
        [InlineKeyboardButton("❌ Cancel", callback_data="promo_cancel")],
    ]
    await update.message.reply_text(
        "📢 *Promo Bot*\n\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def promo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "promo_create":
        promo_drafts[user_id] = {"stage": "awaiting_text"}
        await query.edit_message_text(
            "📝 Send me the promo text.\n"
            "Format: *Title | Message*\n"
            "Or just send plain text.",
            parse_mode="Markdown",
        )
    elif data == "promo_send":
        draft = promo_drafts.get(user_id)
        if not draft or "text" not in draft:
            await query.edit_message_text(
                "⚠️ No promo draft found. Use /promo → Create Promo first."
            )
            return
        keyboard = [[InlineKeyboardButton("📣 Share to Channel", url=CHANNEL_URL)]]
        await query.edit_message_text(
            "📤 *Promo ready!*\n\n"
            f"{draft['text']}\n\n"
            "_Forward this to your audience or channel._",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    elif data == "promo_cancel":
        promo_drafts.pop(user_id, None)
        await query.edit_message_text("❌ Promo cancelled.")


async def handle_promo_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    draft = promo_drafts.get(user_id)
    if not draft or draft.get("stage") != "awaiting_text":
        return False
    text = update.message.text
    if "|" in text:
        title, _, body = text.partition("|")
        formatted = f"*{title.strip()}*\n\n{body.strip()}"
    else:
        formatted = f"*📢 Promo*\n\n{text.strip()}"
    promo_drafts[user_id] = {"stage": "ready", "text": formatted}
    await update.message.reply_text(
        "✅ Promo saved!\n\n"
        f"{formatted}\n\n"
        "Use /promo → Send Promo to preview.",
        parse_mode="Markdown",
    )
    return True


# ---------- Gaming Features ----------
async def games_menu(update_or_query, context: ContextTypes.DEFAULT_TYPE, edit=False):
    keyboard = [
        [InlineKeyboardButton("🎲 Guess the Number", callback_data="game_guess")],
        [InlineKeyboardButton("✂️ Rock Paper Scissors", callback_data="game_rps")],
        [InlineKeyboardButton("🎯 Dice Roll", callback_data="game_dice")],
        [InlineKeyboardButton("🎰 Slot Machine", callback_data="game_slots")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_main")],
    ]
    text = (
        "🎮 *Gaming Zone*\n\n"
        "Pick a game:\n\n"
        "🎲 *Guess the Number* — I pick 1–100, you guess\n"
        "✂️ *Rock Paper Scissors* — play vs bot\n"
        "🎯 *Dice Roll* — roll and beat the bot\n"
        "🎰 *Slot Machine* — try to hit triple 7s"
    )
    markup = InlineKeyboardMarkup(keyboard)
    if edit:
        await update_or_query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await update_or_query.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await games_menu(update, context)


async def game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # ---- Guess the Number ----
    if data == "game_guess":
        number = random.randint(1, 100)
        game_sessions[user_id] = {"game": "guess", "number": number, "attempts": 0}
        await query.edit_message_text(
            "🎲 *Guess the Number*\n\n"
            "I'm thinking of a number between *1 and 100*.\n"
            "Send your guess as a message!",
            parse_mode="Markdown",
        )

    # ---- Rock Paper Scissors ----
    elif data == "game_rps":
        keyboard = [
            [
                InlineKeyboardButton("🪨 Rock", callback_data="rps_rock"),
                InlineKeyboardButton("📄 Paper", callback_data="rps_paper"),
                InlineKeyboardButton("✂️ Scissors", callback_data="rps_scissors"),
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu_games")],
        ]
        await query.edit_message_text(
            "✂️ *Rock Paper Scissors*\n\nChoose your move:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data.startswith("rps_"):
        player = data.split("_")[1]
        bot = random.choice(["rock", "paper", "scissors"])
        emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        if player == bot:
            result = "🤝 *It's a tie!*"
        elif (
            (player == "rock" and bot == "scissors")
            or (player == "paper" and bot == "rock")
            or (player == "scissors" and bot == "paper")
        ):
            result = "🎉 *You win!*"
        else:
            result = "😢 *You lose!*"
        keyboard = [
            [InlineKeyboardButton("🔁 Play Again", callback_data="game_rps")],
            [InlineKeyboardButton("⬅️ Games Menu", callback_data="menu_games")],
        ]
        await query.edit_message_text(
            f"✂️ *Rock Paper Scissors*\n\n"
            f"You: {emojis[player]} {player.title()}\n"
            f"Bot: {emojis[bot]} {bot.title()}\n\n"
            f"{result}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    # ---- Dice Roll ----
    elif data == "game_dice":
        player = random.randint(1, 6)
        bot = random.randint(1, 6)
        if player > bot:
            result = "🎉 *You win!*"
        elif player < bot:
            result = "😢 *You lose!*"
        else:
            result = "🤝 *It's a tie!*"
        keyboard = [
            [InlineKeyboardButton("🎯 Roll Again", callback_data="game_dice")],
            [InlineKeyboardButton("⬅️ Games Menu", callback_data="menu_games")],
        ]
        await query.edit_message_text(
            f"🎯 *Dice Roll*\n\n"
            f"Your roll: `{player}`\n"
            f"Bot roll: `{bot}`\n\n"
            f"{result}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    # ---- Slot Machine ----
    elif data == "game_slots":
        symbols = ["🍒", "🍋", "🔔", "⭐", "💎", "7️⃣"]
        reels = [random.choice(symbols) for _ in range(3)]
        if reels[0] == reels[1] == reels[2]:
            if reels[0] == "7️⃣":
                result = "🎉🎉 *JACKPOT! Triple 7s!* 🎉🎉"
            else:
                result = f"🎉 *Triple match! Big win!*"
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            result = "✨ *Two matches — small win!*"
        else:
            result = "😢 *No match. Try again!*"
        keyboard = [
            [InlineKeyboardButton("🎰 Spin Again", callback_data="game_slots")],
            [InlineKeyboardButton("⬅️ Games Menu", callback_data="menu_games")],
        ]
        await query.edit_message_text(
            f"🎰 *Slot Machine*\n\n"
            f"┃ {reels[0]} ┃ {reels[1]} ┃ {reels[2]} ┃\n\n"
            f"{result}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


# ---------- Main Menu Callbacks ----------
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_games":
        await games_menu(query, context, edit=True)

    elif data == "menu_promo":
        keyboard = [
            [InlineKeyboardButton("📝 Create Promo", callback_data="promo_create")],
            [InlineKeyboardButton("📤 Send Promo", callback_data="promo_send")],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu_main")],
        ]
        await query.edit_message_text(
            "📢 *Promo Bot*\n\nChoose an option:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data == "menu_main":
        keyboard = [
            [InlineKeyboardButton("📣 Join Our Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton("🎮 Play Games", callback_data="menu_games")],
            [InlineKeyboardButton("📢 Promo Bot", callback_data="menu_promo")],
        ]
        await query.edit_message_text(
            "🤖 *VIPPromo88bot* — Your All-in-One Assistant\n\n"
            "👇 Choose an option below:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True,
        )


# ---------- Guess Number Handler ----------
async def guess_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    session = game_sessions.get(user_id)
    if not session or session.get("game") != "guess":
        return False

    text = (update.message.text or "").strip()
    if not text.isdigit():
        return False

    guess = int(text)
    target = session["number"]
    session["attempts"] += 1
    attempts = session["attempts"]

    if guess < target:
        await update.message.reply_text(
            f"📉 Too *low*! Try higher. (Attempt {attempts})", parse_mode="Markdown"
        )
    elif guess > target:
        await update.message.reply_text(
            f"📈 Too *high*! Try lower. (Attempt {attempts})", parse_mode="Markdown"
        )
    else:
        keyboard = [
            [InlineKeyboardButton("🎲 Play Again", callback_data="game_guess")],
            [InlineKeyboardButton("⬅️ Games Menu", callback_data="menu_games")],
        ]
        await update.message.reply_text(
            f"🎉 *Correct!* You guessed it in *{attempts}* attempts.\n"
            f"The number was `{target}`.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        game_sessions.pop(user_id, None)
    return True


# ---------- Text Router ----------
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1) Guess number game
    if await guess_number_handler(update, context):
        return
    # 2) Promo draft
    if await handle_promo_text(update, context):
        return
    # 3) Grammar correction
    await grammar_correction(update, context)


# ---------- Error Handler ----------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling update:", exc_info=context.error)


# ---------- Main ----------
def main():
    if not BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN not set. Add it in Railway Variables.")

    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("tts", tts))
    app.add_handler(CommandHandler("count", count))
    app.add_handler(CommandHandler("promo", promo))
    app.add_handler(CommandHandler("channel", channel))
    app.add_handler(CommandHandler("games", games_command))

    # Callbacks
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu_"))
    app.add_handler(CallbackQueryHandler(game_callback, pattern=r"^(game_|rps_)"))
    app.add_handler(CallbackQueryHandler(promo_callback, pattern=r"^promo_"))

    # Text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    app.add_error_handler(error_handler)

    logger.info("🚀 VIPPromo88bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
