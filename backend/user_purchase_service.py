"""
User Purchase Flow Service
Handles design/theme purchases with dynamic feature selection
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

from enhanced_pricing_models import (
    UserTypeEnum, PurchaseRequest
)
from pricing_calculation_service import PricingCalculationService

logger = logging.getLogger(__name__)


def build_user_purchase_router(
    db: AsyncIOMotorDatabase,
    get_current_admin,
    credit_service
) -> APIRouter:
    """Build user purchase flow router"""
    router = APIRouter(prefix="/api/user/purchase", tags=["user_purchase"])
    
    pricing_service = PricingCalculationService(db)
    
    async def _resolve_admin(admin_id_or_dict):
        """get_current_admin returns a string admin_id. Fetch admin doc."""
        if isinstance(admin_id_or_dict, dict):
            doc = admin_id_or_dict
        else:
            doc = await db.admins.find_one({"id": admin_id_or_dict}) or {}
        return doc
    
    # =====================================================================
    # BROWSE & PREVIEW
    # =====================================================================
    
    @router.get("/designs")
    async def browse_designs(
        theme: str = None,
        event_type: str = None,
        current_admin: dict = Depends(get_current_admin)
    ):
        """Browse available designs with pricing"""
        try:
            query = {}
            if theme:
                query["theme"] = theme
            if event_type:
                query["event_type"] = event_type
            
            designs = await db.design_pricing_enhanced.find(
                query,
                {"_id": 0}
            ).to_list(1000)
            
            # Determine user type
            user_type = UserTypeEnum.PHOTOGRAPHER if (await _resolve_admin(current_admin)).get("role") == "admin" else UserTypeEnum.USER
            
            # Add appropriate pricing to each design
            for design in designs:
                if user_type == UserTypeEnum.USER:
                    design["base_credits"] = design.get("base_user_credits", 0)
                else:
                    design["base_credits"] = design.get("base_photographer_credits", 0)
            
            return {
                "success": True,
                "designs": designs,
                "count": len(designs),
                "user_type": user_type.value
            }
        except Exception as e:
            logger.error(f"Error browsing designs: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.get("/themes")
    async def browse_theme_packs(
        current_admin: dict = Depends(get_current_admin)
    ):
        """Browse available theme packages"""
        try:
            themes = await db.theme_pricing_enhanced.find(
                {"is_active": True},
                {"_id": 0}
            ).to_list(100)
            
            # Determine user type
            user_type = UserTypeEnum.PHOTOGRAPHER if (await _resolve_admin(current_admin)).get("role") == "admin" else UserTypeEnum.USER
            
            # Add appropriate pricing
            for theme in themes:
                if user_type == UserTypeEnum.USER:
                    theme["base_credits"] = theme.get("user_credits", 0)
                else:
                    theme["base_credits"] = theme.get("photographer_credits", 0)
            
            return {
                "success": True,
                "themes": themes,
                "count": len(themes),
                "user_type": user_type.value
            }
        except Exception as e:
            logger.error(f"Error browsing themes: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.get("/features/{event_type}")
    async def get_available_features(
        event_type: str,
        current_admin: dict = Depends(get_current_admin)
    ):
        """Get available features for specific event type"""
        try:
            features = await pricing_service.get_available_features_for_event(event_type)
            
            # Determine user type
            user_type = UserTypeEnum.PHOTOGRAPHER if (await _resolve_admin(current_admin)).get("role") == "admin" else UserTypeEnum.USER
            
            # Add appropriate pricing and info
            for feature in features:
                if feature.get("is_free"):
                    feature["credits"] = 0
                else:
                    if user_type == UserTypeEnum.USER:
                        feature["credits"] = feature.get("user_credits", 0)
                    else:
                        feature["credits"] = feature.get("photographer_credits", 0)
            
            return {
                "success": True,
                "features": features,
                "count": len(features),
                "event_type": event_type
            }
        except Exception as e:
            logger.error(f"Error getting features: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.get("/durations")
    async def get_duration_options(
        current_admin: dict = Depends(get_current_admin)
    ):
        """Get available duration options"""
        try:
            durations = await pricing_service.get_duration_options()
            
            # Determine user type
            user_type = UserTypeEnum.PHOTOGRAPHER if (await _resolve_admin(current_admin)).get("role") == "admin" else UserTypeEnum.USER
            
            # Add appropriate pricing
            for duration in durations:
                if user_type == UserTypeEnum.USER:
                    duration["credits"] = duration.get("user_credits", 0)
                else:
                    duration["credits"] = duration.get("photographer_credits", 0)
            
            return {
                "success": True,
                "durations": durations,
                "count": len(durations)
            }
        except Exception as e:
            logger.error(f"Error getting durations: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    # =====================================================================
    # PURCHASE CALCULATION
    # =====================================================================
    
    @router.post("/calculate")
    async def calculate_purchase(
        request: PurchaseRequest,
        current_admin: dict = Depends(get_current_admin)
    ):
        """Calculate total credits for purchase"""
        try:
            # Override user type based on admin role
            if (await _resolve_admin(current_admin)).get("role") == "admin":
                request.user_type = UserTypeEnum.PHOTOGRAPHER
            else:
                request.user_type = UserTypeEnum.USER
            
            calculation = await pricing_service.calculate_purchase_price(request)
            
            return {
                "success": True,
                "calculation": calculation.dict()
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error calculating purchase: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    # =====================================================================
    # CONFIRM PURCHASE
    # =====================================================================
    
    @router.post("/confirm")
    async def confirm_purchase(
        request: PurchaseRequest,
        current_admin: dict = Depends(get_current_admin)
    ):
        """Confirm and process design purchase"""
        try:
            # Determine user type
            if (await _resolve_admin(current_admin)).get("role") == "admin":
                request.user_type = UserTypeEnum.PHOTOGRAPHER
            else:
                request.user_type = UserTypeEnum.USER
            
            # Check if super admin (free purchases)
            is_super_admin = (await _resolve_admin(current_admin)).get("role") == "super_admin"
            
            # Calculate total
            calculation = await pricing_service.calculate_purchase_price(request)
            total_credits = calculation.total_credits
            
            # Resolve actor's actual admin_id (handle dict or string from dep)
            actor_doc = await _resolve_admin(current_admin)
            actor_id  = actor_doc.get("id") or (current_admin if isinstance(current_admin, str) else None)

            if not is_super_admin:
                if not actor_id:
                    raise HTTPException(status_code=401, detail="Could not resolve account")
                # Spend credits through the canonical CreditService (atomic
                # balance check + ledger write). Anything > 0 mandates a row.
                if total_credits > 0:
                    try:
                        await credit_service.use_credits(
                            admin_id=actor_id,
                            amount=total_credits,
                            reason=f"Purchase: design={request.design_id} event={request.event_type}",
                            related_wedding_id=getattr(request, "wedding_id", None) or request.design_id,
                            metadata=calculation.dict(),
                        )
                    except ValueError as ve:
                        # use_credits raises ValueError on insufficient balance
                        raise HTTPException(status_code=400, detail=str(ve))
            
            # Calculate expiry date
            duration = await db.duration_options.find_one({"duration_id": request.duration_id})
            if duration and duration.get("days"):
                expiry_date = datetime.now(timezone.utc) + timedelta(days=duration["days"])
            else:
                expiry_date = None

            # Create purchase record
            buyer_id = (await _resolve_admin(current_admin)).get("id") or (current_admin if isinstance(current_admin, str) else "unknown")
            purchase_record = {
                "purchase_id": str(uuid.uuid4()),
                "admin_id": buyer_id,
                "design_id": request.design_id,
                "event_type": request.event_type,
                "selected_features": request.selected_features,
                "duration_id": request.duration_id,
                "is_mixed_theme": request.is_mixed_theme,
                "credits_paid": total_credits if not is_super_admin else 0,
                "calculation": calculation.dict(),
                "purchased_at": datetime.now(timezone.utc),
                "is_super_admin_purchase": is_super_admin,
                "expires_at": expiry_date,
            }

            await db.design_purchases.insert_one(purchase_record)
            
            return {
                "success": True,
                "message": "Purchase successful",
                "purchase_id": purchase_record["purchase_id"],
                "credits_deducted": total_credits if not is_super_admin else 0,
                "expiry_date": expiry_date.isoformat() if expiry_date else None,
                "breakdown": calculation.breakdown
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error confirming purchase: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.get("/my-purchases")
    async def get_my_purchases(
        current_admin: dict = Depends(get_current_admin)
    ):
        """Get user's purchase history"""
        try:
            purchases = await db.design_purchases.find(
                {"admin_id": current_admin},
                {"_id": 0}
            ).sort("purchased_at", -1).to_list(100)
            
            return {
                "success": True,
                "purchases": purchases,
                "count": len(purchases)
            }
        except Exception as e:
            logger.error(f"Error getting purchases: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    return router


# Import uuid at the top
import uuid
