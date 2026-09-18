import os
import time
import shutil
import tarfile
import urllib.request
import threading
import telebot
from telebot import types
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

# VNC ডিসপ্লে এনভায়রনমেন্ট
if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":1"

# geckodriver না থাকলে অটোমেটিক ডাউনলোড ও ইনস্টল ফাংশন
def check_and_install_gecko():
    if not shutil.which("geckodriver") and not os.path.exists("/usr/local/bin/geckodriver"):
        try:
            print("[*] Downloading geckodriver...")
            url = "https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz"
            tar_path = "/tmp/geckodriver.tar.gz"
            urllib.request.urlretrieve(url, tar_path)
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extract("geckodriver", path="/usr/local/bin")
            os.chmod("/usr/local/bin/geckodriver", 0o755)
            print("[+] geckodriver ready!")
        except Exception as e:
            print(f"[-] Gecko install warning: {e}")

check_and_install_gecko()

BOT_TOKEN = "8955426078:AAFpjgYEYHDyNJ2dJhqZ5S4e4qzINulz5js"
bot = telebot.TeleBot(BOT_TOKEN)

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
# ব্রাউজার যাতে স্ক্রিন থেকে বন্ধ না হয়ে যায় তার জন্য গ্লোবাল রেফারেন্স
active_browsers = {}

# CSS সিলেক্টর
SEL_PHONE = "body > div > div:nth-of-type(2) > div:nth-of-type(4) > div > div > div > div:nth-of-type(2) > input"
SEL_PASS = "body > div > div:nth-of-type(2) > div:nth-of-type(4) > div > div > div:nth-of-type(2) > div:nth-of-type(2) > input"
SEL_LOGIN = "body > div > div:nth-of-type(2) > div:nth-of-type(4) > div > div > div:nth-of-type(4) > button"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_amar = types.InlineKeyboardButton("🔥 Amarclub", callback_data="btn_amarclub")
    btn_dk = types.InlineKeyboardButton("⚡ DK Win", callback_data="btn_dkwin")
    markup.add(btn_amar, btn_dk)
    
    bot.send_message(
        message.chat.id,
        "👋 **স্বাগতম Dark Killer Automation প্যানেলে!**\n\nলগইন করার জন্য সাইট সিলেক্ট করুন:",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data in SITES)
def select_site(call):
    chat_id = call.message.chat.id
    site_info = SITES[call.data]
    user_data[chat_id] = {"target": site_info}
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        chat_id, 
        f"🌐 সাইট: **{site_info['name']}**\n\n📱 আপনার **মোবাইল নম্বর (N)** পাঠান:",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, get_phone_step)

def get_phone_step(message):
    chat_id = message.chat.id
    phone = message.text.strip()
    user_data[chat_id]["phone"] = phone
    
    msg = bot.send_message(chat_id, "🔑 এবার আপনার **পাসওয়ার্ড (P)** পাঠান:")
    bot.register_next_step_handler(msg, get_password_step)

def get_password_step(message):
    chat_id = message.chat.id
    password = message.text.strip()
    user_data[chat_id]["password"] = password
    
    target_name = user_data[chat_id]["target"]["name"]
    target_url = user_data[chat_id]["target"]["url"]
    phone = user_data[chat_id]["phone"]
    
    bot.send_message(
        chat_id, 
        f"🚀 **{target_name}** ডেস্কটপে ওপেন হচ্ছে...\nঅটোমেটিক নম্বর, পাসওয়ার্ড এবং লগইন সম্পন্ন করা হচ্ছে।"
    )
    
    thread = threading.Thread(
        target=run_login_automation, 
        args=(chat_id, target_url, phone, password)
    )
    thread.start()

