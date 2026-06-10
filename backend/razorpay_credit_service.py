"""
Razorpay Payment Integration for Credit Purchases
Handles payment order creation, verification, and credit addition
"""
import os
import hmac
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import razorpay
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

from credit_packages import UserType

logger = logging.getLogger(__name__)


class CreatePaymentOrderRequest(BaseModel):
    """Request to create payment order"""
    package_id: str
    user_type: UserType  # photographer or user


class VerifyPaymentRequest(BaseModel):
    """Request to verify payment"""
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    package_id: str


class PaymentRecord(BaseModel):
    """Payment record for database"""
    payment_id: str
    order_id: str
    admin_id: str
    package_id: str
    user_type: str
    amount: float
    currency: str
    credits_purchased: int
    status: str  # created, paid, failed
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None


def build_razorpay_credit_router(
    db: AsyncIOMotorDatabase,
    get_current_admin,
    credit_service
) -> APIRouter:
    """Build Razorpay payment router for credit purchases"""
    router = APIRouter(prefix="/api/payments", tags=["payments"])
    
    # Initialize Razorpay client
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
    
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        logger.warning("⚠️  Razorpay credentials not configured. Payment features will not work.")
        razorpay_client = None
    else:
        try:
            razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
            logger.info("✅ Razorpay client initialized for credit purchases")
        except Exception as e:
            logger.error(f"❌ Razorpay client initialization failed: {e}")
            razorpay_client = None
    
    
    @router.post("/create-order")
    async def create_payment_order(
        request: CreatePaymentOrderRequest,
        current_admin: dict = Depends(get_current_admin)
    ):
        """Create Razorpay payment order for credit purchase"""
        try:
            if not razorpay_client:
                raise HTTPException(
                    status_code=503,
                    detail="Payment service not configured. Please contact support."
                )
            
            # Get credit package
            package = await db.credit_packages.find_one(
                {"package_id": request.package_id, "is_active": True},
                {"_id": 0}
            )
            
            if not package:
                raise HTTPException(status_code=404, detail="Credit package not found")
            
            # Determine price based on user type
            if request.user_type == UserType.PHOTOGRAPHER:
                if package.get("discount_enabled"):
                    price = package.get("photographer_discount_price", package["photographer_price"])
                else:
                    price = package["photographer_price"]
            else:  # USER
                if package.get("discount_enabled"):
                    price = package.get("user_discount_price", package["user_price"])
                else:
                    price = package["user_price"]
            
            # Convert to paise (Razorpay uses smallest currency unit)
            amount_paise = int(price * 100)
            
            # Create Razorpay order
            razorpay_order = razorpay_client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "receipt": f"credit_{package['package_id']}_{current_admin['id'][:8]}",
                "notes": {
                    "admin_id": current_admin['id'],
                    "package_id": request.package_id,
                    "credits": package["credits"],
                    "user_type": request.user_type.value
                }
            })
            
            # Save payment record
            payment_record = {
                "payment_id": razorpay_order["id"],
                "order_id": razorpay_order["id"],
                "admin_id": current_admin['id'],
                "package_id": request.package_id,
                "user_type": request.user_type.value,
                "amount": price,
                "currency": "INR",
                "credits_purchased": package["credits"],
                "status": "created",
                "created_at": datetime.now(timezone.utc),
                "razorpay_order": razorpay_order
            }
            
            await db.payment_records.insert_one(payment_record)
            
            return {
                "success": True,
                "order_id": razorpay_order["id"],
                "amount": amount_paise,
                "currency": "INR",
                "key_id": RAZORPAY_KEY_ID,
                "credits": package["credits"],
                "package_name": package["name"]
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating payment order: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.post("/verify-payment")
    async def verify_payment(
        request: VerifyPaymentRequest,
        current_admin: dict = Depends(get_current_admin)
    ):
        """Verify Razorpay payment signature and add credits"""
        try:
            if not razorpay_client:
                raise HTTPException(
                    status_code=503,
                    detail="Payment service not configured"
                )
            
            # Verify signature
            generated_signature = hmac.new(
                RAZORPAY_KEY_SECRET.encode('utf-8'),
                f"{request.razorpay_order_id}|{request.razorpay_payment_id}".encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            if generated_signature != request.razorpay_signature:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid payment signature. Payment verification failed."
                )
            
            # Get payment record
            payment_record = await db.payment_records.find_one({
                "order_id": request.razorpay_order_id,
                "admin_id": current_admin['id']
            })
            
            if not payment_record:
                raise HTTPException(status_code=404, detail="Payment record not found")
            
            # Check if already processed
            if payment_record.get("status") == "paid":
                return {
                    "success": True,
                    "message": "Payment already processed",
                    "credits_added": payment_record["credits_purchased"]
                }
            
            # Add credits to admin account
            credits_to_add = payment_record["credits_purchased"]
            
            await credit_service.add_credits(
                admin_id=current_admin['id'],
                amount=credits_to_add,
                reason=f"Credit purchase - Package: {payment_record['package_id']} - Payment: {request.razorpay_payment_id}",
                performed_by=current_admin['id']
            )
            
            # Update payment record
            await db.payment_records.update_one(
                {"order_id": request.razorpay_order_id},
                {
                    "$set": {
                        "status": "paid",
                        "razorpay_payment_id": request.razorpay_payment_id,
                        "razorpay_signature": request.razorpay_signature,
                        "paid_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            return {
                "success": True,
                "message": "Payment verified successfully",
                "credits_added": credits_to_add,
                "payment_id": request.razorpay_payment_id
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.get("/history")
    async def get_payment_history(
        current_admin: dict = Depends(get_current_admin)
    ):
        """Get payment history for current admin"""
        try:
            payments = await db.payment_records.find(
                {"admin_id": current_admin['id']},
                {"_id": 0, "razorpay_order": 0}
            ).sort("created_at", -1).to_list(100)
            
            return {
                "success": True,
                "payments": payments,
                "count": len(payments)
            }
        except Exception as e:
            logger.error(f"Error fetching payment history: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.get("/packages")
    async def get_available_packages(
        user_type: UserType,
        current_admin: dict = Depends(get_current_admin)
    ):
        """Get available credit packages for purchase"""
        try:
            packages = await db.credit_packages.find(
                {"is_active": True},
                {"_id": 0}
            ).sort("display_order", 1).to_list(100)
            
            # Add pricing info based on user type
            for package in packages:
                if user_type == UserType.PHOTOGRAPHER:
                    if package.get("discount_enabled"):
                        package["price"] = package.get("photographer_discount_price", package["photographer_price"])
                        package["original_price"] = package["photographer_price"]
                    else:
                        package["price"] = package["photographer_price"]
                else:
                    if package.get("discount_enabled"):
                        package["price"] = package.get("user_discount_price", package["user_price"])
                        package["original_price"] = package["user_price"]
                    else:
                        package["price"] = package["user_price"]
            
            return {
                "success": True,
                "packages": packages,
                "count": len(packages),
                "user_type": user_type.value
            }
        except Exception as e:
            logger.error(f"Error fetching packages: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    return router
