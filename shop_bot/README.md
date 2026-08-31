# 🛍️ ربات شاپیار — فروشگاه اشتراک‌های نرم‌افزاری

ربات تلگرامی کامل برای فروش اشتراک‌های نرم‌افزاری با پنل ادمین داخلی، سیستم ارسال خودکار اکانت، کیف پول، رفرال، تیکت پشتیبانی و ۱۰+ درگاه پرداخت.

---

## ⚡ راه‌اندازی سریع (ویندوز لوکال)

### ۱. پیش‌نیازها
- Python 3.10+
- Git

### ۲. کلون و نصب
```bash
# ایجاد محیط مجازی
python -m venv venv
venv\Scripts\activate

# نصب وابستگی‌ها
pip install -r requirements.txt
```

### ۳. تنظیم Environment
```bash
copy .env.example .env
# فایل .env را با ویرایشگر باز کنید و مقادیر را وارد کنید
```

حداقل مقادیر ضروری در `.env`:
```env
TELEGRAM_BOT_TOKEN=your_token_from_botfather
ADMIN_IDS=your_telegram_id
```

### ۴. راه‌اندازی دیتابیس
```bash
python scripts/init_db.py
```

### ۵. اجرا
```bash
python run.py
```

---

## 🐳 اجرا با Docker (توصیه‌شده برای تولید)

```bash
# کپی env
copy .env.example .env
# ویرایش .env

# اجرا
docker-compose up -d

# مشاهده لاگ
docker-compose logs -f bot
```

---

## 🌐 دیپلوی روی Ubuntu/Debian

```bash
# نصب Python و Git
sudo apt update && sudo apt install -y python3.11 python3-pip git

# کلون پروژه
git clone <repo_url> shop_bot
cd shop_bot

# محیط مجازی
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# تنظیم .env
cp .env.example .env
nano .env

# init دیتابیس
python scripts/init_db.py

# راه‌اندازی به عنوان سرویس
sudo nano /etc/systemd/system/shopbot.service
```

محتوای فایل سرویس:
```ini
[Unit]
Description=Shapiyar Shop Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/shop_bot
ExecStart=/home/ubuntu/shop_bot/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable shopbot
sudo systemctl start shopbot
sudo systemctl status shopbot
```

---

## 🏗️ معماری پروژه

```
shop_bot/
├── config/          # تنظیمات و لاگ‌گیری
├── models/          # ۱۴ مدل SQLAlchemy
├── repositories/    # ۱۰ ریپازیتوری (Data Access Layer)
├── services/        # ۸ سرویس (Business Logic Layer)
├── handlers/
│   ├── user/        # ۵ هندلر کاربر
│   └── admin/       # ۱ هندلر ادمین (شامل همه بخش‌ها)
├── utils/           # کیبوردها، دکوراتورها، helpers
├── core/            # Database، Bot، Middleware، Dispatcher
└── scripts/         # اسکریپت‌های مدیریتی
```

---

## 🗄️ مدل‌های دیتابیس

| جدول | توضیح |
|---|---|
| `users` | کاربران ربات |
| `products` | محصولات |
| `orders` | سفارشات |
| `order_items` | آیتم‌های سفارش |
| `inventory` | انبار اکانت‌ها |
| `payments` | تراکنش‌های مالی |
| `wallets` | کیف پول کاربران |
| `tickets` | تیکت‌های پشتیبانی |
| `ticket_messages` | پیام‌های تیکت |
| `referrals` | سیستم رفرال |
| `discounts` | کدهای تخفیف |
| `settings` | تنظیمات ربات |
| `admins` | ادمین‌ها |
| `tutorials` | آموزش‌ها |

---

## 💳 درگاه‌های پرداخت

| درگاه | وضعیت | توضیح |
|---|---|---|
| کیف پول داخلی | ✅ کامل | پرداخت از موجودی |
| زرین‌پال | ✅ کامل | درگاه ریالی |
| آیدی‌پی | ✅ کامل | درگاه ریالی |
| NOWPayments | ✅ کامل | رمزارز (USDT) |
| Telegram Stars | 🔧 Stub | نیاز به تنظیم |
| سایر درگاه‌ها | 🔧 Stub | آماده توسعه |

---

## ⚙️ ویژگی‌های اصلی

### 🤖 ارسال خودکار اکانت
- انتخاب با `SELECT FOR UPDATE SKIP LOCKED`
- اولویت‌بندی بر اساس تاریخ انقضا (FIFO)
- پشتیبانی از اکانت‌های چندنفره

### 🔗 سیستم رفرال
- لینک دعوت اختصاصی برای هر کاربر
- بررسی خودکار شرایط (cron job)
- پاداش نقدی + تخفیف

### 🔔 ۲۵+ نوتیفیکیشن
- سفارش جدید / پرداخت / ارسال اکانت
- یادآوری انقضای اشتراک
- پاسخ تیکت + اطلاع به ادمین

---

## 🔑 دستورات مدیریتی

```bash
# ایجاد ادمین جدید
python scripts/create_admin.py <TELEGRAM_ID> [owner|manager|support]

# بازسازی دیتابیس
python scripts/init_db.py
```

---

## 📝 لایسنس

این پروژه برای استفاده شخصی ساخته شده است.
