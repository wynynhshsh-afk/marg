# ============================================
# ربات ویو زن شیشه‌ای - کد کامل
# پایتون 3.14 - python-telegram-bot v21.8
# ============================================

import asyncio
import aiohttp
import random
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ContextTypes

# ==================== تنظیمات اولیه ====================

# دریافت از محیط اجرا (برای Render)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://yourdomain.com")
WEBHOOK_PORT = int(os.environ.get("PORT", 8443))

# آیدی عددی دو ادمین اصلی (اینجا تغییر دهید)
MASTER_ADMINS = [123456789, 987654321]  # آیدی خود را وارد کنید

# لیست اولیه پروکسی‌ها (حداقل ۵۰ عدد برای عملکرد بهتر)
PROXY_LIST = [
    "http://proxy1:8080",
    "http://proxy2:8080",
    "http://proxy3:8080",
    "http://proxy4:8080",
    "http://proxy5:8080",
    # ... ۴۵ پروکسی دیگر اضافه کنید
]

# تنظیمات پیش‌فرض
DEFAULT_SETTINGS = {
    'speed': 1000,
    'delay': 0,
    'random_header': True,
    'auto_rotate': True,
}

# ==================== کلاس مدیریت کاربران ====================

class UserManager:
    def __init__(self, file_path='users.json'):
        self.file_path = file_path
        self.users = []
        self.load()
    
    def load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.users = json.load(f)
        else:
            self.users = MASTER_ADMINS.copy()
            self.save()
    
    def save(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.users, f)
    
    def add_user(self, user_id: int):
        if user_id not in self.users:
            self.users.append(user_id)
            self.save()
            return True
        return False
    
    def remove_user(self, user_id: int):
        if user_id in self.users and user_id not in MASTER_ADMINS:
            self.users.remove(user_id)
            self.save()
            return True
        return False
    
    def is_allowed(self, user_id: int):
        return user_id in self.users

# ==================== کلاس مدیریت آمار ====================

class StatsManager:
    def __init__(self, file_path='stats.json'):
        self.file_path = file_path
        self.data = {'today': 0, 'week': 0, 'month': 0, 'total': 0, 'failed': 0}
        self.load()
    
    def load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.data = json.load(f)
    
    def save(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.data, f)
    
    def add_success(self, count: int):
        self.data['today'] += count
        self.data['week'] += count
        self.data['month'] += count
        self.data['total'] += count
        self.save()
    
    def add_failed(self, count: int = 1):
        self.data['failed'] += count
        self.save()
    
    def reset_today(self):
        self.data['today'] = 0
        self.save()

# ==================== کلاس مدیریت تنظیمات ====================

class SettingsManager:
    def __init__(self, file_path='settings.json'):
        self.file_path = file_path
        self.settings = DEFAULT_SETTINGS.copy()
        self.load()
    
    def load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.settings = json.load(f)
    
    def save(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.settings, f)
    
    def get(self, key):
        return self.settings.get(key, DEFAULT_SETTINGS.get(key))
    
    def set(self, key, value):
        self.settings[key] = value
        self.save()

# ==================== نمونه‌سازی کلاس‌ها ====================

user_manager = UserManager()
stats_manager = StatsManager()
settings_manager = SettingsManager()

# ==================== توابع کیبورد ====================

