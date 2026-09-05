import time
import threading
import requests
import json
import os

# ================= CONFIGURATION =================
BOT_TOKEN = "8864547814:AAEBQxt864_3n06RLllIqCsN3AuyGmJhSzg"
BOT_USERNAME = "DRX_TM_POD_BOT" 
CHANNEL_USERNAME = "@DARK67HACK"
BASE_API = "https://sh-tim-faruk-vai.ai.studio/api"
LEADERBOARD_API = "https://sh-tim-faruk-vai.ai.studio/apipid.json"

ADMIN_ID = "8707571669" # Admin User ID

# Premium Traders List
ALL_TRADERS = [
    {"name": "Subs Pro VIP", "slug": "subs"},
    {"name": "Dragon Pro VIP", "slug": "dragon-pro"},
    {"name": "Tiger Pro VIP", "slug": "tiger-pro"},
    {"name": "Dragon King", "slug": "dragon-king"},
    {"name": "Phoenix VIP", "slug": "phoenix-vip"},
    {"name": "Eagle Eye", "slug": "eagle-eye"},
    {"name": "Lion Heart", "slug": "lion-heart"},
    {"name": "Thunder Bolt", "slug": "thunder-bolt"},
    {"name": "Shadow X", "slug": "shadow-x"},
    {"name": "Cobra Strike", "slug": "cobra-strike"},
    {"name": "Wolf Pack", "slug": "wolf-pack"},
    {"name": "Blaze Pro", "slug": "blaze-pro"},
    {"name": "Viper Gold", "slug": "viper-gold"},
    {"name": "Rocket Star", "slug": "rocket-star"},
    {"name": "Storm Chaser", "slug": "storm-chaser"},
    {"name": "Ninja Master", "slug": "ninja-master"},
    {"name": "Falcon Rush", "slug": "falcon-rush"},
    {"name": "Panther VIP", "slug": "panther-vip"},
    {"name": "Ghost Rider", "slug": "ghost-rider"},
    {"name": "Shark Tank", "slug": "shark-tank"},
    {"name": "Bullet Pro", "slug": "bullet-pro"},
    {"name": "Dark Horse", "slug": "dark-horse"},
    {"name": "Quantum X", "slug": "quantum-x"},
    {"name": "Apex Titan", "slug": "apex-titan"},
    {"name": "Nova Prime", "slug": "nova-prime"},
    {"name": "Stealth Hawk", "slug": "stealth-hawk"},
    {"name": "Omega Force", "slug": "omega-force"},
    {"name": "Zenith Pro", "slug": "zenith-pro"},
    {"name": "Crypto Wolf", "slug": "crypto-wolf"},
    {"name": "Rapid Fire", "slug": "rapid-fire"},
    {"name": "Iron Pulse", "slug": "iron-pulse"},
    {"name": "Shadow Blade", "slug": "shadow-blade"}
]

USER_SESSIONS = {}
LAST_UPDATE_ID = 0
DB_FILE = "users_db.json"

# ================= PREMIUM FONT GENERATOR =================
def to_premium(text):
    mapping = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
    )
    return text.translate(mapping)

# ================= DATABASE & REFERRAL LOGIC =================
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                db = json.load(f)
                if "__config__" not in db:
                    db["__config__"] = {"bypass_password": None}
                return db
        except Exception:
            pass
    return {"__config__": {"bypass_password": None}}

def save_db(db):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(db, f)
    except Exception as e:
        print(f"[-] DB Save Error: {e}")

USERS_DB = load_db()

def check_channel_member(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {"chat_id": CHANNEL_USERNAME, "user_id": user_id}
    try:
        res = requests.get(url, params=params, timeout=3).json()
        if res.get("ok"):
            status = res["result"]["status"]
            return status in ["member", "administrator", "creator"]
    except Exception:
        pass
    return False

def get_user_task_info(user_id):
    user_id = str(user_id)
    # বাংলাদেশ সময় অনুযায়ী (UTC+6) রাত ১২টায় দিন পরিবর্তন হবে
    current_day = int(time.time() + 21600) // 86400 
    
    if user_id not in USERS_DB:
        USERS_DB[user_id] = {
            "joined_day": current_day,
            "referrals": [],
            "unlocked_days": []
        }
        save_db(USERS_DB)
        
    user_data = USERS_DB[user_id]
    days_active = current_day - user_data.get("joined_day", current_day)
    
    # প্রথম দিন ২ জন, এরপর প্রতিদিন ১ জন করে বাড়বে
    target_shares = 2 + days_active
    current_referrals = len(user_data.get("referrals", []))
    is_unlocked_today = str(current_day) in user_data.get("unlocked_days", [])
    
    return target_shares, current_referrals, is_unlocked_today, current_day

def send_telegram_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=4)
    except: pass

