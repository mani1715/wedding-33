"""
Initialize Default Design Prices for All Designs
Sets default pricing when user opens the page
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "test_database")


# Sample design data (you'll need to populate with your actual 180+ designs)
SAMPLE_DESIGNS = [
    # Temple Theme - Marriage
    {"design_id": "temple_marriage_01", "design_name": "Temple Marriage Classic", "theme": "Temple", "event_type": "marriage"},
    {"design_id": "temple_marriage_02", "design_name": "Temple Marriage Royal", "theme": "Temple", "event_type": "marriage"},
    {"design_id": "temple_marriage_03", "design_name": "Temple Marriage Grand", "theme": "Temple", "event_type": "marriage"},
    
    # Temple Theme - Engagement
    {"design_id": "temple_engagement_01", "design_name": "Temple Engagement Classic", "theme": "Temple", "event_type": "engagement"},
    {"design_id": "temple_engagement_02", "design_name": "Temple Engagement Royal", "theme": "Temple", "event_type": "engagement"},
    
    # Temple Theme - Haldi
    {"design_id": "temple_haldi_01", "design_name": "Temple Haldi Classic", "theme": "Temple", "event_type": "haldi"},
    {"design_id": "temple_haldi_02", "design_name": "Temple Haldi Bright", "theme": "Temple", "event_type": "haldi"},
    
    # Beach Theme - Marriage
    {"design_id": "beach_marriage_01", "design_name": "Beach Marriage Sunset", "theme": "Beach", "event_type": "marriage"},
    {"design_id": "beach_marriage_02", "design_name": "Beach Marriage Tropical", "theme": "Beach", "event_type": "marriage"},
    {"design_id": "beach_marriage_03", "design_name": "Beach Marriage Paradise", "theme": "Beach", "event_type": "marriage"},
    
    # Beach Theme - Engagement  
    {"design_id": "beach_engagement_01", "design_name": "Beach Engagement Romantic", "theme": "Beach", "event_type": "engagement"},
    {"design_id": "beach_engagement_02", "design_name": "Beach Engagement Bliss", "theme": "Beach", "event_type": "engagement"},
    
    # Mughal Theme - Marriage
    {"design_id": "mughal_marriage_01", "design_name": "Mughal Marriage Royal", "theme": "Mughal", "event_type": "marriage"},
    {"design_id": "mughal_marriage_02", "design_name": "Mughal Marriage Palace", "theme": "Mughal", "event_type": "marriage"},
    {"design_id": "mughal_marriage_03", "design_name": "Mughal Marriage Empress", "theme": "Mughal", "event_type": "marriage"},
    
    # Mughal Theme - Engagement
    {"design_id": "mughal_engagement_01", "design_name": "Mughal Engagement Regal", "theme": "Mughal", "event_type": "engagement"},
    
    # Mughal Theme - Reception
    {"design_id": "mughal_reception_01", "design_name": "Mughal Reception Grand", "theme": "Mughal", "event_type": "reception"},
    {"design_id": "mughal_reception_02", "design_name": "Mughal Reception Imperial", "theme": "Mughal", "event_type": "reception"},
    
    # Garden Theme - Marriage
    {"design_id": "garden_marriage_01", "design_name": "Garden Marriage Floral", "theme": "Garden", "event_type": "marriage"},
    {"design_id": "garden_marriage_02", "design_name": "Garden Marriage Bloom", "theme": "Garden", "event_type": "marriage"},
    
    # Garden Theme - Mehendi
    {"design_id": "garden_mehendi_01", "design_name": "Garden Mehendi Green", "theme": "Garden", "event_type": "mehendi"},
    {"design_id": "garden_mehendi_02", "design_name": "Garden Mehendi Fresh", "theme": "Garden", "event_type": "mehendi"},
]


async def initialize_default_design_prices():
    """Initialize default design prices for user and photographer"""
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("🚀 Initializing default design prices...")
    
    # Default pricing strategy
    DEFAULT_USER_CREDITS = 50
    DEFAULT_PHOTOGRAPHER_CREDITS = 30
    
    user_count = 0
    photographer_count = 0
    
    for design in SAMPLE_DESIGNS:
        # User pricing
        user_design = {
            **design,
            "user_type": "user",
            "credits": DEFAULT_USER_CREDITS,
            "is_premium": False
        }
        
        await db.design_pricing_by_user_type.update_one(
            {
                "design_id": design["design_id"],
                "user_type": "user"
            },
            {"$set": user_design},
            upsert=True
        )
        user_count += 1
        
        # Photographer pricing
        photographer_design = {
            **design,
            "user_type": "photographer",
            "credits": DEFAULT_PHOTOGRAPHER_CREDITS,
            "is_premium": False
        }
        
        await db.design_pricing_by_user_type.update_one(
            {
                "design_id": design["design_id"],
                "user_type": "photographer"
            },
            {"$set": photographer_design},
            upsert=True
        )
        photographer_count += 1
    
    print(f"✅ Initialized {user_count} user design prices (default: {DEFAULT_USER_CREDITS} credits)")
    print(f"✅ Initialized {photographer_count} photographer design prices (default: {DEFAULT_PHOTOGRAPHER_CREDITS} credits)")
    
    print("\n📝 Sample designs initialized:")
    themes = list(set(d["theme"] for d in SAMPLE_DESIGNS))
    for theme in themes:
        theme_designs = [d for d in SAMPLE_DESIGNS if d["theme"] == theme]
        print(f"   {theme}: {len(theme_designs)} designs")
    
    print("\n💡 Next steps:")
    print("1. Add more designs to SAMPLE_DESIGNS list")
    print("2. Update prices via admin panel")
    print("3. Create theme packs and design packs")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(initialize_default_design_prices())
