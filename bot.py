# ============================================
# ربات ویو زن شیشه‌ای - نسخه نهایی با پشتیبانی از پروکسی MTProto
# کاملاً سازگار با پایتون 3.14 و Render
# ============================================

import asyncio
import aiohttp
import random
import json
import os
import logging
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ContextTypes

# ==================== تنظیمات اولیه ====================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MASTER_ADMINS = [8540004957, 601668306]  # آیدی خود را جایگزین کنید

# ==================== پروکسی‌های MTProto ====================

MTProto_PROXIES = [
    {
        'server': '116.203.140.198',
        'port': 8443,
        'secret': 'dd104462821249bd7ac519130220c25d09',
        'type': 'mtproto'
    },
    {
        'server': 'rain.golgoli2.co.uk',
        'port': 2096,
        'secret': 'ee1603010200010001fc030386e24c3add7777772e7961686f6f2e636f6d',
        'type': 'mtproto'
    }
]

PROXY_LIST = [
    "http://116.203.140.198:8443",
    "http://rain.golgoli2.co.uk:2096",
]

DEFAULT_SETTINGS = {
    'speed': 1000,
    'delay': 0,
    'random_header': True,
    'auto_rotate': True,
    'use_mtproto': False,
}

# ==================== کلاس‌های مدیریت ====================

class UserManager:
    def __init__(self, file_path: str = 'users.json'):
        self.file_path = file_path
        self.users: List[int] = []
        self.load()
    
    def load(self) -> None:
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                file_users = json.load(f)
            self.users = list(set(file_users + MASTER_ADMINS))
            self.save()
        else:
            self.users = MASTER_ADMINS.copy()
            self.save()
    
    def save(self) -> None:
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=2)
    
    def add_user(self, user_id: int) -> bool:
        if user_id not in self.users:
            self.users.append(user_id)
            self.save()
            return True
        return False
    
    def remove_user(self, user_id: int) -> bool:
        if user_id in self.users and user_id not in MASTER_ADMINS:
            self.users.remove(user_id)
            self.save()
            return True
        return False
    
    def is_allowed(self, user_id: int) -> bool:
        return user_id in self.users

class StatsManager:
    def __init__(self, file_path: str = 'stats.json'):
        self.file_path = file_path
        self.data: Dict[str, int] = {'today': 0, 'week': 0, 'month': 0, 'total': 0, 'failed': 0}
        self.load()
    
    def load(self) -> None:
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
    
    def save(self) -> None:
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2)
    
    def add_success(self, count: int) -> None:
        self.data['today'] += count
        self.data['week'] += count
        self.data['month'] += count
        self.data['total'] += count
        self.save()
    
    def add_failed(self, count: int = 1) -> None:
        self.data['failed'] += count
        self.save()

class SettingsManager:
    def __init__(self, file_path: str = 'settings.json'):
        self.file_path = file_path
        self.settings: Dict[str, Any] = DEFAULT_SETTINGS.copy()
        self.load()
    
    def load(self) -> None:
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
    
    def save(self) -> None:
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2)
    
    def get(self, key: str) -> Any:
        return self.settings.get(key, DEFAULT_SETTINGS.get(key))
    
    def set(self, key: str, value: Any) -> None:
        self.settings[key] = value
        self.save()

# ==================== نمونه‌سازی ====================

user_manager = UserManager()
stats_manager = StatsManager()
settings_manager = SettingsManager()

# ==================== توابع کیبورد ====================

