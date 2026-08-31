"""
اسکریپت اولیه‌سازی دیتابیس
Initialize database tables and seed default settings
"""
import asyncio
import sys
import os
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# افزودن مسیر پروژه به Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config.settings import settings
from core.database import init_engine, init_db, get_db
from services.ticket_service import SettingService


async def main():
    print("[*] Initializing database...")
    init_engine(settings.DATABASE_URL)
    await init_db()
    print("[OK] Tables created successfully")

    async with get_db() as session:
        setting_service = SettingService(session)
        await setting_service.initialize_defaults()
        print("[OK] Default settings initialized")

    print("")
    print("[DONE] Database initialization complete!")
    print(f"[DB]   {settings.DATABASE_URL}")


if __name__ == "__main__":
    asyncio.run(main())