# ================= TASK PROMPT & MENU =================
def send_welcome_task_menu(chat_id, msg_id=None):
    target, current, _, _ = get_user_task_info(chat_id)
    
    text = (
        f"<b>{to_premium('WELCOME TO WINGO PREMIUM BOT')}</b>\n\n"
        "আসসালামু আলাইকুম। আশা করি সকলে ভালো আছেন।\n\n"
        "এই 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐓𝐑𝐀𝐃𝐈𝐍𝐆 𝐁𝐎𝐓 ব্যবহার করার জন্য আপনাকে নিচের শর্ত পূরণ করতে হবে <b>অথবা</b> এডমিনের দেয়া পাসওয়ার্ড সাবমিট করতে হবে:\n\n"
        f"১. আমাদের অফিশিয়াল চ্যানেলে জয়েন থাকতে হবে।\n"
        f"২. বটটি প্রথমবার আনলক করতে <b>২ জন</b> রিয়েল রেফার করতে হবে। পরবর্তীতে প্রতিদিন <b>১ জন</b> করে রেফার করতে হবে।\n\n"
        "⚠️ <b>সতর্কতা:</b> রেফার করা মেম্বারকে অবশ্যই চ্যানেলে জয়েন থাকতে হবে!\n\n"
        f"🎯 আপনার বর্তমান টার্গেট: <b>{to_premium(str(target))}</b> জন।\n"
        f"👥 লিংকে ক্লিক করেছে: <b>{to_premium(str(current))}</b> জন।\n\n"
        "🔑 <i>আপনার কাছে পাসওয়ার্ড থাকলে সেটি সরাসরি লিখে সেন্ড করুন।</i>"
    )
    
    channel_link = f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"
    personal_ref_link = f"https://t.me/{BOT_USERNAME}?start={chat_id}"
    share_url = f"https://t.me/share/url?url={personal_ref_link}&text=Join%20Premium%20WinGo%20Prediction%20Terminal"

    keyboard = [
        [{"text": to_premium("JOIN CHANNEL"), "url": channel_link}],
        [{"text": to_premium("SHARE LINK"), "url": share_url}],
        [{"text": to_premium("VERIFY REFERRALS"), "callback_data": "verify_task"}]
    ]

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": keyboard}
    }

    if msg_id:
        payload["message_id"] = msg_id
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        
    try:
        res = requests.post(url, json=payload, timeout=4).json()
        if not msg_id and res.get("ok"):
            USER_SESSIONS[str(chat_id)] = {
                "msg_id": res["result"]["message_id"],
                "view": "task",
                "slug": None
            }
    except Exception:
        pass

# ================= API DATA & TIMER =================
def fetch_leaderboard():
    try:
        res = requests.get(LEADERBOARD_API, timeout=3)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return {}

def fetch_trader_data(slug):
    url = f"{BASE_API}/apipid-{slug}.json"
    try:
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return {}

def get_countdown():
    return 30 - (int(time.time()) % 30)

def get_timer_display():
    sec = get_countdown()
    blocks = int((sec / 30.0) * 15)  # 15 blocks maximum
    bar = "▓" * blocks + "░" * (15 - blocks)
    return f"⏳ {sec:02d}S [{bar}]"

# ================= MAIN TRADING MENU =================
def build_menu_markup():
    leaderboard = fetch_leaderboard()
    keyboard = []
    
    # Premium Timer Button with Animation Bar
    keyboard.append([
        {"text": get_timer_display(), "callback_data": "noop"}
    ])

    top_traders = leaderboard.get("top_3_traders", [])
    top_names_api = [t.get("name", "").strip().lower() for t in top_traders if t.get("name")]

    ordered_traders = []
    seen_slugs = set()

    for t_name in top_names_api:
        for t in ALL_TRADERS:
            if t["name"].strip().lower() == t_name and t["slug"] not in seen_slugs:
                ordered_traders.append(t)
                seen_slugs.add(t["slug"])
                break

    for t in ALL_TRADERS:
        if t["slug"] not in seen_slugs:
            ordered_traders.append(t)
            seen_slugs.add(t["slug"])

    row = []
    for t in ordered_traders:
        row.append({
            "text": to_premium(t["name"].upper()),
            "callback_data": f"open_{t['slug']}"
        })
        if len(row) == 2: # Changed to 2 buttons per row for bigger/premium look
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)

    return to_premium("WINGO 30SEC PREDICTION TERMINAL"), keyboard