def get_glass_menu():
    """منوی اصلی با استایل شیشه‌ای"""
    keyboard = [
        [InlineKeyboardButton("💎 ویو تصادفی", callback_data="random_view")],
        [InlineKeyboardButton("🎯 ویو دلخواه", callback_data="custom_view")],
        [InlineKeyboardButton("📊 آمار ویوها", callback_data="stats")],
        [InlineKeyboardButton("🔄 تغییر پروکسی", callback_data="proxy")],
        [InlineKeyboardButton("👥 مدیریت کاربران", callback_data="users")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_random_view_menu():
    """منوی انتخاب تعداد تصادفی"""
    keyboard = [
        [InlineKeyboardButton("🎲 ۱۰۰ ویو", callback_data="rand_100")],
        [InlineKeyboardButton("🎲 ۵۰۰ ویو", callback_data="rand_500")],
        [InlineKeyboardButton("🎲 ۱۰۰۰ ویو", callback_data="rand_1000")],
        [InlineKeyboardButton("🎲 ۵۰۰۰ ویو", callback_data="rand_5000")],
        [InlineKeyboardButton("🎲 ۱۰۰۰۰ ویو", callback_data="rand_10000")],
        [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_custom_number_keyboard():
    """کیبورد عددی برای ویو دلخواه"""
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="num_1"),
            InlineKeyboardButton("2", callback_data="num_2"),
            InlineKeyboardButton("3", callback_data="num_3"),
            InlineKeyboardButton("⌫", callback_data="backspace"),
        ],
        [
            InlineKeyboardButton("4", callback_data="num_4"),
            InlineKeyboardButton("5", callback_data="num_5"),
            InlineKeyboardButton("6", callback_data="num_6"),
            InlineKeyboardButton("✅", callback_data="confirm_number"),
        ],
        [
            InlineKeyboardButton("7", callback_data="num_7"),
            InlineKeyboardButton("8", callback_data="num_8"),
            InlineKeyboardButton("9", callback_data="num_9"),
            InlineKeyboardButton("0", callback_data="num_0"),
        ],
        [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_stats_menu():
    """منوی آمار"""
    keyboard = [
        [InlineKeyboardButton("📅 امروز", callback_data="stats_today")],
        [InlineKeyboardButton("📆 این هفته", callback_data="stats_week")],
        [InlineKeyboardButton("📈 این ماه", callback_data="stats_month")],
        [InlineKeyboardButton("📊 کل ویوها", callback_data="stats_total")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_proxy_menu():
    """منوی مدیریت پروکسی"""
    auto_status = "✅ فعال" if settings_manager.get('auto_rotate') else "❌ غیرفعال"
    keyboard = [
        [InlineKeyboardButton(f"🔄 چرخش خودکار ({auto_status})", callback_data="proxy_auto")],
        [InlineKeyboardButton("🌐 افزودن پروکسی", callback_data="proxy_add")],
        [InlineKeyboardButton("📋 لیست پروکسی‌ها", callback_data="proxy_list")],
        [InlineKeyboardButton("🗑 پاک کردن همه", callback_data="proxy_clear")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_users_menu():
    """منوی مدیریت کاربران (فقط ادمین)"""
    keyboard = [
        [InlineKeyboardButton("➕ افزودن کاربر", callback_data="user_add")],
        [InlineKeyboardButton("➖ حذف کاربر", callback_data="user_remove")],
        [InlineKeyboardButton("👥 لیست کاربران", callback_data="user_list")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_menu():
    """منوی تنظیمات"""
    keyboard = [
        [InlineKeyboardButton("⏱ سرعت ویو", callback_data="set_speed")],
        [InlineKeyboardButton("🛡 تاخیر بین ویوها", callback_data="set_delay")],
        [InlineKeyboardButton("🌍 تغییر هدر", callback_data="set_header")],
        [InlineKeyboardButton("💾 ذخیره تنظیمات", callback_data="save_settings")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== تابع ارسال ویو ====================

async def send_view_async(url: str, proxy: str, headers: dict) -> bool:
    """ارسال یک ویو به صورت غیرهمزمان"""
    try:
        timeout = aiohttp.ClientTimeout(total=3)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, proxy=proxy, headers=headers, ssl=False) as resp:
                return resp.status in [200, 201, 202, 204, 301, 302]
    except Exception as e:
        logging.error(f"ویو ناموفق: {e}")
        return False

async def execute_views(post_url: str, count: int, context: ContextTypes.DEFAULT_TYPE) -> int:
    """اجرای همزمان ویوها با سرعت مشخص"""
    success_count = 0
    speed = settings_manager.get('speed')
    delay = settings_manager.get('delay')
    
    # ایجاد لیست پروکسی‌های قابل استفاده
    available_proxies = PROXY_LIST.copy()
    if not available_proxies:
        available_proxies = [None]
    
    # اجرا به صورت بچ‌های همزمان
    batch_size = speed
    total_batches = (count + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        batch_count = min(batch_size, count - (batch_num * batch_size))
        tasks = []
        
        for _ in range(batch_count):
            proxy = random.choice(available_proxies) if available_proxies and settings_manager.get('auto_rotate') else None
            
            # تولید هدر تصادفی
            headers = {
                'User-Agent': random.choice([
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
                ]),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            if settings_manager.get('random_header'):
                headers['Referer'] = random.choice([
                    'https://www.google.com/',
                    'https://www.bing.com/',
                    'https://www.yahoo.com/',
                    'https://www.instagram.com/',
                    'https://www.facebook.com/',
                ])
            
            tasks.append(send_view_async(post_url, proxy, headers))
        
        # اجرای همزمان بچ
        results = await asyncio.gather(*tasks)
        success_count += sum(results)
        
        # اعمال تاخیر بین بچ‌ها
        if delay > 0 and batch_num < total_batches - 1:
            await asyncio.sleep(delay / 1000)
    
    # به‌روزرسانی آمار
    if success_count > 0:
        stats_manager.add_success(success_count)
    failed = count - success_count
    if failed > 0:
        stats_manager.add_failed(failed)
    
    return success_count

# ==================== هندلرهای ربات ====================

# وضعیت‌های مکالمه
WAITING_FOR_LINK, WAITING_FOR_PROXY, WAITING_FOR_USER = range(3)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    user_id = update.effective_user.id
    if not user_manager.is_allowed(user_id):
        await update.message.reply_text("⛔ شما دسترسی به این ربات ندارید!")
        return
    
    welcome_text = (
        "✨💎 **ربات ویو زن شیشه‌ای** 💎✨\n\n"
        f"🌀 **سرعت:** {settings_manager.get('speed')} ویو در ثانیه\n"
        f"🔮 **پروکسی چرخشی:** {'✅ فعال' if settings_manager.get('auto_rotate') else '❌ غیرفعال'}\n"
        "📡 **وضعیت:** 🟢 آنلاین\n\n"
        "از دکمه‌های زیر برای شروع استفاده کنید:"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_glass_menu(), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت تمام کلیک‌های دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not user_manager.is_allowed(user_id):
        await query.edit_message_text("⛔ شما دسترسی ندارید!", reply_markup=get_glass_menu())
        return
    
    data = query.data
    
    # ========== بازگشت به منو ==========
    if data == "menu":
        await query.edit_message_text(
            "✨💎 **ربات ویو زن شیشه‌ای** 💎✨\n\nمنوی اصلی:",
            reply_markup=get_glass_menu(),
            parse_mode='Markdown'
        )
        context.user_data.clear()
    
    # ========== ویو تصادفی ==========
    elif data == "random_view":
        await query.edit_message_text(
            "🎲 **تعداد ویو تصادفی را انتخاب کنید:**",
            reply_markup=get_random_view_menu(),
            parse_mode='Markdown'
        )
    
    elif data.startswith("rand_"):
        count = int(data.split("_")[1])
        # اعمال تصادفی‌سازی ±۲۰%
        actual_count = int(count * random.uniform(0.8, 1.2))
        context.user_data['target_count'] = actual_count
        context.user_data['view_type'] = 'random'
        context.user_data['state'] = WAITING_FOR_LINK
        
        await query.edit_message_text(
            f"✅ **{actual_count} ویو** تنظیم شد (محدوده: {count} ± ۲۰%)\n\n"
            f"📎 لینک پست را ارسال کنید:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="menu")]
            ]),
            parse_mode='Markdown'
        )
    
    # ========== ویو دلخواه ==========
    elif data == "custom_view":
        context.user_data['number_input'] = ""
        await query.edit_message_text(
            "🔢 **تعداد ویو را با دکمه‌ها وارد کنید:**",
            reply_markup=get_custom_number_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == "backspace":
        if 'number_input' in context.user_data:
            context.user_data['number_input'] = context.user_data['number_input'][:-1]
        await query.edit_message_text(
            f"🔢 تعداد: `{context.user_data.get('number_input', '')}`",
            reply_markup=get_custom_number_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data.startswith("num_"):
        digit = data.split("_")[1]
        if 'number_input' not in context.user_data:
            context.user_data['number_input'] = ""
        context.user_data['number_input'] += digit
        await query.edit_message_text(
            f"🔢 تعداد: `{context.user_data['number_input']}`",
            reply_markup=get_custom_number_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == "confirm_number":
        if 'number_input' in context.user_data and context.user_data['number_input']:
            count = int(context.user_data['number_input'])
            if count < 1 or count > 1000000:
                await query.edit_message_text(
                    "❌ تعداد باید بین ۱ تا ۱,۰۰۰,۰۰۰ باشد!",
                    reply_markup=get_custom_number_keyboard()
                )
                return
            
            context.user_data['target_count'] = count
            context.user_data['view_type'] = 'custom'
            context.user_data['state'] = WAITING_FOR_LINK
            
            await query.edit_message_text(
                f"✅ **{count} ویو** تنظیم شد.\n\n📎 لینک پست را ارسال کنید:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="menu")]
                ]),
                parse_mode='Markdown'
            )
    
    # ========== آمار ==========
    elif data == "stats":
        await query.edit_message_text(
            "📊 **آمار ویوها:**\n\n"
            f"📅 امروز: **{stats_manager.data['today']}** ویو\n"
            f"📆 این هفته: **{stats_manager.data['week']}** ویو\n"
            f"📈 این ماه: **{stats_manager.data['month']}** ویو\n"
            f"📊 کل: **{stats_manager.data['total']}** ویو\n"
            f"❌ ناموفق: **{stats_manager.data['failed']}** ویو\n"
            f"⚡ سرعت لحظه‌ای: **{settings_manager.get('speed')}** ویو/ثانیه",
            reply_markup=get_stats_menu(),
            parse_mode='Markdown'
        )
    
    elif data.startswith("stats_"):
        period = data.split("_")[1]
        if period == "today":
            await query.edit_message_text(
                f"📅 **آمار امروز:**\n✅ {stats_manager.data['today']} ویو موفق",
                reply_markup=get_stats_menu()
            )
        elif period == "week":
            await query.edit_message_text(
                f"📆 **آمار این هفته:**\n✅ {stats_manager.data['week']} ویو موفق",
                reply_markup=get_stats_menu()
            )
        elif period == "month":
            await query.edit_message_text(
                f"📈 **آمار این ماه:**\n✅ {stats_manager.data['month']} ویو موفق",
                reply_markup=get_stats_menu()
            )
        elif period == "total":
            await query.edit_message_text(
                f"📊 **آمار کل:**\n✅ {stats_manager.data['total']} ویو موفق\n❌ {stats_manager.data['failed']} ویو ناموفق",
                reply_markup=get_stats_menu()
            )
    
    # ========== مدیریت پروکسی ==========
    elif data == "proxy":
        await query.edit_message_text(
            "🌍 **مدیریت پروکسی شیشه‌ای:**\n\n"
            f"📋 تعداد پروکسی‌ها: **{len(PROXY_LIST)}** عدد\n"
            f"🔄 چرخش خودکار: **{'✅ فعال' if settings_manager.get('auto_rotate') else '❌ غیرفعال'}**",
            reply_markup=get_proxy_menu(),
            parse_mode='Markdown'
        )
    
    elif data == "proxy_auto":
        current = settings_manager.get('auto_rotate')
        settings_manager.set('auto_rotate', not current)
        await query.edit_message_text(
            f"🔄 چرخش خودکار: **{'✅ فعال' if settings_manager.get('auto_rotate') else '❌ غیرفعال'}**",
            reply_markup=get_proxy_menu(),
            parse_mode='Markdown'
        )
    
    elif data == "proxy_add":
        await query.edit_message_text(
            "🌐 **لطفاً پروکسی جدید را به فرمت زیر وارد کنید:**\n\n"
            "`http://ip:port`\n"
            "یا\n"
            "`socks5://ip:port`\n\n"
            "مثال: `http://192.168.1.1:8080`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 لغو", callback_data="proxy")]
            ]),
            parse_mode='Markdown'
        )
        context.user_data['state'] = WAITING_FOR_PROXY
    
    elif data == "proxy_list":
        if not PROXY_LIST:
            await query.edit_message_text(
                "📋 **لیست پروکسی‌ها خالی است!**",
                reply_markup=get_proxy_menu()
            )
            return
        
        proxy_text = "📋 **۵ پروکسی آخر:**\n\n"
        for i, proxy in enumerate(PROXY_LIST[-5:], 1):
            proxy_text += f"{i}. `{proxy}`\n"
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="proxy")]
        ]
        await query.edit_message_text(
            proxy_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "proxy_clear":
        # تأیید دوم
        keyboard = [
            [InlineKeyboardButton("✅ بله، پاک کن", callback_data="proxy_clear_confirm")],
            [InlineKeyboardButton("❌ لغو", callback_data="proxy")],
        ]
        await query.edit_message_text(
            "⚠️ **آیا از پاک کردن همه پروکسی‌ها مطمئن هستید؟**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "proxy_clear_confirm":
        PROXY_LIST.clear()
        await query.edit_message_text(
            "🗑 **همه پروکسی‌ها پاک شدند!**",
            reply_markup=get_proxy_menu()
        )
    
    # ========== مدیریت کاربران (فقط ادمین) ==========
    elif data == "users":
        if user_id not in MASTER_ADMINS:
            await query.edit_message_text(
                "⛔ فقط ادمین اصلی دسترسی دارد!",
                reply_markup=get_glass_menu()
            )
            return
        await query.edit_message_text(
            "👥 **مدیریت کاربران:**\n\n"
            f"👤 تعداد کاربران مجاز: **{len(user_manager.users)}** نفر",
            reply_markup=get_users_menu(),
            parse_mode='Markdown'
        )
    
    elif data == "user_add":
        if user_id not in MASTER_ADMINS:
            await query.edit_message_text("⛔ دسترسی غیرمجاز!", reply_markup=get_glass_menu())
            return
        await query.edit_message_text(
            "➕ **آیدی عددی کاربر جدید را وارد کنید:**\n\n"
            "مثال: `123456789`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 لغو", callback_data="users")]
            ]),
            parse_mode='Markdown'
        )
        context.user_data['state'] = WAITING_FOR_USER
        context.user_data['user_action'] = 'add'
    
    elif data == "user_remove":
        if user_id not in MASTER_ADMINS:
            await query.edit_message_text("⛔ دسترسی غیرمجاز!", reply_markup=get_glass_menu())
            return
        
        keyboard = []
        for uid in user_manager.users:
            if uid not in MASTER_ADMINS:
                keyboard.append([
                    InlineKeyboardButton(f"❌ {uid}", callback_data=f"remove_{uid}")
                ])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="users")])
        
        if len(keyboard) == 1:
            await query.edit_message_text(
                "👥 **هیچ کاربر غیرادمینی وجود ندارد!**",
                reply_markup=get_users_menu()
            )
            return
        
        await query.edit_message_text(
            "👥 **لیست کاربران (برای حذف کلیک کنید):**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("remove_"):
        if user_id not in MASTER_ADMINS:
            await query.edit_message_text("⛔ دسترسی غیرمجاز!", reply_markup=get_glass_menu())
            return
        
        remove_id = int(data.split("_")[1])
        if user_manager.remove_user(remove_id):
            await query.edit_message_text(
                f"✅ کاربر {remove_id} با موفقیت حذف شد!",
                reply_markup=get_users_menu()
            )
        else:
            await query.edit_message_text(
                f"❌ کاربر {remove_id} یافت نشد یا ادمین است!",
                reply_markup=get_users_menu()
            )
    
    elif data == "user_list":
        if user_id not in MASTER_ADMINS:
            await query.edit_message_text("⛔ دسترسی غیرمجاز!", reply_markup=get_glass_menu())
            return
        
        user_text = "👥 **لیست کاربران مجاز:**\n\n"
        for uid in user_manager.users:
            user_text += f"🔹 `{uid}` {'⭐ (ادمین)' if uid in MASTER_ADMINS else ''}\n"
        
        await query.edit_message_text(
            user_text,
            reply_markup=get_users_menu(),
            parse_mode='Markdown'
        )
    
    # ========== تنظیمات ==========
    elif data == "settings":
        await query.edit_message_text(
            "⚙️ **تنظیمات شیشه‌ای:**\n\n"
            f"⏱ سرعت: **{settings_manager.get('speed')}** ویو/ثانیه\n"
            f"🛡 تاخیر: **{settings_manager.get('delay')}** ms\n"
            f"🌍 هدر تصادفی: **{'✅' if settings_manager.get('random_header') else '❌'}**\n"
            f"🔄 چرخش خودکار: **{'✅' if settings_manager.get('auto_rotate') else '❌'}**",
            reply_markup=get_settings_menu(),
            parse_mode='Markdown'
        )
    
    elif data == "set_speed":
        keyboard = [
            [InlineKeyboardButton("۵۰۰/ثانیه", callback_data="speed_500")],
            [InlineKeyboardButton("۱۰۰۰/ثانیه", callback_data="speed_1000")],
            [InlineKeyboardButton("۲۰۰۰/ثانیه", callback_data="speed_2000")],
            [InlineKeyboardButton("۵۰۰۰/ثانیه", callback_data="speed_5000")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="settings")],
        ]
        await query.edit_message_text(
            "⏱ **سرعت ویو را انتخاب کنید:**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("speed_"):
        speed = int(data.split("_")[1])
        settings_manager.set('speed', speed)
        await query.edit_message_text(
            f"✅ سرعت به **{speed}** ویو/ثانیه تغییر کرد!",
            reply_markup=get_settings_menu()
        )
    
    elif data == "set_delay":
        keyboard = [
            [InlineKeyboardButton("۰ ms", callback_data="delay_0")],
            [InlineKeyboardButton("۵ ms", callback_data="delay_5")],
            [InlineKeyboardButton("۱۰ ms", callback_data="delay_10")],
            [InlineKeyboardButton("۵۰ ms", callback_data="delay_50")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="settings")],
        ]
        await query.edit_message_text(
            "🛡 **تاخیر بین ویوها را انتخاب کنید:**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("delay_"):
        delay = int(data.split("_")[1])
        settings_manager.set('delay', delay)
        await query.edit_message_text(
            f"✅ تاخیر به **{delay}** میلی‌ثانیه تغییر کرد!",
            reply_markup=get_settings_menu()
        )
    
    elif data == "set_header":
        current = settings_manager.get('random_header')
        settings_manager.set('random_header', not current)
        await query.edit_message_text(
            f"🌍 هدر تصادفی: **{'✅ فعال' if settings_manager.get('random_header') else '❌ غیرفعال'}**",
            reply_markup=get_settings_menu(),
            parse_mode='Markdown'
        )
    
    elif data == "save_settings":
        settings_manager.save()
        await query.edit_message_text(
            "💾 **تنظیمات با موفقیت ذخیره شد!**",
            reply_markup=get_settings_menu()
        )

# ==================== هندلر دریافت متن ====================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت متن از کاربر (لینک، پروکسی، آیدی کاربر)"""
    user_id = update.effective_user.id
    if not user_manager.is_allowed(user_id):
        await update.message.reply_text("⛔ شما دسترسی ندارید!")
        return
    
    text = update.message.text
    state = context.user_data.get('state')
    
    # ===== دریافت لینک پست =====
    if state == WAITING_FOR_LINK:
        if not text.startswith(('http://', 'https://')):
            await update.message.reply_text(
                "❌ لطفاً یک لینک معتبر ارسال کنید!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="menu")]
                ])
            )
            return
        
        count = context.user_data.get('target_count', 100)
        
        # ارسال پیام شروع
        status_msg = await update.message.reply_text(
            f"🌀 در حال ارسال **{count}** ویو به:\n`{text}`",
            parse_mode='Markdown'
        )
        
        # اجرای ویوها
        try:
            success = await execute_views(text, count, context)
            failed = count - success
            
            result_text = (
                f"✅ **{success}** ویو با موفقیت ارسال شد!\n"
                f"❌ **{failed}** ویو ناموفق\n"
                f"⚡ سرعت: {settings_manager.get('speed')} ویو/ثانیه"
            )
            
            await status_msg.edit_text(
                result_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="menu")]
                ]),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await status_msg.edit_text(
                f"❌ خطا در اجرای عملیات:\n`{str(e)}`",
                parse_mode='Markdown'
            )
        
        # پاک کردن وضعیت
        context.user_data.clear()
    
    # ===== دریافت پروکسی جدید =====
    elif state == WAITING_FOR_PROXY:
        if '://' in text and ':' in text.split('://')[1]:
            PROXY_LIST.append(text)
            await update.message.reply_text(
                f"✅ پروکسی `{text}` با موفقیت اضافه شد!\n"
                f"📋 تعداد کل پروکسی‌ها: **{len(PROXY_LIST)}** عدد",
                reply_markup=get_proxy_menu(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ فرمت پروکسی نامعتبر!\n"
                "لطفاً به فرمت `http://ip:port` وارد کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="proxy")]
                ]),
                parse_mode='Markdown'
            )
        context.user_data.clear()
    
    # ===== دریافت آیدی کاربر جدید =====
    elif state == WAITING_FOR_USER:
        if user_id not in MASTER_ADMINS:
            await update.message.reply_text("⛔ دسترسی غیرمجاز!")
            return
        
        try:
            new_user_id = int(text)
            if user_manager.add_user(new_user_id):
                await update.message.reply_text(
                    f"✅ کاربر `{new_user_id}` با موفقیت اضافه شد!",
                    reply_markup=get_users_menu(),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"⚠️ کاربر `{new_user_id}` از قبل وجود دارد!",
                    reply_markup=get_users_menu(),
                    parse_mode='Markdown'
                )
        except ValueError:
            await update.message.reply_text(
                "❌ آیدی باید عددی باشد!",
                reply_markup=get_users_menu()
            )
        context.user_data.clear()

# ==================== اجرای اصلی ====================

def main():
    """اجرای ربات با وب‌هوک برای Render"""
    # تنظیم لاگ
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # ساخت اپلیکیشن
    application = Application.builder().token(BOT_TOKEN).build()
    
    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    # اجرا با وب‌هوک (برای Render)
    application.run_webhook(
        listen="0.0.0.0",
        port=WEBHOOK_PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