def run_login_automation(chat_id, url, phone, password):
    try:
        options = Options()
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference('useAutomationExtension', False)
        options.add_argument("--width=1280")
        options.add_argument("--height=720")

        # ফায়ারফক্স ব্রাউজার ওপেন
        driver = webdriver.Firefox(options=options)
        active_browsers[chat_id] = driver  # ব্রাউজার সেশন ধরে রাখা (যাতে ক্লোজ না হয়)

        driver.get(url)
        wait = WebDriverWait(driver, 30)

        # পেজের ইনপুট বক্স লোড হওয়া নিশ্চিত করা
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SEL_PHONE)))
        time.sleep(2)

        # ১. জাভাস্ক্রিপ্ট দিয়ে Vue.js রিয়্যাক্টিভ ফিল্ডে N (ফোন) ও P (পাসওয়ার্ড) ইনপুট
        js_fill_script = f"""
        function triggerInput(selector, value) {{
            let el = document.querySelector(selector);
            if(el) {{
                el.focus();
                el.value = value;
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }}
            return false;
        }}
        triggerInput('{SEL_PHONE}', '{phone}');
        triggerInput('{SEL_PASS}', '{password}');
        """
        driver.execute_script(js_fill_script)
        time.sleep(1.5)

        # ২. L (লগইন বাটন) ক্লিক করা
        js_click_login = f"""
        let btn = document.querySelector('{SEL_LOGIN}');
        if(btn) {{
            btn.click();
        }}
        """
        driver.execute_script(js_click_login)

        # ৩. আপনার দেওয়া ভাসমান কন্ট্রোল বাটনটি পেজে যোগ করে দেওয়া
        js_inject_box = f"""
        if(!document.getElementById('_run_box')) {{
            let d=[
                {{"name":"N","sel":"{SEL_PHONE}"}},
                {{"name":"P","sel":"{SEL_PASS}"}},
                {{"name":"L","sel":"{SEL_LOGIN}"}}
            ];
            let b=document.createElement('div');
            b.id='_run_box';
            b.style.cssText='position:fixed;bottom:20px;right:20px;background:#18181b;padding:6px 10px;border-radius:30px;display:flex;gap:6px;align-items:center;z-index:99999999;box-shadow:0 6px 16px rgba(0,0,0,0.5);font:12px sans-serif;border:1px solid #00f2fe;';
            
            let all=document.createElement('button');
            all.innerText='▶ All';
            all.style.cssText='background:#f59e0b;color:#000;border:none;padding:5px 10px;border-radius:20px;cursor:pointer;font-weight:bold;font-size:11px;';
            all.onclick=()=>{{
                d.forEach((x,i)=>{{
                    setTimeout(()=>{{
                        let el=document.querySelector(x.sel);
                        if(el) el.click();
                    }}, i*400);
                }});
            }};
            b.appendChild(all);

            d.forEach(x=>{{
                let btn=document.createElement('button');
                btn.innerText=x.name;
                btn.style.cssText='background:#22c55e;color:#000;border:none;padding:5px 10px;border-radius:20px;cursor:pointer;font-weight:bold;font-size:11px;';
                btn.onclick=()=>{{
                    let el=document.querySelector(x.sel);
                    if(el) el.click();
                }};
                b.appendChild(btn);
            }});

            let x=document.createElement('span');
            x.innerText='✕';
            x.style.cssText='cursor:pointer;color:#a1a1aa;margin-left:6px;font-weight:bold;';
            x.onclick=()=>b.remove();
            b.appendChild(x);
            document.body.appendChild(b);
        }}
        """
        driver.execute_script(js_inject_box)
        time.sleep(3)

        # স্ক্রিনশট পাঠিয়ে টেলিগ্রামে নিশ্চিত করা
        shot_path = f"/tmp/login_{chat_id}.png"
        driver.save_screenshot(shot_path)
        with open(shot_path, "rb") as pic:
            bot.send_photo(chat_id, pic, caption="✅ লগইন ডেটা প্রবেশ করানো হয়েছে এবং সাইটটি ডেস্কটপে চালু আছে।")
        if os.path.exists(shot_path):
            os.remove(shot_path)

    except Exception as err:
        bot.send_message(chat_id, f"❌ সমস্যা হয়েছে:\n`{str(err)}`", parse_mode="Markdown")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