# ================= MARKET VIEW =================
def build_market_markup(slug):
    data = fetch_trader_data(slug)
    
    keyboard = []
    full_target_period = str(data.get("period", "--------"))
    period_8 = full_target_period[-8:] if len(full_target_period) >= 8 else full_target_period
    
    main_pred = data.get("main_prediction", {})
    action = str(main_pred.get("prediction", "-")).upper()
    pred_num = str(main_pred.get("predicted_number", "-"))

    keyboard.append([
        {"text": to_premium(f"PERIOD: {period_8}"), "callback_data": "noop"}
    ])
    keyboard.append([
        {"text": get_timer_display(), "callback_data": "noop"}
    ])

    keyboard.append([
        {"text": to_premium(action), "callback_data": "noop"},
        {"text": to_premium(f"NUM: {pred_num}"), "callback_data": "noop"},
        {"text": to_premium("🔙 BACK"), "callback_data": "back_to_menu"}
    ])

    history = data.get("history", [])[:10]
    for item in history:
        period_4 = str(item.get("period", ""))[-4:]
        actual_num = str(item.get("actual_number", "-"))
        pred = str(item.get("prediction", "-")).upper()
        res = str(item.get("result", "-")).upper()

        keyboard.append([
            {"text": to_premium(period_4 if period_4 else "----"), "callback_data": "noop"},
            {"text": to_premium(actual_num), "callback_data": "noop"},
            {"text": to_premium(pred), "callback_data": "noop"},
            {"text": to_premium(res), "callback_data": "noop"}
        ])

    trader_name = data.get("trader_name", slug.upper()).upper()
    text_title = f"<b>{to_premium('WINGO 30S LIVE:')}</b>\n{to_premium(trader_name)}"
    return text_title, keyboard

# ================= TELEGRAM HANDLERS =================
def send_main_menu(chat_id, msg_id=None):
    text, markup = build_menu_markup()
    payload = {
        "chat_id": chat_id,
        "text": f"<b>{text}</b>",
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": markup}
    }
    
    if msg_id:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        payload["message_id"] = msg_id
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        res = requests.post(url, json=payload, timeout=4).json()
        if res.get("ok"):
            save_msg_id = msg_id if msg_id else res["result"]["message_id"]
            USER_SESSIONS[str(chat_id)] = {
                "msg_id": save_msg_id,
                "view": "menu",
                "slug": None
            }
    except Exception:
        pass

def switch_view(chat_id, msg_id, view, slug=None):
    if view == "menu":
        text, markup = build_menu_markup()
        text = f"<b>{text}</b>"
    else:
        text, markup = build_market_markup(slug)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": msg_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": markup}
    }
    try:
        requests.post(url, json=payload, timeout=4)
        USER_SESSIONS[str(chat_id)] = {
            "msg_id": msg_id,
            "view": view,
            "slug": slug
        }
    except Exception:
        pass

def live_update_keyboard(chat_id, msg_id, view, slug):
    if view == "menu":
        _, markup = build_menu_markup()
    else:
        _, markup = build_market_markup(slug)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup"
    payload = {
        "chat_id": chat_id,
        "message_id": msg_id,
        "reply_markup": {"inline_keyboard": markup}
    }
    try:
        requests.post(url, json=payload, timeout=3)
    except Exception:
        pass

def answer_callback(cb_id, text="", show_alert=False):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": cb_id, "text": text, "show_alert": show_alert}
    try:
        requests.post(url, json=payload, timeout=2)
    except Exception:
        pass

# ================= REALTIME ENGINE =================
def realtime_sync_engine():
    while True:
        try:
            for chat_id, session in list(USER_SESSIONS.items()):
                if session["view"] in ["menu", "market"]:
                    live_update_keyboard(
                        chat_id, 
                        session["msg_id"], 
                        session["view"], 
                        session["slug"]
                    )
        except Exception:
            pass
        time.sleep(1)

