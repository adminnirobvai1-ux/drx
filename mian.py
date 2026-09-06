import time
import threading
import requests
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException

# --- কনফিগারেশন ---
BOT_TOKEN = "8949748635:AAF9w3mFRx2fqcE6AslsrR7AUuNJQzqB-PA"
API_URL = "https://advanced-predict1.ai.studio/apipid.json"

bot = telebot.TeleBot(BOT_TOKEN)

# লাইভ স্ট্যাটাস (শুরু থেকে ০ থাকবে, কোনো ফেক ডাটা নেই)
stats = {
    "total_games": 0,
    "wins": 0,
    "losses": 0,
    "current_loss_streak": 0,
    "max_loss": 0,
    "history": []  # [{'period': '2229', 'num': 2, 'type': 'SMALL', 'result': 'WIN'}]
}

# ইউজারের মেসেজ ও পেজ ট্র্যাকিং
active_dashboards = {}  # {chat_id: message_id}
user_pages = {}         # {chat_id: current_page (1 to 10)}

# বর্তমান লাইভ প্রেডিকশন
current_pred = {
    "period": None,
    "n1": None,
    "n2": None,
    "btn_size": "BIG",
    "btn_num": "NUM: -",
    "btn_color": "RED",
    "active_size": None,
    "active_color": None
}

def get_color(num):
    """নাম্বারের কালার নির্ধারণ: 0,2,4,6,8 = RED এবং 1,3,5,7,9 = GREEN"""
    num = int(num)
    if num in [0, 2, 4, 6, 8]:
        return "RED"
    return "GREEN"

def get_size(num):
    """নাম্বারের সাইজ নির্ধারণ: 0-4 = SMALL এবং 5-9 = BIG"""
    num = int(num)
    return "BIG" if num >= 5 else "SMALL"

def analyze_pattern(market_history):
    """
    পেজ ১ ও ২ (প্রথম ২০টি ড্র) বাদ দিয়ে পেজ ৩ থেকে ১০ (বাকি ডাটা)
    এর ভেতর টপের ২ ডিজিট বা তার উল্টো সিকোয়েন্স খুঁজে উপরের ও নিচের নাম্বার বের করা।
    """
    if len(market_history) < 25:
        n1, n2 = 7, 3
    else:
        # টপের ২টি সংখ্যা
        top_n1 = int(market_history[0].get("number", 0))
        top_n2 = int(market_history[1].get("number", 0))
        
        pair_normal = [top_n2, top_n1]
        pair_reverse = [top_n1, top_n2]
        
        # পেজ ১ ও ২ বাদ দিয়ে পেজ ৩ থেকে অনুসন্ধান (ইনডেক্স ২০ থেকে শুরু)
        search_list = market_history[20:]
        found_n1, found_n2 = None, None

        for i in range(1, len(search_list) - 2):
            curr_pair = [
                int(search_list[i+1].get("number", -1)),
                int(search_list[i].get("number", -1))
            ]
            # সোজা অথবা উল্টো সিকোয়েন্স ম্যাচিং
            if curr_pair == pair_normal or curr_pair == pair_reverse:
                # ওই পেয়ারের ঠিক উপরের এবং নিচের সংখ্যা নেওয়া
                found_n1 = int(search_list[i-1].get("number", 0))  # উপরের
                found_n2 = int(search_list[i+2].get("number", 0))  # নিচের
                break
        
        if found_n1 is not None and found_n2 is not None:
            n1, n2 = found_n1, found_n2
        else:
            # ম্যাচ না পেলে ব্যাকআপ ট্রেন্ড
            n1 = (top_n1 + 4) % 10
            n2 = (top_n2 + 3) % 10

    s1, s2 = get_size(n1), get_size(n2)
    c1, c2 = get_color(n1), get_color(n2)

    btn_size = ""
    btn_color = ""
    active_size = None
    active_color = None

    # ১. সাইজ এক কিন্তু কালার ভিন্ন -> শুধু সাইজ প্রেডিকশন
    if s1 == s2 and c1 != c2:
        btn_size = s1
        btn_color = "95%"
        active_size = s1

    # ২. কালার এক কিন্তু সাইজ ভিন্ন -> শুধু কালার প্রেডিকশন
    elif c1 == c2 and s1 != s2:
        btn_color = c1
        btn_size = "95%"
        active_color = c1

    # ৩. সাইজ ও কালার উভয়ই এক -> দুটিই প্রেডিকশন
    elif s1 == s2 and c1 == c2:
        btn_size = s1
        btn_color = c1
        active_size = s1
        active_color = c1

    # ৪. সাইজ ও কালার উভয়ই ভিন্ন -> শুধু ২-ডিজিট নাম্বার
    else:
        btn_size = "❌ 95%"
        btn_color = "❌ 95%"

    btn_num = f"NUM: {n1}" if n1 == n2 else f"NUM: {n1},{n2}"

    return {
        "n1": n1,
        "n2": n2,
        "btn_size": btn_size,
        "btn_num": btn_num,
        "btn_color": btn_color,
        "active_size": active_size,
        "active_color": active_color
    }

