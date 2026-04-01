import os
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN  = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WA_NUMBER = "whatsapp:+14155238886"  # Twilio Sandbox number (change after approval)
OWNER_WA = "whatsapp:+13479077077"           # Your WhatsApp number
APPOINTMENT_URL = "https://app.acuityscheduling.com/schedule/59bf9b8d"

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# In-memory state
user_state  = {}  # phone → step
user_data   = {}  # phone → {name, goal}
owner_reply = {}  # OWNER → client phone (when owner is typing a reply)

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

def send_message(to, body):
    client.messages.create(from_=TWILIO_WA_NUMBER, to=to, body=body)

def send_to_owner(body):
    client.messages.create(from_=TWILIO_WA_NUMBER, to=OWNER_WA, body=body)

def forward_media(from_number, media_url, media_type):
    client.messages.create(
        from_=TWILIO_WA_NUMBER,
        to=OWNER_WA,
        body=f"📥 Media from client {from_number}:",
        media_url=[media_url]
    )

@app.route("/webhook", methods=["POST"])
def webhook():
    from_number = request.form.get("From", "")
    body        = request.form.get("Body", "").strip()
    num_media   = int(request.form.get("NumMedia", 0))
    media_url   = request.form.get("MediaUrl0", "")
    media_type  = request.form.get("MediaContentType0", "")

    # ── OWNER commands ──────────────────────────────────────────────
    if from_number == OWNER_WA:
        handle_owner(from_number, body)
        return "", 204

    # ── CLIENT flow ─────────────────────────────────────────────────
    state = user_state.get(from_number, "start")

    # Photo or video received
    if num_media > 0 and ("image" in media_type or "video" in media_type):
        user_data[from_number] = user_data.get(from_number, {})
        user_state[from_number] = "awaiting_goal"
        forward_media(from_number, media_url, media_type)
        send_message(from_number,
            "✨ Thank you!\n\n"
            "💬 *What result are you looking for?*\n\n"
            "Reply with a number:\n"
            "1️⃣ — Volume only (same length)\n"
            "2️⃣ — Length up to 18 inches\n"
            "3️⃣ — Length up to 24 inches"
        )
        return "", 204

    # Start / greeting
    if state == "start" or body.lower() in ["hi", "hello", "start", "привет"]:
        user_state[from_number] = "awaiting_media"
        send_message(from_number,
            "👋 Welcome to KAIZER Beauty Salon!\n\n"
            "We specialize in IBE Hair Extensions — the most natural, seamless, and safest method available today.\n\n"
            "📸 Please send us a *photo or video* of your hair from the back so we can give you an accurate price estimate!"
        )
        return "", 204

    # Goal selection
    if state == "awaiting_goal":
        goal_map = {"1": "💫 Volume only", "2": "✂️ Length up to 18 inches", "3": "🌿 Length up to 24 inches"}
        goal = goal_map.get(body)
        if goal:
            user_data[from_number]["goal"] = goal
            user_state[from_number] = "awaiting_price"
            send_message(from_number,
                f"✅ *{goal}*\n\n"
                "⏳ Our specialist is reviewing your submission and will send you a price estimate shortly!"
            )
            price_list = "\n".join([f"{i+1}. {p}" for i, p in enumerate(PRICE_OPTIONS)])
            send_to_owner(
                f"🔔 *New client!*\n"
                f"📱 {from_number}\n"
                f"🎯 {goal}\n\n"
                f"💰 Reply with price number(s):\n{price_list}\n\n"
                f"Or reply:\n"
                f"SEND 1 {from_number} — send one price\n"
                f"SEND 1,2 {from_number} — send two prices\n"
                f"PHOTO {from_number} — request new photo/video\n"
                f"REPLY {from_number} — write custom message"
            )
        else:
            send_message(from_number, "Please reply with *1*, *2*, or *3* to choose your goal.")
        return "", 204

    # FAQ
    if state == "faq":
        if body in FAQ:
            q, a = FAQ[body]
            send_message(from_number, f"*{q}*\n\n{a}")
            send_message(from_number,
                "💬 Any other questions? Reply with a number:\n"
                "1 — How long do extensions last?\n"
                "2 — Correction cost?\n"
                "3 — Where are you located?\n"
                "4 — Nearest appointment?\n\n"
                f"📅 Book here: {APPOINTMENT_URL}"
            )
        elif body.lower() == "book":
            send_message(from_number, f"📅 Book your appointment here:\n{APPOINTMENT_URL}")
            user_state[from_number] = "done"
        else:
            send_message(from_number, "Please reply with *1*, *2*, *3*, or *4*.")
        return "", 204

    # Catch-all: forward text to owner
    send_to_owner(
        f"❓ Message from {from_number}:\n\n{body}\n\n"
        f"To reply: REPLY {from_number}"
    )
    send_message(from_number,
        "✅ Your message has been received! Our specialist will reply shortly. 😊\n\n"
        "💬 Or ask a question:\n"
        "1 — How long do extensions last?\n"
        "2 — Correction cost?\n"
        "3 — Where are you located?\n"
        "4 — Nearest appointment?"
    )
    user_state[from_number] = "faq"
    return "", 204


def handle_owner(from_number, body):
    """Parse owner commands"""
    parts = body.strip().split()
    if not parts:
        return

    cmd = parts[0].upper()

    # SEND 1 whatsapp:+1xxx  or  SEND 1,2 whatsapp:+1xxx
    if cmd == "SEND" and len(parts) >= 3:
        price_nums = parts[1].split(",")
        client_num = parts[2]
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
            send_message(client_num,
                f"✨ *Here is your personalized recommendation:*\n\n"
                f"{price_text}\n\n"
                f"💬 Ready to book?\n📅 {APPOINTMENT_URL}"
            )
            send_to_owner(f"✅ Price sent to {client_num}")
            user_state[client_num] = "faq"
        return

    # PHOTO whatsapp:+1xxx — request new photo
    if cmd == "PHOTO" and len(parts) >= 2:
        client_num = parts[1]
        send_message(client_num,
            "📸 Thank you for reaching out!\n\n"
            "To give you the most accurate price estimate, we kindly ask you to send us another *photo or video*. "
            "Please make sure it is taken *from the back*, in good natural lighting, with your hair down — "
            "this will help us clearly see your hair length and volume. 🙏"
        )
        user_state[client_num] = "awaiting_media"
        send_to_owner(f"✅ Photo request sent to {client_num}")
        return

    # REPLY whatsapp:+1xxx — next message goes to client
    if cmd == "REPLY" and len(parts) >= 2:
        client_num = parts[1]
        owner_reply[OWNER_WA] = client_num
        send_to_owner(f"✍️ Type your reply — it will be sent to {client_num}:")
        return

    # If owner is in reply mode — send their message to client
    if OWNER_WA in owner_reply:
        client_num = owner_reply.pop(OWNER_WA)
        send_message(client_num,
            f"💬 *Answer from KAIZER Salon:*\n\n{body}"
        )
        send_to_owner(f"✅ Reply sent to {client_num}")
        return


if __name__ == "__main__":
    app.run(debug=True, port=5000)
