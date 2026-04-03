import os
import json
import requests
from flask import Flask, request

app = Flask(__name__)
import logging
logging.basicConfig(level=logging.INFO)

ID_INSTANCE    = os.environ.get("GREEN_API_ID_INSTANCE", "7107571360")
API_TOKEN      = os.environ.get("GREEN_API_TOKEN", "")
BASE_URL       = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}"

OWNER_CHAT     = "13475171517@c.us"   # личный номер — сюда приходят уведомления
APPOINTMENT_URL = "https://app.acuityscheduling.com/schedule/59bf9b8d"

# In-memory state
user_state          = {}   # chatId → step
user_data           = {}   # chatId → {name, goal}
owner_reply         = {}   # OWNER_CHAT → client chatId
owner_current_client = {}  # OWNER_CHAT → last client chatId (for quick price reply)

PRICE_OPTIONS = [
    "$650 — 1 row / 2 wefts (40g) / 90 min",
    "$800 — 1 row / 3 wefts (60g) / 90 min",
    "$1,000 — 1 row / 4 wefts (80g) / 90 min",
    "$1,300 — 2 rows / 2 wefts (80g) / 90 min",
    "$1,600 — 2 rows / 3 wefts (120g) / 180 min",
    "$2,000 — 2 rows / 4 wefts (160g) / 180 min",
    "$2,400 — 3 rows / 3 wefts (180g) / 270 min",
]

FAQ = {
    "1": ("⏳ How long do IBE extensions last?",
          "IBE extensions require a correction every 2-3 months to move the rows higher toward the root as your natural hair grows. This keeps them looking seamless and natural! 💛"),
    "2": ("💰 How much does a correction cost?",
          "The correction price depends on the number of rows installed:\n\n✅ 1 row correction — $400\n\nThe price includes removal, reinstallation, and blowout styling. 💅"),
    "3": ("📍 Where are you located?",
          "📍 KAIZER Beauty Salon is located at 1019 Avenue P, Brooklyn, NY 11223."),
    "4": ("📅 When is the nearest available appointment?",
          f"You can check the nearest available time here:\n{APPOINTMENT_URL}"),
}


def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage/{API_TOKEN}"
    resp = requests.post(url, json={"chatId": chat_id, "message": text}, timeout=10)
    app.logger.info(f"send_message to {chat_id}: status={resp.status_code} body={resp.text}")


def send_file_by_url(chat_id, file_url, file_name, caption=""):
    url = f"{BASE_URL}/sendFileByUrl/{API_TOKEN}"
    requests.post(url, json={
        "chatId": chat_id,
        "urlFile": file_url,
        "fileName": file_name,
        "caption": caption
    }, timeout=10)


def send_to_owner(text):
    send_message(OWNER_CHAT, text)


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return "", 200

    app.logger.info(f"WEBHOOK: {json.dumps(data)}")

    if data.get("typeWebhook") != "incomingMessageReceived":
        app.logger.info(f"SKIPPED typeWebhook: {data.get('typeWebhook')}")
        return "", 200

    sender_data  = data.get("senderData", {})
    from_chat    = sender_data.get("chatId", "")
    sender_name  = sender_data.get("senderName", "Client")
    message_data = data.get("messageData", {})
    type_message = message_data.get("typeMessage", "")

    body = ""
    if type_message == "textMessage":
        body = message_data.get("textMessageData", {}).get("textMessage", "").strip()

    # ── OWNER commands ──────────────────────────────────────────────
    if from_chat == OWNER_CHAT:
        handle_owner(from_chat, body)
        return "", 200

    # ── CLIENT flow ─────────────────────────────────────────────────
    state = user_state.get(from_chat, "start")

    # Photo or video received
    if type_message in ("imageMessage", "videoMessage"):
        file_data = message_data.get("fileMessageData", {})
        file_url  = file_data.get("downloadUrl", "")
        caption   = file_data.get("caption", "")
        file_name = "photo.jpg" if type_message == "imageMessage" else "video.mp4"

        user_data[from_chat] = user_data.get(from_chat, {"name": sender_name})
        user_state[from_chat] = "awaiting_goal"

        # Forward media to owner
        send_file_by_url(OWNER_CHAT, file_url, file_name,
                         f"📥 Photo from client {sender_name} ({from_chat})")

        send_message(from_chat,
            "✨ Thank you!\n\n"
            "💬 What result are you looking for?\n\n"
            "Reply with a number:\n"
            "1️⃣ — Volume only (same length)\n"
            "2️⃣ — Length up to 18 inches\n"
            "3️⃣ — Length up to 24 inches"
        )
        return "", 200

    # Start / greeting
    if state == "start" or body.lower() in ["hi", "hello", "start", "привет"]:
        user_state[from_chat] = "awaiting_media"
        send_message(from_chat,
            "👋 Welcome to KAIZER Beauty Salon!\n\n"
            "We specialize in IBE Hair Extensions — the most natural, seamless, and safest method available today.\n\n"
            "📸 Please send us a photo or video of your hair from the back so we can give you an accurate price estimate!"
        )
        return "", 200

    # Goal selection
    if state == "awaiting_goal":
        goal_map = {"1": "💫 Volume only", "2": "✂️ Length up to 18 inches", "3": "🌿 Length up to 24 inches"}
        goal = goal_map.get(body)
        if goal:
            user_data[from_chat] = user_data.get(from_chat, {})
            user_data[from_chat]["goal"] = goal
            user_state[from_chat] = "awaiting_price"
            send_message(from_chat,
                f"✅ {goal}\n\n"
                "⏳ Our specialist is reviewing your submission and will send you a price estimate shortly!"
            )
            owner_current_client[OWNER_CHAT] = from_chat
            price_list = "\n".join([f"{i+1}. {p}" for i, p in enumerate(PRICE_OPTIONS)])
            send_to_owner(
                f"🔔 New client!\n"
                f"👤 {sender_name}\n"
                f"🎯 {goal}\n\n"
                f"💰 Reply with a number to send price:\n{price_list}\n\n"
                f"Or:\n"
                f"1,2 — send two prices\n"
                f"PHOTO — request new photo\n"
                f"REPLY — write custom message"
            )
        else:
            send_message(from_chat, "Please reply with *1*, *2*, or *3* to choose your goal.")
        return "", 200

    # FAQ
    if state == "faq":
        if body in FAQ:
            q, a = FAQ[body]
            send_message(from_chat, f"*{q}*\n\n{a}")
            send_message(from_chat,
                "💬 Any other questions? Reply with a number:\n"
                "1 — How long do extensions last?\n"
                "2 — Correction cost?\n"
                "3 — Where are you located?\n"
                "4 — Nearest appointment?\n\n"
                f"📅 Book here: {APPOINTMENT_URL}"
            )
        elif body.lower() == "book":
            send_message(from_chat, f"📅 Book your appointment here:\n{APPOINTMENT_URL}")
            user_state[from_chat] = "done"
        else:
            send_message(from_chat, "Please reply with *1*, *2*, *3*, or *4*.")
        return "", 200

    # Catch-all: forward text to owner
    send_to_owner(
        f"❓ Message from {sender_name} ({from_chat}):\n\n{body}\n\n"
        f"To reply: REPLY {from_chat}"
    )
    send_message(from_chat,
        "✅ Your message has been received! Our specialist will reply shortly. 😊\n\n"
        "💬 Or ask a question:\n"
        "1 — How long do extensions last?\n"
        "2 — Correction cost?\n"
        "3 — Where are you located?\n"
        "4 — Nearest appointment?"
    )
    user_state[from_chat] = "faq"
    return "", 200


