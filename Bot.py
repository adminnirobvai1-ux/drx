import os
import sys
import subprocess

# টার্মিনাল কালার কোড
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def run_command(cmd, desc):
    print(f"\n{YELLOW}[+] {desc}...{RESET}")
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"{GREEN}[✓] সফলভাবে সম্পন্ন হয়েছে!{RESET}")
    except subprocess.CalledProcessError as e:
        print(f"{RED}[✗] এরর এসেছে: {e}{RESET}")

def install_all_packages():
    print(f"\n{CYAN}{BOLD}=== ফুল এনভায়রনমেন্ট ও প্যাকেজ সেটআপ শুরু হচ্ছে ==={RESET}\n")

    # ১. সিস্টেম আপডেট ও প্যাকেজ তালিকা রিফ্রেশ
    run_command("sudo apt update && sudo apt upgrade -y", "সিস্টেম আপডেট এবং আপগ্রেড করা হচ্ছে")

    # ২. সিস্টেম লেভেলের প্রয়োজনীয় টুলস, কম্পাইলার ও বিল্ড প্যাকেজ
    sys_packages = (
        "git curl wget unzip zip tar gzip bzip2 p7zip-full nano vim htop tmux "
        "screen net-tools iputils-ping dnsutils software-properties-common "
        "build-essential make cmake gcc g++ clang libssl-dev zlib1g-dev "
        "libbz2-dev libreadline-dev libsqlite3-dev libffi-dev libxml2-dev "
        "libxslt1-dev libjpeg-dev zlib1g-dev libpng-dev libpq-dev default-libmysqlclient-dev"
    )
    run_command(f"sudo apt install -y {sys_packages}", "সিস্টেম কোর ইউটিলিটি ও বিল্ড ডিপেনডেন্সি ইনস্টল করা হচ্ছে")

    # ৩. পাইথন এনভায়রনমেন্ট ও প্যাকেজ ম্যানেজার
    run_command("sudo apt install -y python3 python3-pip python3-dev python3-venv python3-setuptools python3-wheel", "পাইথন কোর ও পিপ ইনস্টল করা হচ্ছে")
    run_command("python3 -m pip install --upgrade pip setuptools wheel", "পিপ এবং বিল্ড টুলস আপগ্রেড করা হচ্ছে")

    # ৪. পিএইচপি এবং তার প্রয়োজনীয় সব এক্সটেনশন
    php_packages = (
        "php php-cli php-fpm php-json php-common php-mysql php-zip php-gd "
        "php-mbstring php-curl php-xml php-pear php-bcmath php-intl php-soap"
    )
    run_command(f"sudo apt install -y {php_packages}", "পিএইচপি এবং সব এক্সটেনশন ইনস্টল করা হচ্ছে")

    # ৫. পাইথনের গুরুত্বপূর্ণ প্যাকেজসমূহ (ওয়েব, স্ক্র্যাপিং, অটোমেশন, ডাটা সায়েন্স ও ইউটিলিটি)
    # --ignore-installed রাখা হয়েছে যাতে পূর্বের বিল্ট-ইন প্যাকেজের কনফ্লিক্ট এড়িয়ে ইনস্টল হয়
    pip_packages = [
        # নেটওয়ার্কিং ও এপিআই
        "requests", "urllib3", "aiohttp", "httpx", "certifi", "chardet", "idna", "websockets",
        
        # ওয়েব ফ্রেমওয়ার্ক ও ব্যাকএন্ড
        "flask", "flask-cors", "fastapi", "uvicorn[standard]", "django", "tornado", "bottle",
        
        # স্ক্র্যাপিং ও পার্সিং
        "beautifulsoup4", "lxml", "html5lib", "selenium", "playwright", "scrapy",
        
        # টেলিগ্রাম ও চ্যাটবট অটোমেশন
        "python-telegram-bot", "telethon", "pyrogram", "tgcrypto", "schedule", "pyautogui",
        
        # ডাটা প্রসেসিং, এক্সেল ও ডাটাবেস
        "numpy", "pandas", "openpyxl", "xlsxwriter", "xlrd", "sqlalchemy", "pymongo", "redis", "psycopg2-binary",
        
        # ইমেজ, মিডিয়া ও ভিডিও এডিটিং
        "pillow", "moviepy", "opencv-python-headless", "mutagen", "imageio",
        
        # কনফিগারেশন, ক্রিপ্টোগ্রাফি ও এনক্রিপশন
        "python-dotenv", "pyyaml", "cryptography", "pycryptodome", "bcrypt",
        
        # কোড কোয়ালিটি ও টেস্টিং
        "pytest", "black", "flake8", "tqdm", "colorama", "rich"
    ]
    
    pip_cmd = f"pip3 install --ignore-installed {' '.join(pip_packages)}"
    run_command(pip_cmd, "পাইথনের শত শত প্রয়োজনীয় লাইব্রেরি ও ফ্রেমওয়ার্ক ইনস্টল করা হচ্ছে")

    print(f"\n{GREEN}{BOLD}=================================================={RESET}")
    print(f"{GREEN}{BOLD}   সব প্যাকেজ সফলভাবে ইনস্টল সম্পন্ন হয়েছে!         {RESET}")
    print(f"{GREEN}{BOLD}=================================================={RESET}\n")

def show_menu():
    while True:
        print(f"\n{CYAN}{BOLD}=========================================={RESET}")
        print(f"{GREEN}{BOLD}     অল-ইন-ওয়ান প্যাকেজ ইনস্টলার মেনু      {RESET}")
        print(f"{CYAN}{BOLD}=========================================={RESET}")
        print(f"{YELLOW}[1]{RESET} সমস্ত প্যাকেজ ইনস্টল করুন (All Setup)")
        print(f"{YELLOW}[2]{RESET} বের হয়ে যান (Exit)")
        print(f"{CYAN}------------------------------------------{RESET}")
        
        choice = input(f"{BOLD}আপনার পছন্দ নির্বাচন করুন (1/2): {RESET}").strip()
        
        if choice == "1":
            install_all_packages()
            break
        elif choice == "2":
            print(f"\n{RED}প্রোগ্রামটি বন্ধ করা হলো। ভালো থাকবেন!{RESET}\n")
            sys.exit(0)
        else:
            print(f"\n{RED}[!] ভুল অপশন নির্বাচন করেছেন। ১ অথবা ২ চাপুন।{RESET}")

if __name__ == "__main__":
    show_menu()