# ================= MAIN LISTENER =================
def telegram_listener():
    global LAST_UPDATE_ID
    print("[*] Engine Running. Premium Design & Password System Active.")

    while True:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        params = {"offset": LAST_UPDATE_ID + 1, "timeout": 2}
        
        try:
            res = requests.get(url, params=params, timeout=4)
            data = res.json()
            
            if data.get("ok"):
                for item in data["result"]:
                    LAST_UPDATE_ID = item["update_id"]

                    if "message" in item and "text" in item["message"]:
                        chat_id = str(item["message"]["chat"]["id"])
                        msg_text = item["message"]["text"].strip()
                        
                        # --- ADMIN PASSWORD SETTING ---
                        if chat_id == ADMIN_ID and msg_text.startswith("/admin "):
                            new_pass = msg_text.split(" ", 1)[1].strip()
                            USERS_DB["__config__"]["bypass_password"] = new_pass
                            save_db(USERS_DB)
                            send_telegram_msg(chat_id, f"✅ <b>Bypass password successfully set to:</b> {new_pass}")
                            continue

                        # --- USER PASSWORD BYPASS ---
                        global_pass = USERS_DB.get("__config__", {}).get("bypass_password")
                        if global_pass and msg_text == global_pass:
                            _, _, _, current_day = get_user_task_info(chat_id)
                            if "unlocked_days" not in USERS_DB[chat_id]:
                                USERS_DB[chat_id]["unlocked_days"] = []
                            if str(current_day) not in USERS_DB[chat_id]["unlocked_days"]:
                                USERS_DB[chat_id]["unlocked_days"].append(str(current_day))
                                save_db(USERS_DB)
                            
                            send_telegram_msg(chat_id, "✅ <b>𝐏𝐀𝐒𝐒𝐖𝐎𝐑𝐃 𝐀𝐂𝐂𝐄𝐏𝐓𝐄𝐃!</b>\nআপনি আজকের জন্য রেফারাল ছাড়াই ভিআইপি বট আনলক করেছেন।")
                            send_main_menu(chat_id)
                            continue

                        # --- REFERRAL TRACKING (/start ...) ---
                        if msg_text.startswith("/start ") and len(msg_text.split()) > 1:
                            referrer_id = msg_text.split()[1].strip()
                            if chat_id not in USERS_DB:
                                get_user_task_info(chat_id)
                                if referrer_id in USERS_DB and referrer_id != chat_id:
                                    if "referrals" not in USERS_DB[referrer_id]:
                                        USERS_DB[referrer_id]["referrals"] = []
                                    if chat_id not in USERS_DB[referrer_id]["referrals"]:
                                        USERS_DB[referrer_id]["referrals"].append(chat_id)
                                        save_db(USERS_DB)
                                        
                        is_member = check_channel_member(chat_id)
                        target, current_refs, is_unlocked, _ = get_user_task_info(chat_id)
                        
                        if is_unlocked and is_member:
                            send_main_menu(chat_id)
                        else:
                            send_welcome_task_menu(chat_id)

                    elif "callback_query" in item:
                        cb = item["callback_query"]
                        cb_id = cb["id"]
                        data = cb.get("data", "")
                        chat_id = str(cb["message"]["chat"]["id"])
                        msg_id = cb["message"]["message_id"]

                        if data == "verify_task":
                            is_member = check_channel_member(chat_id)
                            target, _, is_unlocked, current_day = get_user_task_info(chat_id)
                            
                            if not is_member:
                                answer_callback(cb_id, "Access Denied: You must join the channel first.", show_alert=True)
                            else:
                                raw_referrals = USERS_DB[chat_id].get("referrals", [])
                                valid_referrals = 0
                                fake_referrals = 0
                                
                                for ref_id in raw_referrals:
                                    if check_channel_member(ref_id):
                                        valid_referrals += 1
                                    else:
                                        fake_referrals += 1

                                if valid_referrals < target:
                                    remaining = target - valid_referrals
                                    alert_text = f"Access Denied: {remaining} more REAL users must JOIN the channel."
                                    if fake_referrals > 0:
                                        alert_text += f"\n\n⚠️ Detected {fake_referrals} fake referrals!"
                                    
                                    answer_callback(cb_id, alert_text, show_alert=True)
                                    send_welcome_task_menu(chat_id, msg_id)
                                else:
                                    if not is_unlocked:
                                        if "unlocked_days" not in USERS_DB[chat_id]:
                                            USERS_DB[chat_id]["unlocked_days"] = []
                                        USERS_DB[chat_id]["unlocked_days"].append(str(current_day))
                                        save_db(USERS_DB)
                                        
                                    answer_callback(cb_id, "Access Granted. Real Referrals Verified! ✅", show_alert=False)
                                    send_main_menu(chat_id, msg_id)
                                
                        elif data.startswith("open_"):
                            selected_slug = data.replace("open_", "")
                            switch_view(chat_id, msg_id, "market", selected_slug)
                            answer_callback(cb_id)

                        elif data == "back_to_menu":
                            switch_view(chat_id, msg_id, "menu", None)
                            answer_callback(cb_id)

                        else:
                            answer_callback(cb_id)
                            
        except Exception as e:
            pass
            
        time.sleep(0.5)

if __name__ == "__main__":
    sync_thread = threading.Thread(target=realtime_sync_engine, daemon=True)
    sync_thread.start()
    telegram_listener()
