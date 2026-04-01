import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "5290790830:AAELVq-28oh-6_5CT6OoC-vquUuCF6paztI")
APPOINTMENT_URL = "https://app.acuityscheduling.com/schedule/59bf9b8d"
OWNER_ID = 523301991

user_data = {}
owner_waiting_reply = {}  # owner_id → client_id (for text replies)
message_to_client = {}

PRICE_OPTIONS = [
    ("$650 — 1 row / 2 wefts (40g) / 90 min",   "p650"),
    ("$800 — 1 row / 3 wefts (60g) / 90 min",   "p800"),
    ("$1,000 — 1 row / 4 wefts (80g) / 90 min", "p1000"),
    ("$1,300 — 2 rows / 2 wefts (80g) / 90 min","p1300"),
    ("$1,600 — 2 rows / 3 wefts (120g) / 180 min","p1600"),
    ("$2,000 — 2 rows / 4 wefts (160g) / 180 min","p2000"),
    ("$2,400 — 3 rows / 3 wefts (180g) / 270 min","p2400"),
]

FAQ = {
    "faq1": {
        "q": "⏳ How long do IBE extensions last?",
        "a": "IBE extensions require a correction every 2-3 months to move the rows higher toward the root as your natural hair grows. This keeps them looking seamless and natural! 💛"
    },
    "faq2": {
        "q": "💰 How much does a correction cost?",
        "a": "The correction price depends on the number of rows installed:\n\n✅ 1 row correction — $400\n\nThe price includes removal, reinstallation, and blowout styling. 💅"
    },
    "faq3": {
        "q": "📍 Where are you located?",
        "a": "📍 KAIZER Beauty Salon is located at 1019 Avenue P, Brooklyn, NY 11223."
    },
    "faq4": {
        "q": "📅 When is the nearest available appointment?",
        "a": "You can check the nearest available time by clicking the link below — simply select the service you need and pick a time that works for you! 🗓️"
    },
}

PRICE_TEXTS = {
    "p650":  "1 Row / 2 Wefts (40g) — $650 — 90 min",
    "p800":  "1 Row / 3 Wefts (60g) — $800 — 90 min",
    "p1000": "1 Row / 4 Wefts (80g) — $1,000 — 90 min",
    "p1300": "2 Rows / 2 Wefts (80g) — $1,300 — 90 min",
    "p1600": "2 Rows / 3 Wefts (120g) — $1,600 — 180 min",
    "p2000": "2 Rows / 4 Wefts (160g) — $2,000 — 180 min",
    "p2400": "3 Rows / 3 Wefts (180g) — $2,400 — 270 min",
}

