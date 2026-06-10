"""
Restructured Admin Panel Service
Implements hierarchical pricing management
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

from restructured_pricing_models import (
    UserTypeCategory, PackType,
    UpdateDesignPriceRequest,
    CreateThemePackRequest, CreateDesignPackRequest,
    CreateCreditPlanRequest, UpdateCreditPlanRequest,
    CreateMonthlyPlanRequest, UpdateMonthlyPlanRequest,
    ThemePackConfig, DesignPackConfig,
    CreditPlan, MonthlyPlan
)

logger = logging.getLogger(__name__)


def build_restructured_admin_router(
    db: AsyncIOMotorDatabase,
    require_super_admin
) -> APIRouter:
    """Build restructured admin panel router"""
    router = APIRouter(prefix="/api/admin/restructured", tags=["admin_restructured"])
    
    # =====================================================================
    # DESIGN PRICING (User / Photographer)
    # =====================================================================
    
    @router.get("/design-pricing/{user_type}")
    async def get_design_pricing(
        user_type: UserTypeCategory,
        theme: Optional[str] = None,
        event_type: Optional[str] = None,
        current_admin: dict = Depends(require_super_admin)
    ):
        """Get design pricing for user type"""
        try:
            query = {"user_type": user_type.value}
            if theme:
                query["theme"] = theme
            if event_type:
                query["event_type"] = event_type
            
            designs = await db.design_pricing_by_user_type.find(
                query,
                {"_id": 0}
            ).to_list(1000)
            
            return {
                "success": True,
                "user_type": user_type.value,
                "designs": designs,
                "count": len(designs)
            }
        except Exception as e:
            logger.error(f"Error getting design pricing: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.post("/design-pricing/{user_type}/batch")
    async def update_design_pricing_batch(
        user_type: UserTypeCategory,
        updates: List[UpdateDesignPriceRequest],
        current_admin: dict = Depends(require_super_admin)
    ):
        """Batch update design pricing for user type"""
        try:
            updated_count = 0
            
            for update in updates:
                result = await db.design_pricing_by_user_type.update_one(
                    {
                        "design_id": update.design_id,
                        "user_type": user_type.value
                    },
                    {
                        "$set": {
                            "credits": update.credits,
                            "updated_at": datetime.now(timezone.utc)
                        }
                    },
                    upsert=True
                )
                
                if result.modified_count > 0 or result.upserted_id:
                    updated_count += 1
            
            return {
                "success": True,
                "message": f"Updated {updated_count} designs for {user_type.value}",
                "updated_count": updated_count
            }
        except Exception as e:
            logger.error(f"Error updating design pricing: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    # =====================================================================
    # CREDIT PACKS (User/Photographer → Full Theme / Random Design)
    # =====================================================================
    
    @router.get("/credit-packs/{user_type}/{pack_type}")
    async def get_credit_packs(
        user_type: UserTypeCategory,
        pack_type: PackType,
        current_admin: dict = Depends(require_super_admin)
    ):
        """Get credit packs for user type and pack type"""
        try:
            packs = await db.credit_pack_categories.find_one(
                {
                    "user_type": user_type.value,
                    "pack_type": pack_type.value
                },
                {"_id": 0}
            )
            
            if not packs:
                packs = {
                    "user_type": user_type.value,
                    "pack_type": pack_type.value,
                    "theme_packs": [] if pack_type == PackType.FULL_THEME else None,
                    "design_packs": [] if pack_type == PackType.RANDOM_DESIGN else None
                }
            
            return {
                "success": True,
                "user_type": user_type.value,
                "pack_type": pack_type.value,
                "packs": packs
            }
        except Exception as e:
            logger.error(f"Error getting credit packs: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.post("/credit-packs/{user_type}/full-theme")
    async def create_theme_pack(
        user_type: UserTypeCategory,
        request: CreateThemePackRequest,
        current_admin: dict = Depends(require_super_admin)
    ):
        """Create full theme pack"""
        try:
            theme_pack = ThemePackConfig(
                theme_name=request.theme_name,
                credits=request.credits,
                description=request.description
            )
            
            await db.credit_pack_categories.update_one(
                {
                    "user_type": user_type.value,
                    "pack_type": PackType.FULL_THEME.value
                },
                {
                    "$push": {"theme_packs": theme_pack.dict()},
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                },
                upsert=True
            )
            
            return {
                "success": True,
                "message": "Theme pack created",
                "pack_id": theme_pack.pack_id
            }
        except Exception as e:
            logger.error(f"Error creating theme pack: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.post("/credit-packs/{user_type}/random-design")
    async def create_design_pack(
        user_type: UserTypeCategory,
        request: CreateDesignPackRequest,
        current_admin: dict = Depends(require_super_admin)
    ):
        """Create random design pack"""
        try:
            total_credits = request.design_count * request.credits_per_design
            
            design_pack = DesignPackConfig(
                pack_name=request.pack_name,
                design_count=request.design_count,
                credits_per_design=request.credits_per_design,
                total_credits=total_credits,
                description=request.description
            )
            
            await db.credit_pack_categories.update_one(
                {
                    "user_type": user_type.value,
                    "pack_type": PackType.RANDOM_DESIGN.value
                },
                {
                    "$push": {"design_packs": design_pack.dict()},
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                },
                upsert=True
            )
            
            return {
                "success": True,
                "message": "Design pack created",
                "pack_id": design_pack.pack_id
            }
        except Exception as e:
            logger.error(f"Error creating design pack: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    # =====================================================================
    # PLANS & PRICING
    # =====================================================================
    
    @router.get("/plans-pricing/user")
    async def get_user_plans(
        current_admin: dict = Depends(require_super_admin)
    ):
        """Get all user credit plans"""
        try:
            plans = await db.credit_plans.find(
                {"user_type": UserTypeCategory.USER.value},
                {"_id": 0}
            ).sort("display_order", 1).to_list(100)
            
            return {
                "success": True,
                "user_type": "user",
                "plans": plans,
                "count": len(plans)
            }
        except Exception as e:
            logger.error(f"Error getting user plans: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.post("/plans-pricing/user")
    async def create_user_plan(
        request: CreateCreditPlanRequest,
        current_admin: dict = Depends(require_super_admin)
    ):
        """Create user credit plan"""
        try:
            # Force user type
            request.user_type = UserTypeCategory.USER
            
            # Calculate discount percentage if needed
            if request.discount_enabled and request.discounted_price:
                discount_pct = int(((request.price - request.discounted_price) / request.price) * 100)
            else:
                discount_pct = None
            
            plan = CreditPlan(
                **request.dict(),
                discount_percentage=discount_pct
            )
            
            await db.credit_plans.insert_one(plan.dict())
            
            return {
                "success": True,
                "message": "User credit plan created",
                "plan_id": plan.plan_id
            }
        except Exception as e:
            logger.error(f"Error creating user plan: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.put("/plans-pricing/user/{plan_id}")
    async def update_user_plan(
        plan_id: str,
        request: UpdateCreditPlanRequest,
        current_admin: dict = Depends(require_super_admin)
    ):
        """Update user credit plan"""
        try:
            update_data = {k: v for k, v in request.dict().items() if v is not None and k != "plan_id"}
            update_data["updated_at"] = datetime.now(timezone.utc)
            
            # Recalculate discount percentage if price changed
            if "price" in update_data or "discounted_price" in update_data:
                existing = await db.credit_plans.find_one({"plan_id": plan_id})
                if existing:
                    price = update_data.get("price", existing.get("price"))
                    disc_price = update_data.get("discounted_price", existing.get("discounted_price"))
                    if disc_price and price:
                        update_data["discount_percentage"] = int(((price - disc_price) / price) * 100)
            
            result = await db.credit_plans.update_one(
                {"plan_id": plan_id},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                raise HTTPException(status_code=404, detail="Plan not found")
            
            return {
                "success": True,
                "message": "User credit plan updated"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating user plan: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.get("/plans-pricing/photographer/monthly")
    async def get_photographer_monthly_plans(
        current_admin: dict = Depends(require_super_admin)
    ):
        """Get photographer monthly plans"""
        try:
            plans = await db.monthly_plans.find(
                {},
                {"_id": 0}
            ).sort("display_order", 1).to_list(100)
            
            return {
                "success": True,
                "plan_type": "monthly",
                "plans": plans,
                "count": len(plans)
            }
        except Exception as e:
            logger.error(f"Error getting monthly plans: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.post("/plans-pricing/photographer/monthly")
    async def create_monthly_plan(
        request: CreateMonthlyPlanRequest,
        current_admin: dict = Depends(require_super_admin)
    ):
        """Create photographer monthly plan"""
        try:
            # Calculate discount percentage if needed
            if request.discount_enabled and request.discounted_price:
                discount_pct = int(((request.price - request.discounted_price) / request.price) * 100)
            else:
                discount_pct = None
            
            plan = MonthlyPlan(
                **request.dict(),
                discount_percentage=discount_pct
            )
            
            await db.monthly_plans.insert_one(plan.dict())
            
            return {
                "success": True,
                "message": "Monthly plan created",
                "plan_id": plan.plan_id
            }
        except Exception as e:
            logger.error(f"Error creating monthly plan: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.put("/plans-pricing/photographer/monthly/{plan_id}")
    async def update_monthly_plan(
        plan_id: str,
        request: UpdateMonthlyPlanRequest,
        current_admin: dict = Depends(require_super_admin)
    ):
        """Update photographer monthly plan"""
        try:
            update_data = {k: v for k, v in request.dict().items() if v is not None and k != "plan_id"}
            update_data["updated_at"] = datetime.now(timezone.utc)
            
            # Recalculate discount percentage if price changed
            if "price" in update_data or "discounted_price" in update_data:
                existing = await db.monthly_plans.find_one({"plan_id": plan_id})
                if existing:
                    price = update_data.get("price", existing.get("price"))
                    disc_price = update_data.get("discounted_price", existing.get("discounted_price"))
                    if disc_price and price:
                        update_data["discount_percentage"] = int(((price - disc_price) / price) * 100)
            
            result = await db.monthly_plans.update_one(
                {"plan_id": plan_id},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                raise HTTPException(status_code=404, detail="Plan not found")
            
            return {
                "success": True,
                "message": "Monthly plan updated"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating monthly plan: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.get("/plans-pricing/photographer/credits")
    async def get_photographer_credit_plans(
        current_admin: dict = Depends(require_super_admin)
    ):
        """Get photographer credit plans"""
        try:
            plans = await db.credit_plans.find(
                {"user_type": UserTypeCategory.PHOTOGRAPHER.value},
                {"_id": 0}
            ).sort("display_order", 1).to_list(100)
            
            return {
                "success": True,
                "user_type": "photographer",
                "plan_type": "credits",
                "plans": plans,
                "count": len(plans)
            }
        except Exception as e:
            logger.error(f"Error getting photographer credit plans: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.post("/plans-pricing/photographer/credits")
    async def create_photographer_credit_plan(
        request: CreateCreditPlanRequest,
        current_admin: dict = Depends(require_super_admin)
    ):
        """Create photographer credit plan"""
        try:
            # Force photographer type
            request.user_type = UserTypeCategory.PHOTOGRAPHER
            
            # Calculate discount percentage if needed
            if request.discount_enabled and request.discounted_price:
                discount_pct = int(((request.price - request.discounted_price) / request.price) * 100)
            else:
                discount_pct = None
            
            plan = CreditPlan(
                **request.dict(),
                discount_percentage=discount_pct
            )
            
            await db.credit_plans.insert_one(plan.dict())
            
            return {
                "success": True,
                "message": "Photographer credit plan created",
                "plan_id": plan.plan_id
            }
        except Exception as e:
            logger.error(f"Error creating photographer credit plan: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    return router
