"""
اسکریپت ایجاد یا ارتقای ادمین
Create or promote an admin user
"""
import asyncio
import sys
import os
import io

# تنظیم انکودینگ برای ترمینال ویندوز
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# افزودن مسیر پروژه به sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config.settings import settings
from core.database import init_engine, init_db, get_db
from repositories.user_repository import UserRepository
from models.setting import Admin


async def create_admin(telegram_id: int, level: str = "owner"):
    init_engine(settings.DATABASE_URL)
    # اطمینان از ساخته شدن جداول قبل از ساخت ادمین
    await init_db()

    async with get_db() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(telegram_id)

        if not user:
            user = await user_repo.create_user(
                telegram_id=telegram_id,
                first_name="Admin",
            )
            print(f"[OK] User created with ID: {telegram_id}")

        from sqlalchemy import select
        result = await session.execute(
            select(Admin).where(Admin.user_id == telegram_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.level = level
            session.add(existing)
            print(f"[OK] Admin level updated to '{level}'")
        else:
            admin = Admin(user_id=telegram_id, level=level, is_active=True)
            session.add(admin)
            print(f"[OK] Admin created with level '{level}'")

    print("")
    print(f"[DONE] Admin {telegram_id} is successfully registered!")
    print(f"[NOTE] Make sure {telegram_id} is also added to ADMIN_IDS in .env")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/create_admin.py <telegram_id> [level]")
        print("Levels: owner, manager, support, seller")
        sys.exit(1)

    tid = int(sys.argv[1])
    lvl = sys.argv[2] if len(sys.argv) > 2 else "owner"
    asyncio.run(create_admin(tid, lvl))