def client_keyboard(client_id):
    return [
        [InlineKeyboardButton("📅 Make Appointment", url=APPOINTMENT_URL)],
        [InlineKeyboardButton("💬 Ask a question", callback_data=f"askq.{client_id}")],
    ]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Kaizer Salon!\n\n"
        "We specialize in IBE Hair Extensions — the most natural, seamless, and safest hair extension method available today.\n\n"
        "📸 Please send us a photo or video of your hair from the back so we can give you an accurate price estimate!"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name or "Client"
    username = update.message.from_user.username
    user_data[user_id] = {"name": user_name, "username": username}

    keyboard = [
        [InlineKeyboardButton("💫 Volume only (same length)", callback_data=f"goal.volume.{user_id}")],
        [InlineKeyboardButton("✂️ Length up to 18 inches",   callback_data=f"goal.18.{user_id}")],
        [InlineKeyboardButton("🌿 Length up to 24 inches",   callback_data=f"goal.24.{user_id}")],
    ]
    await update.message.reply_text(
        "✨ Thank you for the photo! 💬 *What result are you looking for?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    await context.bot.forward_message(
        chat_id=OWNER_ID,
        from_chat_id=update.message.chat_id,
        message_id=update.message.message_id
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name or "Client"
    username = update.message.from_user.username
    user_data[user_id] = {"name": user_name, "username": username}

    keyboard = [
        [InlineKeyboardButton("💫 Volume only (same length)", callback_data=f"goal.volume.{user_id}")],
        [InlineKeyboardButton("✂️ Length up to 18 inches",   callback_data=f"goal.18.{user_id}")],
        [InlineKeyboardButton("🌿 Length up to 24 inches",   callback_data=f"goal.24.{user_id}")],
    ]
    await update.message.reply_text(
        "✨ Thank you for the video! 💬 *What result are you looking for?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    await context.bot.forward_message(
        chat_id=OWNER_ID,
        from_chat_id=update.message.chat_id,
        message_id=update.message.message_id
    )

async def handle_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, goal, client_id = query.data.split(".")
    client_id = int(client_id)

    goal_map = {"volume": "💫 Volume only", "18": "✂️ Length up to 18 inches", "24": "🌿 Length up to 24 inches"}
    goal_label = goal_map.get(goal, goal)

    await query.edit_message_text(
        f"✅ *{goal_label}*\n\n⏳ Our specialist is reviewing your submission and will send you a price estimate shortly!",
        parse_mode="Markdown"
    )

    user_name = user_data.get(client_id, {}).get("name", "Client")
    username = user_data.get(client_id, {}).get("username", "")
    user_link = f"@{username}" if username else user_name

    # Build price keyboard: sel1.PRICE.CLIENT_ID
    keyboard = [[InlineKeyboardButton(f"💰 {label}", callback_data=f"sel1.{key}.{client_id}")]
                for label, key in PRICE_OPTIONS]
    keyboard.append([InlineKeyboardButton("📸 Request new photo", callback_data=f"reqphoto.{client_id}")])
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"🔔 *New client!*\n👤 {user_link}\n🎯 {goal_label}\n\n👇 Select price (Option 1):",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_sel1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner selected first price"""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != OWNER_ID:
        return

    _, p1, client_id = query.data.split(".")
    client_id = int(client_id)
    price_text = PRICE_TEXTS[p1]

    keyboard = [
        [InlineKeyboardButton("✅ Send this only",  callback_data=f"send1.{p1}.{client_id}")],
        [InlineKeyboardButton("➕ Add 2nd option",  callback_data=f"add2.{p1}.{client_id}")],
        [InlineKeyboardButton("↩️ Start over",      callback_data=f"over1.{client_id}")],
    ]
    await query.edit_message_text(
        f"✅ Option 1 selected:\n💰 *{price_text}*\n\nSend this only or add a second option?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_send1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send one price to client"""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != OWNER_ID:
        return

    _, p1, client_id = query.data.split(".")
    client_id = int(client_id)
    text = PRICE_TEXTS[p1]

    await context.bot.send_message(
        chat_id=client_id,
        text=f"✨ *Here is your personalized recommendation:*\n\n✅ {text}\n\n💬 Ready to book?",
        reply_markup=InlineKeyboardMarkup(client_keyboard(client_id)),
        parse_mode="Markdown"
    )
    await query.edit_message_text(f"✅ Sent to client:\n{text}", parse_mode="Markdown")

async def handle_add2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show keyboard for second price"""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != OWNER_ID:
        return

    _, p1, client_id = query.data.split(".")
    text1 = PRICE_TEXTS[p1]

    # sel2.P1.PRICE2.CLIENT_ID
    keyboard = [[InlineKeyboardButton(f"💰 {label}", callback_data=f"sel2.{p1}.{key}.{client_id}")]
                for label, key in PRICE_OPTIONS]
    keyboard.append([InlineKeyboardButton("↩️ Start over", callback_data=f"over1.{client_id}")])

    await query.edit_message_text(
        f"Option 1: ✅ *{text1}*\n\n👇 Select Option 2:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_sel2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner selected second price — show confirmation before sending"""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != OWNER_ID:
        return

    parts = query.data.split(".")
    # sel2.P1.P2.CLIENT_ID
    p1 = parts[1]
    p2 = parts[2]
    client_id = parts[3]

    text1 = PRICE_TEXTS[p1]
    text2 = PRICE_TEXTS[p2]

    keyboard = [
        [InlineKeyboardButton("✅ Send both options", callback_data=f"send2.{p1}.{p2}.{client_id}")],
        [InlineKeyboardButton("↩️ Start over",        callback_data=f"over1.{client_id}")],
    ]
    await query.edit_message_text(
        f"✅ Option 1: *{text1}*\n✅ Option 2: *{text2}*\n\nSend both to client?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_send2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send both prices to client"""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != OWNER_ID:
        return

    parts = query.data.split(".")
    p1 = parts[1]
    p2 = parts[2]
    client_id = int(parts[3])

    text1 = PRICE_TEXTS[p1]
    text2 = PRICE_TEXTS[p2]

    await context.bot.send_message(
        chat_id=client_id,
        text=f"✨ *Here are your personalized recommendations:*\n\n"
             f"✅ *Option 1:* {text1}\n\n"
             f"✅ *Option 2:* {text2}\n\n"
             f"💬 Choose the option that fits you best and book below!",
        reply_markup=InlineKeyboardMarkup(client_keyboard(client_id)),
        parse_mode="Markdown"
    )
    await query.edit_message_text(
        f"✅ Both options sent!\nOption 1: {text1}\nOption 2: {text2}",
        parse_mode="Markdown"
    )

async def handle_over1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start over — show first price keyboard again"""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != OWNER_ID:
        return

    client_id = int(query.data.split(".")[1])
    keyboard = [[InlineKeyboardButton(f"💰 {label}", callback_data=f"sel1.{key}.{client_id}")]
                for label, key in PRICE_OPTIONS]
    await query.edit_message_text(
        "↩️ *Restarted. Select price (Option 1):*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_askq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show FAQ buttons to client"""
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton(FAQ[key]["q"], callback_data=f"faq.{key}")] for key in FAQ]
    keyboard.append([InlineKeyboardButton("✍️ Ask my own question", callback_data="faq.custom")])

    await context.bot.send_message(
        chat_id=query.from_user.id,
        text="💬 Choose a question or ask your own:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Answer FAQ or prompt custom question"""
    query = update.callback_query
    await query.answer()

    key = query.data.split(".")[1]

    if key == "custom":
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="✍️ Please type your question and we'll get back to you shortly!"
        )
        return

    answer = FAQ[key]["a"]
    keyboard = [
        [InlineKeyboardButton("📅 Check available times", url=APPOINTMENT_URL)] if key == "faq4"
        else [InlineKeyboardButton("📅 Make Appointment", url=APPOINTMENT_URL)],
        [InlineKeyboardButton("💬 Ask another question", callback_data=f"askq.{query.from_user.id}")],
    ]
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=answer,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_reqphoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner requests a new photo from client"""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != OWNER_ID:
        return

    client_id = int(query.data.split(".")[1])
    await context.bot.send_message(
        chat_id=client_id,
        text=(
            "📸 Thank you for reaching out!\n\n"
            "To give you the most accurate price estimate, we kindly ask you to send us another photo or video. "
            "Please make sure it is taken *from the back*, in good natural lighting, with your hair down — "
            "this will help us clearly see your hair length and volume. 🙏"
        ),
        parse_mode="Markdown"
    )
    await query.edit_message_text("📸 New photo request sent to client.")

async def handle_reply_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner clicks ✍️ Reply button"""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != OWNER_ID:
        return
    client_id = int(query.data.split(".")[1])
    owner_waiting_reply[OWNER_ID] = client_id
    await context.bot.send_message(chat_id=OWNER_ID, text="✍️ Type your reply and send it:")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id == OWNER_ID:
        client_id = owner_waiting_reply.pop(OWNER_ID, None)
        if client_id:
            await context.bot.send_message(
                chat_id=client_id,
                text=f"💬 *Answer from Kaizer Salon:*\n\n{update.message.text}",
                parse_mode="Markdown"
            )
            await update.message.reply_text("✅ Reply sent to client!")
        return

    user_name = update.message.from_user.first_name or "Client"
    username = update.message.from_user.username
    user_link = f"@{username}" if username else user_name
    user_data[user_id] = {"name": user_name, "username": username}

    keyboard = [[InlineKeyboardButton("✍️ Reply to client", callback_data=f"replyto.{user_id}")]]
    sent = await context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"❓ *Question from {user_link}:*\n\n{update.message.text}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    message_to_client[sent.message_id] = user_id

    await update.message.reply_text(
        "✅ Your question has been received! Our specialist will reply shortly. 😊"
    )

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(CallbackQueryHandler(handle_goal,     pattern=r"^goal\."))
    app.add_handler(CallbackQueryHandler(handle_sel2,     pattern=r"^sel2\."))
    app.add_handler(CallbackQueryHandler(handle_send2,    pattern=r"^send2\."))
    app.add_handler(CallbackQueryHandler(handle_sel1,     pattern=r"^sel1\."))
    app.add_handler(CallbackQueryHandler(handle_send1,    pattern=r"^send1\."))
    app.add_handler(CallbackQueryHandler(handle_add2,     pattern=r"^add2\."))
    app.add_handler(CallbackQueryHandler(handle_over1,    pattern=r"^over1\."))
    app.add_handler(CallbackQueryHandler(handle_askq,     pattern=r"^askq\."))
    app.add_handler(CallbackQueryHandler(handle_faq,      pattern=r"^faq\."))
    app.add_handler(CallbackQueryHandler(handle_reqphoto,  pattern=r"^reqphoto\."))
    app.add_handler(CallbackQueryHandler(handle_reply_btn,pattern=r"^replyto\."))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
