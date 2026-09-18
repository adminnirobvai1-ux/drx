import os
import time
import threading
import telebot
from telebot import types
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options

# VNC সার্ভারের ডিসপ্লে পোর্ট ফিক্স (:1)
os.environ["DISPLAY"] = ":1"

BOT_TOKEN = "8955426078:AAFpjgYEYHDyNJ2dJhqZ5S4e4qzINulz5js"
bot = telebot.TeleBot(BOT_TOKEN)

# সাইটের সঠিক লগইন লিংক
SITES = {
    "btn_amarclub": {
        "name": "Amarclub",
        "url": "https://amarclub6.com/#/login"
    },
    "btn_dkwin": {
        "name": "DK Win",
        "url": "https://dkwin6.com/#/login"
    }
}

user_data = {}

# /start কমান্ড
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_amar = types.InlineKeyboardButton("🔥 Amarclub", callback_data="btn_amarclub")
    btn_dk = types.InlineKeyboardButton("⚡ DK Win", callback_data="btn_dkwin")
    markup.add(btn_amar, btn_dk)
    
    bot.send_message(
        message.chat.id,
        "👋 **স্বাগতম Dark Killer Automation প্যানেলে!**\n\nযে সাইটে লগইন করতে চান সেটি নির্বাচন করুন:",
        parse_mode="Markdown",
        reply_markup=markup
    )

# সাইট সিলেকশন বাটন হ্যান্ডলার
@bot.callback_query_handler(func=lambda call: call.data in SITES)
def select_site(call):
    chat_id = call.message.chat.id
    site_info = SITES[call.data]
    user_data[chat_id] = {"target": site_info}
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        chat_id, 
        f"🌐 নির্বাচিত সাইট: **{site_info['name']}**\n\n📱 আপনার **মোবাইল নম্বর (N)** লিখে পাঠান:",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, get_phone_step)

# নম্বর ইনপুট গ্রহণ
def get_phone_step(message):
    chat_id = message.chat.id
    phone = message.text.strip()
    user_data[chat_id]["phone"] = phone
    
    msg = bot.send_message(chat_id, "🔑 এবার আপনার **পাসওয়ার্ড (P)** লিখে পাঠান:")
    bot.register_next_step_handler(msg, get_password_step)

# পাসওয়ার্ড ইনপুট ও অটোমেশন কল
def get_password_step(message):
    chat_id = message.chat.id
    password = message.text.strip()
    user_data[chat_id]["password"] = password
    
    target_name = user_data[chat_id]["target"]["name"]
    target_url = user_data[chat_id]["target"]["url"]
    phone = user_data[chat_id]["phone"]
    
    bot.send_message(
        chat_id, 
        f"🚀 **{target_name}**-এ লগইন প্রসেস শুরু হচ্ছে...\nডেস্কটপ স্ক্রিনে ব্রাউজার ওপেন হচ্ছে, অপেক্ষা করুন।"
    )
    
    # বট যাতে আটকে না যায় তাই থ্রেডে সেলেনিয়াম রান করানো হচ্ছে
    thread = threading.Thread(
        target=run_login_automation, 
        args=(chat_id, target_url, phone, password)
    )
    thread.start()

# ব্রাউজার অটোমেশন ফাংশন
def run_login_automation(chat_id, url, phone, password):
    driver = None
    try:
        options = Options()
        options.add_argument("--width=1280")
        options.add_argument("--height=720")
        
        driver = webdriver.Firefox(options=options)
        driver.get(url)
        wait = WebDriverWait(driver, 25)

        # ১. নম্বর ফিল্ড (N) সিলেক্টর
        phone_sel = "body > div > div:nth-of-type(2) > div:nth-of-type(4) > div > div > div > div:nth-of-type(2) > input"
        phone_elem = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, phone_sel)))
        phone_elem.clear()
        phone_elem.send_keys(phone)
        time.sleep(1)

        # ২. পাসওয়ার্ড ফিল্ড (P) সিলেক্টর
        pass_sel = "body > div > div:nth-of-type(2) > div:nth-of-type(4) > div > div > div:nth-of-type(2) > div:nth-of-type(2) > input"
        pass_elem = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, pass_sel)))
        pass_elem.clear()
        pass_elem.send_keys(password)
        time.sleep(1)

        # ৩. লগইন বাটন (L) সিলেক্টর
        btn_sel = "body > div > div:nth-of-type(2) > div:nth-of-type(4) > div > div > div:nth-of-type(4) > button"
        btn_elem = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, btn_sel)))
        btn_elem.click()

        time.sleep(5)

        # কনফার্মেশন স্ক্রিনশট নেওয়া
        screenshot_path = f"/tmp/shot_{chat_id}.png"
        driver.save_screenshot(screenshot_path)
        with open(screenshot_path, "rb") as pic:
            bot.send_photo(
                chat_id, 
                pic, 
                caption="✅ লগইন ইনপুট সম্পন্ন হয়েছে এবং সাইট ওপেন রয়েছে।"
            )
        
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)

    except Exception as err:
        bot.send_message(chat_id, f"❌ ত্রুটি দেখা দিয়েছে:\n`{str(err)}`", parse_mode="Markdown")

if __name__ == "__main__":
    print("Bot is listening on DISPLAY=:1...")
    bot.infinity_polling()
