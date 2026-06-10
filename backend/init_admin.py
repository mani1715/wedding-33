"""
Initialize admin user in database
Run this script once to create the default admin user
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from auth import get_password_hash
from models import Admin
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def init_admin():
    # Connect to MongoDB
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    # Check if admin already exists
    existing_admin = await db.admins.find_one({"email": "admin@wedding.com"})
    
    if existing_admin:
        print("Admin user already exists!")
        return
    
    # Create admin user
    admin = Admin(
        email="admin@wedding.com",
        name="Demo Photographer",
        password_hash=get_password_hash("admin123")
    )
    
    doc = admin.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.admins.insert_one(doc)
    
    print("✅ Admin user created successfully!")
    print("Email: admin@wedding.com")
    print("Password: admin123")
    print("\n⚠️  IMPORTANT: Change this password in production!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(init_admin())
