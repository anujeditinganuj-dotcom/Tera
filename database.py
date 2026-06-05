"""
database.py  —  MongoDB async helpers via Motor.
"""

from datetime import datetime, timedelta
import motor.motor_asyncio

from config import MONGO_URI, MONGO_DB_NAME

# ── Module-level globals set by init_mongo() ────────────────────────────────
mongo_client: motor.motor_asyncio.AsyncIOMotorClient = None
db = None


async def init_mongo():
    global mongo_client, db
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = mongo_client[MONGO_DB_NAME]
    await db.users.create_index("user_id", unique=True)
    print("✅ MongoDB connected!")


# ── User helpers ─────────────────────────────────────────────────────────────

async def get_user(user_id: int) -> dict:
    today = str(datetime.now().date())
    doc = await db.users.find_one({"user_id": user_id})
    if not doc:
        doc = {
            "user_id":         user_id,
            "name":            "",
            "joined":          today,
            "total_downloads": 0,
            "today_downloads": 0,
            "today_date":      today,
            "premium_expiry":  None,
            "shares_today":    0,
            "shares_date":     today,
        }
        await db.users.insert_one(doc)
    else:
        if doc.get("today_date") != today:
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "today_downloads": 0, "today_date": today,
                    "shares_today":    0, "shares_date": today,
                }},
            )
            doc.update(today_downloads=0, today_date=today,
                       shares_today=0,    shares_date=today)
    return doc


async def update_user(user_id: int, **fields):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": fields},
        upsert=True,
    )


async def inc_downloads(user_id: int):
    await db.users.update_one(
        {"user_id": user_id},
        {"$inc": {"today_downloads": 1, "total_downloads": 1}},
    )


# ── Premium helpers ──────────────────────────────────────────────────────────

def is_premium(doc: dict) -> bool:
    exp = doc.get("premium_expiry")
    if not exp:
        return False
    try:
        return datetime.now() < datetime.fromisoformat(exp)
    except Exception:
        return False


def premium_days_left(doc: dict) -> int:
    exp = doc.get("premium_expiry")
    if not exp:
        return 0
    try:
        delta = datetime.fromisoformat(exp) - datetime.now()
        return max(0, delta.days)
    except Exception:
        return 0


async def add_premium(user_id: int, days: int) -> datetime:
    doc = await get_user(user_id)
    now = datetime.now()
    try:
        exp = datetime.fromisoformat(doc["premium_expiry"]) if doc.get("premium_expiry") else now
        exp = max(exp, now) + timedelta(days=days)
    except Exception:
        exp = now + timedelta(days=days)
    await update_user(user_id, premium_expiry=exp.isoformat())
    return exp


async def remove_premium(user_id: int):
    await update_user(user_id, premium_expiry=None)


# ── Stats helpers ─────────────────────────────────────────────────────────────

async def count_users() -> tuple[int, int]:
    """Returns (total_users, premium_users)."""
    total = await db.users.count_documents({})
    prem  = await db.users.count_documents(
        {"premium_expiry": {"$gt": datetime.now().isoformat()}}
    )
    return total, prem