def handle_owner(from_chat, body):
    parts = body.strip().split()
    if not parts:
        return

    cmd = parts[0].upper()

    # Quick reply: just numbers like "3" or "1,2"
    if cmd in ("PHOTO", "REPLY") or cmd == "SEND":
        pass  # handled below
    elif all(c.isdigit() or c == ',' for c in parts[0]):
        client_chat = owner_current_client.get(from_chat)
        if client_chat:
            price_nums = parts[0].split(",")
            prices = []
            for n in price_nums:
                try:
                    idx = int(n.strip()) - 1
                    if 0 <= idx < len(PRICE_OPTIONS):
                        prices.append(PRICE_OPTIONS[idx])
                except ValueError:
                    pass
            if prices:
                price_text = "\n\n".join([f"✅ Option {i+1}: {p}" for i, p in enumerate(prices)])
                send_message(client_chat,
                    f"✨ Here is your personalized recommendation:\n\n"
                    f"{price_text}\n\n"
                    f"💬 Ready to book?\n📅 {APPOINTMENT_URL}"
                )
                send_to_owner(f"✅ Price sent to {client_chat}")
                user_state[client_chat] = "faq"
        return

    # SEND 1 chatId  or  SEND 1,2 chatId
    if cmd == "SEND" and len(parts) >= 3:
        price_nums  = parts[1].split(",")
        client_chat = parts[2]
        prices = []
        for n in price_nums:
            try:
                idx = int(n.strip()) - 1
                if 0 <= idx < len(PRICE_OPTIONS):
                    prices.append(PRICE_OPTIONS[idx])
            except ValueError:
                pass
        if prices:
            price_text = "\n\n".join([f"✅ Option {i+1}: {p}" for i, p in enumerate(prices)])
            send_message(client_chat,
                f"✨ Here is your personalized recommendation:\n\n"
                f"{price_text}\n\n"
                f"💬 Ready to book?\n📅 {APPOINTMENT_URL}"
            )
            send_to_owner(f"✅ Price sent to {client_chat}")
            user_state[client_chat] = "faq"
        return

    # PHOTO — request new photo
    if cmd == "PHOTO":
        client_chat = parts[1] if len(parts) >= 2 else owner_current_client.get(from_chat)
        if not client_chat:
            return
        send_message(client_chat,
            "📸 Thank you for reaching out!\n\n"
            "To give you the most accurate price estimate, please send us another *photo or video* "
            "from the back, in good natural lighting, with your hair down. 🙏"
        )
        user_state[client_chat] = "awaiting_media"
        send_to_owner(f"✅ Photo request sent to {client_chat}")
        return

    # REPLY — next message goes to client
    if cmd == "REPLY":
        client_chat = parts[1] if len(parts) >= 2 else owner_current_client.get(from_chat)
        if not client_chat:
            return
        owner_reply[from_chat] = client_chat
        send_to_owner(f"✍️ Type your reply — it will be sent to client:")
        return

    # If owner is in reply mode
    if from_chat in owner_reply:
        client_chat = owner_reply.pop(from_chat)
        send_message(client_chat, f"💬 Answer from KAIZER Salon:\n\n{body}")
        send_to_owner(f"✅ Reply sent to {client_chat}")
        return


if __name__ == "__main__":
    app.run(debug=True, port=5000)
