# ============================================
# ربات ویو زن - نسخه نهایی با پشتیبانی از Proxy و Direct
# ============================================

import asyncio
import aiohttp
import random
import json
import os
import logging
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ContextTypes

# ==================== تنظیمات لاگ ====================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== تنظیمات اولیه ====================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MASTER_ADMINS = [8540004957, 601668306]

# ==================== لیست پروکسی‌ها ====================

# پروکسی‌های HTTP/SOCKS معتبر (برای چرخش)
PROXY_LIST = [
    "http://37.97.169.58:3128",
    "http://45.76.112.154:3128", 
    "http://50.174.7.158:80",
    "http://51.15.166.107:3128",
    "http://138.68.60.157:3128",
    "http://190.61.44.86:8080",
    "http://103.152.112.120:80",
    "http://103.216.49.210:8080",
    "http://103.250.166.132:8080",
    "http://103.172.108.210:80",
]

# پروکسی‌های MTProto (برای اتصال به تلگرام)
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

# ==================== تنظیمات پیش‌فرض ====================

DEFAULT_SETTINGS = {
    'speed': 5,           # تعداد درخواست همزمان (کم برای جلوگیری از بلاک)
    'delay': 200,         # تاخیر بین بچ‌ها (میلی‌ثانیه)
    'random_header': True,
    'auto_rotate': True,   # چرخش خودکار پروکسی
    'use_proxy': True,     # True = با پروکسی، False = بدون پروکسی
    'use_mtproto': False,  # استفاده از MTProto
    'max_retries': 2,      # تعداد تلاش مجدد
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

user_manager = UserManager()
stats_manager = StatsManager()
settings_manager = SettingsManager()

# ==================== توابع کیبورد ====================

def get_glass_menu() -> InlineKeyboardMarkup:
    proxy_status = "✅" if settings_manager.get('use_proxy') else "❌"
    keyboard = [
        [InlineKeyboardButton("💎 ویو تصادفی", callback_data="random_view")],
        [InlineKeyboardButton("🎯 ویو دلخواه", callback_data="custom_view")],
        [InlineKeyboardButton("📊 آمار ویوها", callback_data="stats")],
        [InlineKeyboardButton(f"🔄 پروکسی ({proxy_status})", callback_data="toggle_proxy")],
        [InlineKeyboardButton("👥 مدیریت کاربران", callback_data="users")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_random_view_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🎲 ۱۰ ویو", callback_data="rand_10")],
        [InlineKeyboardButton("🎲 ۵۰ ویو", callback_data="rand_50")],
        [InlineKeyboardButton("🎲 ۱۰۰ ویو", callback_data="rand_100")],
        [InlineKeyboardButton("🎲 ۵۰۰ ویو", callback_data="rand_500")],
        [InlineKeyboardButton("🎲 ۱۰۰۰ ویو", callback_data="rand_1000")],
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
    use_proxy = "✅ فعال" if settings_manager.get('use_proxy') else "❌ غیرفعال"
    auto_rotate = "✅ فعال" if settings_manager.get('auto_rotate') else "❌ غیرفعال"
    mtproto = "✅ فعال" if settings_manager.get('use_mtproto') else "❌ غیرفعال"
    
    keyboard = [
        [InlineKeyboardButton(f"🌐 استفاده از پروکسی ({use_proxy})", callback_data="toggle_proxy")],
        [InlineKeyboardButton(f"🔄 چرخش خودکار ({auto_rotate})", callback_data="proxy_auto")],
        [InlineKeyboardButton(f"🔮 MTProto ({mtproto})", callback_data="proxy_mtproto")],
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
        [InlineKeyboardButton("🔁 تعداد تلاش مجدد", callback_data="set_retry")],
        [InlineKeyboardButton("💾 ذخیره تنظیمات", callback_data="save_settings")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== توابع اصلی ویو ====================

async def send_view_with_proxy(url: str, proxy: str, headers: dict, session: aiohttp.ClientSession) -> bool:
    """ارسال ویو با پروکسی"""
    try:
        async with session.get(url, proxy=proxy, headers=headers, ssl=False, timeout=10) as resp:
            status = resp.status
            if status in [200, 201, 202, 203, 204, 301, 302, 307, 308]:
                logger.debug(f"✅ ویو موفق با پروکسی {proxy} - کد {status}")
                return True
            else:
                logger.debug(f"⚠️ پاسخ غیرمنتظره با پروکسی {proxy} - کد {status}")
                return False
    except asyncio.TimeoutError:
        logger.debug(f"⏰ تایم‌اوت با پروکسی {proxy}")
        return False
    except Exception as e:
        logger.debug(f"❌ خطا با پروکسی {proxy}: {e}")
        return False

async def send_view_direct(url: str, headers: dict, session: aiohttp.ClientSession) -> bool:
    """ارسال ویو بدون پروکسی (IP ثابت سرور)"""
    try:
        async with session.get(url, headers=headers, ssl=False, timeout=10) as resp:
            status = resp.status
            if status in [200, 201, 202, 203, 204, 301, 302, 307, 308]:
                logger.debug(f"✅ ویو موفق بدون پروکسی - کد {status}")
                return True
            else:
                logger.debug(f"⚠️ پاسخ غیرمنتظره بدون پروکسی - کد {status}")
                return False
    except asyncio.TimeoutError:
        logger.debug(f"⏰ تایم‌اوت بدون پروکسی")
        return False
    except Exception as e:
        logger.debug(f"❌ خطا بدون پروکسی: {e}")
        return False

async def execute_views(post_url: str, count: int, context: ContextTypes.DEFAULT_TYPE) -> int:
    """اجرای ویوها با تنظیمات انتخاب شده"""
    success_count = 0
    speed = settings_manager.get('speed')
    delay = settings_manager.get('delay')
    use_proxy = settings_manager.get('use_proxy')
    auto_rotate = settings_manager.get('auto_rotate')
    max_retries = settings_manager.get('max_retries', 2)
    
    logger.info(f"🚀 شروع ارسال {count} ویو به {post_url}")
    logger.info(f"📊 تنظیمات: speed={speed}, delay={delay}, use_proxy={use_proxy}, auto_rotate={auto_rotate}")
    
    # آماده‌سازی پروکسی‌ها
    available_proxies = PROXY_LIST.copy() if use_proxy else []
    
    if use_proxy and not available_proxies:
        logger.warning("⚠️ هیچ پروکسی موجود نیست! استفاده از حالت مستقیم...")
        use_proxy = False
    
    # استفاده از Session برای بهینه‌سازی
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=20)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        batch_size = speed
        total_batches = (count + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            batch_count = min(batch_size, count - (batch_num * batch_size))
            tasks = []
            
            for i in range(batch_count):
                # تولید هدر تصادفی
                headers = {
                    'User-Agent': random.choice([
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
                    ]),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9,fa;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                }
                
                if settings_manager.get('random_header'):
                    headers['Referer'] = random.choice([
                        'https://www.google.com/',
                        'https://www.bing.com/',
                        'https://www.yahoo.com/',
                        'https://www.instagram.com/',
                        'https://www.facebook.com/',
                        'https://twitter.com/',
                        'https://www.youtube.com/',
                    ])
                
                # انتخاب پروکسی (با چرخش)
                if use_proxy and available_proxies:
                    if auto_rotate:
                        proxy = random.choice(available_proxies)
                    else:
                        proxy = available_proxies[0] if available_proxies else None
                    
                    # ارسال با پروکسی
                    tasks.append(send_view_with_proxy(post_url, proxy, headers, session))
                else:
                    # ارسال مستقیم (بدون پروکسی)
                    tasks.append(send_view_direct(post_url, headers, session))
            
            # اجرای همزمان بچ
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # شمارش موفقیت‌ها
            for result in results:
                if isinstance(result, bool) and result:
                    success_count += 1
                elif isinstance(result, Exception):
                    logger.debug(f"❌ استثنا در بچ: {result}")
            
            batch_success = sum(1 for r in results if isinstance(r, bool) and r)
            logger.info(f"✅ بچ {batch_num+1}/{total_batches}: {batch_success}/{batch_count} موفق")
            
            # تاخیر بین بچ‌ها
            if delay > 0 and batch_num < total_batches - 1:
                await asyncio.sleep(delay / 1000)
    
    # به‌روزرسانی آمار
    if success_count > 0:
        stats_manager.add_success(success_count)
    failed = count - success_count
    if failed > 0:
        stats_manager.add_failed(failed)
    
    logger.info(f"🏁 نهایی: {success_count}/{count} ویو موفق")
    return success_count

# ==================== هندلرهای ربات ====================

WAITING_FOR_LINK, WAITING_FOR_PROXY, WAITING_FOR_USER = range(3)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not user_manager.is_allowed(user_id):
        await update.message.reply_text("⛔ شما دسترسی به این ربات ندارید!")
        return
    
    proxy_status = "✅ فعال" if settings_manager.get('use_proxy') else "❌ غیرفعال"
    mtproto_status = "✅ فعال" if settings_manager.get('use_mtproto') else "❌ غیرفعال"
    
    welcome_text = (
        "✨💎 **ربات ویو زن شیشه‌ای** 💎✨\n\n"
        f"🌀 **سرعت:** {settings_manager.get('speed')} ویو در ثانیه\n"
        f"🌐 **پروکسی:** {proxy_status}\n"
        f"🔄 **چرخش خودکار:** {'✅ فعال' if settings_manager.get('auto_rotate') else '❌ غیرفعال'}\n"
        f"🔮 **MTProto:** {mtproto_status}\n"
        f"📋 **تعداد پروکسی‌ها:** {len(PROXY_LIST)} عدد\n"
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
    
    # ====== ویو تصادفی ======
    elif data == "random_view":
        await query.edit_message_text("🎲 **تعداد ویو تصادفی را انتخاب کنید:**", reply_markup=get_random_view_menu(), parse_mode='Markdown')
    
    elif data.startswith("rand_"):
        count = int(data.split("_")[1])
        context.user_data['target_count'] = count
        context.user_data['state'] = WAITING_FOR_LINK
        
        await query.edit_message_text(
            f"✅ **{count} ویو** تنظیم شد.\n\n📎 لینک پست را ارسال کنید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="menu")]]),
            parse_mode='Markdown'
        )
    
    # ====== ویو دلخواه ======
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
            if count < 1 or count > 100000:
                await query.edit_message_text("❌ تعداد باید بین ۱ تا ۱۰۰,۰۰۰ باشد!", reply_markup=get_custom_number_keyboard())
                return
            
            context.user_data['target_count'] = count
            context.user_data['state'] = WAITING_FOR_LINK
            
            await query.edit_message_text(
                f"✅ **{count} ویو** تنظیم شد.\n\n📎 لینک پست را ارسال کنید:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="menu")]]),
                parse_mode='Markdown'
            )
    
    # ====== آمار ======
    elif data == "stats":
        await query.edit_message_text(
            "📊 **آمار ویوها:**\n\n"
            f"📅 امروز: **{stats_manager.data['today']}** ویو\n"
            f"📆 این هفته: **{stats_manager.data['week']}** ویو\n"
            f"📈 این ماه: **{stats_manager.data['month']}** ویو\n"
            f"📊 کل: **{stats_manager.data['total']}** ویو\n"
            f"❌ ناموفق: **{stats_manager.data['failed']}** ویو\n"
            f"⚡ سرعت: **{settings_manager.get('speed')}** ویو/ثانیه",
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
    
    # ====== مدیریت پروکسی ======
    elif data == "toggle_proxy":
        current = settings_manager.get('use_proxy')
        settings_manager.set('use_proxy', not current)
        status = "✅ فعال" if settings_manager.get('use_proxy') else "❌ غیرفعال"
        await query.edit_message_text(f"🌐 استفاده از پروکسی: **{status}**", reply_markup=get_proxy_menu(), parse_mode='Markdown')
    
    elif data == "proxy":
        await query.edit_message_text(
            "🌍 **مدیریت پروکسی:**\n\n"
            f"📋 تعداد پروکسی‌ها: **{len(PROXY_LIST)}** عدد\n"
            f"🌐 استفاده از پروکسی: **{'✅ فعال' if settings_manager.get('use_proxy') else '❌ غیرفعال'}**\n"
            f"🔄 چرخش خودکار: **{'✅ فعال' if settings_manager.get('auto_rotate') else '❌ غیرفعال'}**\n"
            f"🔮 MTProto: **{'✅ فعال' if settings_manager.get('use_mtproto') else '❌ غیرفعال'}**",
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
        await query.edit_message_text(f"🔮 استفاده از MTProto: **{'✅ فعال' if settings_manager.get('use_mtproto') else '❌ غیرفعال'}**", reply_markup=get_proxy_menu(), parse_mode='Markdown')
    
    elif data == "proxy_add":
        await query.edit_message_text(
            "🌐 **لطفاً پروکسی جدید را وارد کنید:**\n\n"
            "**فرمت HTTP:** `http://ip:port`\n"
            "**فرمت MTProto:** `tg://proxy?server=ip&port=port&secret=secret`\n\n"
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
            for i, proxy in enumerate(PROXY_LIST[:10], 1):
                proxy_text += f"{i}. `{proxy}`\n"
            if len(PROXY_LIST) > 10:
                proxy_text += f"... و {len(PROXY_LIST)-10} عدد دیگر\n"
        else:
            proxy_text += "❌ هیچ پروکسی HTTP موجود نیست\n"
        
        proxy_text += "\n**MTProto Proxy:**\n"
        if MTProto_PROXIES:
            for i, proxy in enumerate(MTProto_PROXIES[:5], 1):
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
    
    # ====== مدیریت کاربران ======
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
    
    # ====== تنظیمات ======
    elif data == "settings":
        await query.edit_message_text(
            "⚙️ **تنظیمات:**\n\n"
            f"⏱ سرعت: **{settings_manager.get('speed')}** ویو/ثانیه\n"
            f"🛡 تاخیر: **{settings_manager.get('delay')}** ms\n"
            f"🌍 هدر تصادفی: **{'✅' if settings_manager.get('random_header') else '❌'}**\n"
            f"🔄 چرخش خودکار: **{'✅' if settings_manager.get('auto_rotate') else '❌'}**\n"
            f"🌐 استفاده از پروکسی: **{'✅' if settings_manager.get('use_proxy') else '❌'}**\n"
            f"🔁 تلاش مجدد: **{settings_manager.get('max_retries')}** بار",
            reply_markup=get_settings_menu(),
            parse_mode='Markdown'
        )
    
    elif data == "set_speed":
        keyboard = [
            [InlineKeyboardButton("۱/ثانیه", callback_data="speed_1")],
            [InlineKeyboardButton("۵/ثانیه", callback_data="speed_5")],
            [InlineKeyboardButton("۱۰/ثانیه", callback_data="speed_10")],
            [InlineKeyboardButton("۵۰/ثانیه", callback_data="speed_50")],
            [InlineKeyboardButton("۱۰۰/ثانیه", callback_data="speed_100")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="settings")],
        ]
        await query.edit_message_text("⏱ **سرعت ویو را انتخاب کنید:**\n(تعداد درخواست همزمان)", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("speed_"):
        speed = int(data.split("_")[1])
        settings_manager.set('speed', speed)
        await query.edit_message_text(f"✅ سرعت به **{speed}** ویو/ثانیه تغییر کرد!", reply_markup=get_settings_menu())
    
    elif data == "set_delay":
        keyboard = [
            [InlineKeyboardButton("۰ ms", callback_data="delay_0")],
            [InlineKeyboardButton("۱۰۰ ms", callback_data="delay_100")],
            [InlineKeyboardButton("۵۰۰ ms", callback_data="delay_500")],
            [InlineKeyboardButton("۱۰۰۰ ms", callback_data="delay_1000")],
            [InlineKeyboardButton("۲۰۰۰ ms", callback_data="delay_2000")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="settings")],
        ]
        await query.edit_message_text("🛡 **تاخیر بین بچ‌ها را انتخاب کنید:**", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("delay_"):
        delay = int(data.split("_")[1])
        settings_manager.set('delay', delay)
        await query.edit_message_text(f"✅ تاخیر به **{delay}** میلی‌ثانیه تغییر کرد!", reply_markup=get_settings_menu())
    
    elif data == "set_header":
        current = settings_manager.get('random_header')
        settings_manager.set('random_header', not current)
        await query.edit_message_text(f"🌍 هدر تصادفی: **{'✅ فعال' if settings_manager.get('random_header') else '❌ غیرفعال'}**", reply_markup=get_settings_menu(), parse_mode='Markdown')
    
    elif data == "set_retry":
        keyboard = [
            [InlineKeyboardButton("۰ بار", callback_data="retry_0")],
            [InlineKeyboardButton("۱ بار", callback_data="retry_1")],
            [InlineKeyboardButton("۲ بار", callback_data="retry_2")],
            [InlineKeyboardButton("۳ بار", callback_data="retry_3")],
            [InlineKeyboardButton("۵ بار", callback_data="retry_5")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="settings")],
        ]
        await query.edit_message_text("🔁 **تعداد تلاش مجدد برای هر ویو:**", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("retry_"):
        retry = int(data.split("_")[1])
        settings_manager.set('max_retries', retry)
        await query.edit_message_text(f"✅ تعداد تلاش مجدد به **{retry}** بار تغییر کرد!", reply_markup=get_settings_menu())
    
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
        
        count = context.user_data.get('target_count', 10)
        status_msg = await update.message.reply_text(
            f"🌀 در حال ارسال **{count}** ویو به:\n`{text}`\n\n"
            f"🌐 حالت: {'با پروکسی' if settings_manager.get('use_proxy') else 'بدون پروکسی (IP ثابت)'}\n"
            f"⏳ لطفاً صبر کنید...",
            parse_mode='Markdown'
        )
        
        try:
            success = await execute_views(text, count, context)
            failed = count - success
            
            result_text = (
                f"✅ **{success}** ویو با موفقیت ارسال شد!\n"
                f"❌ **{failed}** ویو ناموفق\n"
                f"⚡ سرعت: {settings_manager.get('speed')} ویو/ثانیه\n"
                f"🌐 حالت: {'با پروکسی' if settings_manager.get('use_proxy') else 'بدون پروکسی'}"
            )
            await status_msg.edit_text(result_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منو", callback_data="menu")]]), parse_mode='Markdown')
        except Exception as e:
            logger.error(f"❌ خطا در اجرای عملیات: {e}")
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
                    f"🌐 سرور: `{new_proxy['server']}:{new_proxy['port']}`",
                    reply_markup=get_proxy_menu(),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ فرمت MTProto نامعتبر!",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="proxy")]])
                )
        elif '://' in text and ':' in text.split('://')[1]:
            PROXY_LIST.append(text)
            await update.message.reply_text(
                f"✅ پروکسی HTTP `{text}` با موفقیت اضافه شد!\n"
                f"📋 تعداد کل: **{len(PROXY_LIST)}** عدد",
                reply_markup=get_proxy_menu(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ فرمت پروکسی نامعتبر!\n"
                "فرمت HTTP: `http://ip:port`\n"
                "فرمت MTProto: `tg://proxy?server=ip&port=port&secret=secret`",
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

# ==================== تابع اصلی ====================

async def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    logger.info("🤖 ربات با موفقیت راه‌اندازی شد!")
    
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        await application.stop()

if __name__ == "__main__":
    asyncio.run(main())
