"""
Seed default credit packs into `credit_packs` collection.
Used by /api/public/credit-packs (user-facing) and /api/admin/credit-packs (photographer-facing).

Idempotent: upserts by `id`.
"""
import asyncio
import os
import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "test_database")


DEFAULT_PACKS = [
    # User-facing (guest)
    {
        "id": "pack_guest_starter",
        "label": "Starter",
        "price_inr": 99,
        "credits": 50,
        "description": "Try your first wedding invitation",
        "badge": None,
        "audience": "guest",
        "sort_order": 1,
    },
    {
        "id": "pack_guest_popular",
        "label": "Popular",
        "price_inr": 299,
        "credits": 200,
        "description": "Best value for one full wedding",
        "badge": "Most Popular",
        "audience": "guest",
        "sort_order": 2,
    },
    {
        "id": "pack_guest_pro",
        "label": "Pro",
        "price_inr": 599,
        "credits": 500,
        "description": "Multi-event wedding bundle",
        "badge": "Best Deal",
        "audience": "guest",
        "sort_order": 3,
    },
    # Photographer
    {
        "id": "pack_photo_studio",
        "label": "Studio",
        "price_inr": 999,
        "credits": 1000,
        "description": "Studio starter — 1000 credits",
        "badge": None,
        "audience": "photographer",
        "sort_order": 1,
    },
    {
        "id": "pack_photo_agency",
        "label": "Agency",
        "price_inr": 4999,
        "credits": 6000,
        "description": "Agency bulk — 6000 credits + 1000 bonus",
        "badge": "Most Popular",
        "audience": "photographer",
        "sort_order": 2,
    },
]


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    print(f"🚀 Seeding credit_packs into {DB_NAME} …")
    now = datetime.now(timezone.utc).isoformat()
    upserted = 0
    for pack in DEFAULT_PACKS:
        doc = {
            **pack,
            "design_id": None,
            "is_active": True,
            "updated_at": now,
        }
        await db.credit_packs.update_one(
            {"id": pack["id"]},
            {"$set": doc, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        upserted += 1
    print(f"✅ Upserted {upserted} credit packs")
    guest = await db.credit_packs.count_documents({"audience": {"$in": ["guest", "both"]}})
    photo = await db.credit_packs.count_documents({"audience": {"$in": ["photographer", "both"]}})
    print(f"   guest-visible: {guest} · photographer-visible: {photo}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