def fetch_market_data():
    """API থেকে লাইভ ডাটা রিড করা"""
    try:
        res = requests.get(API_URL, timeout=6)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

def build_interface(chat_id, period, seconds_left):
    """ছবির ইন্টারফেস এবং ১০ পেজের বাটন গ্রিড তৈরি"""
    # প্রগ্রেস বার (ছবির মতো)
    filled = max(1, min(20, (30 - seconds_left) * 20 // 30))
    bar = "█" * filled + "░" * (20 - filled)

    header_text = (
        f"<b>PERIOD: {period}</b>\n\n"
        f"⏳ <b>{seconds_left:02d}S</b> [{bar}]"
    )

    markup = types.InlineKeyboardMarkup()

    # রো ১: ৩টি প্রেডিকশন বাটন (ছবির মতো [BIG] [NUM: 7] [BACK/COLOR])
    b_size = types.InlineKeyboardButton(current_pred["btn_size"], callback_data="pred_size")
    b_num = types.InlineKeyboardButton(current_pred["btn_num"], callback_data="pred_num")
    b_color = types.InlineKeyboardButton(current_pred["btn_color"], callback_data="pred_color")
    markup.row(b_size, b_num, b_color)

    # পেজিনেশন অনুযায়ী হিস্ট্রি নির্বাচন (প্রতি পেজে ১০টি রেজাল্ট)
    current_page = user_pages.get(chat_id, 1)
    all_history = list(reversed(stats["history"]))  # সাম্প্রতিক রেজাল্ট আগে
    
    start_idx = (current_page - 1) * 10
    end_idx = start_idx + 10
    page_items = all_history[start_idx:end_idx]

    # রো ২-১১: ১০টি হিস্ট্রি রো (৪ কলাম: PERIOD, NUM, SIZE, WIN/LOSS)
    for row in page_items:
        b_p = types.InlineKeyboardButton(str(row["period"]), callback_data="h_p")
        b_n = types.InlineKeyboardButton(str(row["num"]), callback_data="h_n")
        b_s = types.InlineKeyboardButton(str(row["type"]), callback_data="h_s")
        b_r = types.InlineKeyboardButton(str(row["result"]), callback_data="h_r")
        markup.row(b_p, b_n, b_s, b_r)

    # রো ১২: পেজ নেভিগেশন বাটন (১০টি পেজ ব্রাউজ করার জন্য)
    btn_prev = types.InlineKeyboardButton("◀️ Prev", callback_data="page_prev")
    btn_page = types.InlineKeyboardButton(f"Page {current_page}/10", callback_data="page_cur")
    btn_next = types.InlineKeyboardButton("Next ▶️", callback_data="page_next")
    markup.row(btn_prev, btn_page, btn_next)

    return header_text, markup

def check_win_loss(actual_num):
    """প্রেডিকশন যাচাই ও উইন/লস স্ট্যাটাস আপডেট"""
    is_win = False
    actual_size = get_size(actual_num)
    actual_color = get_color(actual_num)

    # ১. নাম্বারে মিলে গেলে ডাইরেক্ট উইন (জ্যাকপট)
    if actual_num in [current_pred["n1"], current_pred["n2"]]:
        is_win = True
    # ২. সাইজ প্রেডিকশন থাকলে এবং মিললে
    elif current_pred["active_size"] and current_pred["active_size"] == actual_size:
        is_win = True
    # ৩. কালার প্রেডিকশন থাকলে এবং মিললে
    elif current_pred["active_color"] and current_pred["active_color"] == actual_color:
        is_win = True

    stats["total_games"] += 1
    if is_win:
        stats["wins"] += 1
        stats["current_loss_streak"] = 0
        return "WIN"
    else:
        stats["losses"] += 1
        stats["current_loss_streak"] += 1
        if stats["current_loss_streak"] > stats["max_loss"]:
            stats["max_loss"] = stats["current_loss_streak"]
        return "LOSS"

def live_worker():
    """২৪ ঘণ্টা ব্যাকগ্রাউন্ডে চলার প্রধান ইঞ্জিন"""
    global current_pred
    last_period = None

    while True:
        try:
            api_data = fetch_market_data()
            if api_data:
                payload = api_data.get("data", api_data)
                period = payload.get("period", "00052230")
                seconds_left = int(payload.get("seconds_left", payload.get("time_remaining", 10)))
                history_list = payload.get("history", payload.get("list", []))

                # নতুন পিরিয়ড এলে আগেরটির রেজাল্ট হিসাব ও নতুন প্রেডিকশন জেনারেট
                if period != last_period and last_period is not None:
                    if history_list:
                        latest_draw = history_list[0]
                        actual_num = int(latest_draw.get("number", 0))
                        actual_size = get_size(actual_num)

                        result = check_win_loss(actual_num)

                        # হিস্ট্রিতে ৪-ডিজিট পিরিয়ড যুক্ত করা (ছবির মতো: ২২২৯, ২২২৮ ইত্যাদি)
                        stats["history"].append({
                            "period": str(last_period)[-4:],
                            "num": actual_num,
                            "type": actual_size,
                            "result": result
                        })

                    # পরবর্তী পিরিয়ডের জন্য প্যাটার্ন সার্চ
                    analysis = analyze_pattern(history_list)
                    current_pred.update(analysis)
                    current_pred["period"] = period
                    last_period = period

                elif last_period is None:
                    last_period = period
                    analysis = analyze_pattern(history_list)
                    current_pred.update(analysis)
                    current_pred["period"] = period

                # লাইভ মেসেজ ও বাটন আপডেট
                for chat_id, msg_id in list(active_dashboards.items()):
                    header_text, keyboard = build_interface(chat_id, period, seconds_left)
                    try:
                        bot.edit_message_text(
                            header_text,
                            chat_id=chat_id,
                            message_id=msg_id,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                    except ApiTelegramException as e:
                        if "message to edit not found" in str(e).lower():
                            active_dashboards.pop(chat_id, None)
                    except Exception:
                        pass

            time.sleep(2)  # প্রতি ২ সেকেন্ড পর পর টাইমার ও বাটন সিঙ্ক
        except Exception:
            time.sleep(4)

# --- টেলিগ্রাম বট হ্যান্ডলার ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_pages[chat_id] = 1
    init_msg = bot.send_message(chat_id, "<b>বট সংযুক্ত হচ্ছে...</b>", parse_mode="HTML")
    active_dashboards[chat_id] = init_msg.message_id

@bot.callback_query_handler(func=lambda call: True)
def handle_pagination(call):
    chat_id = call.message.chat.id
    cur = user_pages.get(chat_id, 1)

    if call.data == "page_prev":
        if cur > 1:
            user_pages[chat_id] = cur - 1
            bot.answer_callback_query(call.id, text=f"পেজ {cur - 1}")
        else:
            bot.answer_callback_query(call.id, text="প্রথম পেজে আছেন")

    elif call.data == "page_next":
        if cur < 10:
            user_pages[chat_id] = cur + 1
            bot.answer_callback_query(call.id, text=f"পেজ {cur + 1}")
        else:
            bot.answer_callback_query(call.id, text="শেষ পেজে আছেন")

    else:
        bot.answer_callback_query(call.id)

if __name__ == "__main__":
    # ব্যাকগ্রাউন্ড প্রেডিকশন থ্রেড চালু
    t = threading.Thread(target=live_worker, daemon=True)
    t.start()

    # টেলিগ্রাম বট পোলিং
    bot.infinity_polling(skip_pending=True)