def get_glass_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("💎 ویو تصادفی", callback_data="random_view")],
        [InlineKeyboardButton("🎯 ویو دلخواه", callback_data="custom_view")],
        [InlineKeyboardButton("📊 آمار ویوها", callback_data="stats")],
        [InlineKeyboardButton("🔄 تغییر پروکسی", callback_data="proxy")],
        [InlineKeyboardButton("👥 مدیریت کاربران", callback_data="users")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_random_view_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🎲 ۱۰۰ ویو", callback_data="rand_100")],
        [InlineKeyboardButton("🎲 ۵۰۰ ویو", callback_data="rand_500")],
        [InlineKeyboardButton("🎲 ۱۰۰۰ ویو", callback_data="rand_1000")],
        [InlineKeyboardButton("🎲 ۵۰۰۰ ویو", callback_data="rand_5000")],
        [InlineKeyboardButton("🎲 ۱۰۰۰۰ ویو", callback_data="rand_10000")],
        [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_custom_number_keyboard() -> InlineKeyboardMarkup:
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

def get_stats_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📅 امروز", callback_data="stats_today")],
        [InlineKeyboardButton("📆 این هفته", callback_data="stats_week")],
        [InlineKeyboardButton("📈 این ماه", callback_data="stats_month")],
        [InlineKeyboardButton("📊 کل ویوها", callback_data="stats_total")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_proxy_menu() -> InlineKeyboardMarkup:
    auto_status = "✅ فعال" if settings_manager.get('auto_rotate') else "❌ غیرفعال"
    mtproto_status = "✅ فعال" if settings_manager.get('use_mtproto') else "❌ غیرفعال"
    keyboard = [
        [InlineKeyboardButton(f"🔄 چرخش خودکار ({auto_status})", callback_data="proxy_auto")],
        [InlineKeyboardButton(f"🔮 پروکسی MTProto ({mtproto_status})", callback_data="proxy_mtproto")],
        [InlineKeyboardButton("🌐 افزودن پروکسی", callback_data="proxy_add")],
        [InlineKeyboardButton("📋 لیست پروکسی‌ها", callback_data="proxy_list")],
        [InlineKeyboardButton("🗑 پاک کردن همه", callback_data="proxy_clear")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_users_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("➕ افزودن کاربر", callback_data="user_add")],
        [InlineKeyboardButton("➖ حذف کاربر", callback_data="user_remove")],
        [InlineKeyboardButton("👥 لیست کاربران", callback_data="user_list")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("⏱ سرعت ویو", callback_data="set_speed")],
        [InlineKeyboardButton("🛡 تاخیر بین ویوها", callback_data="set_delay")],
        [InlineKeyboardButton("🌍 تغییر هدر", callback_data="set_header")],
        [InlineKeyboardButton("💾 ذخیره تنظیمات", callback_data="save_settings")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== توابع اصلی ویو ====================

async def send_view_async(url: str, proxy: str, headers: dict) -> bool:
    try:
        timeout = aiohttp.ClientTimeout(total=3)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, proxy=proxy, headers=headers, ssl=False) as resp:
                return resp.status in [200, 201, 202, 204, 301, 302]
    except Exception as e:
        logging.error(f"ویو ناموفق: {e}")
        return False

async def send_view_mtproto(url: str, proxy: dict, headers: dict) -> bool:
    try:
        http_proxy = f"http://{proxy['server']}:{proxy['port']}"
        timeout = aiohttp.ClientTimeout(total=3)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, proxy=http_proxy, headers=headers, ssl=False) as resp:
                return resp.status in [200, 201, 202, 204, 301, 302]
    except Exception as e:
        logging.error(f"ویو با MTProto ناموفق: {e}")
        return False

async def execute_views(post_url: str, count: int, context: ContextTypes.DEFAULT_TYPE) -> int:
    success_count = 0
    speed = settings_manager.get('speed')
    delay = settings_manager.get('delay')
    use_mtproto = settings_manager.get('use_mtproto')
    
    if use_mtproto and MTProto_PROXIES:
        available_proxies = MTProto_PROXIES.copy()
        proxy_type = 'mtproto'
    else:
        available_proxies = PROXY_LIST.copy() if PROXY_LIST else [None]
        proxy_type = 'http'
    
    batch_size = speed
    total_batches = (count + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        batch_count = min(batch_size, count - (batch_num * batch_size))
        tasks = []
        
        for _ in range(batch_count):
            if available_proxies and settings_manager.get('auto_rotate'):
                proxy = random.choice(available_proxies)
            else:
                proxy = available_proxies[0] if available_proxies else None
            
            headers = {
                'User-Agent': random.choice([
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
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
            
            if proxy_type == 'mtproto' and proxy:
                tasks.append(send_view_mtproto(post_url, proxy, headers))
            else:
                tasks.append(send_view_async(post_url, proxy, headers))
        
        results = await asyncio.gather(*tasks)
        success_count += sum(results)
        
        if delay > 0 and batch_num < total_batches - 1:
            await asyncio.sleep(delay / 1000)
    
    if success_count > 0:
        stats_manager.add_success(success_count)
    failed = count - success_count
    if failed > 0:
        stats_manager.add_failed(failed)
    
    return success_count

# ==================== هندلرهای ربات ====================

WAITING_FOR_LINK, WAITING_FOR_PROXY, WAITING_FOR_USER = range(3)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not user_manager.is_allowed(user_id):
        await update.message.reply_text("⛔ شما دسترسی به این ربات ندارید!")
        return
    
    welcome_text = (
        "✨💎 **ربات ویو زن شیشه‌ای** 💎✨\n\n"
        f"🌀 **سرعت:** {settings_manager.get('speed')} ویو در ثانیه\n"
        f"🔮 **پروکسی چرخشی:** {'✅ فعال' if settings_manager.get('auto_rotate') else '❌ غیرفعال'}\n"
        f"🔐 **پروکسی MTProto:** {'✅ فعال' if settings_manager.get('use_mtproto') else '❌ غیرفعال'}\n"
        "📡 **وضعیت:** 🟢 آنلاین\n\n"
        "از دکمه‌های زیر برای شروع استفاده کنید:"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_glass_menu(), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not user_manager.is_allowed(user_id):
        await query.edit_message_text("⛔ شما دسترسی ندارید!", reply_markup=get_glass_menu())
        return
    
    data = query.data
    
    if data == "menu":
        await query.edit_message_text("✨💎 **ربات ویو زن شیشه‌ای** 💎✨\n\nمنوی اصلی:", reply_markup=get_glass_menu(), parse_mode='Markdown')
        context.user_data.clear()
    
    elif data == "random_view":
        await query.edit_message_text("🎲 **تعداد ویو تصادفی را انتخاب کنید:**", reply_markup=get_random_view_menu(), parse_mode='Markdown')
    
    elif data.startswith("rand_"):
        count = int(data.split("_")[1])
        actual_count = int(count * random.uniform(0.8, 1.2))
        context.user_data['target_count'] = actual_count
        context.user_data['state'] = WAITING_FOR_LINK
        
        await query.edit_message_text(
            f"✅ **{actual_count} ویو** تنظیم شد (محدوده: {count} ± ۲۰%)\n\n📎 لینک پست را ارسال کنید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="menu")]]),
            parse_mode='Markdown'
        )
    
    elif data == "custom_view":
        context.user_data['number_input'] = ""
        await query.edit_message_text("🔢 **تعداد ویو را با دکمه‌ها وارد کنید:**", reply_markup=get_custom_number_keyboard(), parse_mode='Markdown')
    
    elif data == "backspace":
        if 'number_input' in context.user_data:
            context.user_data['number_input'] = context.user_data['number_input'][:-1]
        await query.edit_message_text(f"🔢 تعداد: `{context.user_data.get('number_input', '')}`", reply_markup=get_custom_number_keyboard(), parse_mode='Markdown')
    
    elif data.startswith("num_"):
        digit = data.split("_")[1]
        if 'number_input' not in context.user_data:
            context.user_data['number_input'] = ""
        context.user_data['number_input'] += digit
        await query.edit_message_text(f"🔢 تعداد: `{context.user_data['number_input']}`", reply_markup=get_custom_number_keyboard(), parse_mode='Markdown')
    
    elif data == "confirm_number":
        if 'number_input' in context.user_data and context.user_data['number_input']:
            count = int(context.user_data['number_input'])
            if count < 1 or count > 1000000:
                await query.edit_message_text("❌ تعداد باید بین ۱ تا ۱,۰۰۰,۰۰۰ باشد!", reply_markup=get_custom_number_keyboard())
                return
            
            context.user_data['target_count'] = count
            context.user_data['state'] = WAITING_FOR_LINK
            
            await query.edit_message_text(
                f"✅ **{count} ویو** تنظیم شد.\n\n📎 لینک پست را ارسال کنید:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="menu")]]),
                parse_mode='Markdown'
            )
    
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
            await query.edit_message_text(f"📅 **آمار امروز:**\n✅ {stats_manager.data['today']} ویو موفق", reply_markup=get_stats_menu())
        elif period == "week":
            await query.edit_message_text(f"📆 **آمار این هفته:**\n✅ {stats_manager.data['week']} ویو موفق", reply_markup=get_stats_menu())
        elif period == "month":
            await query.edit_message_text(f"📈 **آمار این ماه:**\n✅ {stats_manager.data['month']} ویو موفق", reply_markup=get_stats_menu())
        elif period == "total":
            await query.edit_message_text(f"📊 **آمار کل:**\n✅ {stats_manager.data['total']} ویو موفق\n❌ {stats_manager.data['failed']} ویو ناموفق", reply_markup=get_stats_menu())
    
    elif data == "proxy":
        await query.edit_message_text(
            "🌍 **مدیریت پروکسی شیشه‌ای:**\n\n"
            f"📋 تعداد پروکسی‌های HTTP: **{len(PROXY_LIST)}** عدد\n"
            f"🔮 تعداد پروکسی‌های MTProto: **{len(MTProto_PROXIES)}** عدد\n"
            f"🔄 چرخش خودکار: **{'✅ فعال' if settings_manager.get('auto_rotate') else '❌ غیرفعال'}**\n"
            f"🔐 استفاده از MTProto: **{'✅ فعال' if settings_manager.get('use_mtproto') else '❌ غیرفعال'}**",
            reply_markup=get_proxy_menu(),
            parse_mode='Markdown'
        )
    
    elif data == "proxy_auto":
        current = settings_manager.get('auto_rotate')
        settings_manager.set('auto_rotate', not current)
        await query.edit_message_text(f"🔄 چرخش خودکار: **{'✅ فعال' if settings_manager.get('auto_rotate') else '❌ غیرفعال'}**", reply_markup=get_proxy_menu(), parse_mode='Markdown')
    
    elif data == "proxy_mtproto":
        current = settings_manager.get('use_mtproto')
        settings_manager.set('use_mtproto', not current)
        await query.edit_message_text(f"🔐 استفاده از MTProto: **{'✅ فعال' if settings_manager.get('use_mtproto') else '❌ غیرفعال'}**", reply_markup=get_proxy_menu(), parse_mode='Markdown')
    
    elif data == "proxy_add":
        await query.edit_message_text(
            "🌐 **لطفاً پروکسی جدید را به فرمت زیر وارد کنید:**\n\n"
            "**HTTP:** `http://ip:port`\n"
            "**MTProto:** `tg://proxy?server=ip&port=port&secret=secret`\n\n"
            "مثال HTTP: `http://192.168.1.1:8080`\n"
            "مثال MTProto: `tg://proxy?server=116.203.140.198&port=8443&secret=dd104462...`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لغو", callback_data="proxy")]]),
            parse_mode='Markdown'
        )
        context.user_data['state'] = WAITING_FOR_PROXY
    
    elif data == "proxy_list":
        proxy_text = "📋 **لیست پروکسی‌ها:**\n\n"
        proxy_text += "**HTTP Proxy:**\n"
        if PROXY_LIST:
            for i, proxy in enumerate(PROXY_LIST[-5:], 1):
                proxy_text += f"{i}. `{proxy}`\n"
        else:
            proxy_text += "❌ هیچ پروکسی HTTP موجود نیست\n"
        
        proxy_text += "\n**MTProto Proxy:**\n"
        if MTProto_PROXIES:
            for i, proxy in enumerate(MTProto_PROXIES[-5:], 1):
                proxy_text += f"{i}. `{proxy['server']}:{proxy['port']}`\n"
        else:
            proxy_text += "❌ هیچ پروکسی MTProto موجود نیست\n"
        
        await query.edit_message_text(
            proxy_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="proxy")]]),
            parse_mode='Markdown'
        )
    
    elif data == "proxy_clear":
        keyboard = [[InlineKeyboardButton("✅ بله، پاک کن", callback_data="proxy_clear_confirm")], [InlineKeyboardButton("❌ لغو", callback_data="proxy")]]
        await query.edit_message_text("⚠️ **آیا از پاک کردن همه پروکسی‌ها مطمئن هستید؟**", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "proxy_clear_confirm":
        PROXY_LIST.clear()
        MTProto_PROXIES.clear()
        await query.edit_message_text("🗑 **همه پروکسی‌ها پاک شدند!**", reply_markup=get_proxy_menu())
    
    elif data == "users":
        if user_id not in MASTER_ADMINS:
            await query.edit_message_text("⛔ فقط ادمین اصلی دسترسی دارد!", reply_markup=get_glass_menu())
            return
        await query.edit_message_text(f"👥 **مدیریت کاربران:**\n\n👤 تعداد کاربران مجاز: **{len(user_manager.users)}** نفر", reply_markup=get_users_menu(), parse_mode='Markdown')
    
    elif data == "user_add":
        if user_id not in MASTER_ADMINS:
            await query.edit_message_text("⛔ دسترسی غیرمجاز!", reply_markup=get_glass_menu())
            return
        await query.edit_message_text(
            "➕ **آیدی عددی کاربر جدید را وارد کنید:**\n\nمثال: `123456789`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لغو", callback_data="users")]]),
            parse_mode='Markdown'
        )
        context.user_data['state'] = WAITING_FOR_USER
    
    elif data == "user_remove":
        if user_id not in MASTER_ADMINS:
            await query.edit_message_text("⛔ دسترسی غیرمجاز!", reply_markup=get_glass_menu())
            return
        
        keyboard = [[InlineKeyboardButton(f"❌ {uid}", callback_data=f"remove_{uid}")] for uid in user_manager.users if uid not in MASTER_ADMINS]
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="users")])
        
        if len(keyboard) == 1:
            await query.edit_message_text("👥 **هیچ کاربر غیرادمینی وجود ندارد!**", reply_markup=get_users_menu())
            return
        
        await query.edit_message_text("👥 **لیست کاربران (برای حذف کلیک کنید):**", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("remove_"):
        if user_id not in MASTER_ADMINS:
            await query.edit_message_text("⛔ دسترسی غیرمجاز!", reply_markup=get_glass_menu())
            return
        
        remove_id = int(data.split("_")[1])
        if user_manager.remove_user(remove_id):
            await query.edit_message_text(f"✅ کاربر {remove_id} با موفقیت حذف شد!", reply_markup=get_users_menu())
        else:
            await query.edit_message_text(f"❌ کاربر {remove_id} یافت نشد یا ادمین است!", reply_markup=get_users_menu())
    
    elif data == "user_list":
        if user_id not in MASTER_ADMINS:
            await query.edit_message_text("⛔ دسترسی غیرمجاز!", reply_markup=get_glass_menu())
            return
        
        user_text = "👥 **لیست کاربران مجاز:**\n\n" + "\n".join([f"🔹 `{uid}` {'⭐ (ادمین)' if uid in MASTER_ADMINS else ''}" for uid in user_manager.users])
        await query.edit_message_text(user_text, reply_markup=get_users_menu(), parse_mode='Markdown')
    
    elif data == "settings":
        await query.edit_message_text(
            "⚙️ **تنظیمات شیشه‌ای:**\n\n"
            f"⏱ سرعت: **{settings_manager.get('speed')}** ویو/ثانیه\n"
            f"🛡 تاخیر: **{settings_manager.get('delay')}** ms\n"
            f"🌍 هدر تصادفی: **{'✅' if settings_manager.get('random_header') else '❌'}**\n"
            f"🔄 چرخش خودکار: **{'✅' if settings_manager.get('auto_rotate') else '❌'}**\n"
            f"🔐 استفاده از MTProto: **{'✅' if settings_manager.get('use_mtproto') else '❌'}**",
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
        await query.edit_message_text("⏱ **سرعت ویو را انتخاب کنید:**", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("speed_"):
        speed = int(data.split("_")[1])
        settings_manager.set('speed', speed)
        await query.edit_message_text(f"✅ سرعت به **{speed}** ویو/ثانیه تغییر کرد!", reply_markup=get_settings_menu())
    
    elif data == "set_delay":
        keyboard = [
            [InlineKeyboardButton("۰ ms", callback_data="delay_0")],
            [InlineKeyboardButton("۵ ms", callback_data="delay_5")],
            [InlineKeyboardButton("۱۰ ms", callback_data="delay_10")],
            [InlineKeyboardButton("۵۰ ms", callback_data="delay_50")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="settings")],
        ]
        await query.edit_message_text("🛡 **تاخیر بین ویوها را انتخاب کنید:**", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("delay_"):
        delay = int(data.split("_")[1])
        settings_manager.set('delay', delay)
        await query.edit_message_text(f"✅ تاخیر به **{delay}** میلی‌ثانیه تغییر کرد!", reply_markup=get_settings_menu())
    
    elif data == "set_header":
        current = settings_manager.get('random_header')
        settings_manager.set('random_header', not current)
        await query.edit_message_text(f"🌍 هدر تصادفی: **{'✅ فعال' if settings_manager.get('random_header') else '❌ غیرفعال'}**", reply_markup=get_settings_menu(), parse_mode='Markdown')
    
    elif data == "save_settings":
        settings_manager.save()
        await query.edit_message_text("💾 **تنظیمات با موفقیت ذخیره شد!**", reply_markup=get_settings_menu())

# ==================== هندلر دریافت متن ====================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not user_manager.is_allowed(user_id):
        await update.message.reply_text("⛔ شما دسترسی ندارید!")
        return
    
    text = update.message.text
    state = context.user_data.get('state')
    
    if state == WAITING_FOR_LINK:
        if not text.startswith(('http://', 'https://')):
            await update.message.reply_text("❌ لطفاً یک لینک معتبر ارسال کنید!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منو", callback_data="menu")]]))
            return
        
        count = context.user_data.get('target_count', 100)
        status_msg = await update.message.reply_text(f"🌀 در حال ارسال **{count}** ویو به:\n`{text}`", parse_mode='Markdown')
        
        try:
            success = await execute_views(text, count, context)
            failed = count - success
            
            result_text = f"✅ **{success}** ویو با موفقیت ارسال شد!\n❌ **{failed}** ویو ناموفق\n⚡ سرعت: {settings_manager.get('speed')} ویو/ثانیه"
            await status_msg.edit_text(result_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منو", callback_data="menu")]]), parse_mode='Markdown')
        except Exception as e:
            await status_msg.edit_text(f"❌ خطا در اجرای عملیات:\n`{str(e)}`", parse_mode='Markdown')
        
        context.user_data.clear()
    
    elif state == WAITING_FOR_PROXY:
        if text.startswith('tg://proxy?'):
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(text).query)
            if 'server' in parsed and 'port' in parsed and 'secret' in parsed:
                new_proxy = {
                    'server': parsed['server'][0],
                    'port': int(parsed['port'][0]),
                    'secret': parsed['secret'][0],
                    'type': 'mtproto'
                }
                MTProto_PROXIES.append(new_proxy)
                await update.message.reply_text(
                    f"✅ پروکسی MTProto با موفقیت اضافه شد!\n"
                    f"🌐 سرور: `{new_proxy['server']}:{new_proxy['port']}`\n"
                    f"📋 تعداد کل پروکسی‌های MTProto: **{len(MTProto_PROXIES)}** عدد",
                    reply_markup=get_proxy_menu(),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ فرمت پروکسی MTProto نامعتبر!\n"
                    "لطفاً به فرمت `tg://proxy?server=ip&port=port&secret=secret` وارد کنید.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="proxy")]]),
                    parse_mode='Markdown'
                )
        elif '://' in text and ':' in text.split('://')[1]:
            PROXY_LIST.append(text)
            await update.message.reply_text(
                f"✅ پروکسی HTTP `{text}` با موفقیت اضافه شد!\n"
                f"📋 تعداد کل پروکسی‌های HTTP: **{len(PROXY_LIST)}** عدد",
                reply_markup=get_proxy_menu(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ فرمت پروکسی نامعتبر!\n"
                "لطفاً به فرمت:\n"
                "- HTTP: `http://ip:port`\n"
                "- MTProto: `tg://proxy?server=ip&port=port&secret=secret`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="proxy")]]),
                parse_mode='Markdown'
            )
        context.user_data.clear()
    
    elif state == WAITING_FOR_USER:
        if user_id not in MASTER_ADMINS:
            await update.message.reply_text("⛔ دسترسی غیرمجاز!")
            return
        
        try:
            new_user_id = int(text)
            if user_manager.add_user(new_user_id):
                await update.message.reply_text(f"✅ کاربر `{new_user_id}` با موفقیت اضافه شد!", reply_markup=get_users_menu(), parse_mode='Markdown')
            else:
                await update.message.reply_text(f"⚠️ کاربر `{new_user_id}` از قبل وجود دارد!", reply_markup=get_users_menu(), parse_mode='Markdown')
        except ValueError:
            await update.message.reply_text("❌ آیدی باید عددی باشد!", reply_markup=get_users_menu())
        context.user_data.clear()

# ==================== تابع اصلی (اصلاح شده برای پایتون 3.14) ====================

async def main() -> None:
    """تابع اصلی غیرهمزمان برای راه‌اندازی ربات"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    # اجرای Polling به صورت غیرهمزمان
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    # نگه داشتن ربات در حالت اجرا
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        await application.stop()

if __name__ == "__main__":
    asyncio.run(main())
