from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Request, Header
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
import os
import logging
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
from datetime import datetime, timedelta, timezone
import re
import random
import string
import io
import shutil
import bleach
import uuid
import base64
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib import colors as rl_colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import urllib.request
from PIL import Image as PILImage
import qrcode
from icalendar import Calendar, Event as ICalEvent
from io import BytesIO
import razorpay
import hmac
import hashlib


from models import (
    Admin, AdminLogin, AdminResponse, AdminRegister, AdminRole, AdminStatus,
    PhotographerSignupRequest, OTPSendRequest, OTPVerifyRequest,
    CreditLedger, CreditLedgerResponse, CreditActionType,
    AddCreditsRequest, DeductCreditsRequest, CreditBalanceResponse,
    Profile, ProfileCreate, ProfileUpdate, ProfileResponse,
    ProfileMedia, ProfileMediaCreate,
    Greeting, GreetingCreate, GreetingResponse,
    InvitationPublicView, SectionsEnabled, BackgroundMusic, MapSettings, ContactInfo,
    RSVPSettings, HoneymoonFund,
    LiveStreamSettings, SongRequestSettings, DressCodeSettings, DressCodeItem,
    SongRequest, SongRequestCreate, SongRequestResponse,
    CheckIn, CheckInCreate, CheckInResponse, CheckInStats,
    GuestRoom, PreWeddingLink,
    WeddingEvent, EventType,
    EventInvitation, EventInvitationCreate, EventInvitationUpdate, EventInvitationResponse,
    RSVP, RSVPCreate, RSVPResponse, RSVPStats,
    Analytics, ViewSession, DailyView, ViewTrackingRequest, InteractionTrackingRequest, 
    LanguageTrackingRequest, AnalyticsResponse, AnalyticsSummary,
    RateLimit, AuditLog, AuditLogResponse,
    DesignConfig, DesignConfigResponse, UpdateEventBackgroundRequest,
    LordLibrary, LordLibraryResponse, UpdateEventLordSettingsRequest,
    GuestWish, GuestWishCreate, GuestWishResponse,
    GuestReaction, GuestReactionCreate, GuestReactionStats,
    UpdateEventEngagementSettingsRequest,
    # PHASE 26: AI-Powered Personalization
    TranslationCache, TranslationRequest, TranslationResponse,
    GenerateDescriptionRequest, GenerateDescriptionResponse,
    RSVPSuggestionsRequest, RSVPSuggestionsResponse,
    GuestInsightsRequest, GuestInsightsResponse,
    AIRateLimitStatus,
    # PHASE 27: Post-Wedding Value (Combined)
    ThankYouMessage, ThankYouMessageCreate, ThankYouMessageResponse,
    WeddingAlbumMedia, WeddingAlbumMediaCreate, WeddingAlbumMediaResponse,
    MemoryModeStatus,
    # PHASE 28: Viral Sharing & Growth Engine
    ShareMetadata, QRCodeRequest, QRCodeResponse,
    # PHASE 29E: Admin Safety Nets & Recovery
    ProfileVersion, ProfileVersionResponse, ProfileVersionListResponse, RestoreVersionRequest,
    # PHASE 30: Analytics, Insights & Guest Intelligence
    DeviceType, AnalyticsEventType, IPLocationCache, ViewAnalytics, EngagementAnalytics,
    AnalyticsTrackRequest, AnalyticsSummaryRequest, ViewAnalyticsData, EngagementAnalyticsData,
    RSVPAnalyticsData, AnalyticsSummaryResponse,
    # PHASE 31: SEO, Social Sharing & Discovery
    SEOSettings,
    # PHASE 32: Security & Access Control
    CaptchaChallenge, CaptchaVerifyRequest, SubmissionAttempt,
    # PHASE 33: Monetization & Premium Plans
    UpdatePlanRequest, PlanInfoResponse, FeatureFlagsResponse,
    # PHASE 34: Payment & Plan Activation
    Payment, PaymentStatus, CreatePaymentOrderRequest, CreatePaymentOrderResponse,
    VerifyPaymentRequest, VerifyPaymentResponse, PaymentHistoryResponse,
    # PHASE 35: Referral, Credits & Viral Growth
    Referral, ReferralStatus, CreditTransaction, CreditTransactionType, CreditWallet,
    ReferralCodeResponse, ReferralStatsResponse, ApplyReferralRequest,
    CreditWalletResponse, SpendCreditsRequest, SpendCreditsResponse,
    CreditPricingConfig, AdminReferralOverrideRequest,
    # PHASE 34: Design System & Theme Engine
    ThemeSettings, ThemeUpdateRequest, ThemePreviewRequest,
    # PHASE 36: Template Marketplace & Creator Ecosystem
    Template, TemplateCreate, TemplateUpdate, TemplateResponse, TemplateListResponse,
    TemplateCategory, TemplateStatus, CreatorProfile, CreatorProfileCreate,
    CreatorProfileUpdate, CreatorProfileResponse, CreatorStatus, TemplatePurchase,
    TemplatePurchaseRequest, TemplatePurchaseResponse, TemplateReview, TemplateReviewRequest,
    AdminTemplateReviewRequest, AdminCreatorActionRequest, TemplateEarnings,
    TemplateStats, MarketplaceFilters
)
from auth import (
    get_password_hash, verify_password, 
    create_access_token, get_current_admin,
    get_current_admin_with_role, require_super_admin, require_admin
)
from design_registry import (
    get_all_designs, get_designs_by_event_type, 
    get_design_by_id, get_default_design_for_event,
    validate_design_for_event
)
from lord_library import (
    get_all_lords, get_lords_by_event_type,
    get_lord_by_id, get_default_lord,
    is_lord_allowed_for_event
)
# PHASE 26: AI-Powered Personalization
from ai_service import (
    ai_service, 
    check_translation_rate_limit, 
    check_admin_generation_rate_limit,
    SUPPORTED_LANGUAGES
)
# PHASE 32: Security & Access Control
from security_middleware import (
    SecurityHeadersMiddleware,
    BotDetectionMiddleware,
    AbusePreventionMiddleware
)
from access_control import (
    hash_passcode,
    validate_passcode_format,
    verify_passcode,
    check_event_access
)
# PHASE 33: Monetization & Premium Plans
from feature_gating import (
    has_feature,
    Feature,
    get_gallery_limit,
    get_feature_flags,
    requires_watermark,
    get_plan_info,
    PlanType
)
# PHASE 36: Template Marketplace & Creator Ecosystem
from template_validator import (
    validate_template,
    sanitize_template_for_storage,
    calculate_performance_score,
    TemplateValidationError
)
# PHASE 35: Credit Management Service
from credit_service import CreditService
import hashlib



ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# PHASE 35: Initialize Credit Service
credit_service = CreditService(db)

# PHASE 37: Initialize Wedding Lifecycle Service
from wedding_lifecycle_service import WeddingLifecycleService
wedding_lifecycle_service = WeddingLifecycleService(db, credit_service)

# PHASE 34: Razorpay Payment Gateway Client
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_PLACEHOLDER_KEY_ID')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'PLACEHOLDER_SECRET_KEY')

try:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    print("✅ Razorpay client initialized successfully")
except Exception as e:
    print(f"⚠️  Razorpay client initialization failed: {e}")
    print("⚠️  Payment features will not work until valid credentials are provided")
    razorpay_client = None


# Create the main app without a prefix
app = FastAPI()

# Create uploads directory
UPLOADS_DIR = Path("/app/uploads/photos")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files for serving uploaded photos
# Original mount at /uploads is kept for backward-compatibility with any code/tests
# that hit the backend directly. The /api/uploads mount is the one the Kubernetes
# ingress actually routes to (only /api/* paths reach the backend in production).
app.mount("/uploads", StaticFiles(directory="/app/uploads"), name="uploads")
app.mount("/api/uploads", StaticFiles(directory="/app/uploads"), name="api_uploads")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ===========================================================================
# 2026 — Universal Invitation Categories (Wedding + 4 new ceremony types)
# ===========================================================================
from invitation_categories import (
    InvitationCategory as _InvCat,
    get_all_categories as _ic_all,
    get_category as _ic_get,
    get_category_designs as _ic_designs,
    get_category_features as _ic_features,
    get_category_pricing as _ic_pricing,
    DEFAULT_CATEGORY_PRICING as _ic_default_pricing,
)


@api_router.get("/event-categories")
async def list_event_categories():
    """Public list of all invitation categories (wedding + ceremonies).

    Returned shape:
      { categories: [ { id, label, label_traditional, tagline, icon,
                        cover_preview, hero_gradient, primary_color,
                        accent_color, order } ] }
    """
    return {"categories": _ic_all()}


@api_router.get("/event-categories/{category_id}")
async def get_event_category(category_id: str):
    cat = _ic_get(category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return {
        **cat,
        "designs": _ic_designs(category_id),
        "features": _ic_features(category_id),
    }


@api_router.get("/event-categories/{category_id}/designs")
async def list_category_designs(category_id: str):
    if not _ic_get(category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    return {"designs": _ic_designs(category_id)}


@api_router.get("/event-categories/{category_id}/features")
async def list_category_features(category_id: str):
    if not _ic_get(category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    return {"features": _ic_features(category_id)}


@api_router.get("/event-categories/{category_id}/pricing")
async def get_event_category_pricing(category_id: str, user_type: str = "photographer"):
    """Returns credit cost configuration for a category and user type.

    Checks DB overrides first (event_category_pricing), then falls back to
    the in-memory defaults from invitation_categories.
    """
    if not _ic_get(category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    if user_type not in ("photographer", "normal_user"):
        raise HTTPException(status_code=400, detail="user_type must be photographer|normal_user")
    # 1. DB override
    override = await db.event_category_pricing.find_one(
        {"category_id": category_id, "user_type": user_type},
        {"_id": 0, "category_id": 0, "user_type": 0},
    )
    defaults = _ic_pricing(category_id, user_type)
    if override:
        # Merge: DB values win, but missing keys fall back to defaults.
        out = {
            "design_credits": override.get("design_credits", defaults.get("design_credits", 1)),
            "feature_credits": {
                **defaults.get("feature_credits", {}),
                **(override.get("feature_credits") or {}),
            },
        }
        return out
    return defaults


@api_router.get("/super-admin/event-categories/pricing")
async def super_admin_get_all_category_pricing():
    """Super-admin view: full pricing matrix for all non-wedding categories."""
    # In a future iteration we will read overrides from DB; for now return defaults.
    return _ic_default_pricing


class CategoryPricingUpdateBody(BaseModel):
    category_id: str
    user_type: str  # 'photographer' | 'normal_user'
    design_credits: Optional[int] = None
    feature_credits: Optional[Dict[str, int]] = None


@api_router.post("/super-admin/event-categories/pricing")
async def super_admin_update_category_pricing(body: CategoryPricingUpdateBody):
    """Update credit pricing for a non-wedding category. Persists to MongoDB."""
    if body.category_id not in _ic_default_pricing:
        raise HTTPException(status_code=400, detail="Unknown category_id")
    if body.user_type not in ("photographer", "normal_user"):
        raise HTTPException(status_code=400, detail="user_type must be photographer|normal_user")
    update_doc = {"category_id": body.category_id, "user_type": body.user_type}
    if body.design_credits is not None:
        update_doc["design_credits"] = body.design_credits
    if body.feature_credits is not None:
        update_doc["feature_credits"] = body.feature_credits
    # Upsert into a small collection so super-admin overrides are persisted.
    await db.event_category_pricing.update_one(
        {"category_id": body.category_id, "user_type": body.user_type},
        {"$set": update_doc},
        upsert=True,
    )
    # Update in-memory cache so subsequent reads reflect immediately.
    current = _ic_default_pricing.setdefault(body.category_id, {}).setdefault(body.user_type, {})
    if body.design_credits is not None:
        current["design_credits"] = body.design_credits
    if body.feature_credits is not None:
        current.setdefault("feature_credits", {}).update(body.feature_credits)
    return {"success": True, "pricing": current}


# ===========================================================================



# PHASE 29C: Standardized Error Response Helper
class ErrorResponse:
    """Standardized error response format"""
    
    @staticmethod
    def not_found(detail: str = "Resource not found"):
        """404 - Resource not found"""
        return HTTPException(
            status_code=404,
            detail={
                "error": "Not Found",
                "message": detail,
                "status_code": 404
            }
        )
    
    @staticmethod
    def expired(detail: str = "Resource has expired"):
        """410 - Resource expired/gone"""
        return HTTPException(
            status_code=410,
            detail={
                "error": "Expired",
                "message": detail,
                "status_code": 410
            }
        )
    
    @staticmethod
    def bad_request(detail: str = "Invalid request"):
        """400 - Bad request/validation error"""
        return HTTPException(
            status_code=400,
            detail={
                "error": "Bad Request",
                "message": detail,
                "status_code": 400
            }
        )
    
    @staticmethod
    def rate_limited(detail: str = "Too many requests"):
        """429 - Rate limit exceeded"""
        return HTTPException(
            status_code=429,
            detail={
                "error": "Too Many Requests",
                "message": detail,
                "status_code": 429
            }
        )
    
    @staticmethod
    def server_error(detail: str = "Internal server error"):
        """500 - Internal server error"""
        return HTTPException(
            status_code=500,
            detail={
                "error": "Internal Server Error",
                "message": detail,
                "status_code": 500
            }
        )


# Helper Functions
def generate_slug(groom_name: str, bride_name: str) -> str:
    """Generate unique URL slug from names"""
    # Take first names only and clean
    groom = re.sub(r'[^a-zA-Z]', '', groom_name.split()[0].lower())
    bride = re.sub(r'[^a-zA-Z]', '', bride_name.split()[0].lower())
    
    # Add random suffix
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    
    return f"{groom}-{bride}-{suffix}"


def calculate_expiry_date(expiry_type: str, expiry_value: Optional[int]) -> Optional[datetime]:
    """Calculate link expiry date"""
    now = datetime.now(timezone.utc)
    
    # Default to 30 days if not specified
    if not expiry_type or expiry_type == "days":
        days = expiry_value if expiry_value else 30
        return now + timedelta(days=days)
    elif expiry_type == "hours" and expiry_value:
        return now + timedelta(hours=expiry_value)
    
    return None


def calculate_invitation_expires_at(event_date: datetime, expires_at: Optional[datetime] = None) -> datetime:
    """Calculate invitation expiry date. Default: event_date + 7 days"""
    if expires_at:
        return expires_at
    
    # Ensure event_date is timezone-aware
    if event_date.tzinfo is None:
        event_date = event_date.replace(tzinfo=timezone.utc)
    
    # Default: wedding date + 7 days
    return event_date + timedelta(days=7)


async def check_profile_active(profile: dict) -> bool:
    """Check if profile is active and not expired"""
    if not profile:
        return False
    # If explicitly disabled, treat as inactive
    if profile.get('is_active') is False:
        return False
    # Check link_expiry_date if present
    expiry = profile.get('link_expiry_date') or profile.get('expires_at')
    if expiry:
        if isinstance(expiry, str):
            try:
                expiry = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
            except Exception:
                return True
        if getattr(expiry, 'tzinfo', None) is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expiry:
            return False
    return True



async def _track_invitation_view_audit(profile_id: str, client_ip: str):
    """Track invitation view for audit logs"""
    try:
        now = datetime.now(timezone.utc)
        
        # Increment view count
        await db.profiles.update_one(
            {"id": profile_id},
            {
                "$inc": {"view_count": 1},
                "$set": {"last_viewed_at": now}
            }
        )
        
        # Track unique visitors (simple IP-based tracking)
        visitor_key = f"{profile_id}_{client_ip}"
        visitor_exists = await db.invitation_visitors.find_one({"visitor_key": visitor_key})
        
        if not visitor_exists:
            await db.invitation_visitors.insert_one({
                "visitor_key": visitor_key,
                "profile_id": profile_id,
                "client_ip": client_ip,
                "first_visit": now,
                "last_visit": now
            })
            # Increment unique visitor count
            await db.profiles.update_one(
                {"id": profile_id},
                {"$inc": {"unique_visitors": 1}}
            )
        else:
            # Update last visit
            await db.invitation_visitors.update_one(
                {"visitor_key": visitor_key},
                {"$set": {"last_visit": now}}
            )
    except Exception as e:
        # Don't fail the request if tracking fails
        logger.error(f"Error tracking invitation view: {str(e)}")


# PHASE 35: Data Isolation Helper
def build_isolation_query(base_query: dict, admin_data: dict) -> dict:
    """
    Build query with data isolation for multi-tenant architecture
    Super Admin can access all data, regular Admins only their own
    """
    query = base_query.copy()
    
    # Super Admin bypass - can access all data
    if admin_data['role'] == 'super_admin':
        return query
    
    # Regular Admin - enforce data isolation
    query['admin_id'] = admin_data['admin_id']
    return query


async def check_profile_ownership(profile_id: str, admin_data, db) -> dict:
    """
    Check if admin owns the profile (or is Super Admin)
    Accepts either an admin_id string (from get_current_admin) or an admin dict.
    Returns profile if authorized, raises 404 if not found or unauthorized.
    """
    # Normalize to a dict with 'role' + 'admin_id'
    if isinstance(admin_data, str):
        admin_doc = await db.admins.find_one({"id": admin_data}) or {}
        admin_data = {"role": admin_doc.get("role", "admin"), "admin_id": admin_data}
    elif "admin_id" not in admin_data:
        admin_data = {"role": admin_data.get("role", "admin"), "admin_id": admin_data.get("id")}
    
    query = build_isolation_query({"id": profile_id}, admin_data)
    profile = await db.profiles.find_one(query, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return profile


async def check_profile_active_old(profile: dict) -> bool:
    """Check if profile is active and not expired"""
    if not profile.get('is_active', True):
        return False
    
    expiry_date = profile.get('link_expiry_date')
    if expiry_date:
        if isinstance(expiry_date, str):
            expiry_date = datetime.fromisoformat(expiry_date)
        
        # Ensure expiry_date is timezone-aware
        if expiry_date.tzinfo is None:
            expiry_date = expiry_date.replace(tzinfo=timezone.utc)
        
        if datetime.now(timezone.utc) > expiry_date:
            return False
    
    return True


def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    # Check for X-Forwarded-For header (from proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Get first IP if multiple are present
        return forwarded.split(",")[0].strip()
    
    # Fall back to direct client host
    return request.client.host if request.client else "unknown"


async def check_rate_limit(ip_address: str, endpoint: str, max_count: int) -> bool:
    """
    Check if IP has exceeded rate limit for endpoint
    Returns True if allowed, False if limit exceeded
    
    Args:
        ip_address: Client IP address
        endpoint: "rsvp" or "wishes"
        max_count: Maximum allowed submissions per day
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Find or create rate limit record
    rate_record = await db.rate_limits.find_one({
        "ip_address": ip_address,
        "endpoint": endpoint,
        "date": today
    }, {"_id": 0})
    
    if not rate_record:
        # Create new record
        new_record = RateLimit(
            ip_address=ip_address,
            endpoint=endpoint,
            date=today,
            count=1
        )
        doc = new_record.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.rate_limits.insert_one(doc)
        return True
    
    # Check if limit exceeded
    if rate_record['count'] >= max_count:
        return False


def generate_event_links(slug: str, events: List) -> Dict[str, str]:
    """
    PHASE 13: Generate event-specific invitation links
    
    Args:
        slug: Profile slug
        events: List of event dictionaries or WeddingEvent objects
    
    Returns:
        Dictionary mapping event_type to full invitation link
    """
    event_links = {}
    for event in events:
        # Handle both dict and WeddingEvent object
        if hasattr(event, 'event_type'):
            # WeddingEvent object - handle enum properly
            event_type_raw = event.event_type
            if hasattr(event_type_raw, 'value'):
                event_type = event_type_raw.value.lower()
            else:
                event_type = str(event_type_raw).lower()
            visible = getattr(event, 'visible', True)
        else:
            # Dictionary
            event_type = event.get('event_type', '').lower()
            visible = event.get('visible', True)
            
        if event_type and visible:
            event_links[event_type] = f"/invite/{slug}/{event_type}"
    return event_links


async def log_audit_action(
    action: str, 
    admin_id: str, 
    profile_id: Optional[str] = None,
    profile_slug: Optional[str] = None,
    details: Optional[dict] = None
):
    """
    Log admin action to audit log
    Automatically maintains last 1000 logs
    
    Args:
        action: Action type (profile_create, profile_update, profile_delete, profile_duplicate, template_save)
        admin_id: Admin user ID
        profile_id: Profile ID if applicable
        profile_slug: Profile slug if applicable
        details: Additional context like profile names
    """
    try:
        # Create audit log entry
        audit_log = AuditLog(
            action=action,
            admin_id=admin_id,
            profile_id=profile_id,
            profile_slug=profile_slug,
            details=details or {}
        )
        
        doc = audit_log.model_dump()
        doc['timestamp'] = doc['timestamp'].isoformat()
        
        # Insert log
        await db.audit_logs.insert_one(doc)
        
        # Maintain only last 1000 logs
        total_logs = await db.audit_logs.count_documents({})
        if total_logs > 1000:
            # Get the 1000th oldest log timestamp
            logs_to_keep = await db.audit_logs.find({}, {"_id": 0, "timestamp": 1}).sort("timestamp", -1).skip(999).limit(1).to_list(1)
            if logs_to_keep:
                cutoff_timestamp = logs_to_keep[0]['timestamp']
                # Delete all logs older than cutoff
                await db.audit_logs.delete_many({"timestamp": {"$lt": cutoff_timestamp}})
    
    except Exception as e:
        # Log error but don't fail the main operation
        logging.error(f"Failed to create audit log: {e}")





# HTML Sanitization
ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'a', 'h3', 'h4']
ALLOWED_ATTRIBUTES = {'a': ['href', 'title']}

def sanitize_html(html: str) -> str:
    """Sanitize HTML to prevent XSS attacks"""
    if not html:
        return html
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )


# File Upload Validation
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def validate_image_file(file: UploadFile) -> tuple[bool, str]:
    """Validate image file"""
    # Check extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, "Invalid file type. Allowed: JPG, PNG, WebP, GIF"
    
    # Check file size
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        return False, "File too large. Maximum size: 5MB"
    
    return True, ""


async def convert_to_webp(file: UploadFile, quality: int = 85) -> tuple[bytes, int]:
    """Convert image to WebP format and return bytes with size"""
    try:
        # Read image
        image_data = await file.read()
        img = PILImage.open(io.BytesIO(image_data))
        
        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = PILImage.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        
        # Resize if too large (max 1920px width)
        max_width = 1920
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), PILImage.Resampling.LANCZOS)
        
        # Convert to WebP
        output = io.BytesIO()
        img.save(output, format='WebP', quality=quality, optimize=True)
        webp_data = output.getvalue()
        
        return webp_data, len(webp_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")


# Mobile-perf: multi-size responsive WebP pipeline.
# Generates 320 / 640 / 1280 / original variants from a single upload, all WebP,
# preserves EXIF orientation, preserves aspect ratio (no crop). Returns paths
# + intrinsic dimensions so the frontend can render <picture srcset> + width/height
# without layout shift.
RESPONSIVE_WIDTHS = [
    ("small",  320),
    ("medium", 640),
    ("large",  1280),
]
RESPONSIVE_ORIGINAL_MAX = 1920  # cap for "original" variant to avoid 10MP files
RESPONSIVE_QUALITY = {
    "small":    78,
    "medium":   82,
    "large":    85,
    "original": 88,
}


async def convert_to_webp_responsive(
    file: UploadFile,
    out_dir: Path,
    base_name: str,
) -> Dict[str, Any]:
    """Generate small/medium/large/original WebP variants of an upload.

    Args:
        file:       FastAPI UploadFile (image)
        out_dir:    directory to write files into (must exist)
        base_name:  filename without extension. Variant suffix is appended:
                    {base_name}_small.webp, _medium.webp, _large.webp, .webp (= original)

    Returns dict with shape:
        {
          "small":    "/uploads/.../base_small.webp",
          "medium":   "/uploads/.../base_medium.webp",
          "large":    "/uploads/.../base_large.webp",
          "original": "/uploads/.../base.webp",
          "width":    intrinsic original width (after orientation fix, capped),
          "height":   intrinsic original height,
          "size":     bytes of original variant (legacy compat),
        }

    Paths returned are URL paths (prefixed with /uploads/...) — caller is
    responsible for passing out_dir that lives under /app/uploads.
    """
    try:
        raw = await file.read()
        img = PILImage.open(io.BytesIO(raw))

        # Preserve EXIF orientation (phones photograph sideways).
        from PIL import ImageOps as _ImageOps
        img = _ImageOps.exif_transpose(img)

        # Flatten alpha onto white for predictable WebP
        if img.mode in ('RGBA', 'LA', 'P'):
            bg = PILImage.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Cap original variant width
        orig = img
        if orig.width > RESPONSIVE_ORIGINAL_MAX:
            ratio = RESPONSIVE_ORIGINAL_MAX / orig.width
            new_h = int(orig.height * ratio)
            orig = orig.resize((RESPONSIVE_ORIGINAL_MAX, new_h), PILImage.Resampling.LANCZOS)

        out_dir.mkdir(parents=True, exist_ok=True)
        # Map filesystem dir -> URL prefix
        try:
            rel = out_dir.relative_to(Path("/app"))
            url_prefix = f"/{rel.as_posix()}"
        except Exception:
            url_prefix = f"/uploads/{out_dir.name}"

        variants: Dict[str, str] = {}
        # Original (capped)
        orig_path = out_dir / f"{base_name}.webp"
        with open(orig_path, "wb") as f:
            buf = io.BytesIO()
            orig.save(buf, format="WebP", quality=RESPONSIVE_QUALITY["original"], optimize=True)
            data = buf.getvalue()
            f.write(data)
        variants["original"] = f"{url_prefix}/{orig_path.name}"
        original_size = len(data)

        # Smaller variants — never upscale.
        for label, target_w in RESPONSIVE_WIDTHS:
            if target_w >= orig.width:
                # Source is already smaller than target — reuse original.
                variants[label] = variants["original"]
                continue
            ratio = target_w / orig.width
            new_h = max(1, int(orig.height * ratio))
            small = orig.resize((target_w, new_h), PILImage.Resampling.LANCZOS)
            sbuf = io.BytesIO()
            small.save(sbuf, format="WebP", quality=RESPONSIVE_QUALITY[label], optimize=True)
            sp = out_dir / f"{base_name}_{label}.webp"
            with open(sp, "wb") as fh:
                fh.write(sbuf.getvalue())
            variants[label] = f"{url_prefix}/{sp.name}"

        variants["width"]  = orig.width
        variants["height"] = orig.height
        variants["size"]   = original_size
        return variants
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")


# PHASE 25: Basic Profanity Filter
PROFANITY_WORDS = [
    'damn', 'hell', 'shit', 'fuck', 'ass', 'bitch', 'bastard', 'crap',
    'dick', 'piss', 'slut', 'whore', 'idiot', 'stupid', 'dumb'
]

def contains_profanity(text: str) -> bool:
    """Basic profanity filter check"""
    text_lower = text.lower()
    for word in PROFANITY_WORDS:
        if word in text_lower:
            return True
    return False


# ==================== AUTH ROUTES ====================

@api_router.post("/auth/login")
async def login(login_data: AdminLogin):
    """Admin login endpoint - supports both Super Admin and Admin.
    Accepts either email or username via `email` or `username_or_email`."""
    identifier = (login_data.username_or_email or login_data.email or "").strip()
    if not identifier:
        raise HTTPException(status_code=400, detail="Email or username is required")

    # Look up by email first, then by username (case-insensitive)
    admin = await db.admins.find_one({"email": identifier.lower()}, {"_id": 0})
    if not admin:
        admin = await db.admins.find_one({"username": identifier.lower()}, {"_id": 0})

    if not admin or not verify_password(login_data.password, admin['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials"
        )
    
    # PHASE 35: Check account status
    if admin.get('status') == AdminStatus.SUSPENDED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended. Please contact support."
        )
    
    if admin.get('status') == AdminStatus.INACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account inactive. Please contact support."
        )
    
    # PHASE 35: Include role in token
    access_token = create_access_token(data={
        "sub": admin['id'],
        "role": admin.get('role', AdminRole.ADMIN.value)
    })
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "admin": {
            "id": admin['id'],
            "email": admin['email'],
            "name": admin.get('name', admin['email']),
            "role": admin.get('role', AdminRole.ADMIN.value),
            "status": admin.get('status', AdminStatus.ACTIVE.value),
            "available_credits": admin.get('total_credits', 0) - admin.get('used_credits', 0)
        }
    }


@api_router.get("/auth/me", response_model=AdminResponse)
async def get_current_admin_info(admin_id: str = Depends(get_current_admin)):
    """Get current admin info"""
    admin = await db.admins.find_one({"id": admin_id}, {"_id": 0})
    
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    # Credits are stored as total_credits/used_credits — derive available_credits.
    total = admin.get("total_credits", 0) or 0
    used  = admin.get("used_credits", 0) or 0
    admin["available_credits"] = max(total - used, 0)
    
    return AdminResponse(**admin)


# ==================== PHOTOGRAPHER SELF-SIGNUP ====================

# In-memory OTP store: { phone: { otp, expires_at, attempts } }
# For dev/demo only — production must use Twilio + Redis.
_OTP_STORE: Dict[str, Dict[str, Any]] = {}
_OTP_TTL_SECONDS = 600  # 10 minutes
# DEV mode flag — when no SMS provider is configured AND DEV_MODE_OTP=1,
# return the OTP in the API response so signup still works locally.
_DEV_MODE_OTP = os.environ.get("DEV_MODE_OTP", "1") == "1"

from sms_service import send_otp_sms, sms_provider_status  # noqa: E402


def _generate_otp() -> str:
    return ''.join(random.choices(string.digits, k=6))


@api_router.post("/auth/send-otp")
async def auth_send_otp(payload: OTPSendRequest):
    """Send an OTP to a phone number for signup verification.

    Provider auto-selected from env (MSG91 > Twilio > dev mode). When no
    real provider is configured AND DEV_MODE_OTP=1 (default), the OTP is
    echoed back in the response so signup works without an SMS gateway."""
    phone = payload.phone
    otp = _generate_otp()
    _OTP_STORE[phone] = {
        "otp": otp,
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=_OTP_TTL_SECONDS),
        "attempts": 0,
    }
    # Attempt real SMS delivery
    delivery = send_otp_sms(phone, otp)
    real_provider = delivery.get("ok") and not delivery.get("dev_mode")
    if real_provider:
        logger.info("OTP sent to %s via %s", phone, delivery.get("provider"))
    else:
        logger.info("OTP for %s (dev fallback): %s", phone, otp)

    resp: Dict[str, Any] = {
        "success": True,
        "message": "OTP sent successfully",
        "provider": delivery.get("provider", "none"),
    }
    # Surface the OTP in the response ONLY when no real provider is wired
    # and DEV_MODE_OTP is enabled.  In production with MSG91/Twilio
    # configured, the OTP is never returned.
    if not real_provider and _DEV_MODE_OTP:
        resp["otp"] = otp
        resp["dev_mode"] = True
    return resp


@api_router.get("/auth/sms-status")
async def auth_sms_status():
    """Diagnostic — surface which SMS provider is currently active."""
    return sms_provider_status()


@api_router.post("/auth/verify-otp")
async def auth_verify_otp(payload: OTPVerifyRequest):
    """Verify a previously-issued phone OTP."""
    entry = _OTP_STORE.get(payload.phone)
    if not entry:
        raise HTTPException(status_code=400, detail="No OTP requested for this phone. Please send OTP first.")
    if datetime.now(timezone.utc) > entry["expires_at"]:
        _OTP_STORE.pop(payload.phone, None)
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
    entry["attempts"] += 1
    if entry["attempts"] > 5:
        _OTP_STORE.pop(payload.phone, None)
        raise HTTPException(status_code=429, detail="Too many incorrect attempts. Please request a new OTP.")
    if entry["otp"] != payload.otp:
        raise HTTPException(status_code=400, detail="Incorrect OTP")
    entry["verified"] = True
    return {"success": True, "verified": True}


def _is_phone_verified(phone: str) -> bool:
    entry = _OTP_STORE.get(phone)
    return bool(entry and entry.get("verified") and datetime.now(timezone.utc) <= entry["expires_at"])


@api_router.post("/auth/register")
async def auth_register_photographer(payload: PhotographerSignupRequest):
    """Photographer self-signup. Requires that the phone was previously verified
    via /api/auth/send-otp + /api/auth/verify-otp in the same OTP session."""

    if not _is_phone_verified(payload.phone):
        raise HTTPException(
            status_code=400,
            detail="Phone number not verified. Please verify your phone via OTP before signing up."
        )

    email_lower = payload.email.lower()
    username_lower = payload.username.lower()

    # Uniqueness checks
    if await db.admins.find_one({"email": email_lower}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await db.admins.find_one({"username": username_lower}):
        raise HTTPException(status_code=400, detail="Username already taken")
    if await db.admins.find_one({"phone": payload.phone}):
        raise HTTPException(status_code=400, detail="Phone number already registered")

    new_admin = Admin(
        email=email_lower,
        password_hash=get_password_hash(payload.password),
        name=payload.name,
        role=AdminRole.ADMIN,
        status=AdminStatus.ACTIVE,
        total_credits=0,
        used_credits=0,
        username=username_lower,
        phone=payload.phone,
        phone_verified=True,
        self_signup=True,
        created_by=None,
    )
    await db.admins.insert_one(new_admin.model_dump())

    # Clear OTP entry
    _OTP_STORE.pop(payload.phone, None)

    # Auto-login: issue access token immediately so user lands in dashboard
    access_token = create_access_token(data={
        "sub": new_admin.id,
        "role": AdminRole.ADMIN.value,
    })
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "admin": {
            "id": new_admin.id,
            "email": new_admin.email,
            "name": new_admin.name,
            "username": new_admin.username,
            "phone": new_admin.phone,
            "phone_verified": True,
            "role": AdminRole.ADMIN.value,
            "status": AdminStatus.ACTIVE.value,
            "available_credits": 0,
        }
    }


# ==================== END PHOTOGRAPHER SELF-SIGNUP ====================



# ==================== PHASE 35: SUPER ADMIN ROUTES ====================

@api_router.post("/super-admin/admins", response_model=AdminResponse)
async def create_admin_account(
    admin_data: AdminRegister,
    super_admin_id: str = Depends(require_super_admin)
):
    """PHASE 35: Create a new Admin (Photographer) account - Super Admin only"""
    
    # Check if email already exists
    existing_admin = await db.admins.find_one({"email": admin_data.email})
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new admin
    new_admin = Admin(
        email=admin_data.email,
        password_hash=get_password_hash(admin_data.password),
        name=admin_data.name,
        role=AdminRole.ADMIN,  # Always create as regular Admin
        status=AdminStatus.ACTIVE,
        total_credits=admin_data.initial_credits,
        used_credits=0,
        created_by=super_admin_id
    )
    
    await db.admins.insert_one(new_admin.model_dump())
    
    # Create ledger entry if initial credits > 0
    if admin_data.initial_credits > 0:
        await credit_service.add_credits(
            admin_id=new_admin.id,
            amount=admin_data.initial_credits,
            reason="Initial credits on account creation",
            performed_by=super_admin_id,
            metadata={"event": "account_creation"}
        )
    
    return AdminResponse(
        id=new_admin.id,
        email=new_admin.email,
        name=new_admin.name,
        role=new_admin.role,
        status=new_admin.status,
        total_credits=new_admin.total_credits,
        used_credits=new_admin.used_credits,
        available_credits=new_admin.available_credits,
        created_at=new_admin.created_at,
        created_by=new_admin.created_by
    )


@api_router.get("/super-admin/admins", response_model=List[AdminResponse])
async def get_all_admins(
    super_admin_id: str = Depends(require_super_admin),
    status_filter: Optional[str] = None
):
    """PHASE 35: Get all Admin accounts - Super Admin only"""
    
    # Build filter
    query = {"role": AdminRole.ADMIN.value}  # Exclude other Super Admins
    if status_filter:
        query["status"] = status_filter
    
    # Get all admins
    admins = await db.admins.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Format response
    admin_list = []
    for admin in admins:
        admin_list.append(AdminResponse(
            id=admin['id'],
            email=admin['email'],
            name=admin.get('name', admin['email']),
            role=admin.get('role', AdminRole.ADMIN.value),
            status=admin.get('status', AdminStatus.ACTIVE.value),
            total_credits=admin.get('total_credits', 0),
            used_credits=admin.get('used_credits', 0),
            available_credits=admin.get('total_credits', 0) - admin.get('used_credits', 0),
            username=admin.get('username'),
            phone=admin.get('phone'),
            phone_verified=admin.get('phone_verified', False),
            created_at=admin['created_at'],
            created_by=admin.get('created_by')
        ))
    
    return admin_list


@api_router.post("/super-admin/credits/add")
async def add_credits_to_admin(
    request: AddCreditsRequest,
    super_admin_id: str = Depends(require_super_admin)
):
    """PHASE 35: Add credits to an Admin account - Super Admin only"""
    
    try:
        result = await credit_service.add_credits(
            admin_id=request.admin_id,
            amount=request.amount,
            reason=request.reason,
            performed_by=super_admin_id,
            metadata={"action": "super_admin_add"}
        )
        
        return {
            "success": True,
            "message": f"Successfully added {request.amount} credits",
            **result
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add credits: {str(e)}"
        )


@api_router.post("/super-admin/credits/deduct")
async def deduct_credits_from_admin(
    request: DeductCreditsRequest,
    super_admin_id: str = Depends(require_super_admin)
):
    """PHASE 35: Deduct credits from an Admin account - Super Admin only"""
    
    try:
        result = await credit_service.deduct_credits(
            admin_id=request.admin_id,
            amount=request.amount,
            reason=request.reason,
            performed_by=super_admin_id,
            metadata={"action": "super_admin_deduct"}
        )
        
        return {
            "success": True,
            "message": f"Successfully deducted {request.amount} credits",
            **result
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deduct credits: {str(e)}"
        )


@api_router.get("/super-admin/credits/ledger/{admin_id}", response_model=List[CreditLedgerResponse])
async def get_admin_credit_ledger(
    admin_id: str,
    super_admin_id: str = Depends(require_super_admin),
    limit: int = 100,
    skip: int = 0
):
    """PHASE 35: Get credit transaction history for an Admin - Super Admin only"""
    
    try:
        result = await credit_service.get_credit_ledger(
            admin_id=admin_id,
            limit=limit,
            skip=skip
        )
        
        # Convert to response model
        ledger_entries = []
        for entry in result['entries']:
            ledger_entries.append(CreditLedgerResponse(
                credit_id=entry['credit_id'],
                admin_id=entry['admin_id'],
                action_type=entry['action_type'],
                amount=entry['amount'],
                balance_before=entry['balance_before'],
                balance_after=entry['balance_after'],
                reason=entry['reason'],
                related_wedding_id=entry.get('related_wedding_id'),
                performed_by=entry['performed_by'],
                created_at=entry['created_at'],
                metadata=entry.get('metadata')
            ))
        
        return ledger_entries
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve ledger: {str(e)}"
        )


class _AdminStatusBody(BaseModel):
    """Body shape accepted by /super-admin/admins/{id}/status — keeps the
    super-admin UI's `axios.put(..., { status: 'suspended' })` working
    without forcing the frontend to always send a query-string."""
    status: AdminStatus


@api_router.put("/super-admin/admins/{admin_id}/status")
async def update_admin_status(
    admin_id: str,
    body: Optional[_AdminStatusBody] = None,
    status: Optional[AdminStatus] = None,
    super_admin_id: str = Depends(require_super_admin)
):
    """PHASE 35: Update Admin account status - Super Admin only.
    Accepts EITHER:
      - query string: `?status=active|suspended|inactive`
      - JSON body:    `{ "status": "active" }`
    The body wins when both are provided. This fix removes a 422 the user
    hit because the frontend always sent JSON.
    """
    # Resolve the requested status from whichever transport the caller used
    new_status_enum = (body.status if body else None) or status
    if new_status_enum is None:
        raise HTTPException(
            status_code=422,
            detail="Missing 'status' — pass either ?status=… or JSON body {status: …}",
        )

    # Check if admin exists (use numeric codes — `status` arg shadows the fastapi.status import)
    admin = await db.admins.find_one({"id": admin_id})
    if not admin:
        raise HTTPException(
            status_code=404,
            detail="Admin not found"
        )

    # Prevent modifying Super Admin accounts
    if admin.get('role') == AdminRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Cannot modify Super Admin accounts"
        )

    # Update status
    await db.admins.update_one(
        {"id": admin_id},
        {"$set": {"status": new_status_enum.value}}
    )

    return {
        "success": True,
        "message": f"Admin status updated to {new_status_enum.value}",
        "admin_id": admin_id,
        "new_status": new_status_enum.value
    }


# ==================== PHASE 35: ADMIN CREDIT ROUTES ====================

@api_router.get("/admin/credits", response_model=CreditBalanceResponse)
async def get_own_credit_balance(admin_data: dict = Depends(require_admin)):
    """PHASE 35: Get own credit balance - Read-only for Admins"""
    
    try:
        balance = await credit_service.get_credit_balance(admin_data['admin_id'])
        
        return CreditBalanceResponse(
            total_credits=balance['total_credits'],
            used_credits=balance['used_credits'],
            available_credits=balance['available_credits']
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve balance: {str(e)}"
        )


@api_router.get("/admin/credits/ledger", response_model=List[CreditLedgerResponse])
async def get_own_credit_ledger(
    admin_data: dict = Depends(require_admin),
    limit: int = 50,
    skip: int = 0
):
    """PHASE 35: Get own credit transaction history - Admins can view their own ledger"""
    
    try:
        result = await credit_service.get_credit_ledger(
            admin_id=admin_data['admin_id'],
            limit=limit,
            skip=skip
        )
        
        # Convert to response model
        ledger_entries = []
        for entry in result['entries']:
            ledger_entries.append(CreditLedgerResponse(
                credit_id=entry['credit_id'],
                admin_id=entry['admin_id'],
                action_type=entry['action_type'],
                amount=entry['amount'],
                balance_before=entry['balance_before'],
                balance_after=entry['balance_after'],
                reason=entry['reason'],
                related_wedding_id=entry.get('related_wedding_id'),
                performed_by=entry['performed_by'],
                created_at=entry['created_at'],
                metadata=entry.get('metadata')
            ))
        
        return ledger_entries
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve ledger: {str(e)}"
        )


# ==================== ADMIN - PROFILE ROUTES ====================

@api_router.get("/admin/profiles", response_model=List[ProfileResponse])
async def get_all_profiles(admin_data: dict = Depends(require_admin)):
    """Get all profiles (excluding templates) - PHASE 35: Data isolation enforced"""
    admin_id = admin_data['admin_id']
    role = admin_data['role']
    
    # PHASE 35: Data isolation - Admins see only their data, Super Admin sees all
    query = {"is_template": {"$ne": True}}
    if role != 'super_admin':
        query['admin_id'] = admin_id
    
    profiles = await db.profiles.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Convert date strings back to datetime
    for profile in profiles:
        if isinstance(profile.get('event_date'), str):
            profile['event_date'] = datetime.fromisoformat(profile['event_date'])
        if isinstance(profile.get('created_at'), str):
            profile['created_at'] = datetime.fromisoformat(profile['created_at'])
        if isinstance(profile.get('updated_at'), str):
            profile['updated_at'] = datetime.fromisoformat(profile['updated_at'])
        if profile.get('link_expiry_date') and isinstance(profile['link_expiry_date'], str):
            profile['link_expiry_date'] = datetime.fromisoformat(profile['link_expiry_date'])
        if profile.get('expires_at') and isinstance(profile['expires_at'], str):
            profile['expires_at'] = datetime.fromisoformat(profile['expires_at'])
        
        # Add invitation link
        profile['invitation_link'] = f"/invite/{profile['slug']}"
        
        # PHASE 13: Generate event-specific links
        profile['event_links'] = generate_event_links(profile['slug'], profile.get('events', []))
    
    return profiles


@api_router.post("/admin/profiles", response_model=ProfileResponse)
async def create_profile(
    profile_data: ProfileCreate,
    on_behalf_of: Optional[str] = None,
    admin_data: dict = Depends(require_admin),
):
    """Create new profile - PHASE 35: Auto-assign admin_id.
    Super-admins may pass ?on_behalf_of=<photographer_admin_id> to create
    an invitation under that photographer's account.
    """
    admin_id = admin_data['admin_id']

    # Super-admin impersonation: create under a specific photographer
    if on_behalf_of and admin_data.get('role') == 'super_admin':
        target = await db.admins.find_one({"id": on_behalf_of, "role": "admin"}, {"_id": 0, "id": 1})
        if not target:
            raise HTTPException(status_code=404, detail="Photographer not found")
        admin_id = on_behalf_of
    
    # Generate unique slug
    slug = generate_slug(profile_data.groom_name, profile_data.bride_name)
    
    # Check if slug exists (rare but possible)
    while await db.profiles.find_one({"slug": slug}):
        slug = generate_slug(profile_data.groom_name, profile_data.bride_name)
    
    # Calculate expiry date
    expiry_date = calculate_expiry_date(
        profile_data.link_expiry_type,
        profile_data.link_expiry_value
    )
    
    # Calculate invitation expiry (PHASE 12: default event_date + 7 days)
    invitation_expires_at = calculate_invitation_expires_at(
        profile_data.event_date,
        profile_data.expires_at
    )
    
    # Sanitize HTML fields
    about_couple = sanitize_html(profile_data.about_couple) if profile_data.about_couple else None
    family_details = sanitize_html(profile_data.family_details) if profile_data.family_details else None
    love_story = sanitize_html(profile_data.love_story) if profile_data.love_story else None
    
    # Create profile object
    profile = Profile(
        admin_id=admin_id,  # PHASE 35: Owner admin ID
        slug=slug,
        groom_name=profile_data.groom_name,
        bride_name=profile_data.bride_name,
        event_type=profile_data.event_type,
        event_date=profile_data.event_date,
        venue=profile_data.venue,
        city=profile_data.city,
        invitation_message=profile_data.invitation_message,
        language=profile_data.language,
        design_id=profile_data.design_id,
        deity_id=profile_data.deity_id,
        whatsapp_groom=profile_data.whatsapp_groom,
        whatsapp_bride=profile_data.whatsapp_bride,
        enabled_languages=profile_data.enabled_languages,
        custom_text=profile_data.custom_text,
        about_couple=about_couple,
        family_details=family_details,
        love_story=love_story,
        bride_photo_url=profile_data.bride_photo_url,
        groom_photo_url=profile_data.groom_photo_url,
        couple_photo_url=profile_data.couple_photo_url,
        bride_about=sanitize_html(profile_data.bride_about) if profile_data.bride_about else None,
        groom_about=sanitize_html(profile_data.groom_about) if profile_data.groom_about else None,
        cover_photo_id=profile_data.cover_photo_id,
        show_couple_photo=getattr(profile_data, 'show_couple_photo', True),
        show_bride_photo=getattr(profile_data, 'show_bride_photo', True),
        show_groom_photo=getattr(profile_data, 'show_groom_photo', True),
        use_couple_photo_as_opening_bg=getattr(profile_data, 'use_couple_photo_as_opening_bg', True),
        opening_bg_source=getattr(profile_data, 'opening_bg_source', 'couple') or 'couple',
        opening_photo_url=getattr(profile_data, 'opening_photo_url', None),
        sections_enabled=profile_data.sections_enabled,
        background_music=profile_data.background_music,
        map_settings=profile_data.map_settings,
        events=profile_data.events,
        # July 2025 — defensive access. ProfileCreate now includes these
        # fields but use getattr() so older callers / tests that pass a
        # subset still survive instead of 500-ing on AttributeError.
        guest_rooms=getattr(profile_data, 'guest_rooms', None) or [],
        pre_wedding_links=getattr(profile_data, 'pre_wedding_links', None) or [],
        rsvp_settings=getattr(profile_data, 'rsvp_settings', None) or RSVPSettings(),  # Phase 1C
        honeymoon_fund=getattr(profile_data, 'honeymoon_fund', None) or HoneymoonFund(),  # Phase 1H
        link_expiry_type=profile_data.link_expiry_type,
        link_expiry_value=profile_data.link_expiry_value,
        link_expiry_date=expiry_date,
        expires_at=invitation_expires_at,
        # 2026 — Universal Invitation Categories
        invitation_category=getattr(profile_data, 'invitation_category', None) or "wedding",
        celebrant_info=getattr(profile_data, 'celebrant_info', None),
        design_selections=getattr(profile_data, 'design_selections', None) or {},
    )
    
    # Convert to dict and serialize dates
    doc = profile.model_dump()
    doc['event_date'] = doc['event_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc['link_expiry_date']:
        doc['link_expiry_date'] = doc['link_expiry_date'].isoformat()
    if doc['expires_at']:
        doc['expires_at'] = doc['expires_at'].isoformat()
    
    await db.profiles.insert_one(doc)
    
    # PHASE 12 - PART 5: Audit log
    await log_audit_action(
        action="profile_create",
        admin_id=admin_id,
        profile_id=profile.id,
        profile_slug=profile.slug,
        details={
            "groom_name": profile_data.groom_name,
            "bride_name": profile_data.bride_name,
            "event_type": profile_data.event_type
        }
    )
    
    # Prepare response
    response_data = profile.model_dump()
    response_data['invitation_link'] = f"/invite/{profile.slug}"
    
    # PHASE 13: Generate event-specific links
    response_data['event_links'] = generate_event_links(profile.slug, profile_data.events)
    
    return ProfileResponse(**response_data)


@api_router.get("/admin/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: str, admin_data: dict = Depends(require_admin)):
    """Get single profile - PHASE 35: Data isolation enforced"""
    admin_id = admin_data['admin_id']
    role = admin_data['role']
    
    # PHASE 35: Data isolation query
    query = {"id": profile_id}
    if role != 'super_admin':
        query['admin_id'] = admin_id
    
    profile = await db.profiles.find_one(query, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Convert date strings
    if isinstance(profile.get('event_date'), str):
        profile['event_date'] = datetime.fromisoformat(profile['event_date'])
    if isinstance(profile.get('created_at'), str):
        profile['created_at'] = datetime.fromisoformat(profile['created_at'])
    if isinstance(profile.get('updated_at'), str):
        profile['updated_at'] = datetime.fromisoformat(profile['updated_at'])
    if profile.get('link_expiry_date') and isinstance(profile['link_expiry_date'], str):
        profile['link_expiry_date'] = datetime.fromisoformat(profile['link_expiry_date'])
    if profile.get('expires_at') and isinstance(profile['expires_at'], str):
        profile['expires_at'] = datetime.fromisoformat(profile['expires_at'])
    
    profile['invitation_link'] = f"/invite/{profile['slug']}"
    
    # PHASE 13: Generate event-specific links
    profile['event_links'] = generate_event_links(profile['slug'], profile.get('events', []))
    
    return ProfileResponse(**profile)


@api_router.put("/admin/profiles/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: str,
    update_data: ProfileUpdate,
    admin_data: dict = Depends(require_admin)
):
    """Update profile - PHASE 35: Data isolation enforced"""
    admin_id = admin_data['admin_id']
    role = admin_data['role']
    
    # PHASE 35: Data isolation query
    query = {"id": profile_id}
    if role != 'super_admin':
        query['admin_id'] = admin_id
    
    existing_profile = await db.profiles.find_one(query, {"_id": 0})
    
    if not existing_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Prepare update
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Sanitize HTML fields if present
    if 'about_couple' in update_dict and update_dict['about_couple']:
        update_dict['about_couple'] = sanitize_html(update_dict['about_couple'])
    if 'family_details' in update_dict and update_dict['family_details']:
        update_dict['family_details'] = sanitize_html(update_dict['family_details'])
    if 'love_story' in update_dict and update_dict['love_story']:
        update_dict['love_story'] = sanitize_html(update_dict['love_story'])
    # Bride / Groom mini-bios — sanitize too (these surface on the public page)
    if 'bride_about' in update_dict and update_dict['bride_about']:
        update_dict['bride_about'] = sanitize_html(update_dict['bride_about'])
    if 'groom_about' in update_dict and update_dict['groom_about']:
        update_dict['groom_about'] = sanitize_html(update_dict['groom_about'])
    
    # Recalculate expiry if changed
    if 'link_expiry_type' in update_dict or 'link_expiry_value' in update_dict:
        expiry_type = update_dict.get('link_expiry_type', existing_profile['link_expiry_type'])
        expiry_value = update_dict.get('link_expiry_value', existing_profile.get('link_expiry_value'))
        update_dict['link_expiry_date'] = calculate_expiry_date(expiry_type, expiry_value)
    
    # PHASE 12: Recalculate invitation expiry if event_date or expires_at changed
    if 'event_date' in update_dict or 'expires_at' in update_dict:
        event_date_for_calc = update_dict.get('event_date', existing_profile.get('event_date'))
        if isinstance(event_date_for_calc, str):
            event_date_for_calc = datetime.fromisoformat(event_date_for_calc)
        expires_at = update_dict.get('expires_at')
        update_dict['expires_at'] = calculate_invitation_expires_at(event_date_for_calc, expires_at)
    
    # Update timestamp
    update_dict['updated_at'] = datetime.now(timezone.utc)
    
    # Serialize dates
    if 'event_date' in update_dict:
        update_dict['event_date'] = update_dict['event_date'].isoformat()
    update_dict['updated_at'] = update_dict['updated_at'].isoformat()
    if 'link_expiry_date' in update_dict and update_dict['link_expiry_date']:
        update_dict['link_expiry_date'] = update_dict['link_expiry_date'].isoformat()
    if 'expires_at' in update_dict and update_dict['expires_at']:
        update_dict['expires_at'] = update_dict['expires_at'].isoformat()
    
    await db.profiles.update_one(
        {"id": profile_id},
        {"$set": update_dict}
    )
    
    # Get updated profile
    updated_profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    
    # PHASE 12 - PART 5: Audit log
    await log_audit_action(
        action="profile_update",
        admin_id=admin_id,
        profile_id=profile_id,
        profile_slug=updated_profile.get('slug'),
        details={
            "updated_fields": list(update_data.model_dump(exclude_unset=True).keys()),
            "groom_name": updated_profile.get('groom_name'),
            "bride_name": updated_profile.get('bride_name')
        }
    )
    
    # PHASE 29E: Save version snapshot on major updates
    # Detect if this is a "publish" action (significant update)
    updated_fields = update_data.model_dump(exclude_unset=True).keys()
    major_fields = {'groom_name', 'bride_name', 'event_date', 'venue', 'events', 'sections_enabled'}
    is_major_update = bool(major_fields.intersection(updated_fields))
    
    if is_major_update:
        await save_profile_version(profile_id, admin_id, "publish")
    
    # Convert dates back
    if isinstance(updated_profile.get('event_date'), str):
        updated_profile['event_date'] = datetime.fromisoformat(updated_profile['event_date'])
    if isinstance(updated_profile.get('created_at'), str):
        updated_profile['created_at'] = datetime.fromisoformat(updated_profile['created_at'])
    if isinstance(updated_profile.get('updated_at'), str):
        updated_profile['updated_at'] = datetime.fromisoformat(updated_profile['updated_at'])
    if updated_profile.get('link_expiry_date') and isinstance(updated_profile['link_expiry_date'], str):
        updated_profile['link_expiry_date'] = datetime.fromisoformat(updated_profile['link_expiry_date'])
    if updated_profile.get('expires_at') and isinstance(updated_profile['expires_at'], str):
        updated_profile['expires_at'] = datetime.fromisoformat(updated_profile['expires_at'])
    
    updated_profile['invitation_link'] = f"/invite/{updated_profile['slug']}"
    
    # PHASE 13: Generate event-specific links
    updated_profile['event_links'] = generate_event_links(updated_profile['slug'], updated_profile.get('events', []))
    
    return ProfileResponse(**updated_profile)


@api_router.delete("/admin/profiles/{profile_id}")
async def delete_profile(profile_id: str, admin_data: dict = Depends(require_admin)):
    """Delete profile (soft delete) - PHASE 35: Data isolation enforced"""
    admin_id = admin_data['admin_id']
    
    # PHASE 35: Check ownership
    profile = await check_profile_ownership(profile_id, admin_data, db)
    
    result = await db.profiles.update_one(
        {"id": profile_id},
        {"$set": {"is_active": False}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # PHASE 12 - PART 5: Audit log
    await log_audit_action(
        action="profile_delete",
        admin_id=admin_id,
        profile_id=profile_id,
        profile_slug=profile.get('slug'),
        details={
            "groom_name": profile.get('groom_name'),
            "bride_name": profile.get('bride_name')
        }
    )
    
    return {"message": "Profile deleted successfully"}



# PHASE 32: Admin Action Security - Disable/Enable/Expire Invitation Endpoints
@api_router.put("/admin/profiles/{profile_id}/disable")
async def disable_profile(profile_id: str, admin_data: dict = Depends(require_admin)):
    """
    PHASE 32: Disable invitation (make it inaccessible) - PHASE 35: Data isolation enforced
    Guests cannot view the invitation when disabled
    Can be re-enabled later
    """
    admin_id = admin_data['admin_id']
    
    # PHASE 35: Check ownership
    profile = await check_profile_ownership(profile_id, admin_data, db)
    
    result = await db.profiles.update_one(
        {"id": profile_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Audit log
    await log_audit_action(
        action="profile_disable",
        admin_id=admin_id,
        profile_id=profile_id,
        profile_slug=profile.get('slug'),
        details={
            "groom_name": profile.get('groom_name'),
            "bride_name": profile.get('bride_name'),
            "action": "disable_invitation"
        }
    )
    
    return {"message": "Invitation disabled successfully", "is_active": False}


@api_router.put("/admin/profiles/{profile_id}/enable")
async def enable_profile(profile_id: str, admin_id: str = Depends(get_current_admin)):
    """
    PHASE 32: Re-enable previously disabled invitation
    Makes invitation accessible again
    """
    profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    result = await db.profiles.update_one(
        {"id": profile_id},
        {"$set": {"is_active": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Audit log
    await log_audit_action(
        action="profile_enable",
        admin_id=admin_id,
        profile_id=profile_id,
        profile_slug=profile.get('slug'),
        details={
            "groom_name": profile.get('groom_name'),
            "bride_name": profile.get('bride_name'),
            "action": "enable_invitation"
        }
    )
    
    return {"message": "Invitation enabled successfully", "is_active": True, "share_link": profile.get('slug'), "slug": profile.get('slug')}


@api_router.put("/admin/profiles/{profile_id}/expire")
async def expire_profile(profile_id: str, admin_id: str = Depends(get_current_admin)):
    """
    PHASE 32: Expire invitation (mark as past event)
    Sets expires_at to now, making invitation inactive
    Typically done after event is over
    """
    profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Set expires_at to current time
    now = datetime.now(timezone.utc)
    result = await db.profiles.update_one(
        {"id": profile_id},
        {"$set": {
            "expires_at": now.isoformat(),
            "updated_at": now.isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Audit log
    await log_audit_action(
        action="profile_expire",
        admin_id=admin_id,
        profile_id=profile_id,
        profile_slug=profile.get('slug'),
        details={
            "groom_name": profile.get('groom_name'),
            "bride_name": profile.get('bride_name'),
            "action": "expire_invitation",
            "expired_at": now.isoformat()
        }
    )
    
    return {"message": "Invitation expired successfully", "expires_at": now.isoformat()}


@api_router.put("/admin/profiles/{profile_id}/unexpire")
async def unexpire_profile(profile_id: str, admin_id: str = Depends(get_current_admin)):
    """
    PHASE 32: Remove expiration from invitation
    Useful if invitation was expired by mistake
    """
    profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Calculate new expiry based on event date (30 days after event)
    event_date = profile.get('event_date')
    if isinstance(event_date, str):
        event_date = datetime.fromisoformat(event_date)
    
    new_expires_at = event_date + timedelta(days=30) if event_date else None
    
    result = await db.profiles.update_one(
        {"id": profile_id},
        {"$set": {
            "expires_at": new_expires_at.isoformat() if new_expires_at else None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Audit log
    await log_audit_action(
        action="profile_unexpire",
        admin_id=admin_id,
        profile_id=profile_id,
        profile_slug=profile.get('slug'),
        details={
            "groom_name": profile.get('groom_name'),
            "bride_name": profile.get('bride_name'),
            "action": "unexpire_invitation",
            "new_expires_at": new_expires_at.isoformat() if new_expires_at else None
        }
    )
    
    return {"message": "Invitation expiration removed successfully", "expires_at": new_expires_at.isoformat() if new_expires_at else None}


@api_router.post("/admin/profiles/{profile_id}/duplicate", response_model=ProfileResponse)
async def duplicate_profile(profile_id: str, admin_id: str = Depends(get_current_admin)):
    """Duplicate an existing profile with new slug and appended (Copy) to names"""
    # Fetch the original profile
    original_profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    
    if not original_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Convert date strings back to datetime objects
    if isinstance(original_profile.get('event_date'), str):
        original_profile['event_date'] = datetime.fromisoformat(original_profile['event_date'])
    if isinstance(original_profile.get('created_at'), str):
        original_profile['created_at'] = datetime.fromisoformat(original_profile['created_at'])
    if isinstance(original_profile.get('updated_at'), str):
        original_profile['updated_at'] = datetime.fromisoformat(original_profile['updated_at'])
    if original_profile.get('link_expiry_date') and isinstance(original_profile['link_expiry_date'], str):
        original_profile['link_expiry_date'] = datetime.fromisoformat(original_profile['link_expiry_date'])
    if original_profile.get('expires_at') and isinstance(original_profile['expires_at'], str):
        original_profile['expires_at'] = datetime.fromisoformat(original_profile['expires_at'])
    
    # Create new profile data from original
    new_profile_data = original_profile.copy()
    
    # Generate new unique ID and slug
    new_profile_data['id'] = str(uuid.uuid4())
    
    # Append "(Copy)" to groom and bride names
    new_profile_data['groom_name'] = f"{original_profile['groom_name']} (Copy)"
    new_profile_data['bride_name'] = f"{original_profile['bride_name']} (Copy)"
    
    # Generate unique slug with new names
    slug = generate_slug(new_profile_data['groom_name'], new_profile_data['bride_name'])
    while await db.profiles.find_one({"slug": slug}):
        slug = generate_slug(new_profile_data['groom_name'], new_profile_data['bride_name'])
    new_profile_data['slug'] = slug
    
    # Reset timestamps
    now = datetime.now(timezone.utc)
    new_profile_data['created_at'] = now
    new_profile_data['updated_at'] = now
    
    # Recalculate expiry dates
    expiry_date = calculate_expiry_date(
        new_profile_data.get('link_expiry_type', 'days'),
        new_profile_data.get('link_expiry_value', 30)
    )
    new_profile_data['link_expiry_date'] = expiry_date
    
    invitation_expires_at = calculate_invitation_expires_at(
        new_profile_data['event_date'],
        None  # Will use default: event_date + 7 days
    )
    new_profile_data['expires_at'] = invitation_expires_at
    
    # Copy media references (photos will reference same media items)
    # Note: Media items themselves are not duplicated, only references in the profile
    
    # Serialize dates for MongoDB
    new_profile_data['event_date'] = new_profile_data['event_date'].isoformat()
    new_profile_data['created_at'] = new_profile_data['created_at'].isoformat()
    new_profile_data['updated_at'] = new_profile_data['updated_at'].isoformat()
    if new_profile_data['link_expiry_date']:
        new_profile_data['link_expiry_date'] = new_profile_data['link_expiry_date'].isoformat()
    if new_profile_data['expires_at']:
        new_profile_data['expires_at'] = new_profile_data['expires_at'].isoformat()
    
    # Insert the duplicated profile
    await db.profiles.insert_one(new_profile_data)
    
    # PHASE 12 - PART 5: Audit log
    await log_audit_action(
        action="profile_duplicate",
        admin_id=admin_id,
        profile_id=new_profile_data['id'],
        profile_slug=new_profile_data['slug'],
        details={
            "original_profile_id": profile_id,
            "original_slug": original_profile['slug'],
            "groom_name": new_profile_data['groom_name'],
            "bride_name": new_profile_data['bride_name']
        }
    )
    
    # Prepare response with datetime objects
    response_data = new_profile_data.copy()
    response_data['event_date'] = datetime.fromisoformat(response_data['event_date'])
    response_data['created_at'] = datetime.fromisoformat(response_data['created_at'])
    response_data['updated_at'] = datetime.fromisoformat(response_data['updated_at'])
    if response_data['link_expiry_date']:
        response_data['link_expiry_date'] = datetime.fromisoformat(response_data['link_expiry_date'])
    if response_data['expires_at']:
        response_data['expires_at'] = datetime.fromisoformat(response_data['expires_at'])
    
    response_data['invitation_link'] = f"/invite/{response_data['slug']}"
    
    return ProfileResponse(**response_data)


# ==================== ADMIN - TEMPLATE ROUTES ====================

@api_router.post("/admin/profiles/{profile_id}/save-as-template", response_model=ProfileResponse)
async def save_profile_as_template(profile_id: str, admin_id: str = Depends(get_current_admin)):
    """Save an existing profile as a template"""
    # Fetch the profile
    profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Update the profile to mark it as a template
    await db.profiles.update_one(
        {"id": profile_id},
        {"$set": {"is_template": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # PHASE 12 - PART 5: Audit log
    await log_audit_action(
        action="template_save",
        admin_id=admin_id,
        profile_id=profile_id,
        profile_slug=profile.get('slug'),
        details={
            "groom_name": profile.get('groom_name'),
            "bride_name": profile.get('bride_name')
        }
    )
    
    # Fetch updated profile
    updated_profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    
    # Convert date strings back to datetime
    if isinstance(updated_profile.get('event_date'), str):
        updated_profile['event_date'] = datetime.fromisoformat(updated_profile['event_date'])
    if isinstance(updated_profile.get('created_at'), str):
        updated_profile['created_at'] = datetime.fromisoformat(updated_profile['created_at'])
    if isinstance(updated_profile.get('updated_at'), str):
        updated_profile['updated_at'] = datetime.fromisoformat(updated_profile['updated_at'])
    if updated_profile.get('link_expiry_date') and isinstance(updated_profile['link_expiry_date'], str):
        updated_profile['link_expiry_date'] = datetime.fromisoformat(updated_profile['link_expiry_date'])
    if updated_profile.get('expires_at') and isinstance(updated_profile['expires_at'], str):
        updated_profile['expires_at'] = datetime.fromisoformat(updated_profile['expires_at'])
    
    updated_profile['invitation_link'] = f"/invite/{updated_profile['slug']}"
    
    return ProfileResponse(**updated_profile)


@api_router.get("/admin/templates", response_model=List[ProfileResponse])
async def get_all_templates(admin_id: str = Depends(get_current_admin)):
    """Get all template profiles"""
    templates = await db.profiles.find({"is_template": True}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Convert date strings back to datetime
    for template in templates:
        if isinstance(template.get('event_date'), str):
            template['event_date'] = datetime.fromisoformat(template['event_date'])
        if isinstance(template.get('created_at'), str):
            template['created_at'] = datetime.fromisoformat(template['created_at'])
        if isinstance(template.get('updated_at'), str):
            template['updated_at'] = datetime.fromisoformat(template['updated_at'])
        if template.get('link_expiry_date') and isinstance(template['link_expiry_date'], str):
            template['link_expiry_date'] = datetime.fromisoformat(template['link_expiry_date'])
        if template.get('expires_at') and isinstance(template['expires_at'], str):
            template['expires_at'] = datetime.fromisoformat(template['expires_at'])
        
        # Add invitation link
        template['invitation_link'] = f"/invite/{template['slug']}"
    
    return templates


@api_router.post("/admin/profiles/from-template/{template_id}", response_model=ProfileResponse)
async def create_profile_from_template(template_id: str, admin_id: str = Depends(get_current_admin)):
    """Create a new profile from a template"""
    # Fetch the template
    template = await db.profiles.find_one({"id": template_id, "is_template": True}, {"_id": 0})
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Convert date strings back to datetime objects
    if isinstance(template.get('event_date'), str):
        template['event_date'] = datetime.fromisoformat(template['event_date'])
    if isinstance(template.get('created_at'), str):
        template['created_at'] = datetime.fromisoformat(template['created_at'])
    if isinstance(template.get('updated_at'), str):
        template['updated_at'] = datetime.fromisoformat(template['updated_at'])
    if template.get('link_expiry_date') and isinstance(template['link_expiry_date'], str):
        template['link_expiry_date'] = datetime.fromisoformat(template['link_expiry_date'])
    if template.get('expires_at') and isinstance(template['expires_at'], str):
        template['expires_at'] = datetime.fromisoformat(template['expires_at'])
    
    # Create new profile data from template
    new_profile_data = template.copy()
    
    # Generate new unique ID and slug
    new_profile_data['id'] = str(uuid.uuid4())
    
    # Keep the template names but allow editing later
    # Generate unique slug
    slug = generate_slug(template['groom_name'], template['bride_name'])
    while await db.profiles.find_one({"slug": slug}):
        slug = generate_slug(template['groom_name'], template['bride_name'])
    new_profile_data['slug'] = slug
    
    # Mark as NOT a template (this is a real profile created from template)
    new_profile_data['is_template'] = False
    
    # Reset timestamps
    now = datetime.now(timezone.utc)
    new_profile_data['created_at'] = now
    new_profile_data['updated_at'] = now
    
    # Recalculate expiry dates
    expiry_date = calculate_expiry_date(
        new_profile_data.get('link_expiry_type', 'days'),
        new_profile_data.get('link_expiry_value', 30)
    )
    new_profile_data['link_expiry_date'] = expiry_date
    
    invitation_expires_at = calculate_invitation_expires_at(
        new_profile_data['event_date'],
        None  # Will use default: event_date + 7 days
    )
    new_profile_data['expires_at'] = invitation_expires_at
    
    # Serialize dates for MongoDB
    new_profile_data['event_date'] = new_profile_data['event_date'].isoformat()
    new_profile_data['created_at'] = new_profile_data['created_at'].isoformat()
    new_profile_data['updated_at'] = new_profile_data['updated_at'].isoformat()
    if new_profile_data['link_expiry_date']:
        new_profile_data['link_expiry_date'] = new_profile_data['link_expiry_date'].isoformat()
    if new_profile_data['expires_at']:
        new_profile_data['expires_at'] = new_profile_data['expires_at'].isoformat()
    
    # Insert the new profile
    await db.profiles.insert_one(new_profile_data)
    
    # Prepare response with datetime objects
    response_data = new_profile_data.copy()
    response_data['event_date'] = datetime.fromisoformat(response_data['event_date'])
    response_data['created_at'] = datetime.fromisoformat(response_data['created_at'])
    response_data['updated_at'] = datetime.fromisoformat(response_data['updated_at'])
    if response_data['link_expiry_date']:
        response_data['link_expiry_date'] = datetime.fromisoformat(response_data['link_expiry_date'])
    if response_data['expires_at']:
        response_data['expires_at'] = datetime.fromisoformat(response_data['expires_at'])
    
    response_data['invitation_link'] = f"/invite/{response_data['slug']}"
    
    return ProfileResponse(**response_data)



# ==================== BRANDED QR HELPERS ====================

_THEME_PRIMARY_COLOR_MAP = {
    "royal_mughal":         "#7B1E1E",
    "south_indian_temple":  "#B8860B",
    "bengali_aristocracy":  "#8B0000",
    "punjabi_grandeur":     "#FFB700",
    "kerala_backwaters":    "#0A7C5A",
    "rajasthani":           "#C2185B",
    "maharashtrian":        "#8B5E3C",
    "muslim_nikah":         "#0E7C4F",
    "minimal_modern":       "#1F1F1F",
    "nature_garden":        "#3F6B2A",
}


def _theme_primary_color(design_id: Optional[str]) -> str:
    if not design_id:
        return "#7B1E1E"
    return _THEME_PRIMARY_COLOR_MAP.get(design_id, "#7B1E1E")


def _couple_monogram(profile: Dict[str, Any]) -> str:
    g = (profile.get("groom_name") or "").strip()
    b = (profile.get("bride_name") or "").strip()
    initials = ""
    if g:
        initials += g[0].upper()
    if b:
        initials += b[0].upper()
    return initials or "✦"


def _hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except Exception:
        return (123, 30, 30)


def _build_branded_qr(
    payload: str,
    monogram: str = "",
    primary_hex: str = "#7B1E1E",
    background_image_bytes: Optional[bytes] = None,
) -> str:
    """Generate a QR with a couple-monogram + theme-color accent ring in the center.
    Optionally composites the QR on top of a background photo (the couple's
    cover photo by default) with a soft cream gradient veil so cells stay readable.

    Returns a data:image/png;base64 string ready for <img src=...>.
    """
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    qr = qrcode.QRCode(
        version=4,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    primary_rgb = _hex_to_rgb(primary_hex)
    # Render QR cells as fully transparent on white so we can composite over a photo.
    qr_layer = qr.make_image(fill_color=(14, 10, 6), back_color=(255, 255, 255)).convert("RGBA")
    w, h = qr_layer.size

    # Build the canvas: photo background (if provided) + cream veil, then QR cells
    base = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    if background_image_bytes:
        try:
            photo = Image.open(BytesIO(background_image_bytes)).convert("RGB")
            # Cover-crop to QR canvas size
            ratio = max(w / photo.width, h / photo.height)
            nw, nh = int(photo.width * ratio), int(photo.height * ratio)
            photo = photo.resize((nw, nh), Image.LANCZOS)
            left = (nw - w) // 2
            top = (nh - h) // 2
            photo = photo.crop((left, top, left + w, top + h))
            # Gentle blur so it doesn't compete with QR cells
            photo = photo.filter(ImageFilter.GaussianBlur(radius=3))
            base = photo.convert("RGBA")
            # Cream veil for QR contrast — tuned for readability vs photo visibility
            veil = Image.new("RGBA", (w, h), (255, 248, 230, 165))
            base = Image.alpha_composite(base, veil)
        except Exception as e:
            logger.warning(f"QR background composite failed, falling back to white: {e}")

    # Drop the white pixels from the QR layer so only the dark cells remain
    qr_pixels = qr_layer.load()
    for y in range(h):
        for x in range(w):
            r, g, b, _a = qr_pixels[x, y]
            if r > 200 and g > 200 and b > 200:
                qr_pixels[x, y] = (255, 255, 255, 0)
            else:
                qr_pixels[x, y] = (14, 10, 6, 255)
    canvas = Image.alpha_composite(base, qr_layer)

    # Centerpiece — accent ring + cream disc + monogram
    overlay = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    cx, cy = w // 2, h // 2
    badge_r = int(min(w, h) * 0.16)
    ring_r = badge_r + max(6, int(badge_r * 0.18))

    draw.ellipse(
        (cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r),
        fill=(*primary_rgb, 255),
    )
    draw.ellipse(
        (cx - badge_r, cy - badge_r, cx + badge_r, cy + badge_r),
        fill=(255, 248, 230, 255),
    )

    label = monogram or "✦"
    font_size = int(badge_r * 1.1)
    font = None
    for cand in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            font = ImageFont.truetype(cand, font_size)
            break
        except Exception:
            font = None
    if font is None:
        font = ImageFont.load_default()
    try:
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = cx - tw // 2 - bbox[0]
        ty = cy - th // 2 - bbox[1]
    except Exception:
        tw, th = (badge_r, badge_r)
        tx, ty = cx - tw // 2, cy - th // 2
    draw.text((tx, ty), label, fill=(*primary_rgb, 255), font=font)

    composed = Image.alpha_composite(canvas, overlay).convert("RGB")
    buf = BytesIO()
    composed.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


async def _load_qr_background_bytes(profile: Dict[str, Any]) -> Optional[bytes]:
    """Resolve which media to use as the QR background and fetch its bytes.

    Resolution order:
      1. If `use_couple_photo_as_qr_bg` is True (default) → couple_photo_url
         from custom_text._maja, or cover_photo_id.
      2. Else → qr_background_media_id OR custom_text._maja.qr_background_photo_url.
      3. Last-resort fallback → couple_photo_url / cover_photo_id.
    """
    maja = (profile.get("custom_text") or {}).get("_maja") or {}
    use_couple = profile.get("use_couple_photo_as_qr_bg", True)

    candidate_urls = []
    candidate_media_ids = []
    if use_couple:
        if maja.get("couple_photo_url"):
            candidate_urls.append(maja["couple_photo_url"])
        if profile.get("cover_photo_id"):
            candidate_media_ids.append(profile["cover_photo_id"])
    else:
        if maja.get("qr_background_photo_url"):
            candidate_urls.append(maja["qr_background_photo_url"])
        if profile.get("qr_background_media_id"):
            candidate_media_ids.append(profile["qr_background_media_id"])

    # last-resort fallback: try the couple photo / cover even if toggle is off
    if maja.get("couple_photo_url"):
        candidate_urls.append(maja["couple_photo_url"])
    if profile.get("cover_photo_id"):
        candidate_media_ids.append(profile["cover_photo_id"])

    async def _bytes_from_url(url: str) -> Optional[bytes]:
        try:
            if url.startswith("/"):
                local = Path("/app") / url.lstrip("/")
                if local.exists():
                    return local.read_bytes()
                # Also try frontend's public/ dir
                alt = Path("/app/frontend/public") / url.lstrip("/")
                if alt.exists():
                    return alt.read_bytes()
            if url.startswith("http"):
                import httpx
                async with httpx.AsyncClient(timeout=10) as c:
                    r = await c.get(url)
                    if r.status_code == 200:
                        return r.content
        except Exception as e:
            logger.warning(f"QR bg URL fetch failed for {url}: {e}")
        return None

    for url in candidate_urls:
        b = await _bytes_from_url(url)
        if b:
            return b

    for media_id in candidate_media_ids:
        try:
            media = await db.profile_media.find_one({"id": media_id}, {"_id": 0})
            if not media:
                continue
            url = media.get("media_url") or media.get("file_url") or media.get("url")
            if url:
                b = await _bytes_from_url(url)
                if b:
                    return b
        except Exception as e:
            logger.warning(f"QR bg media lookup failed for {media_id}: {e}")
    return None




# ==================== ADMIN - EVENT INVITATION ROUTES ====================

@api_router.get("/admin/profiles/{profile_id}/event-invitations", response_model=List[EventInvitationResponse])
async def get_profile_event_invitations(profile_id: str, admin_id: str = Depends(get_current_admin)):
    """Get all event invitations for a profile"""
    # Check if profile exists
    profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    # Ownership check — admin can only access invitations on profiles they own (super_admin bypasses)
    if profile.get("admin_id") and profile["admin_id"] != admin_id:
        requester = await db.admins.find_one({"id": admin_id}, {"_id": 0, "role": 1})
        if not requester or requester.get("role") != AdminRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="You do not have access to this profile")
    
    # Get all event invitations for this profile
    event_invitations = await db.event_invitations.find(
        {"profile_id": profile_id}, 
        {"_id": 0}
    ).to_list(100)
    
    # Lazy-generate QR for old invitations missing one (created before QR feature)
    public_base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    bg_bytes_cached = None  # load once per profile
    for ei in event_invitations:
        if not ei.get("qr_image"):
            try:
                if bg_bytes_cached is None:
                    bg_bytes_cached = await _load_qr_background_bytes(profile)
                link_path = f"/invite/{profile['slug']}/{ei['event_type']}"
                qr_target = f"{public_base}{link_path}" if public_base else link_path
                ei["qr_image"] = _build_branded_qr(
                    payload=qr_target,
                    monogram=_couple_monogram(profile),
                    primary_hex=_theme_primary_color(ei.get("design_id")),
                    background_image_bytes=bg_bytes_cached,
                )
                ei["qr_url"] = qr_target
                await db.event_invitations.update_one(
                    {"id": ei["id"]},
                    {"$set": {"qr_image": ei["qr_image"], "qr_url": qr_target}},
                )
            except Exception as e:
                logger.warning(f"Lazy QR generation failed for {ei.get('id')}: {e}")
    
    # Convert datetime strings back to datetime objects and add invitation_link
    for ei in event_invitations:
        if isinstance(ei.get('created_at'), str):
            ei['created_at'] = datetime.fromisoformat(ei['created_at'])
        if isinstance(ei.get('updated_at'), str):
            ei['updated_at'] = datetime.fromisoformat(ei['updated_at'])
        if isinstance(ei.get('expires_at'), str):
            try:
                ei['expires_at'] = datetime.fromisoformat(ei['expires_at'])
            except Exception:
                ei['expires_at'] = None
        
        # Generate invitation link
        ei['invitation_link'] = f"/invite/{profile['slug']}/{ei['event_type']}"
    
    return [EventInvitationResponse(**ei) for ei in event_invitations]


@api_router.post("/admin/profiles/{profile_id}/event-invitations", response_model=EventInvitationResponse)
async def create_event_invitation(
    profile_id: str,
    event_data: EventInvitationCreate,
    admin_id: str = Depends(get_current_admin)
):
    """Create a new event-specific invitation link for a profile"""
    # Check if profile exists
    profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    # Ownership check
    if profile.get("admin_id") and profile["admin_id"] != admin_id:
        requester = await db.admins.find_one({"id": admin_id}, {"_id": 0, "role": 1})
        if not requester or requester.get("role") != AdminRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="You do not have access to this profile")
    
    # Check if event invitation already exists for this event_type
    existing = await db.event_invitations.find_one({
        "profile_id": profile_id,
        "event_type": event_data.event_type
    })
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Event invitation for {event_data.event_type} already exists"
        )
    
    # Apply deity validation rules based on event_type
    deity_id = event_data.deity_id
    if event_data.event_type in ['haldi', 'mehendi']:
        # Force deity_id to None for Haldi/Mehendi
        deity_id = None
    
    # Compute expiry: explicit if provided, else event_date + 7d, else +30d
    expires_at = event_data.expires_at
    if expires_at is None:
        event_date = profile.get("event_date")
        if isinstance(event_date, str):
            try:
                event_date = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
            except Exception:
                event_date = None
        if isinstance(event_date, datetime):
            base = event_date if event_date.tzinfo else event_date.replace(tzinfo=timezone.utc)
            expires_at = base + timedelta(days=7)
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    # Create event invitation
    event_invitation = EventInvitation(
        profile_id=profile_id,
        event_type=event_data.event_type,
        design_id=event_data.design_id,
        deity_id=deity_id,
        enabled=True,
        expires_at=expires_at,
    )
    
    # Serialize to dict and convert datetime to ISO format
    doc = event_invitation.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('expires_at') is not None:
        doc['expires_at'] = doc['expires_at'].isoformat()
    # event_type is already serialized to string by model_dump (use_enum_values=True)
    if hasattr(doc.get('event_type'), 'value'):
        doc['event_type'] = doc['event_type'].value
    
    # Insert into database
    await db.event_invitations.insert_one(doc)

    # === AI Photo Delivery integration (best-effort, never blocks the API) ===
    invitation_link_path = f"/invite/{profile['slug']}/{doc['event_type']}"
    qr_image_b64 = None
    rekognition_collection_id = None
    public_base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    qr_target = f"{public_base}{invitation_link_path}" if public_base else invitation_link_path
    try:
        bg_bytes = await _load_qr_background_bytes(profile)
        qr_image_b64 = _build_branded_qr(
            payload=qr_target,
            monogram=_couple_monogram(profile),
            primary_hex=_theme_primary_color(event_data.design_id),
            background_image_bytes=bg_bytes,
        )
    except Exception as qr_err:
        logger.warning(f"Branded QR generation failed for {event_invitation.id}: {qr_err}")
        qr_image_b64 = None

    # If AWS is configured, ensure a per-event Rekognition face collection exists.
    try:
        from aws_service import is_configured as aws_is_configured, create_face_collection
        if aws_is_configured():
            rekognition_collection_id = f"ei_{event_invitation.id.replace('-', '')[:60]}"
            create_face_collection(rekognition_collection_id)
    except Exception as rek_err:
        logger.warning(f"Rekognition collection creation skipped for invitation {event_invitation.id}: {rek_err}")
        rekognition_collection_id = None

    # Persist QR + Rekognition metadata
    qr_doc = {
        "qr_url": qr_target,
        "qr_image": qr_image_b64,
        "rekognition_collection_id": rekognition_collection_id,
    }
    await db.event_invitations.update_one({"id": event_invitation.id}, {"$set": qr_doc})

    # Prepare response
    response_data = doc.copy()
    response_data['created_at'] = datetime.fromisoformat(response_data['created_at'])
    response_data['updated_at'] = datetime.fromisoformat(response_data['updated_at'])
    if response_data.get('expires_at') and isinstance(response_data['expires_at'], str):
        response_data['expires_at'] = datetime.fromisoformat(response_data['expires_at'])
    response_data['invitation_link'] = invitation_link_path
    response_data.update(qr_doc)
    
    return EventInvitationResponse(**response_data)


@api_router.put("/admin/event-invitations/{invitation_id}", response_model=EventInvitationResponse)
async def update_event_invitation(
    invitation_id: str,
    update_data: EventInvitationUpdate,
    admin_id: str = Depends(get_current_admin)
):
    """Update an event invitation"""
    # Find the event invitation
    event_invitation = await db.event_invitations.find_one({"id": invitation_id}, {"_id": 0})
    if not event_invitation:
        raise HTTPException(status_code=404, detail="Event invitation not found")
    
    # Get profile for slug + ownership check
    profile = await db.profiles.find_one({"id": event_invitation['profile_id']}, {"_id": 0, "slug": 1, "admin_id": 1})
    if profile and profile.get("admin_id") and profile["admin_id"] != admin_id:
        requester = await db.admins.find_one({"id": admin_id}, {"_id": 0, "role": 1})
        if not requester or requester.get("role") != AdminRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="You do not have access to this profile")
    
    # Prepare update data
    update_dict = {}
    if update_data.design_id is not None:
        update_dict['design_id'] = update_data.design_id
    if update_data.deity_id is not None:
        # Apply deity validation rules based on event_type
        if event_invitation['event_type'] in ['haldi', 'mehendi']:
            # Force deity_id to None for Haldi/Mehendi
            update_dict['deity_id'] = None
        else:
            update_dict['deity_id'] = update_data.deity_id
    if update_data.enabled is not None:
        update_dict['enabled'] = update_data.enabled
        # Re-enabling a previously expired link extends its life
        if update_data.enabled and event_invitation.get('expired'):
            update_dict['expired'] = False
    if update_data.expires_at is not None:
        update_dict['expires_at'] = update_data.expires_at.isoformat() if isinstance(update_data.expires_at, datetime) else update_data.expires_at
        update_dict['expired'] = False  # rescheduling un-expires
    
    update_dict['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # Update in database
    await db.event_invitations.update_one(
        {"id": invitation_id},
        {"$set": update_dict}
    )
    
    # Fetch updated document
    updated = await db.event_invitations.find_one({"id": invitation_id}, {"_id": 0})
    
    # Convert datetime strings
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    if isinstance(updated.get('updated_at'), str):
        updated['updated_at'] = datetime.fromisoformat(updated['updated_at'])
    if isinstance(updated.get('expires_at'), str):
        try:
            updated['expires_at'] = datetime.fromisoformat(updated['expires_at'])
        except Exception:
            updated['expires_at'] = None
    
    updated['invitation_link'] = f"/invite/{profile['slug']}/{updated['event_type']}"
    
    return EventInvitationResponse(**updated)


@api_router.delete("/admin/event-invitations/{invitation_id}")
async def delete_event_invitation(invitation_id: str, admin_id: str = Depends(get_current_admin)):
    """Delete an event invitation, and purge its Rekognition collection + R2 media."""
    invitation = await db.event_invitations.find_one({"id": invitation_id}, {"_id": 0})
    if not invitation:
        raise HTTPException(status_code=404, detail="Event invitation not found")
    # Ownership check via parent profile
    profile = await db.profiles.find_one({"id": invitation["profile_id"]}, {"_id": 0, "admin_id": 1})
    if profile and profile.get("admin_id") and profile["admin_id"] != admin_id:
        requester = await db.admins.find_one({"id": admin_id}, {"_id": 0, "role": 1})
        if not requester or requester.get("role") != AdminRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="You do not have access to this profile")

    # Best-effort cleanup of associated AI face collection + media
    await _purge_invitation_assets(invitation)

    result = await db.event_invitations.delete_one({"id": invitation_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event invitation not found")
    
    return {"message": "Event invitation deleted successfully"}


async def _purge_invitation_assets(invitation: Dict[str, Any]) -> Dict[str, Any]:
    """Delete an invitation's media + AI face collection. Safe to call repeatedly."""
    summary: Dict[str, Any] = {"rekognition": False, "media_files_deleted": 0}
    # 1. Drop Rekognition face collection (if AWS configured)
    coll = invitation.get("rekognition_collection_id")
    if coll:
        try:
            from aws_service import is_configured as aws_is_configured, delete_face_collection, delete_prefix
            if aws_is_configured():
                summary["rekognition"] = bool(delete_face_collection(coll))
                # Drop any photos uploaded to this invitation's S3/R2 prefix
                try:
                    delete_prefix(f"event-invitations/{invitation['id']}/")
                except Exception as e:
                    logger.warning(f"R2 prefix delete failed: {e}")
        except Exception as e:
            logger.warning(f"Rekognition cleanup skipped: {e}")
    # 2. Delete profile_media docs referencing this invitation
    try:
        m_result = await db.profile_media.delete_many({"event_invitation_id": invitation["id"]})
        summary["media_files_deleted"] = m_result.deleted_count
    except Exception as e:
        logger.warning(f"profile_media cleanup failed: {e}")
    # 3. Delete face_matches index entries
    try:
        await db.face_matches.delete_many({"event_invitation_id": invitation["id"]})
    except Exception:
        pass
    return summary


async def _expiry_sweep_once() -> Dict[str, int]:
    """Run one pass: disable expired invitations and purge their media."""
    now = datetime.now(timezone.utc)
    disabled = 0
    purged = 0
    cursor = db.event_invitations.find(
        {
            "expires_at": {"$ne": None, "$lte": now.isoformat()},
            "$or": [{"expired": {"$ne": True}}, {"media_purged": {"$ne": True}}],
        },
        {"_id": 0},
    )
    async for inv in cursor:
        if not inv.get("expired"):
            await db.event_invitations.update_one(
                {"id": inv["id"]},
                {"$set": {"expired": True, "enabled": False, "updated_at": now.isoformat()}},
            )
            disabled += 1
        if not inv.get("media_purged"):
            await _purge_invitation_assets(inv)
            await db.event_invitations.update_one(
                {"id": inv["id"]},
                {"$set": {"media_purged": True, "purged_at": now.isoformat()}},
            )
            purged += 1
    if disabled or purged:
        logger.info(f"Expiry sweep: disabled={disabled} purged={purged}")
    return {"disabled": disabled, "purged": purged}


async def _expiry_sweep_loop():
    """Background loop — wakes every hour and reconciles expired invitations."""
    while True:
        try:
            await _expiry_sweep_once()
        except Exception as e:
            logger.error(f"Expiry sweep loop error: {e}")
        await asyncio.sleep(int(os.environ.get("EXPIRY_SWEEP_INTERVAL_SECONDS", "3600")))


@api_router.post("/admin/event-invitations/sweep-expired")
async def sweep_expired_now(admin_id: str = Depends(require_super_admin)):
    """Manual trigger for the expiry sweep (super admin only)."""
    return await _expiry_sweep_once()


@api_router.post("/admin/event-invitations/{invitation_id}/regenerate-qr")
async def regenerate_qr(invitation_id: str, admin_id: str = Depends(get_current_admin)):
    """Rebuild the QR for one invitation — picks up new couple-photo / background-photo settings."""
    inv = await db.event_invitations.find_one({"id": invitation_id}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Event invitation not found")
    profile = await db.profiles.find_one({"id": inv["profile_id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    # Ownership check
    if profile.get("admin_id") and profile["admin_id"] != admin_id:
        requester = await db.admins.find_one({"id": admin_id}, {"_id": 0, "role": 1})
        if not requester or requester.get("role") != AdminRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="You do not have access to this profile")

    public_base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    link_path = f"/invite/{profile['slug']}/{inv['event_type']}"
    qr_target = f"{public_base}{link_path}" if public_base else link_path
    bg_bytes = await _load_qr_background_bytes(profile)
    qr_image_b64 = _build_branded_qr(
        payload=qr_target,
        monogram=_couple_monogram(profile),
        primary_hex=_theme_primary_color(inv.get("design_id")),
        background_image_bytes=bg_bytes,
    )
    await db.event_invitations.update_one(
        {"id": invitation_id},
        {"$set": {"qr_image": qr_image_b64, "qr_url": qr_target,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"qr_url": qr_target, "qr_image": qr_image_b64, "used_background": bool(bg_bytes)}


@api_router.post("/admin/profiles/{profile_id}/regenerate-all-qrs")
async def regenerate_all_qrs(profile_id: str, admin_id: str = Depends(get_current_admin)):
    """Rebuild every invitation's QR for a profile — used after the couple photo / QR-bg settings change."""
    profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.get("admin_id") and profile["admin_id"] != admin_id:
        requester = await db.admins.find_one({"id": admin_id}, {"_id": 0, "role": 1})
        if not requester or requester.get("role") != AdminRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="You do not have access to this profile")
    bg_bytes = await _load_qr_background_bytes(profile)
    monogram = _couple_monogram(profile)
    public_base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    n = 0
    async for inv in db.event_invitations.find({"profile_id": profile_id}, {"_id": 0}):
        link_path = f"/invite/{profile['slug']}/{inv['event_type']}"
        qr_target = f"{public_base}{link_path}" if public_base else link_path
        try:
            qr_image_b64 = _build_branded_qr(
                payload=qr_target,
                monogram=monogram,
                primary_hex=_theme_primary_color(inv.get("design_id")),
                background_image_bytes=bg_bytes,
            )
            await db.event_invitations.update_one(
                {"id": inv["id"]},
                {"$set": {"qr_image": qr_image_b64, "qr_url": qr_target,
                          "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
            n += 1
        except Exception as e:
            logger.warning(f"regenerate QR failed for {inv.get('id')}: {e}")
    return {"regenerated": n, "used_background": bool(bg_bytes)}


# ==================== PHASE 32: EVENT SECURITY SETTINGS ====================

@api_router.put("/admin/event-invitations/{invitation_id}/security")
async def update_event_security(
    invitation_id: str,
    visibility_mode: str = Form(...),
    passcode: Optional[str] = Form(None),
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 32: Update security settings for an event invitation
    
    Args:
        invitation_id: Event invitation ID
        visibility_mode: "public", "unlisted", or "private"
        passcode: 4-6 digit numeric passcode (required if private, optional to clear)
        admin_id: Current admin ID (from auth)
    
    Returns:
        Updated event invitation with security settings
    """
    # Validate visibility mode
    if visibility_mode not in ["public", "unlisted", "private"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid visibility_mode. Must be 'public', 'unlisted', or 'private'"
        )
    
    # Find the event invitation
    event_invitation = await db.event_invitations.find_one({"id": invitation_id}, {"_id": 0})
    if not event_invitation:
        raise HTTPException(status_code=404, detail="Event invitation not found")
    
    # Prepare update
    update_dict = {
        "visibility_mode": visibility_mode,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Handle passcode based on visibility mode
    if visibility_mode == "private":
        # Private mode requires passcode
        if not passcode or passcode.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="Passcode is required for private events"
            )
        
        # Validate passcode format
        if not validate_passcode_format(passcode):
            raise HTTPException(
                status_code=400,
                detail="Passcode must be 4-6 digits numeric only"
            )
        
        # Hash and store passcode
        update_dict["access_passcode_hash"] = hash_passcode(passcode)
        logger.info(f"Setting passcode for event {invitation_id}")
    else:
        # Public/unlisted mode - clear passcode if exists
        update_dict["access_passcode_hash"] = None
        logger.info(f"Clearing passcode for event {invitation_id} (mode: {visibility_mode})")
    
    # Update in database
    await db.event_invitations.update_one(
        {"id": invitation_id},
        {"$set": update_dict}
    )
    
    # Also update events array in profile
    profile = await db.profiles.find_one({"id": event_invitation['profile_id']}, {"_id": 0})
    if profile and 'events' in profile:
        events = profile['events']
        for event in events:
            if event.get('event_id') == event_invitation.get('event_id'):
                event['visibility_mode'] = visibility_mode
                event['access_passcode_hash'] = update_dict["access_passcode_hash"]
                break
        
        await db.profiles.update_one(
            {"id": event_invitation['profile_id']},
            {"$set": {"events": events}}
        )
    
    # Fetch updated event invitation
    updated = await db.event_invitations.find_one({"id": invitation_id}, {"_id": 0})
    
    # Convert datetime strings
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    if isinstance(updated.get('updated_at'), str):
        updated['updated_at'] = datetime.fromisoformat(updated['updated_at'])
    
    # Add invitation link
    if profile:
        updated['invitation_link'] = f"/invite/{profile['slug']}/{updated['event_type']}"
    
    return EventInvitationResponse(**updated)



# ==================== PHASE 17: EVENT-LEVEL CMS CRUD ROUTES ====================

@api_router.post("/admin/profiles/{profile_id}/events")
async def create_event(
    profile_id: str,
    event: WeddingEvent,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 17: Create a new event for a profile
    
    Features:
    - Auto-generates slug if not provided
    - Validates event-type specific required fields
    - Prevents duplicate event types per profile
    - Validates language_enabled list
    """
    # Check if profile exists
    profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Get existing events
    existing_events = profile.get('events', [])
    
    # Check for duplicate event type
    event_type_lower = str(event.event_type).lower()
    for existing_event in existing_events:
        existing_type = existing_event.get('event_type', '').lower()
        if existing_type == event_type_lower:
            raise HTTPException(
                status_code=400,
                detail=f"Event type '{event.event_type}' already exists for this profile. Each profile can only have one event of each type."
            )
    
    # Auto-generate slug if not provided or empty
    if not event.slug or event.slug.strip() == "":
        short_id = event.event_id[:8]
        event.slug = f"{event_type_lower}-{short_id}"
    
    # Validate that slug is unique within this profile
    for existing_event in existing_events:
        if existing_event.get('slug') == event.slug:
            raise HTTPException(
                status_code=400,
                detail=f"Slug '{event.slug}' already exists for another event in this profile"
            )
    
    # Convert event to dict
    event_dict = event.model_dump()
    
    # Add event to profile's events list
    existing_events.append(event_dict)
    
    # Update profile
    await db.profiles.update_one(
        {"id": profile_id},
        {
            "$set": {
                "events": existing_events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "event_created",
        "resource_type": "event",
        "resource_id": event.event_id,
        "admin_id": admin_id,
        "details": {
            "profile_id": profile_id,
            "event_type": str(event.event_type),
            "event_slug": event.slug
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Event created successfully",
        "event": event_dict
    }


@api_router.put("/admin/events/{event_id}")
async def update_event(
    event_id: str,
    event_update: Dict,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 17: Update an existing event
    
    Features:
    - Updates event fields
    - Validates event-type specific requirements
    - Prevents changing event_type to duplicate
    - Validates language_enabled if provided
    """
    # Find profile containing this event
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Find the event in the events list
    events = profile.get('events', [])
    event_index = None
    current_event = None
    
    for idx, evt in enumerate(events):
        if evt.get('event_id') == event_id:
            event_index = idx
            current_event = evt
            break
    
    if event_index is None:
        raise HTTPException(status_code=404, detail="Event not found in profile")
    
    # Check if changing event_type would create duplicate
    if 'event_type' in event_update:
        new_event_type = event_update['event_type'].lower()
        current_event_type = current_event.get('event_type', '').lower()
        
        if new_event_type != current_event_type:
            # Check if new event_type already exists in profile
            for evt in events:
                if evt.get('event_id') != event_id and evt.get('event_type', '').lower() == new_event_type:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Event type '{event_update['event_type']}' already exists for this profile"
                    )
    
    # Check if changing slug would create duplicate
    if 'slug' in event_update and event_update['slug']:
        new_slug = event_update['slug']
        for evt in events:
            if evt.get('event_id') != event_id and evt.get('slug') == new_slug:
                raise HTTPException(
                    status_code=400,
                    detail=f"Slug '{new_slug}' already exists for another event in this profile"
                )
    
    # Update the event
    updated_event = {**current_event, **event_update}
    events[event_index] = updated_event
    
    # Update profile
    await db.profiles.update_one(
        {"id": profile['id']},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "event_updated",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {
            "profile_id": profile['id'],
            "updated_fields": list(event_update.keys())
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Event updated successfully",
        "event": updated_event
    }


@api_router.delete("/admin/events/{event_id}")
async def delete_event(
    event_id: str,
    hard_delete: bool = False,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 17: Delete an event (soft or hard delete)
    
    By default, performs soft delete (sets enabled=false)
    Set hard_delete=true to permanently remove the event
    """
    # Find profile containing this event
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    events = profile.get('events', [])
    
    if hard_delete:
        # Hard delete - remove event from list
        updated_events = [evt for evt in events if evt.get('event_id') != event_id]
        
        if len(updated_events) == len(events):
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Update profile
        await db.profiles.update_one(
            {"id": profile['id']},
            {
                "$set": {
                    "events": updated_events,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        action = "event_deleted_hard"
        message = "Event permanently deleted successfully"
    else:
        # Soft delete - set enabled=false
        event_found = False
        for evt in events:
            if evt.get('event_id') == event_id:
                evt['enabled'] = False
                event_found = True
                break
        
        if not event_found:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Update profile
        await db.profiles.update_one(
            {"id": profile['id']},
            {
                "$set": {
                    "events": events,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        action = "event_deleted_soft"
        message = "Event disabled successfully"
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": action,
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {
            "profile_id": profile['id'],
            "hard_delete": hard_delete
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": message}



@api_router.post("/admin/events/{event_id}/upload-music")
async def upload_event_music(
    event_id: str,
    file: UploadFile = File(...),
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 20: Upload background music for an event
    
    Requirements:
    - MP3 files only
    - Max file size: 5 MB
    - One music file per event
    """
    # Validate file is MP3
    if not file.filename.lower().endswith('.mp3'):
        raise HTTPException(status_code=400, detail="Only MP3 files are allowed")
    
    # Read file to check size
    file_content = await file.read()
    file_size_mb = len(file_content) / (1024 * 1024)
    
    if file_size_mb > 5:
        raise HTTPException(status_code=400, detail="Music file size must be less than 5 MB")
    
    # Find profile containing this event
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Create music uploads directory
    music_dir = Path("/app/uploads/music")
    music_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    filename = f"event_{event_id[:8]}_{timestamp}_{random_suffix}.mp3"
    file_path = music_dir / filename
    
    # Delete old music file if exists
    events = profile.get('events', [])
    for evt in events:
        if evt.get('event_id') == event_id and evt.get('music_file'):
            old_file_path = Path(f"/app{evt['music_file']}")
            if old_file_path.exists():
                try:
                    old_file_path.unlink()
                except Exception as e:
                    logging.warning(f"Failed to delete old music file: {e}")
    
    # Save new file
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    # Update event with music file path
    music_url = f"/uploads/music/{filename}"
    
    for evt in events:
        if evt.get('event_id') == event_id:
            evt['music_file'] = music_url
            evt['music_enabled'] = True  # Auto-enable when uploading
            break
    
    # Update profile
    await db.profiles.update_one(
        {"id": profile['id']},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "event_music_uploaded",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {
            "profile_id": profile['id'],
            "filename": filename,
            "file_size_mb": round(file_size_mb, 2)
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Music uploaded successfully",
        "music_url": music_url,
        "music_enabled": True
    }


@api_router.delete("/admin/events/{event_id}/music")
async def delete_event_music(
    event_id: str,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 20: Delete background music for an event
    """
    # Find profile containing this event
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    events = profile.get('events', [])
    event_found = False
    
    for evt in events:
        if evt.get('event_id') == event_id:
            event_found = True
            
            # Delete file if exists
            if evt.get('music_file'):
                old_file_path = Path(f"/app{evt['music_file']}")
                if old_file_path.exists():
                    try:
                        old_file_path.unlink()
                    except Exception as e:
                        logging.warning(f"Failed to delete music file: {e}")
            
            # Clear music fields
            evt['music_file'] = None
            evt['music_enabled'] = False
            break
    
    if not event_found:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Update profile
    await db.profiles.update_one(
        {"id": profile['id']},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "event_music_deleted",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {
            "profile_id": profile['id']
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Music deleted successfully"}



@api_router.patch("/admin/events/{event_id}/music-toggle")
async def toggle_event_music(
    event_id: str,
    music_enabled: bool,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 20: Toggle background music enabled/disabled for an event
    """
    # Find profile containing this event
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    events = profile.get('events', [])
    event_found = False
    
    for evt in events:
        if evt.get('event_id') == event_id:
            event_found = True
            evt['music_enabled'] = music_enabled
            break
    
    if not event_found:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Update profile
    await db.profiles.update_one(
        {"id": profile['id']},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": f"event_music_{'enabled' if music_enabled else 'disabled'}",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {
            "profile_id": profile['id'],
            "music_enabled": music_enabled
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": f"Music {'enabled' if music_enabled else 'disabled'} successfully",
        "music_enabled": music_enabled
    }


@api_router.get("/admin/profiles/{profile_id}/events")
async def get_profile_events(
    profile_id: str,
    include_disabled: bool = False,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 17: Get all events for a profile
    
    By default, returns only enabled events
    Set include_disabled=true to include disabled events
    """
    profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0, "events": 1})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    events = profile.get('events', [])
    
    if not include_disabled:
        events = [evt for evt in events if evt.get('enabled', True)]
    
    return {
        "profile_id": profile_id,
        "events": events,
        "total_count": len(events)
    }


# ==================== PHASE 21: EVENT GALLERY ROUTES ====================

@api_router.post("/admin/events/{event_id}/upload-gallery-images")
async def upload_event_gallery_images(
    event_id: str,
    files: List[UploadFile] = File(...),
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 21: Upload multiple images to event gallery
    - Max 20 images per event
    - Max 3MB per image
    - Auto-converts to WebP (quality 80)
    - Resizes if width > 2000px
    - Stores in /app/uploads/gallery/{profile_id}/{event_type}/
    """
    # Find profile containing this event
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Find the event
    events = profile.get('events', [])
    event = None
    event_index = -1
    
    for idx, evt in enumerate(events):
        if evt.get('event_id') == event_id:
            event = evt
            event_index = idx
            break
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # PHASE 33: Check gallery feature access
    gallery_limit = get_gallery_limit(profile)
    if gallery_limit == 0:
        raise HTTPException(
            status_code=403,
            detail="Gallery feature not available on FREE plan. Please upgrade to access gallery features."
        )
    
    # Check current gallery count against plan limit
    current_gallery = event.get('gallery_images', [])
    max_limit = gallery_limit if gallery_limit is not None else 20  # Use plan limit or default
    
    if len(current_gallery) + len(files) > max_limit:
        raise HTTPException(
            status_code=400, 
            detail=f"Gallery limit exceeded. Current: {len(current_gallery)}, Trying to add: {len(files)}, Max allowed: {max_limit}. Upgrade your plan for more storage."
        )
    
    # Create gallery directory
    profile_id = profile['id']
    event_type = event.get('event_type', 'unknown')
    gallery_dir = Path(f"/app/uploads/gallery/{profile_id}/{event_type}")
    gallery_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_images = []
    
    for file in files:
        # Validate file size (3MB = 3 * 1024 * 1024 bytes)
        content = await file.read()
        if len(content) > 3 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds 3MB limit"
            )
        
        # Reset file pointer
        await file.seek(0)
        
        try:
            # Mobile-perf: generate responsive variants for gallery uploads too.
            image_id = str(uuid.uuid4())
            variants = await convert_to_webp_responsive(file, gallery_dir, image_id)

            image_obj = {
                "id": image_id,
                "image_url": variants["original"],
                "variants": variants,
                "order": len(current_gallery) + len(uploaded_images),
            }
            uploaded_images.append(image_obj)
            
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process image {file.filename}: {str(e)}"
            )
    
    # Add images to gallery
    current_gallery.extend(uploaded_images)
    events[event_index]['gallery_images'] = current_gallery
    
    # Update profile
    await db.profiles.update_one(
        {"id": profile_id},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "event_gallery_images_uploaded",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {
            "profile_id": profile_id,
            "images_count": len(uploaded_images),
            "total_gallery_count": len(current_gallery)
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": f"Uploaded {len(uploaded_images)} images successfully",
        "uploaded_images": uploaded_images,
        "total_gallery_count": len(current_gallery)
    }


@api_router.delete("/admin/events/{event_id}/gallery-images/{image_id}")
async def delete_event_gallery_image(
    event_id: str,
    image_id: str,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 21: Delete a specific image from event gallery
    """
    # Find profile containing this event
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Find the event
    events = profile.get('events', [])
    event = None
    event_index = -1
    
    for idx, evt in enumerate(events):
        if evt.get('event_id') == event_id:
            event = evt
            event_index = idx
            break
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Find and remove image
    gallery_images = event.get('gallery_images', [])
    image_to_delete = None
    
    for img in gallery_images:
        if img.get('id') == image_id:
            image_to_delete = img
            break
    
    if not image_to_delete:
        raise HTTPException(status_code=404, detail="Image not found in gallery")
    
    # Delete file from filesystem
    image_path = Path(f"/app{image_to_delete['image_url']}")
    if image_path.exists():
        image_path.unlink()
    
    # Remove from gallery
    gallery_images = [img for img in gallery_images if img.get('id') != image_id]
    
    # Reorder remaining images
    for idx, img in enumerate(gallery_images):
        img['order'] = idx
    
    events[event_index]['gallery_images'] = gallery_images
    
    # Update profile
    await db.profiles.update_one(
        {"id": profile['id']},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "event_gallery_image_deleted",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {
            "profile_id": profile['id'],
            "image_id": image_id,
            "remaining_count": len(gallery_images)
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Image deleted successfully",
        "remaining_count": len(gallery_images)
    }


@api_router.patch("/admin/events/{event_id}/reorder-gallery")
async def reorder_event_gallery(
    event_id: str,
    image_order: List[str],
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 21: Reorder gallery images
    Accepts array of image IDs in desired order
    """
    # Find profile containing this event
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Find the event
    events = profile.get('events', [])
    event = None
    event_index = -1
    
    for idx, evt in enumerate(events):
        if evt.get('event_id') == event_id:
            event = evt
            event_index = idx
            break
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    gallery_images = event.get('gallery_images', [])
    
    # Validate that all image IDs exist
    existing_ids = {img.get('id') for img in gallery_images}
    provided_ids = set(image_order)
    
    if existing_ids != provided_ids:
        raise HTTPException(
            status_code=400,
            detail="Image order array must contain all existing image IDs"
        )
    
    # Create a mapping of id to image
    image_map = {img.get('id'): img for img in gallery_images}
    
    # Reorder images
    reordered_images = []
    for idx, img_id in enumerate(image_order):
        img = image_map[img_id]
        img['order'] = idx
        reordered_images.append(img)
    
    events[event_index]['gallery_images'] = reordered_images
    
    # Update profile
    await db.profiles.update_one(
        {"id": profile['id']},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "event_gallery_reordered",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {
            "profile_id": profile['id'],
            "new_order": image_order
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Gallery reordered successfully",
        "gallery_images": reordered_images
    }


@api_router.patch("/admin/events/{event_id}/gallery-toggle")
async def toggle_event_gallery(
    event_id: str,
    gallery_enabled: bool,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 21: Toggle gallery enabled/disabled for an event
    """
    # Find profile containing this event
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    events = profile.get('events', [])
    event_found = False
    
    for evt in events:
        if evt.get('event_id') == event_id:
            event_found = True
            evt['gallery_enabled'] = gallery_enabled
            break
    
    if not event_found:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Update profile
    await db.profiles.update_one(
        {"id": profile['id']},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": f"event_gallery_{'enabled' if gallery_enabled else 'disabled'}",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {
            "profile_id": profile['id'],
            "gallery_enabled": gallery_enabled
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": f"Gallery {'enabled' if gallery_enabled else 'disabled'} successfully",
        "gallery_enabled": gallery_enabled
    }


# ==================== ADMIN - AUDIT LOG ROUTES ====================

@api_router.get("/admin/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(admin_id: str = Depends(get_current_admin)):
    """
    Get audit logs for admin actions
    Returns last 1000 logs in reverse chronological order (newest first)

    July 2025 — be permissive: older / newer writers (notably the
    super-admin user-management endpoints in `user_features.py`) write
    slightly different shapes. We normalise here so one bad row never
    crashes the whole endpoint and the audit UI stays useful.
    """
    logs = await db.audit_logs.find({}, {"_id": 0}).sort("timestamp", -1).limit(1000).to_list(1000)

    out: List[AuditLogResponse] = []
    for log in logs:
        # Normalise timestamp → datetime
        ts = log.get('timestamp')
        if isinstance(ts, str):
            try:
                log['timestamp'] = datetime.fromisoformat(ts)
            except Exception:
                log['timestamp'] = datetime.now(timezone.utc)
        elif ts is None:
            log['timestamp'] = datetime.now(timezone.utc)

        # Back-fill admin_id from actor_id if writer used the new field
        if not log.get('admin_id') and log.get('actor_id'):
            log['admin_id'] = log['actor_id']

        # Wrap string `details` so old AuditLogResponse(details: Dict)
        # consumers keep working even with the new permissive schema.
        if isinstance(log.get('details'), str):
            log['details'] = {"message": log['details']}

        try:
            out.append(AuditLogResponse(**log))
        except Exception as _e:
            # Don't 500 the whole endpoint for one malformed row.
            logger.warning(f"audit-log row skipped: {_e}")
            continue
    return out

# ==================== ADMIN - MEDIA ROUTES ====================

@api_router.post("/admin/profiles/{profile_id}/media", response_model=ProfileMedia)
async def add_profile_media(
    profile_id: str,
    media_data: ProfileMediaCreate,
    admin_id: str = Depends(get_current_admin)
):
    """Add media to profile"""
    # Check if profile exists
    profile = await db.profiles.find_one({"id": profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    media = ProfileMedia(
        profile_id=profile_id,
        media_type=media_data.media_type,
        media_url=media_data.media_url,
        caption=media_data.caption,
        order=media_data.order
    )
    
    doc = media.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.profile_media.insert_one(doc)
    
    return media


@api_router.delete("/admin/media/{media_id}")
async def delete_media(media_id: str, admin_id: str = Depends(get_current_admin)):
    """Delete media"""
    result = await db.profile_media.delete_one({"id": media_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Media not found")
    
    return {"message": "Media deleted successfully"}


@api_router.get("/admin/profiles/{profile_id}/media", response_model=List[ProfileMedia])
async def get_profile_media(profile_id: str, admin_id: str = Depends(get_current_admin)):
    """Get all media for a profile"""
    media_list = await db.profile_media.find(
        {"profile_id": profile_id},
        {"_id": 0}
    ).sort("order", 1).to_list(1000)
    
    for media in media_list:
        if isinstance(media.get('created_at'), str):
            media['created_at'] = datetime.fromisoformat(media['created_at'])
    
    return media_list



@api_router.post("/admin/upload-image")
async def admin_upload_image(
    file: UploadFile = File(...),
    slot: str = Form("misc"),
    admin_id: str = Depends(get_current_admin),
):
    """Pre-save image upload for the photographer dashboard.
    Used by the wedding-create wizard BEFORE the profile_id exists.
    Returns a public URL the caller stores on the draft form."""
    is_valid, error_msg = validate_image_file(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    webp_data, file_size = await convert_to_webp(file, quality=85)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    slot_safe = ''.join(c for c in (slot or 'misc') if c.isalnum() or c in '-_')[:20] or 'misc'
    filename = f"admin-{admin_id}-{slot_safe}-{ts}-{suffix}.webp"
    out_path = UPLOADS_DIR / filename
    with open(out_path, 'wb') as f:
        f.write(webp_data)
    url = f"/uploads/photos/{filename}"
    try:
        await db.admin_uploads.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": admin_id,
            "slot": slot_safe,
            "url": url,
            "file_size": file_size,
            "original_filename": file.filename,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning(f"admin_uploads insert failed: {e}")
    return {"url": url, "file_size": file_size}


@api_router.post("/admin/profiles/{profile_id}/upload-photo", response_model=ProfileMedia)
async def upload_photo(
    profile_id: str,
    file: UploadFile = File(...),
    caption: str = Form(""),
    admin_id: str = Depends(get_current_admin)
):
    """Upload a photo for a profile with WebP conversion"""
    # Check if profile exists
    profile = await db.profiles.find_one({"id": profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Validate max 20 photos per profile
    media_count = await db.profile_media.count_documents({
        "profile_id": profile_id,
        "media_type": "photo"
    })
    if media_count >= 20:
        raise HTTPException(status_code=400, detail="Maximum 20 photos allowed per profile")
    
    # Validate image file
    is_valid, error_msg = validate_image_file(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Mobile-perf: generate responsive variants (small/medium/large/original)
    # in a single pass. Writes directly into /app/uploads/photos so static mount
    # serves them under /uploads/photos/...
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    base_name = f"{profile_id}_{timestamp}_{random_suffix}"
    variants = await convert_to_webp_responsive(file, UPLOADS_DIR, base_name)
    file_size = int(variants.get("size") or 0)
    
    # Get next order number
    max_order = await db.profile_media.find_one(
        {"profile_id": profile_id},
        sort=[("order", -1)]
    )
    next_order = (max_order.get('order', 0) + 1) if max_order else 0
    
    # Create media record. `media_url` keeps backwards compat (== original variant).
    media = ProfileMedia(
        profile_id=profile_id,
        media_type="photo",
        media_url=variants["original"],
        caption=caption if caption else None,
        order=next_order,
        is_cover=False,
        file_size=file_size,
        original_filename=file.filename,
        media_variants=variants,
    )
    
    doc = media.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.profile_media.insert_one(doc)
    
    return media


@api_router.put("/admin/media/{media_id}/set-cover")
async def set_cover_photo(
    media_id: str,
    admin_id: str = Depends(get_current_admin)
):
    """Set a photo as the cover photo"""
    # Find the media
    media = await db.profile_media.find_one({"id": media_id})
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    if media['media_type'] != 'photo':
        raise HTTPException(status_code=400, detail="Only photos can be set as cover")
    
    profile_id = media['profile_id']
    
    # Unset all other covers for this profile
    await db.profile_media.update_many(
        {"profile_id": profile_id},
        {"$set": {"is_cover": False}}
    )
    
    # Set this media as cover
    await db.profile_media.update_one(
        {"id": media_id},
        {"$set": {"is_cover": True}}
    )
    
    # Update profile cover_photo_id
    await db.profiles.update_one(
        {"id": profile_id},
        {"$set": {"cover_photo_id": media_id}}
    )
    
    return {"message": "Cover photo updated successfully"}


@api_router.post("/admin/profiles/{profile_id}/reorder-media")
async def reorder_media(
    profile_id: str,
    media_ids: List[str],
    admin_id: str = Depends(get_current_admin)
):
    """Reorder media items"""
    # Check if profile exists
    profile = await db.profiles.find_one({"id": profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Update order for each media
    for index, media_id in enumerate(media_ids):
        await db.profile_media.update_one(
            {"id": media_id, "profile_id": profile_id},
            {"$set": {"order": index}}
        )
    
    return {"message": "Media reordered successfully"}


@api_router.put("/admin/media/{media_id}/caption")
async def update_media_caption(
    media_id: str,
    caption: str = Form(""),
    admin_id: str = Depends(get_current_admin)
):
    """Update media caption"""
    result = await db.profile_media.update_one(
        {"id": media_id},
        {"$set": {"caption": caption if caption else None}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Media not found")
    
    return {"message": "Caption updated successfully"}


# ==================== PUBLIC INVITATION ROUTES ====================

async def _build_invitation_public_view(profile: dict) -> "InvitationPublicView":
    """Builds an InvitationPublicView from a raw profile doc.
    Shared helper used by /invite/{slug} and the batched /invite/{slug}/full.
    Assumes caller has already validated existence + expiry."""
    # PHASE 12: Check invitation expiry (separate from link expiry)
    is_expired = False
    expires_at = profile.get('expires_at')
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            is_expired = True

    media_list = await db.profile_media.find(
        {"profile_id": profile['id']},
        {"_id": 0}
    ).sort("order", 1).to_list(1000)

    greetings_list = await db.greetings.find(
        {"profile_id": profile['id'], "approval_status": "approved"},
        {"_id": 0}
    ).sort("created_at", -1).limit(20).to_list(20)

    if isinstance(profile.get('event_date'), str):
        profile['event_date'] = datetime.fromisoformat(profile['event_date'])

    for media in media_list:
        if isinstance(media.get('created_at'), str):
            media['created_at'] = datetime.fromisoformat(media['created_at'])

    for greeting in greetings_list:
        if isinstance(greeting.get('created_at'), str):
            greeting['created_at'] = datetime.fromisoformat(greeting['created_at'])

    return InvitationPublicView(
        slug=profile['slug'],
        groom_name=profile['groom_name'],
        bride_name=profile['bride_name'],
        event_type=profile['event_type'],
        event_date=profile['event_date'],
        venue=profile['venue'],
        city=profile.get('city'),
        invitation_message=profile.get('invitation_message'),
        language=profile['language'],
        design_id=profile['design_id'],
        deity_id=profile.get('deity_id'),
        whatsapp_groom=profile.get('whatsapp_groom'),
        whatsapp_bride=profile.get('whatsapp_bride'),
        enabled_languages=profile.get('enabled_languages', ['english']),
        custom_text=profile.get('custom_text', {}),
        about_couple=profile.get('about_couple'),
        family_details=profile.get('family_details'),
        love_story=profile.get('love_story'),
        bride_photo_url=profile.get('bride_photo_url') or (profile.get('custom_text', {}).get('_maja', {}) or {}).get('bride_photo_url'),
        groom_photo_url=profile.get('groom_photo_url') or (profile.get('custom_text', {}).get('_maja', {}) or {}).get('groom_photo_url'),
        couple_photo_url=profile.get('couple_photo_url') or (profile.get('custom_text', {}).get('_maja', {}) or {}).get('couple_photo_url'),
        bride_about=profile.get('bride_about'),
        groom_about=profile.get('groom_about'),
        cover_photo_id=profile.get('cover_photo_id'),
        show_couple_photo=profile.get('show_couple_photo', True),
        show_bride_photo=profile.get('show_bride_photo', True),
        show_groom_photo=profile.get('show_groom_photo', True),
        use_couple_photo_as_opening_bg=profile.get('use_couple_photo_as_opening_bg', True),
        opening_bg_source=profile.get('opening_bg_source') or 'couple',
        opening_photo_url=profile.get('opening_photo_url'),
        sections_enabled=SectionsEnabled(**profile['sections_enabled']),
        background_music=BackgroundMusic(**profile.get('background_music', {'enabled': False, 'file_url': None})),
        map_settings=MapSettings(**profile.get('map_settings', {'embed_enabled': False})),
        contact_info=ContactInfo(**profile.get('contact_info', {})),
        rsvp_settings=RSVPSettings(**(profile.get('rsvp_settings') or {})),
        honeymoon_fund=HoneymoonFund(**(profile.get('honeymoon_fund') or {})),
        live_stream=LiveStreamSettings(**(profile.get('live_stream') or {})),
        song_requests_settings=SongRequestSettings(**(profile.get('song_requests_settings') or {})),
        dress_code_settings=DressCodeSettings(**(profile.get('dress_code_settings') or {})),
        events=[WeddingEvent(**e) for e in profile.get('events', [])],
        media=[ProfileMedia(**m) for m in media_list],
        greetings=[GreetingResponse(**g) for g in greetings_list],
        guest_rooms=[GuestRoom(**{k: v for k, v in gr.items() if k != 'phone'}) for gr in (profile.get('guest_rooms') or [])],
        pre_wedding_links=[PreWeddingLink(**pl) for pl in (profile.get('pre_wedding_links') or [])],
        is_expired=is_expired,
        decorative_effects=profile.get('sections_enabled', {}).get('decorative_effects', True),
        seo_settings=SEOSettings(**profile.get("seo_settings", {"seo_enabled": True, "social_sharing_enabled": True, "custom_description": None})),
        design_selections=profile.get("design_selections", {}) or {},
        invitation_category=profile.get("invitation_category", "wedding"),
        celebrant_info=profile.get("celebrant_info"),
    )


@api_router.get("/invite/{slug}", response_model=InvitationPublicView)
async def get_invitation(slug: str, request: Request):
    """Get public invitation by slug"""
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    # Track view for audit logs
    client_ip = request.client.host if request.client else "unknown"
    await _track_invitation_view_audit(profile['id'], client_ip)
    
    # Check if active and not expired (link expiry)
    if not await check_profile_active(profile):
        raise HTTPException(status_code=410, detail="This invitation link has expired")

    return await _build_invitation_public_view(profile)


# -----------------------------------------------------------------------------
# Mobile perf: batched endpoint — returns invite + side-data in one round-trip.
# Cuts initial mobile load from ~8-10 parallel requests down to 1.
# -----------------------------------------------------------------------------
@api_router.get("/invite/{slug}/full")
async def get_invitation_full(slug: str, request: Request, wishes_limit: int = 50):
    """Batched public invitation payload — merges /invite/{slug} with side-data
    (wishes, gifts, blessings, gallery_info, referral_code) in a single
    request. Designed to reduce mobile network round-trips & speed up first
    paint on the public invitation page.
    """
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")

    client_ip = request.client.host if request.client else "unknown"
    # Track view (best-effort, don't block)
    asyncio.create_task(_track_invitation_view_audit(profile['id'], client_ip))

    if not await check_profile_active(profile):
        raise HTTPException(status_code=410, detail="This invitation link has expired")

    profile_id = profile['id']
    wishes_n   = max(1, min(int(wishes_limit or 50), 200))

    # Fire all side queries in parallel — safe failures degrade to defaults.
    async def _safe(coro, default):
        try:
            return await coro
        except Exception as e:
            logger.warning(f"/invite/{slug}/full side-query failed: {e}")
            return default

    invite_task         = _build_invitation_public_view(profile)
    wishes_task         = _safe(db.guest_wishes.find(
                            {"profile_id": profile_id, "status": "approved"},
                            {"_id": 0, "ip_hash": 0}
                          ).to_list(wishes_n), [])
    wishes_count_t      = _safe(db.guest_wishes.count_documents(
                            {"profile_id": profile_id, "status": "approved"}), 0)
    gifts_task          = _safe(db.gift_registry.find_one(
                            {"profile_id": profile_id}, {"_id": 0}), None)
    blessings_recent_t  = _safe(db.shagun_records.find(
                            {"profile_id": profile_id}, {"_id": 0}
                          ).sort("created_at", -1).limit(30).to_list(30), [])
    blessings_count_t   = _safe(db.shagun_records.count_documents(
                            {"profile_id": profile_id}), 0)
    blessings_total_t   = _safe(db.shagun_records.aggregate([
                            {"$match": {"profile_id": profile_id}},
                            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
                          ]).to_list(1), [])
    referral_task       = _safe(db.referral_codes.find_one(
                            {"profile_id": profile_id}, {"_id": 0, "code": 1}), None)

    (invite, wishes, wishes_count, gifts_doc, bless_recent, bless_count, bless_total_doc, referral_doc) = await asyncio.gather(
        invite_task, wishes_task, wishes_count_t, gifts_task, blessings_recent_t, blessings_count_t, blessings_total_t, referral_task
    )
    bless_total_amount = int((bless_total_doc[0]["total"] if bless_total_doc else 0) or 0)

    # Sort wishes: featured first, then newest first
    def _ts(w):
        v = w.get("approved_at") or w.get("created_at")
        try:
            return datetime.fromisoformat(v).timestamp() if v else 0
        except Exception:
            return 0
    wishes.sort(key=lambda w: (not w.get("is_featured"), -_ts(w)))
    wishes = wishes[:wishes_n]

    gc = profile.get("gallery_config") or {}
    gallery_info = {
        "enabled":             bool(gc.get("enabled")),
        "total_photos":        int(gc.get("total_photos") or 0),
        "downloads_enabled":   bool(gc.get("downloads_enabled", True)),
        "watermark_enabled":   bool(gc.get("watermark_enabled", False)),
        "watermark_position":  gc.get("watermark_position", "bottom-right"),
        "watermark_text":      gc.get("watermark_text"),
        "upload_methods":      gc.get("upload_methods") or {"face_match": True, "qr_code": True, "shared_link": True},
        "privacy":             gc.get("privacy") or "public",
    }

    s = profile.get("shagun_settings") or {}
    shagun_enabled = bool(s.get("enabled")) and bool(s.get("upi_id"))

    # ---- Build full shagun payload (mirrors /invite/{slug}/shagun) so the
    # public DigitalShagunSection doesn't need a second round-trip.
    shagun_payload: Dict[str, Any] = {"enabled": False}
    if shagun_enabled:
        try:
            import urllib.parse as _up
            couple_str = f"{profile.get('groom_name','')} & {profile.get('bride_name','')}"

            def _upi_link(amount: int) -> str:
                return "upi://pay?" + _up.urlencode({
                    "pa": s["upi_id"],
                    "pn": s.get("payee_name") or couple_str,
                    "am": str(amount),
                    "cu": "INR",
                    "tn": f"Shagun for {couple_str}",
                })

            suggested = [
                {"amount": a, "link": _upi_link(a)}
                for a in s.get("suggested_amounts", [101, 501, 1001])
            ]
            shagun_payload = {
                "enabled": True,
                "couple": couple_str,
                "payee_name": s.get("payee_name") or couple_str,
                "blessing_message": s.get("blessing_message"),
                "upi_id": s["upi_id"],
                "gpay_handle": s.get("gpay_handle"),
                "phonepe_handle": s.get("phonepe_handle"),
                "paytm_handle": s.get("paytm_handle"),
                "suggested": suggested,
                "razorpay_enabled": bool(
                    s.get("razorpay_enabled")
                    and s.get("razorpay_key_id")
                    and s.get("razorpay_key_secret")
                ),
                "platform_fee_percent": float(s.get("platform_fee_percent", 5.0)),
            }
        except Exception as _e:
            logger.warning(f"/full shagun build failed: {_e}")

    # ---- Build venues payload (mirrors /invite/{slug}/venues)
    venues_payload: Dict[str, Any] = {"main_venue": None, "events": []}
    try:
        import urllib.parse as _up

        def _venue_links(lat, lng, name, map_link_paste, w3w):
            name_q = _up.quote(name or "")
            if lat is not None and lng is not None:
                google = (map_link_paste
                          or f"https://www.google.com/maps/search/?api=1&query={lat},{lng}")
                apple = f"https://maps.apple.com/?ll={lat},{lng}&q={name_q}"
                uber = (f"https://m.uber.com/ul/?action=setPickup&pickup=my_location"
                        f"&dropoff[latitude]={lat}&dropoff[longitude]={lng}"
                        f"&dropoff[nickname]={name_q}")
                ola = f"https://book.olacabs.com/?lat={lat}&lng={lng}&drop_name={name_q}"
                rapido = f"https://rapido.bike/Booknow?dropLat={lat}&dropLng={lng}"
                wa = "https://wa.me/?text=" + _up.quote(f"{name or 'Venue'} — {google}")
            else:
                google = (map_link_paste
                          or f"https://www.google.com/maps/search/?api=1&query={name_q}")
                apple = f"https://maps.apple.com/?q={name_q}"
                uber = f"https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[nickname]={name_q}"
                ola = f"https://book.olacabs.com/?drop_name={name_q}"
                rapido = "https://rapido.bike"
                wa = "https://wa.me/?text=" + _up.quote(f"{name or 'Venue'} — {google}")
            return {
                "google_maps": google, "apple_maps": apple,
                "uber": uber, "ola": ola, "rapido": rapido,
                "whatsapp_share": wa,
                "what3words_link": (f"https://what3words.com/{w3w}" if w3w else None),
            }

        ms = profile.get("map_settings", {}) or {}
        main_venue = {
            "kind": "main",
            "name": profile.get("venue") or "Wedding venue",
            "address": profile.get("venue_address") or profile.get("city") or "",
            "latitude": ms.get("latitude"),
            "longitude": ms.get("longitude"),
            "what3words": ms.get("what3words"),
            "parking_info": ms.get("parking_info"),
            "links": _venue_links(ms.get("latitude"), ms.get("longitude"),
                                  profile.get("venue"), ms.get("map_link"),
                                  ms.get("what3words")),
        }
        event_list = []
        for ev in profile.get("events", []) or []:
            event_list.append({
                "kind": "event",
                "event_id": ev.get("event_id"),
                "event_type": ev.get("event_type"),
                "event_name": ev.get("name") or ev.get("event_name") or "Event",
                "date": ev.get("date"),
                "start_time": ev.get("start_time"),
                "name": ev.get("venue_name") or main_venue["name"],
                "address": ev.get("venue_address") or "",
                "latitude": ev.get("latitude"),
                "longitude": ev.get("longitude"),
                "what3words": ev.get("what3words"),
                "parking_info": ev.get("parking_info"),
                "links": _venue_links(ev.get("latitude"), ev.get("longitude"),
                                      ev.get("venue_name") or main_venue["name"],
                                      ev.get("map_link"),
                                      ev.get("what3words")),
            })
        venues_payload = {"main_venue": main_venue, "events": event_list}
    except Exception as _e:
        logger.warning(f"/full venues build failed: {_e}")

    # ---- Build travel payload (mirrors /invite/{slug}/travel)
    travel_payload: Dict[str, Any] = {}
    try:
        import urllib.parse as _up
        venue = profile.get("venue") or "Wedding Venue"
        ms2 = profile.get("map_settings") or {}
        dest_lat = ms2.get("latitude")
        dest_lng = ms2.get("longitude")
        venue_q = _up.quote(venue)
        if dest_lat and dest_lng:
            google_maps = f"https://www.google.com/maps/search/?api=1&query={dest_lat},{dest_lng}"
            ola = f"https://book.olacabs.com/?lat={dest_lat}&lng={dest_lng}&drop_name={venue_q}"
            uber = (f"https://m.uber.com/ul/?action=setPickup&pickup=my_location"
                    f"&dropoff[latitude]={dest_lat}&dropoff[longitude]={dest_lng}"
                    f"&dropoff[nickname]={venue_q}")
            rapido = f"https://rapido.bike/Booknow?dropLat={dest_lat}&dropLng={dest_lng}"
        else:
            google_maps = f"https://www.google.com/maps/search/?api=1&query={venue_q}"
            ola = f"https://book.olacabs.com/?drop_name={venue_q}"
            uber = f"https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[nickname]={venue_q}"
            rapido = "https://rapido.bike"
        travel_payload = {
            "venue": venue,
            "destination": {"lat": dest_lat, "lng": dest_lng} if dest_lat and dest_lng else None,
            "links": {
                "google_maps": google_maps,
                "ola": ola,
                "uber": uber,
                "rapido": rapido,
            },
            "hotels_nearby_query": f"https://www.google.com/maps/search/hotels+near+{venue_q}",
        }
    except Exception as _e:
        logger.warning(f"/full travel build failed: {_e}")

    return {
        "invite":        jsonable_encoder(invite),
        "wishes":        wishes,
        "gifts":         gifts_doc,
        "blessings": {
            # legacy-compatible keys used by DigitalShagunSection / Wall of Love
            "blessing_count":        int(bless_count or 0),
            "blessing_total_amount": bless_total_amount,
            "wishes_count":          int(wishes_count or 0),
            "recent_blessings":      bless_recent,
            # new-shape keys retained for other consumers
            "total_count":           int(bless_count or 0),
            "recent":                bless_recent,
        },
        "gallery_info":  gallery_info,
        "shagun_enabled": shagun_enabled,
        "shagun":        shagun_payload,
        "venues":        venues_payload,
        "travel":        travel_payload,
        "referral_code": (referral_doc or {}).get("code"),
    }


# Phase 2A — Save the Date (lightweight teaser page, separate from full invitation)
@api_router.get("/save-the-date/{slug}")
async def get_save_the_date(slug: str):
    """Lightweight teaser endpoint: returns only what's needed for the Save the Date page.
    No view tracking, no expensive joins."""
    profile = await db.profiles.find_one(
        {"slug": slug},
        {
            "_id": 0,
            "slug": 1,
            "groom_name": 1,
            "bride_name": 1,
            "event_date": 1,
            "venue": 1,
            "city": 1,
            "design_id": 1,
            "bride_photo_url": 1,
            "groom_photo_url": 1,
            "couple_photo_url": 1,
            "cover_photo_id": 1,
            "invitation_message": 1,
            "is_active": 1,
            "link_expiry_date": 1,
            "expires_at": 1,
        },
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if not await check_profile_active(profile):
        raise HTTPException(status_code=410, detail="This invitation link has expired")

    # Normalise event_date
    if isinstance(profile.get('event_date'), str):
        try:
            profile['event_date'] = datetime.fromisoformat(profile['event_date'])
        except Exception:
            pass

    return {
        "slug": profile["slug"],
        "groom_name": profile.get("groom_name", ""),
        "bride_name": profile.get("bride_name", ""),
        "event_date": profile.get("event_date"),
        "venue": profile.get("venue", ""),
        "city": profile.get("city"),
        "design_id": profile.get("design_id", "royal_mughal"),
        "bride_photo_url": profile.get("bride_photo_url"),
        "groom_photo_url": profile.get("groom_photo_url"),
        "couple_photo_url": profile.get("couple_photo_url"),
        "cover_photo_id": profile.get("cover_photo_id"),
        "invitation_message": profile.get("invitation_message"),
        "invitation_link": f"/invite/{profile['slug']}",
    }


# Find My Room — must be declared BEFORE /invite/{slug}/{event_type}
# (FastAPI routes are matched in declaration order — the event_type wildcard
# would otherwise swallow `room-lookup` as if it were an event type.)
@api_router.get("/invite/{slug}/room-lookup")
async def room_lookup_v2(slug: str, name: str = ""):
    """Public endpoint: case-insensitive partial-match search for a guest's room
    in the invitation's guest_rooms list. Returns up to 10 matches.
    """
    name_q = (name or "").strip().lower()
    if len(name_q) < 2:
        raise HTTPException(status_code=400, detail="Please enter at least 2 characters of your name")

    profile = await db.profiles.find_one(
        {"slug": slug},
        {"_id": 0, "guest_rooms": 1, "is_active": 1, "expires_at": 1, "link_expiry_date": 1},
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if not await check_profile_active(profile):
        raise HTTPException(status_code=410, detail="This invitation link has expired")

    rooms = profile.get("guest_rooms") or []
    matches = []
    for r in rooms:
        gname = (r.get("guest_name") or "").lower()
        if name_q in gname:
            safe = {k: v for k, v in r.items() if k != "phone"}
            matches.append(safe)
        if len(matches) >= 10:
            break

    return {"count": len(matches), "matches": matches}


@api_router.get("/invite/{slug}/songs", response_model=List[SongRequestResponse])
async def list_song_requests_public_alias(slug: str, limit: int = 30):
    """Public alias for song requests list (avoids catch-all event_type route)."""
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    settings = (profile.get('song_requests_settings') or {})
    if not settings.get('enabled', False):
        return []
    rows = await db.song_requests.find(
        {"profile_id": profile['id']}, {"_id": 0}
    ).sort("created_at", -1).limit(max(1, min(int(limit or 30), 100))).to_list(100)
    out = []
    for r in rows:
        if isinstance(r.get('created_at'), str):
            r['created_at'] = datetime.fromisoformat(r['created_at'])
        out.append(SongRequestResponse(
            id=r['id'], guest_name=r.get('guest_name', ''), song_title=r.get('song_title', ''),
            artist=r.get('artist'), provider_url=r.get('provider_url'), message=r.get('message'),
            created_at=r['created_at'],
        ))
    return out


# IMPORTANT: this alias MUST stay above the catch-all `/invite/{slug}/{event_type}`
# below — FastAPI matches routes by registration order, so /calendar would otherwise
# be eaten by the catch-all and return 400 "Invalid event type". The original handler
# lives further down in the file; this alias just forwards to it lazily.
@api_router.get("/invite/{slug}/calendar")
async def download_calendar_alias(slug: str, event_id: Optional[str] = None):
    """Public alias for ICS calendar (registered before catch-all)."""
    # Late-bound delegate — `download_calendar` is defined later in this file.
    return await download_calendar(slug, event_id=event_id)  # noqa: F821 (defined later)


@api_router.get("/invite/{slug}/{event_type}", response_model=InvitationPublicView)
async def get_event_invitation(slug: str, event_type: str):
    """Get public invitation for specific event
    
    NEW: Checks EventInvitation first (dedicated event invitation links)
    FALLBACK: Falls back to WeddingEvent within profile (PHASE 13 legacy)
    """
    # Validate event type
    valid_event_types = ['engagement', 'haldi', 'mehendi', 'marriage', 'reception']
    event_type_lower = event_type.lower()
    if event_type_lower not in valid_event_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid event type. Must be one of: {', '.join(valid_event_types)}"
        )
    
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    # Check if active and not expired (link expiry)
    if not await check_profile_active(profile):
        raise HTTPException(status_code=410, detail="This invitation link has expired")
    
    # NEW: Check if EventInvitation exists for this profile and event_type
    event_invitation = await db.event_invitations.find_one({
        "profile_id": profile['id'],
        "event_type": event_type_lower
    }, {"_id": 0})
    
    # If EventInvitation exists, use it
    if event_invitation:
        # Check if enabled
        if not event_invitation.get('enabled', True):
            raise HTTPException(status_code=404, detail="This event invitation is not available")
        
        # Use EventInvitation's design_id and deity_id
        design_id = event_invitation.get('design_id', profile['design_id'])
        deity_id = event_invitation.get('deity_id', profile.get('deity_id'))
    else:
        # FALLBACK: Find the specific event in the profile (PHASE 13 legacy)
        events = profile.get('events', [])
        event_data = None
        for evt in events:
            if evt.get('event_type', '').lower() == event_type_lower:
                event_data = evt
                break
        
        if not event_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Event '{event_type}' not found in this invitation"
            )
        
        # PHASE 17: Check if event is enabled (soft delete check)
        if not event_data.get('enabled', True):
            raise HTTPException(
                status_code=404,
                detail="This event is not available"
            )
        
        # Use event's design or profile default
        design_id = event_data.get('design_preset_id') or profile['design_id']
        deity_id = profile.get('deity_id')
    
    # PHASE 12: Check invitation expiry (separate from link expiry)
    is_expired = False
    expires_at = profile.get('expires_at')
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        # Ensure timezone-aware
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if datetime.now(timezone.utc) > expires_at:
            is_expired = True
    
    # Get media
    media_list = await db.profile_media.find(
        {"profile_id": profile['id']},
        {"_id": 0}
    ).sort("order", 1).to_list(1000)
    
    # Get greetings - Only return approved greetings for public view (last 20)
    greetings_list = await db.greetings.find(
        {"profile_id": profile['id'], "approval_status": "approved"},
        {"_id": 0}
    ).sort("created_at", -1).limit(20).to_list(20)
    
    # Convert date strings
    if isinstance(profile.get('event_date'), str):
        profile['event_date'] = datetime.fromisoformat(profile['event_date'])
    
    for media in media_list:
        if isinstance(media.get('created_at'), str):
            media['created_at'] = datetime.fromisoformat(media['created_at'])
    
    for greeting in greetings_list:
        if isinstance(greeting.get('created_at'), str):
            greeting['created_at'] = datetime.fromisoformat(greeting['created_at'])
    
    # Filter events to only show events matching the event_type (for backward compatibility)
    filtered_events = []
    for evt in profile.get('events', []):
        if evt.get('event_type', '').lower() == event_type_lower:
            filtered_events.append(WeddingEvent(**evt))
    
    return InvitationPublicView(
        slug=profile['slug'],
        groom_name=profile['groom_name'],
        bride_name=profile['bride_name'],
        event_type=profile['event_type'],
        event_date=profile['event_date'],
        venue=profile['venue'],
        city=profile.get('city'),
        invitation_message=profile.get('invitation_message'),
        language=profile['language'],
        design_id=design_id,  # Use EventInvitation's design or fallback
        deity_id=deity_id,  # Use EventInvitation's deity or fallback
        whatsapp_groom=profile.get('whatsapp_groom'),
        whatsapp_bride=profile.get('whatsapp_bride'),
        enabled_languages=profile.get('enabled_languages', ['english']),
        custom_text=profile.get('custom_text', {}),
        about_couple=profile.get('about_couple'),
        family_details=profile.get('family_details'),
        love_story=profile.get('love_story'),
        bride_photo_url=profile.get('bride_photo_url') or (profile.get('custom_text', {}).get('_maja', {}) or {}).get('bride_photo_url'),
        groom_photo_url=profile.get('groom_photo_url') or (profile.get('custom_text', {}).get('_maja', {}) or {}).get('groom_photo_url'),
        couple_photo_url=profile.get('couple_photo_url') or (profile.get('custom_text', {}).get('_maja', {}) or {}).get('couple_photo_url'),
        bride_about=profile.get('bride_about'),
        groom_about=profile.get('groom_about'),
        cover_photo_id=profile.get('cover_photo_id'),
        show_couple_photo=profile.get('show_couple_photo', True),
        show_bride_photo=profile.get('show_bride_photo', True),
        show_groom_photo=profile.get('show_groom_photo', True),
        use_couple_photo_as_opening_bg=profile.get('use_couple_photo_as_opening_bg', True),
        opening_bg_source=profile.get('opening_bg_source') or 'couple',
        opening_photo_url=profile.get('opening_photo_url'),
        sections_enabled=SectionsEnabled(**profile['sections_enabled']),
        background_music=BackgroundMusic(**profile.get('background_music', {'enabled': False, 'file_url': None})),
        map_settings=MapSettings(**profile.get('map_settings', {'embed_enabled': False})),
        contact_info=ContactInfo(**profile.get('contact_info', {})),
        rsvp_settings=RSVPSettings(**(profile.get('rsvp_settings') or {})),
        honeymoon_fund=HoneymoonFund(**(profile.get('honeymoon_fund') or {})),
        live_stream=LiveStreamSettings(**(profile.get('live_stream') or {})),
        song_requests_settings=SongRequestSettings(**(profile.get('song_requests_settings') or {})),
        dress_code_settings=DressCodeSettings(**(profile.get('dress_code_settings') or {})),
        events=filtered_events,  # Show matching events
        media=[ProfileMedia(**m) for m in media_list],
        greetings=[GreetingResponse(**g) for g in greetings_list],
        guest_rooms=[GuestRoom(**gr) for gr in (profile.get('guest_rooms') or [])],
        pre_wedding_links=[PreWeddingLink(**pl) for pl in (profile.get('pre_wedding_links') or [])],
        is_expired=is_expired,
        decorative_effects=profile.get('sections_enabled', {}).get('decorative_effects', True),  # PHASE 17: Decorative effects
        seo_settings=SEOSettings(**profile.get("seo_settings", {"seo_enabled": True, "social_sharing_enabled": True, "custom_description": None})),
        design_selections=profile.get("design_selections", {}) or {},
        invitation_category=profile.get("invitation_category", "wedding"),
        celebrant_info=profile.get("celebrant_info"),
    )


@api_router.get("/invite/{slug}/event/{event_slug}", response_model=InvitationPublicView)
async def get_event_by_slug(slug: str, event_slug: str):
    """
    PHASE 17: Get public invitation for specific event by event slug
    
    This allows accessing events using their unique slug instead of event_type
    Example: /api/invite/john-jane-abc123/event/marriage-a1b2c3d4
    """
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    # Check if active and not expired (link expiry)
    if not await check_profile_active(profile):
        raise HTTPException(status_code=410, detail="This invitation link has expired")
    
    # Find event by slug
    events = profile.get('events', [])
    event_data = None
    for evt in events:
        if evt.get('slug') == event_slug:
            event_data = evt
            break
    
    if not event_data:
        raise HTTPException(
            status_code=404,
            detail=f"Event with slug '{event_slug}' not found"
        )
    
    # PHASE 17: Check if event is enabled
    if not event_data.get('enabled', True):
        raise HTTPException(
            status_code=404,
            detail="This event is not available"
        )
    
    # Get event type for filtering
    event_type_lower = event_data.get('event_type', '').lower()
    
    # Use event's design or profile default
    design_id = event_data.get('design_preset_id') or event_data.get('theme_id') or profile['design_id']
    deity_id = profile.get('deity_id')
    
    # PHASE 12: Check invitation expiry (separate from link expiry)
    is_expired = False
    expires_at = profile.get('expires_at')
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        # Ensure timezone-aware
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if datetime.now(timezone.utc) > expires_at:
            is_expired = True
    
    # Get media
    media_list = await db.profile_media.find(
        {"profile_id": profile['id']},
        {"_id": 0}
    ).sort("order", 1).to_list(1000)
    
    # Get greetings - Only return approved greetings for public view (last 20)
    greetings_list = await db.greetings.find(
        {"profile_id": profile['id'], "approval_status": "approved"},
        {"_id": 0}
    ).sort("created_at", -1).limit(20).to_list(20)
    
    # Convert date strings
    if isinstance(profile.get('event_date'), str):
        profile['event_date'] = datetime.fromisoformat(profile['event_date'])
    
    for media in media_list:
        if isinstance(media.get('created_at'), str):
            media['created_at'] = datetime.fromisoformat(media['created_at'])
    
    for greeting in greetings_list:
        if isinstance(greeting.get('created_at'), str):
            greeting['created_at'] = datetime.fromisoformat(greeting['created_at'])
    
    # Filter to only show this specific event
    filtered_events = [WeddingEvent(**event_data)]
    
    # PHASE 17: Use event's language_enabled if present, otherwise use profile's enabled_languages
    enabled_languages = event_data.get('language_enabled', profile.get('enabled_languages', ['english']))
    
    return InvitationPublicView(
        slug=profile['slug'],
        groom_name=profile['groom_name'],
        bride_name=profile['bride_name'],
        event_type=profile['event_type'],
        event_date=profile['event_date'],
        venue=profile['venue'],
        city=profile.get('city'),
        invitation_message=profile.get('invitation_message'),
        language=profile['language'],
        design_id=design_id,
        deity_id=deity_id,
        whatsapp_groom=profile.get('whatsapp_groom'),
        whatsapp_bride=profile.get('whatsapp_bride'),
        enabled_languages=enabled_languages,  # PHASE 17: Event-specific languages
        custom_text=profile.get('custom_text', {}),
        about_couple=profile.get('about_couple'),
        family_details=profile.get('family_details'),
        love_story=profile.get('love_story'),
        bride_photo_url=profile.get('bride_photo_url') or (profile.get('custom_text', {}).get('_maja', {}) or {}).get('bride_photo_url'),
        groom_photo_url=profile.get('groom_photo_url') or (profile.get('custom_text', {}).get('_maja', {}) or {}).get('groom_photo_url'),
        couple_photo_url=profile.get('couple_photo_url') or (profile.get('custom_text', {}).get('_maja', {}) or {}).get('couple_photo_url'),
        bride_about=profile.get('bride_about'),
        groom_about=profile.get('groom_about'),
        cover_photo_id=profile.get('cover_photo_id'),
        show_couple_photo=profile.get('show_couple_photo', True),
        show_bride_photo=profile.get('show_bride_photo', True),
        show_groom_photo=profile.get('show_groom_photo', True),
        use_couple_photo_as_opening_bg=profile.get('use_couple_photo_as_opening_bg', True),
        opening_bg_source=profile.get('opening_bg_source') or 'couple',
        opening_photo_url=profile.get('opening_photo_url'),
        sections_enabled=SectionsEnabled(**profile['sections_enabled']),
        background_music=BackgroundMusic(**profile.get('background_music', {'enabled': False, 'file_url': None})),
        map_settings=MapSettings(**profile.get('map_settings', {'embed_enabled': False})),
        contact_info=ContactInfo(**profile.get('contact_info', {})),
        rsvp_settings=RSVPSettings(**(profile.get('rsvp_settings') or {})),
        honeymoon_fund=HoneymoonFund(**(profile.get('honeymoon_fund') or {})),
        live_stream=LiveStreamSettings(**(profile.get('live_stream') or {})),
        song_requests_settings=SongRequestSettings(**(profile.get('song_requests_settings') or {})),
        dress_code_settings=DressCodeSettings(**(profile.get('dress_code_settings') or {})),
        events=filtered_events,
        media=[ProfileMedia(**m) for m in media_list],
        greetings=[GreetingResponse(**g) for g in greetings_list],
        guest_rooms=[GuestRoom(**gr) for gr in (profile.get('guest_rooms') or [])],
        pre_wedding_links=[PreWeddingLink(**pl) for pl in (profile.get('pre_wedding_links') or [])],
        is_expired=is_expired,
        decorative_effects=profile.get('sections_enabled', {}).get('decorative_effects', True),  # PHASE 17: Decorative effects
        seo_settings=SEOSettings(**profile.get("seo_settings", {"seo_enabled": True, "social_sharing_enabled": True, "custom_description": None})),
        design_selections=profile.get("design_selections", {}) or {},
        invitation_category=profile.get("invitation_category", "wedding"),
        celebrant_info=profile.get("celebrant_info"),
    )


@api_router.post("/invite/{slug}/greetings", response_model=GreetingResponse)
async def submit_greeting(
    slug: str, 
    greeting_data: GreetingCreate, 
    request: Request,
    captcha_id: Optional[str] = None,
    captcha_answer: Optional[str] = None
):
    """
    Submit greeting for invitation
    
    PHASE 11: Default status is 'pending' for moderation
    PHASE 32: Now includes CAPTCHA verification if required
    """
    # PHASE 12 - PART 4: Rate limiting - 3 wishes per IP per day
    client_ip = get_client_ip(request)
    if not await check_rate_limit(client_ip, "wishes", 3):
        raise HTTPException(
            status_code=429,
            detail="You have exceeded the maximum number of wishes submissions for today. Please try again tomorrow."
        )
    
    # PHASE 32: Check if CAPTCHA is required for this IP/device
    device_id = request.headers.get("X-Device-Id", None)
    captcha_check = await check_submission_captcha_required(slug, client_ip, device_id, "wishes")
    
    if captcha_check["requires_captcha"]:
        # CAPTCHA is required, verify it
        if not captcha_id or not captcha_answer:
            raise HTTPException(
                status_code=400,
                detail="CAPTCHA verification is required. Please complete the CAPTCHA challenge."
            )
        
        # Verify CAPTCHA
        try:
            captcha_challenge = await db.captcha_challenges.find_one({"id": captcha_id}, {"_id": 0})
            
            if not captcha_challenge:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid CAPTCHA. Please try again."
                )
            
            # Check if expired
            expires_at = captcha_challenge.get('expires_at')
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if datetime.now(timezone.utc) > expires_at:
                await db.captcha_challenges.delete_one({"id": captcha_id})
                raise HTTPException(
                    status_code=400,
                    detail="CAPTCHA expired. Please request a new challenge."
                )
            
            # Verify answer
            expected_answer_hash = captcha_challenge.get('answer')
            provided_answer_hash = hashlib.sha256(str(captcha_answer).encode()).hexdigest()
            
            if provided_answer_hash != expected_answer_hash:
                # Wrong answer - track failed attempt
                await track_submission_attempt(client_ip, device_id, "wishes", slug, False, True)
                await db.captcha_challenges.delete_one({"id": captcha_id})
                raise HTTPException(
                    status_code=400,
                    detail="Incorrect CAPTCHA answer. Please try again."
                )
            
            # Correct answer - delete challenge
            await db.captcha_challenges.delete_one({"id": captcha_id})
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"CAPTCHA verification error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="CAPTCHA verification failed. Please try again."
            )
    
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    if not await check_profile_active(profile):
        raise HTTPException(status_code=410, detail="This invitation link has expired")
    
    # PHASE 12: Check invitation expiry (separate from link expiry)
    expires_at = profile.get('expires_at')
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=403, detail="This invitation has expired. Submitting wishes is no longer available.")
    
    # Sanitize input using bleach
    import bleach
    sanitized_name = bleach.clean(greeting_data.guest_name, tags=[], strip=True)
    sanitized_message = bleach.clean(greeting_data.message, tags=[], strip=True)
    
    greeting = Greeting(
        profile_id=profile['id'],
        guest_name=sanitized_name,
        message=sanitized_message,
        approval_status="pending"  # PHASE 11: Default to pending for moderation
    )
    
    doc = greeting.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.greetings.insert_one(doc)
    
    # PHASE 32: Track successful submission (resets CAPTCHA requirement)
    await track_submission_attempt(client_ip, device_id, "wishes", slug, True, captcha_check["requires_captcha"])
    
    return GreetingResponse(
        id=greeting.id,
        guest_name=greeting.guest_name,
        message=greeting.message,
        approval_status=greeting.approval_status,
        created_at=greeting.created_at
    )


@api_router.get("/admin/profiles/{profile_id}/greetings", response_model=List[GreetingResponse])
async def get_profile_greetings(
    profile_id: str, 
    status: Optional[str] = None,
    admin_id: str = Depends(get_current_admin)
):
    """PHASE 11: Get all greetings for a profile with optional status filter"""
    # Build query filter
    query_filter = {"profile_id": profile_id}
    if status and status in ['pending', 'approved', 'rejected']:
        query_filter["approval_status"] = status
    
    greetings = await db.greetings.find(
        query_filter,
        {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    
    for greeting in greetings:
        if isinstance(greeting.get('created_at'), str):
            greeting['created_at'] = datetime.fromisoformat(greeting['created_at'])
        # Set default approval_status for old greetings without this field
        if 'approval_status' not in greeting:
            greeting['approval_status'] = 'approved'
    
    return [GreetingResponse(**g) for g in greetings]


# ==================== PHASE 11: GREETING MODERATION ROUTES ====================

@api_router.put("/admin/greetings/{greeting_id}/approve")
async def approve_greeting(greeting_id: str, admin_id: str = Depends(get_current_admin)):
    """PHASE 11: Approve a greeting"""
    result = await db.greetings.update_one(
        {"id": greeting_id},
        {"$set": {"approval_status": "approved"}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Greeting not found")
    
    return {"message": "Greeting approved successfully"}


@api_router.put("/admin/greetings/{greeting_id}/reject")
async def reject_greeting(greeting_id: str, admin_id: str = Depends(get_current_admin)):
    """PHASE 11: Reject a greeting"""
    result = await db.greetings.update_one(
        {"id": greeting_id},
        {"$set": {"approval_status": "rejected"}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Greeting not found")
    
    return {"message": "Greeting rejected successfully"}


@api_router.delete("/admin/greetings/{greeting_id}")
async def delete_greeting(greeting_id: str, admin_id: str = Depends(get_current_admin)):
    """PHASE 11: Delete a greeting"""
    result = await db.greetings.delete_one({"id": greeting_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Greeting not found")
    
    return {"message": "Greeting deleted successfully"}


# ==================== RSVP ROUTES ====================

@api_router.post("/rsvp", response_model=RSVPResponse)
async def submit_rsvp(
    slug: str, 
    rsvp_data: RSVPCreate, 
    request: Request,
    captcha_id: Optional[str] = None,
    captcha_answer: Optional[str] = None
):
    """
    Submit RSVP for invitation (public endpoint)
    
    PHASE 32: Now includes CAPTCHA verification if required
    """
    # PHASE 12 - PART 4: Rate limiting - 5 RSVPs per IP per day
    client_ip = get_client_ip(request)
    if not await check_rate_limit(client_ip, "rsvp", 5):
        raise HTTPException(
            status_code=429,
            detail="You have exceeded the maximum number of RSVP submissions for today. Please try again tomorrow."
        )
    
    # PHASE 32: Check if CAPTCHA is required for this IP/device
    device_id = request.headers.get("X-Device-Id", None)
    captcha_check = await check_submission_captcha_required(slug, client_ip, device_id, "rsvp")
    
    if captcha_check["requires_captcha"]:
        # CAPTCHA is required, verify it
        if not captcha_id or not captcha_answer:
            raise HTTPException(
                status_code=400,
                detail="CAPTCHA verification is required. Please complete the CAPTCHA challenge."
            )
        
        # Verify CAPTCHA
        try:
            captcha_challenge = await db.captcha_challenges.find_one({"id": captcha_id}, {"_id": 0})
            
            if not captcha_challenge:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid CAPTCHA. Please try again."
                )
            
            # Check if expired
            expires_at = captcha_challenge.get('expires_at')
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if datetime.now(timezone.utc) > expires_at:
                await db.captcha_challenges.delete_one({"id": captcha_id})
                raise HTTPException(
                    status_code=400,
                    detail="CAPTCHA expired. Please request a new challenge."
                )
            
            # Verify answer
            expected_answer_hash = captcha_challenge.get('answer')
            provided_answer_hash = hashlib.sha256(str(captcha_answer).encode()).hexdigest()
            
            if provided_answer_hash != expected_answer_hash:
                # Wrong answer - track failed attempt
                await track_submission_attempt(client_ip, device_id, "rsvp", slug, False, True)
                await db.captcha_challenges.delete_one({"id": captcha_id})
                raise HTTPException(
                    status_code=400,
                    detail="Incorrect CAPTCHA answer. Please try again."
                )
            
            # Correct answer - delete challenge
            await db.captcha_challenges.delete_one({"id": captcha_id})
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"CAPTCHA verification error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="CAPTCHA verification failed. Please try again."
            )
    
    # Find profile by slug
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    # Check if profile is active and not expired
    if not await check_profile_active(profile):
        raise HTTPException(status_code=410, detail="This invitation link has expired")
    
    # PHASE 12: Check invitation expiry (separate from link expiry)
    expires_at = profile.get('expires_at')
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=403, detail="This invitation has expired. RSVP submissions are no longer available.")
    
    # Check for duplicate RSVP (profile_id + guest_phone)
    existing_rsvp = await db.rsvps.find_one({
        "profile_id": profile['id'],
        "guest_phone": rsvp_data.guest_phone
    }, {"_id": 0})
    
    if existing_rsvp:
        # PHASE 11: Check if within 48 hours - allow update instead
        if isinstance(existing_rsvp.get('created_at'), str):
            created_at = datetime.fromisoformat(existing_rsvp['created_at'])
        else:
            created_at = existing_rsvp['created_at']
        
        time_since_creation = datetime.now(timezone.utc) - created_at
        if time_since_creation <= timedelta(hours=48):
            # Update existing RSVP
            update_doc = {
                "guest_name": rsvp_data.guest_name,
                "status": rsvp_data.status,
                "guest_count": rsvp_data.guest_count,
                "message": rsvp_data.message,
                "dietary_preference": rsvp_data.dietary_preference,
                "allergies": rsvp_data.allergies,
                "plus_one": rsvp_data.plus_one,
                "kids_count": rsvp_data.kids_count,
            }
            
            await db.rsvps.update_one(
                {"id": existing_rsvp['id']},
                {"$set": update_doc}
            )
            
            # Fetch updated RSVP
            updated_rsvp = await db.rsvps.find_one({"id": existing_rsvp['id']}, {"_id": 0})
            if isinstance(updated_rsvp.get('created_at'), str):
                updated_rsvp['created_at'] = datetime.fromisoformat(updated_rsvp['created_at'])
            
            return RSVPResponse(**updated_rsvp)
        else:
            raise HTTPException(
                status_code=400,
                detail="You have already submitted an RSVP. Edits are only allowed within 48 hours of submission."
            )
    
    # Create RSVP
    rsvp = RSVP(
        profile_id=profile['id'],
        guest_name=rsvp_data.guest_name,
        guest_phone=rsvp_data.guest_phone,
        status=rsvp_data.status,
        guest_count=rsvp_data.guest_count,
        message=rsvp_data.message,
        dietary_preference=rsvp_data.dietary_preference,
        allergies=rsvp_data.allergies,
        plus_one=rsvp_data.plus_one,
        kids_count=rsvp_data.kids_count,
    )
    
    doc = rsvp.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.rsvps.insert_one(doc)
    
    # PHASE 32: Track successful submission (resets CAPTCHA requirement)
    await track_submission_attempt(client_ip, device_id, "rsvp", slug, True, captcha_check["requires_captcha"])
    
    return RSVPResponse(
        id=rsvp.id,
        guest_name=rsvp.guest_name,
        guest_phone=rsvp.guest_phone,
        status=rsvp.status,
        guest_count=rsvp.guest_count,
        message=rsvp.message,
        dietary_preference=rsvp.dietary_preference,
        allergies=rsvp.allergies,
        plus_one=rsvp.plus_one,
        kids_count=rsvp.kids_count,
        created_at=rsvp.created_at
    )


@api_router.get("/invite/{slug}/rsvp/check")
async def check_rsvp_status(slug: str, phone: str, guest_name: Optional[str] = None):
    """
    PHASE 11 + PHASE 32: Check if RSVP exists and if it can be edited
    
    SECURITY FIX: 
    - Without guest_name: Returns only minimal data (exists, can_edit, hours_remaining)
    - With guest_name: Verifies ownership and returns full RSVP data for editing
    This prevents unauthorized access to RSVP data while maintaining edit functionality
    """
    # Find profile by slug
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    # Find RSVP by phone
    existing_rsvp = await db.rsvps.find_one({
        "profile_id": profile['id'],
        "guest_phone": phone
    }, {"_id": 0})
    
    if not existing_rsvp:
        return {
            "exists": False,
            "can_edit": False,
            "hours_remaining": 0
        }
    
    # Convert created_at if string
    if isinstance(existing_rsvp.get('created_at'), str):
        created_at = datetime.fromisoformat(existing_rsvp['created_at'])
    else:
        created_at = existing_rsvp['created_at']
    
    # Check if within 48 hours
    time_since_creation = datetime.now(timezone.utc) - created_at
    can_edit = time_since_creation <= timedelta(hours=48)
    
    # If guest_name is provided, verify ownership before returning full data
    if guest_name and can_edit:
        # Case-insensitive comparison for name verification
        provided_name = guest_name.strip().lower()
        stored_name = existing_rsvp.get('guest_name', '').strip().lower()
        
        if provided_name == stored_name:
            # Ownership verified - return full RSVP data for editing
            if isinstance(existing_rsvp.get('created_at'), str):
                existing_rsvp['created_at'] = datetime.fromisoformat(existing_rsvp['created_at'])
            
            return {
                "exists": True,
                "can_edit": True,
                "hours_remaining": max(0, 48 - (time_since_creation.total_seconds() / 3600)),
                "rsvp": RSVPResponse(**existing_rsvp)
            }
        else:
            # Name doesn't match - potential unauthorized access attempt
            return {
                "exists": True,
                "can_edit": False,
                "hours_remaining": 0,
                "error": "Name verification failed"
            }
    
    # SECURITY: Without name verification, only return minimal information
    return {
        "exists": True,
        "can_edit": can_edit,
        "hours_remaining": max(0, 48 - (time_since_creation.total_seconds() / 3600)) if can_edit else 0
    }


@api_router.put("/rsvp/{rsvp_id}", response_model=RSVPResponse)
async def update_rsvp(rsvp_id: str, rsvp_data: RSVPCreate):
    """PHASE 11: Update RSVP within 48 hours of creation"""
    # Find existing RSVP
    existing_rsvp = await db.rsvps.find_one({"id": rsvp_id}, {"_id": 0})
    
    if not existing_rsvp:
        raise HTTPException(status_code=404, detail="RSVP not found")
    
    # Convert created_at if string
    if isinstance(existing_rsvp.get('created_at'), str):
        created_at = datetime.fromisoformat(existing_rsvp['created_at'])
    else:
        created_at = existing_rsvp['created_at']
    
    # Check if within 48 hours
    time_since_creation = datetime.now(timezone.utc) - created_at
    if time_since_creation > timedelta(hours=48):
        raise HTTPException(
            status_code=403,
            detail="Cannot edit RSVP after 48 hours of submission"
        )
    
    # Verify phone number matches (security check)
    if existing_rsvp['guest_phone'] != rsvp_data.guest_phone:
        raise HTTPException(
            status_code=403,
            detail="Phone number does not match original RSVP"
        )
    
    # Update RSVP
    update_doc = {
        "guest_name": rsvp_data.guest_name,
        "status": rsvp_data.status,
        "guest_count": rsvp_data.guest_count,
        "message": rsvp_data.message
    }
    
    result = await db.rsvps.update_one(
        {"id": rsvp_id},
        {"$set": update_doc}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="RSVP not found or no changes made")
    
    # Fetch updated RSVP
    updated_rsvp = await db.rsvps.find_one({"id": rsvp_id}, {"_id": 0})
    
    # Convert date strings
    if isinstance(updated_rsvp.get('created_at'), str):
        updated_rsvp['created_at'] = datetime.fromisoformat(updated_rsvp['created_at'])
    
    return RSVPResponse(**updated_rsvp)


@api_router.get("/admin/profiles/{profile_id}/rsvps", response_model=List[RSVPResponse])
async def get_profile_rsvps(
    profile_id: str,
    status: Optional[str] = None,
    admin_id: str = Depends(get_current_admin)
):
    """Get all RSVPs for a profile with optional status filter"""
    # Build query
    query = {"profile_id": profile_id}
    if status and status in ['yes', 'no', 'maybe']:
        query['status'] = status
    
    # Fetch RSVPs (limit 500)
    rsvps = await db.rsvps.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(500).to_list(500)
    
    # Convert date strings
    for rsvp in rsvps:
        if isinstance(rsvp.get('created_at'), str):
            rsvp['created_at'] = datetime.fromisoformat(rsvp['created_at'])
    
    return [RSVPResponse(**r) for r in rsvps]


@api_router.get("/admin/profiles/{profile_id}/rsvps/stats", response_model=RSVPStats)
async def get_rsvp_stats(profile_id: str, admin_id: str = Depends(get_current_admin)):
    """Get RSVP statistics for a profile"""
    # Get all RSVPs for the profile
    rsvps = await db.rsvps.find(
        {"profile_id": profile_id},
        {"_id": 0}
    ).to_list(500)
    
    # Calculate statistics
    total_rsvps = len(rsvps)
    attending_count = sum(1 for r in rsvps if r['status'] == 'yes')
    not_attending_count = sum(1 for r in rsvps if r['status'] == 'no')
    maybe_count = sum(1 for r in rsvps if r['status'] == 'maybe')
    total_guest_count = sum(r.get('guest_count', 1) for r in rsvps if r['status'] == 'yes')
    
    return RSVPStats(
        total_rsvps=total_rsvps,
        attending_count=attending_count,
        not_attending_count=not_attending_count,
        maybe_count=maybe_count,
        total_guest_count=total_guest_count
    )


@api_router.get("/admin/profiles/{profile_id}/rsvps/export")
async def export_rsvps_csv(profile_id: str, admin_id: str = Depends(get_current_admin)):
    """Export RSVPs as CSV"""
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    # Fetch all RSVPs
    rsvps = await db.rsvps.find(
        {"profile_id": profile_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    
    # Convert to CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Guest Name', 'Phone', 'Status', 'Guest Count', 'Message', 'Submitted At'])
    
    # Write data
    for rsvp in rsvps:
        created_at = rsvp.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        writer.writerow([
            rsvp.get('guest_name', ''),
            rsvp.get('guest_phone', ''),
            rsvp.get('status', ''),
            rsvp.get('guest_count', 1),
            rsvp.get('message', ''),
            created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else ''
        ])
    
    # Prepare response
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=rsvps_{profile_id}.csv"
        }
    )


# ============================================================================
# BUCKET 1A — Song Requests & Guest Check-Ins
# ============================================================================

@api_router.post("/invite/{slug}/song-requests", response_model=SongRequestResponse)
async def submit_song_request(slug: str, payload: SongRequestCreate):
    """Public endpoint — guest submits a song suggestion."""
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if not await check_profile_active(profile):
        raise HTTPException(status_code=410, detail="This invitation link has expired")

    settings = (profile.get('song_requests_settings') or {})
    if not settings.get('enabled', False):
        raise HTTPException(status_code=403, detail="Song requests are not enabled for this invitation")

    max_per_guest = int(settings.get('max_per_guest', 3) or 3)

    # Per-guest limit (by name + phone)
    query = {"profile_id": profile['id'], "guest_name": payload.guest_name.strip()}
    if payload.guest_phone:
        query["guest_phone"] = payload.guest_phone
    existing = await db.song_requests.count_documents(query)
    if existing >= max_per_guest:
        raise HTTPException(
            status_code=429,
            detail=f"You have reached the limit of {max_per_guest} song requests."
        )

    sr = SongRequest(
        profile_id=profile['id'],
        guest_name=payload.guest_name,
        guest_phone=payload.guest_phone,
        song_title=payload.song_title,
        artist=payload.artist,
        provider_url=payload.provider_url,
        message=payload.message,
    )
    await db.song_requests.insert_one(sr.model_dump())
    return SongRequestResponse(
        id=sr.id,
        guest_name=sr.guest_name,
        song_title=sr.song_title,
        artist=sr.artist,
        provider_url=sr.provider_url,
        message=sr.message,
        created_at=sr.created_at,
    )


@api_router.get("/invite/{slug}/song-requests", response_model=List[SongRequestResponse])
async def list_song_requests_public(slug: str, limit: int = 30):
    """Public endpoint — list recent song requests (no PII)."""
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")

    settings = (profile.get('song_requests_settings') or {})
    if not settings.get('enabled', False):
        return []

    rows = await db.song_requests.find(
        {"profile_id": profile['id']}, {"_id": 0}
    ).sort("created_at", -1).limit(max(1, min(int(limit or 30), 100))).to_list(100)

    out: List[SongRequestResponse] = []
    for r in rows:
        if isinstance(r.get('created_at'), str):
            r['created_at'] = datetime.fromisoformat(r['created_at'])
        out.append(SongRequestResponse(
            id=r['id'],
            guest_name=r.get('guest_name', ''),
            song_title=r.get('song_title', ''),
            artist=r.get('artist'),
            provider_url=r.get('provider_url'),
            message=r.get('message'),
            created_at=r['created_at'],
        ))
    return out


@api_router.get("/admin/profiles/{profile_id}/song-requests", response_model=List[SongRequestResponse])
async def admin_list_song_requests(profile_id: str, admin_id: str = Depends(get_current_admin)):
    """Admin endpoint — list all song requests for a profile."""
    # Ownership check (admin must own profile)
    profile = await db.profiles.find_one({"id": profile_id, "admin_id": admin_id}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    rows = await db.song_requests.find(
        {"profile_id": profile_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)

    out = []
    for r in rows:
        if isinstance(r.get('created_at'), str):
            r['created_at'] = datetime.fromisoformat(r['created_at'])
        out.append(SongRequestResponse(
            id=r['id'],
            guest_name=r.get('guest_name', ''),
            song_title=r.get('song_title', ''),
            artist=r.get('artist'),
            provider_url=r.get('provider_url'),
            message=r.get('message'),
            created_at=r['created_at'],
        ))
    return out


@api_router.delete("/admin/song-requests/{request_id}")
async def admin_delete_song_request(request_id: str, admin_id: str = Depends(get_current_admin)):
    """Admin endpoint — delete a song request (owner-only)."""
    sr = await db.song_requests.find_one({"id": request_id}, {"_id": 0})
    if not sr:
        raise HTTPException(status_code=404, detail="Song request not found")

    profile = await db.profiles.find_one({"id": sr.get('profile_id'), "admin_id": admin_id}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=403, detail="Not authorized to delete this song request")

    await db.song_requests.delete_one({"id": request_id})
    return {"success": True}


@api_router.post("/invite/{slug}/check-in", response_model=CheckInResponse)
async def guest_check_in(slug: str, payload: CheckInCreate):
    """Public endpoint — guest checks in at the venue/event."""
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if not await check_profile_active(profile):
        raise HTTPException(status_code=410, detail="This invitation link has expired")

    sections = profile.get('sections_enabled', {}) or {}
    if not sections.get('check_in', False):
        raise HTTPException(status_code=403, detail="Check-in is not enabled for this invitation")

    # Validate event_id (if provided) belongs to this profile
    event_id = payload.event_id
    if event_id:
        events = profile.get('events', []) or []
        if not any((e.get('event_id') == event_id) for e in events):
            raise HTTPException(status_code=400, detail="Invalid event_id")

    # Prevent rapid duplicates (same guest_name + phone + event within 30 min)
    # Match guest_name case-insensitively to avoid 'Riya' vs 'riya' duplicates.
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
    name_regex = re.compile(f"^{re.escape(payload.guest_name.strip())}$", re.IGNORECASE)
    dup_q: Dict[str, Any] = {"profile_id": profile['id'], "guest_name": name_regex}
    if event_id:
        dup_q["event_id"] = event_id
    if payload.guest_phone:
        dup_q["guest_phone"] = payload.guest_phone
    recent = await db.check_ins.find(dup_q, {"_id": 0}).sort("created_at", -1).limit(1).to_list(1)
    if recent:
        ts = recent[0].get('created_at')
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts and ts > cutoff:
            return CheckInResponse(
                id=recent[0]['id'],
                guest_name=recent[0]['guest_name'],
                event_id=recent[0].get('event_id'),
                created_at=ts,
            )

    ci = CheckIn(
        profile_id=profile['id'],
        event_id=event_id,
        guest_name=payload.guest_name,
        guest_phone=payload.guest_phone,
        note=payload.note,
        source=(payload.source or "web"),
    )
    await db.check_ins.insert_one(ci.model_dump())
    return CheckInResponse(
        id=ci.id,
        guest_name=ci.guest_name,
        event_id=ci.event_id,
        created_at=ci.created_at,
    )


@api_router.get("/admin/profiles/{profile_id}/check-ins")
async def admin_list_check_ins(profile_id: str, admin_id: str = Depends(get_current_admin)):
    """Admin endpoint — list check-ins + per-event stats."""
    profile = await db.profiles.find_one({"id": profile_id, "admin_id": admin_id}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    rows = await db.check_ins.find(
        {"profile_id": profile_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(1000)

    per_event: Dict[str, int] = {}
    for r in rows:
        key = r.get('event_id') or "_general"
        per_event[key] = per_event.get(key, 0) + 1

    # Coerce timestamps
    for r in rows:
        if isinstance(r.get('created_at'), str):
            r['created_at'] = datetime.fromisoformat(r['created_at'])

    return {
        "check_ins": rows,
        "stats": {
            "total_check_ins": len(rows),
            "per_event": per_event,
        }
    }


# ============================================================================
# END Bucket 1A routes
# ============================================================================


# ==================== ANALYTICS ROUTES (PHASE 9 - ENHANCED) ====================

@api_router.post("/invite/{slug}/view", status_code=204)
async def track_invitation_view(slug: str, view_data: ViewTrackingRequest):
    """Track invitation view with session-based unique visitor tracking (Phase 9)"""
    # Find profile by slug
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    profile_id = profile['id']
    now = datetime.now(timezone.utc)
    current_date = now.date().isoformat()
    current_hour = str(now.hour)
    
    # Check if session exists and is valid (24-hour window)
    existing_session = await db.view_sessions.find_one({
        "session_id": view_data.session_id,
        "profile_id": profile_id,
        "expires_at": {"$gt": now.isoformat()}
    })
    
    is_unique_view = existing_session is None
    
    # If no valid session exists, create one
    if is_unique_view:
        session = ViewSession(
            session_id=view_data.session_id,
            profile_id=profile_id,
            device_type=view_data.device_type,
            created_at=now,
            expires_at=now + timedelta(hours=24)
        )
        
        session_doc = session.model_dump()
        session_doc['created_at'] = session_doc['created_at'].isoformat()
        session_doc['expires_at'] = session_doc['expires_at'].isoformat()
        
        await db.view_sessions.insert_one(session_doc)
    
    # Find or create analytics document
    analytics_doc = await db.analytics.find_one({"profile_id": profile_id}, {"_id": 0})
    
    if analytics_doc:
        # Update existing analytics
        update_data = {
            "total_views": analytics_doc.get('total_views', 0) + 1,
            "last_viewed_at": now.isoformat()
        }
        
        # Update unique views if new session
        if is_unique_view:
            update_data["unique_views"] = analytics_doc.get('unique_views', 0) + 1
            
            # Set first_viewed_at if not set
            if not analytics_doc.get('first_viewed_at'):
                update_data["first_viewed_at"] = now.isoformat()
        
        # Increment device-specific counter
        if view_data.device_type == "mobile":
            update_data["mobile_views"] = analytics_doc.get('mobile_views', 0) + 1
        elif view_data.device_type == "desktop":
            update_data["desktop_views"] = analytics_doc.get('desktop_views', 0) + 1
        elif view_data.device_type == "tablet":
            update_data["tablet_views"] = analytics_doc.get('tablet_views', 0) + 1
        
        # Update hourly distribution
        hourly_dist = analytics_doc.get('hourly_distribution', {})
        hourly_dist[current_hour] = hourly_dist.get(current_hour, 0) + 1
        update_data["hourly_distribution"] = hourly_dist
        
        # Update daily views (keep last 30 days)
        daily_views = analytics_doc.get('daily_views', [])
        today_entry = next((dv for dv in daily_views if dv['date'] == current_date), None)
        
        if today_entry:
            today_entry['count'] += 1
        else:
            daily_views.append({"date": current_date, "count": 1})
        
        # Keep only last 30 days
        if len(daily_views) > 30:
            daily_views = sorted(daily_views, key=lambda x: x['date'], reverse=True)[:30]
        
        update_data["daily_views"] = daily_views
        
        await db.analytics.update_one(
            {"profile_id": profile_id},
            {"$set": update_data}
        )
    else:
        # Create new analytics document
        analytics = Analytics(
            profile_id=profile_id,
            total_views=1,
            unique_views=1 if is_unique_view else 0,
            mobile_views=1 if view_data.device_type == "mobile" else 0,
            desktop_views=1 if view_data.device_type == "desktop" else 0,
            tablet_views=1 if view_data.device_type == "tablet" else 0,
            first_viewed_at=now,
            last_viewed_at=now,
            daily_views=[{"date": current_date, "count": 1}],
            hourly_distribution={current_hour: 1},
            language_views={},
            map_clicks=0,
            rsvp_clicks=0,
            music_plays=0,
            music_pauses=0
        )
        
        doc = analytics.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['first_viewed_at'] = doc['first_viewed_at'].isoformat()
        doc['last_viewed_at'] = doc['last_viewed_at'].isoformat()
        
        await db.analytics.insert_one(doc)
    
    # Return 204 No Content for fast response
    return None


@api_router.post("/invite/{slug}/track-language", status_code=204)
async def track_language_view(slug: str, language_data: LanguageTrackingRequest):
    """Track language selection (public endpoint, Phase 9)"""
    # Find profile by slug
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    profile_id = profile['id']
    
    # Update analytics with language view
    analytics_doc = await db.analytics.find_one({"profile_id": profile_id}, {"_id": 0})
    
    if analytics_doc:
        language_views = analytics_doc.get('language_views', {})
        language_views[language_data.language_code] = language_views.get(language_data.language_code, 0) + 1
        
        await db.analytics.update_one(
            {"profile_id": profile_id},
            {"$set": {"language_views": language_views}}
        )
    
    return None


@api_router.post("/invite/{slug}/track-interaction", status_code=204)
async def track_interaction(slug: str, interaction_data: InteractionTrackingRequest):
    """Track user interactions (public endpoint, Phase 9)"""
    # Find profile by slug
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    profile_id = profile['id']
    
    # Update analytics with interaction
    analytics_doc = await db.analytics.find_one({"profile_id": profile_id}, {"_id": 0})
    
    if analytics_doc:
        update_data = {}
        
        if interaction_data.interaction_type == "map_click":
            update_data["map_clicks"] = analytics_doc.get('map_clicks', 0) + 1
        elif interaction_data.interaction_type == "rsvp_click":
            update_data["rsvp_clicks"] = analytics_doc.get('rsvp_clicks', 0) + 1
        elif interaction_data.interaction_type == "music_play":
            update_data["music_plays"] = analytics_doc.get('music_plays', 0) + 1
        elif interaction_data.interaction_type == "music_pause":
            update_data["music_pauses"] = analytics_doc.get('music_pauses', 0) + 1
        
        if update_data:
            await db.analytics.update_one(
                {"profile_id": profile_id},
                {"$set": update_data}
            )
    
    return None


@api_router.get("/admin/profiles/{profile_id}/analytics", response_model=AnalyticsResponse)
async def get_profile_analytics(profile_id: str, admin_id: str = Depends(get_current_admin)):
    """Get detailed analytics for a specific profile (admin only, Phase 9)"""
    # Verify profile exists
    profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Get analytics
    analytics_doc = await db.analytics.find_one({"profile_id": profile_id}, {"_id": 0})
    
    if not analytics_doc:
        # Return zero stats if no views yet
        return AnalyticsResponse(
            profile_id=profile_id,
            total_views=0,
            unique_views=0,
            mobile_views=0,
            desktop_views=0,
            tablet_views=0,
            first_viewed_at=None,
            last_viewed_at=None,
            daily_views=[],
            hourly_distribution={},
            language_views={},
            map_clicks=0,
            rsvp_clicks=0,
            music_plays=0,
            music_pauses=0
        )
    
    # Convert datetime strings if needed
    first_viewed = analytics_doc.get('first_viewed_at')
    if isinstance(first_viewed, str):
        first_viewed = datetime.fromisoformat(first_viewed)
    
    last_viewed = analytics_doc.get('last_viewed_at')
    if isinstance(last_viewed, str):
        last_viewed = datetime.fromisoformat(last_viewed)
    
    # Convert daily_views to DailyView objects
    daily_views_data = analytics_doc.get('daily_views', [])
    daily_views = [DailyView(**dv) if isinstance(dv, dict) else dv for dv in daily_views_data]
    
    return AnalyticsResponse(
        profile_id=analytics_doc['profile_id'],
        total_views=analytics_doc.get('total_views', 0),
        unique_views=analytics_doc.get('unique_views', 0),
        mobile_views=analytics_doc.get('mobile_views', 0),
        desktop_views=analytics_doc.get('desktop_views', 0),
        tablet_views=analytics_doc.get('tablet_views', 0),
        first_viewed_at=first_viewed,
        last_viewed_at=last_viewed,
        daily_views=daily_views,
        hourly_distribution=analytics_doc.get('hourly_distribution', {}),
        language_views=analytics_doc.get('language_views', {}),
        map_clicks=analytics_doc.get('map_clicks', 0),
        rsvp_clicks=analytics_doc.get('rsvp_clicks', 0),
        music_plays=analytics_doc.get('music_plays', 0),
        music_pauses=analytics_doc.get('music_pauses', 0)
    )


@api_router.get("/admin/profiles/{profile_id}/analytics/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(profile_id: str, date_range: str = "7d", admin_id: str = Depends(get_current_admin)):
    """Get analytics summary with date range filter (admin only, Phase 9)
    
    Args:
        date_range: "7d" (last 7 days), "30d" (last 30 days), or "all" (all time)
    """
    # Verify profile exists
    profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Get analytics
    analytics_doc = await db.analytics.find_one({"profile_id": profile_id}, {"_id": 0})
    
    if not analytics_doc:
        return AnalyticsSummary(
            total_views=0,
            unique_visitors=0,
            most_viewed_language=None,
            peak_hour=None,
            device_breakdown={"mobile": 0, "desktop": 0, "tablet": 0}
        )
    
    # Apply date range filter for daily views
    daily_views = analytics_doc.get('daily_views', [])
    if date_range != "all" and daily_views:
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=int(date_range[:-1]))).date().isoformat()
        daily_views = [dv for dv in daily_views if dv['date'] >= cutoff_date]
    
    # Calculate filtered total views
    if date_range == "all":
        filtered_total_views = analytics_doc.get('total_views', 0)
    else:
        filtered_total_views = sum(dv['count'] for dv in daily_views)
    
    # Find most viewed language
    language_views = analytics_doc.get('language_views', {})
    most_viewed_language = max(language_views.items(), key=lambda x: x[1])[0] if language_views else None
    
    # Find peak hour
    hourly_dist = analytics_doc.get('hourly_distribution', {})
    peak_hour = int(max(hourly_dist.items(), key=lambda x: x[1])[0]) if hourly_dist else None
    
    return AnalyticsSummary(
        total_views=filtered_total_views,
        unique_visitors=analytics_doc.get('unique_views', 0),
        most_viewed_language=most_viewed_language,
        peak_hour=peak_hour,
        device_breakdown={
            "mobile": analytics_doc.get('mobile_views', 0),
            "desktop": analytics_doc.get('desktop_views', 0),
            "tablet": analytics_doc.get('tablet_views', 0)
        }
    )


# =====================================================================
# Audit Logs - Track invitation views and visitors
# =====================================================================

@api_router.get("/admin/profiles/{profile_id}/audit-logs")
async def get_profile_audit_logs(
    profile_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Get audit logs for invitation views and visitors"""
    try:
        # Check ownership
        profile = await check_profile_ownership(profile_id, current_admin, db)
        
        # Get view statistics
        view_count = profile.get("view_count", 0)
        unique_visitors = profile.get("unique_visitors", 0)
        last_viewed_at = profile.get("last_viewed_at")
        
        # Get recent visitors
        visitors = await db.invitation_visitors.find(
            {"profile_id": profile_id}
        ).sort("last_visit", -1).limit(100).to_list(100)
        
        # Format visitors data
        visitors_data = []
        for visitor in visitors:
            visitors_data.append({
                "client_ip": visitor.get("client_ip", "unknown"),
                "first_visit": visitor.get("first_visit"),
                "last_visit": visitor.get("last_visit")
            })
        
        return {
            "success": True,
            "profile_id": profile_id,
            "view_count": view_count,
            "unique_visitors": unique_visitors,
            "last_viewed_at": last_viewed_at,
            "recent_visitors": visitors_data
        }
    except Exception as e:
        logger.error(f"Error retrieving audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/admin/profiles/{profile_id}/digital-shagun")
async def update_digital_shagun(
    profile_id: str,
    request: Dict[str, Any],
    current_admin: dict = Depends(get_current_admin)
):
    """Enable/update Digital Shagun (PhonePe integration)"""
    try:
        # Check ownership
        profile = await check_profile_ownership(profile_id, current_admin, db)
        
        enabled = request.get("enabled", False)
        phonepe_upi_id = request.get("phonepe_upi_id")
        
        update_data = {
            "digital_shagun_enabled": enabled,
            "phonepe_upi_id": phonepe_upi_id,
            "updated_at": datetime.now(timezone.utc)
        }
        
        await db.profiles.update_one(
            {"id": profile_id},
            {"$set": update_data}
        )
        
        return {
            "success": True,
            "message": "Digital Shagun updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating digital shagun: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PDF GENERATION ====================

# Design theme color mappings for PDF
THEME_COLORS = {
    'temple_divine': {'primary': (139, 115, 85), 'secondary': (212, 175, 55), 'text': (74, 55, 40), 'bg': (255, 248, 231)},
    'royal_classic': {'primary': (139, 0, 0), 'secondary': (255, 215, 0), 'text': (74, 26, 26), 'bg': (255, 245, 230)},
    'floral_soft': {'primary': (255, 182, 193), 'secondary': (255, 218, 185), 'text': (107, 78, 113), 'bg': (255, 240, 245)},
    'cinematic_luxury': {'primary': (26, 26, 26), 'secondary': (212, 175, 55), 'text': (245, 245, 245), 'bg': (44, 44, 44)},
    'heritage_scroll': {'primary': (139, 90, 43), 'secondary': (205, 133, 63), 'text': (74, 48, 23), 'bg': (250, 240, 230)},
    'minimal_elegant': {'primary': (128, 128, 128), 'secondary': (169, 169, 169), 'text': (64, 64, 64), 'bg': (255, 255, 255)},
    'modern_premium': {'primary': (47, 79, 79), 'secondary': (72, 209, 204), 'text': (245, 245, 245), 'bg': (32, 32, 32)},
    'artistic_handcrafted': {'primary': (160, 82, 45), 'secondary': (210, 180, 140), 'text': (101, 67, 33), 'bg': (255, 250, 240)}
}

# Language templates for PDF
LANGUAGE_TEMPLATES = {
    'english': {
        'opening_title': 'Wedding Invitation',
        'couple_label': 'Join us in celebrating the union of',
        'events_title': 'Event Schedule',
        'date_label': 'Date',
        'time_label': 'Time',
        'venue_label': 'Venue',
        'contact_title': 'Contact Information',
        'groom_label': 'Groom',
        'bride_label': 'Bride'
    },
    'telugu': {
        'opening_title': 'వివాహ ఆహ్వానం',
        'couple_label': 'మా వివాహ వేడుకలో పాల్గొనండి',
        'events_title': 'కార్యక్రమ షెడ్యూల్',
        'date_label': 'తేదీ',
        'time_label': 'సమయం',
        'venue_label': 'స్థలం',
        'contact_title': 'సంప్రదించండి',
        'groom_label': 'వరుడు',
        'bride_label': 'వధువు'
    },
    'hindi': {
        'opening_title': 'विवाह निमंत्रण',
        'couple_label': 'हमारे विवाह समारोह में शामिल हों',
        'events_title': 'कार्यक्रम कार्यक्रम',
        'date_label': 'तारीख',
        'time_label': 'समय',
        'venue_label': 'स्थान',
        'contact_title': 'संपर्क जानकारी',
        'groom_label': 'वर',
        'bride_label': 'वधू'
    },
    'tamil': {
        'opening_title': 'திருமண அழைப்பிதழ்',
        'couple_label': 'எங்கள் திருமண நிகழ்வில் சேரவும்',
        'events_title': 'நிகழ்வு அட்டவணை',
        'date_label': 'தேதி',
        'time_label': 'நேரம்',
        'venue_label': 'இடம்',
        'contact_title': 'தொடர்பு தகவல்',
        'groom_label': 'மணமகன்',
        'bride_label': 'மணமகள்'
    },
    'kannada': {
        'opening_title': 'ಮದುವೆ ಆಮಂತ್ರಣ',
        'couple_label': 'ನಮ್ಮ ಮದುವೆ ಸಮಾರಂಭದಲ್ಲಿ ಸೇರಿ',
        'events_title': 'ಕಾರ್ಯಕ್ರಮದ ವೇಳಾಪಟ್ಟಿ',
        'date_label': 'ದಿನಾಂಕ',
        'time_label': 'ಸಮಯ',
        'venue_label': 'ಸ್ಥಳ',
        'contact_title': 'ಸಂಪರ್ಕ ಮಾಹಿತಿ',
        'groom_label': 'ವರ',
        'bride_label': 'ವಧು'
    },
    'malayalam': {
        'opening_title': 'വിവാഹ ക്ഷണം',
        'couple_label': 'ഞങ്ങളുടെ വിവാഹ ചടങ്ങിൽ പങ്കെടുക്കൂ',
        'events_title': 'പരിപാടി ഷെഡ്യൂൾ',
        'date_label': 'തീയതി',
        'time_label': 'സമയം',
        'venue_label': 'സ്ഥലം',
        'contact_title': 'ബന്ധപ്പെടുക',
        'groom_label': 'വരൻ',
        'bride_label': 'വധു'
    }
}


def get_theme_colors(design_id: str):
    """Get theme colors for PDF generation"""
    return THEME_COLORS.get(design_id, THEME_COLORS['royal_classic'])


def get_language_text(language: str):
    """Get language-specific text for PDF"""
    return LANGUAGE_TEMPLATES.get(language, LANGUAGE_TEMPLATES['english'])


def rgb_to_reportlab_color(rgb_tuple):
    """Convert RGB tuple to ReportLab color"""
    r, g, b = rgb_tuple
    return rl_colors.Color(r/255.0, g/255.0, b/255.0)


async def generate_invitation_pdf(profile: dict, language: str = 'english'):
    """Generate PDF invitation from profile data"""
    buffer = io.BytesIO()
    
    # Get theme colors and language text
    theme = get_theme_colors(profile.get('design_id', 'royal_classic'))
    lang_text = get_language_text(language)
    
    # Convert colors
    primary_color = rgb_to_reportlab_color(theme['primary'])
    secondary_color = rgb_to_reportlab_color(theme['secondary'])
    text_color = rgb_to_reportlab_color(theme['text'])
    
    # Get deity background path if present
    deity_id = profile.get('deity_id')
    deity_bg_path = None
    if deity_id and deity_id != 'none':
        # Map deity IDs to local file paths
        deity_file_map = {
            'ganesha': '/app/frontend/public/assets/deities/ganesha_desktop.jpg',
            'venkateswara_padmavati': '/app/frontend/public/assets/deities/venkateswara_padmavati_desktop.jpg',
            'shiva_parvati': '/app/frontend/public/assets/deities/shiva_parvati_desktop.jpg',
            'lakshmi_vishnu': '/app/frontend/public/assets/deities/lakshmi_vishnu_desktop.jpg'
        }
        deity_bg_path = deity_file_map.get(deity_id)
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Container for PDF elements
    story = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=primary_color,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Heading style
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=secondary_color,
        spaceAfter=12,
        spaceBefore=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Subheading style
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=primary_color,
        spaceAfter=8,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Body style
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        textColor=text_color,
        spaceAfter=6,
        alignment=TA_LEFT,
        fontName='Helvetica'
    )
    
    # Center body style
    center_body_style = ParagraphStyle(
        'CustomCenterBody',
        parent=body_style,
        alignment=TA_CENTER
    )
    
    # Add title
    story.append(Paragraph(lang_text['opening_title'], title_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Add couple names
    story.append(Paragraph(lang_text['couple_label'], center_body_style))
    story.append(Spacer(1, 0.2*inch))
    
    couple_text = f"<b>{profile['groom_name']}</b> & <b>{profile['bride_name']}</b>"
    story.append(Paragraph(couple_text, heading_style))
    story.append(Spacer(1, 0.4*inch))
    
    # Add events section
    events = profile.get('events', [])
    visible_events = [e for e in events if e.get('visible', True)]
    
    if visible_events:
        story.append(Paragraph(lang_text['events_title'], heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Sort events by date
        sorted_events = sorted(visible_events, key=lambda x: x.get('date', ''))
        
        for event in sorted_events:
            # Event name
            event_name_style = ParagraphStyle(
                'EventName',
                parent=subheading_style,
                fontSize=14,
                textColor=primary_color,
                alignment=TA_LEFT
            )
            story.append(Paragraph(f"<b>{event['name']}</b>", event_name_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Event details
            date_str = event.get('date', '')
            time_str = event.get('start_time', '')
            if event.get('end_time'):
                time_str += f" - {event['end_time']}"
            
            story.append(Paragraph(f"<b>{lang_text['date_label']}:</b> {date_str}", body_style))
            story.append(Paragraph(f"<b>{lang_text['time_label']}:</b> {time_str}", body_style))
            story.append(Paragraph(f"<b>{lang_text['venue_label']}:</b> {event.get('venue_name', '')}", body_style))
            story.append(Paragraph(f"{event.get('venue_address', '')}", body_style))
            
            if event.get('description'):
                story.append(Spacer(1, 0.05*inch))
                story.append(Paragraph(event['description'], body_style))
            
            story.append(Spacer(1, 0.25*inch))
    
    # Add contact information
    if profile.get('whatsapp_groom') or profile.get('whatsapp_bride'):
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(lang_text['contact_title'], heading_style))
        story.append(Spacer(1, 0.15*inch))
        
        if profile.get('whatsapp_groom'):
            story.append(Paragraph(
                f"<b>{lang_text['groom_label']}:</b> {profile['whatsapp_groom']}", 
                body_style
            ))
        
        if profile.get('whatsapp_bride'):
            story.append(Paragraph(
                f"<b>{lang_text['bride_label']}:</b> {profile['whatsapp_bride']}", 
                body_style
            ))
    
    # Build PDF with deity background if present
    if deity_bg_path and os.path.exists(deity_bg_path):
        def add_deity_background(canvas_obj, doc_obj):
            """Add deity background with very light opacity"""
            canvas_obj.saveState()
            try:
                # Load and compress deity image
                img = PILImage.open(deity_bg_path)
                
                # Resize to optimize file size (max 800px width)
                max_width = 800
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), PILImage.Resampling.LANCZOS)
                
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save compressed image to buffer
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='JPEG', quality=70, optimize=True)
                img_buffer.seek(0)
                
                # Create ReportLab Image
                img_reader = ImageReader(img_buffer)
                
                # Calculate centered position
                page_width, page_height = A4
                img_width, img_height = img.size
                
                # Scale to fit page while maintaining aspect ratio
                scale = min(page_width / img_width, page_height / img_height)
                scaled_width = img_width * scale
                scaled_height = img_height * scale
                
                # Center on page
                x = (page_width - scaled_width) / 2
                y = (page_height - scaled_height) / 2
                
                # Draw with very light opacity (0.12)
                canvas_obj.setFillAlpha(0.12)
                canvas_obj.drawImage(
                    img_reader, 
                    x, y, 
                    width=scaled_width, 
                    height=scaled_height,
                    preserveAspectRatio=True,
                    mask='auto'
                )
            except Exception as e:
                # If deity image fails, continue without it
                logging.warning(f"Failed to add deity background: {e}")
            finally:
                canvas_obj.restoreState()
        
        doc.build(story, onFirstPage=add_deity_background, onLaterPages=add_deity_background)
    else:
        doc.build(story)
    
    # Get PDF data
    buffer.seek(0)
    return buffer


@api_router.get("/admin/profiles/{profile_id}/download-pdf")
async def download_invitation_pdf(
    profile_id: str, 
    language: str = 'english',
    admin_id: str = Depends(get_current_admin)
):
    """Generate and download PDF invitation (admin only)"""
    # Fetch profile
    profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Generate PDF
    pdf_buffer = await generate_invitation_pdf(profile, language)
    
    # Create filename
    groom_name = re.sub(r'[^a-zA-Z]', '', profile['groom_name'].split()[0].lower())
    bride_name = re.sub(r'[^a-zA-Z]', '', profile['bride_name'].split()[0].lower())
    filename = f"wedding-invitation-{groom_name}-{bride_name}.pdf"
    
    # Return PDF as download
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# ==================== CONFIGURATION ROUTES ====================

@api_router.get("/config/designs")
async def get_designs():
    """Get all available design themes"""
    designs = [
        {
            "id": "royal_classic",
            "name": "Royal Classic",
            "description": "Elegant maroon and gold with traditional motifs",
            "thumbnail": "/assets/designs/royal_classic_thumb.webp",
            "preview": "/assets/designs/royal_classic_preview.webp"
        },
        {
            "id": "floral_soft",
            "name": "Floral Soft",
            "description": "Pastel pink with delicate floral patterns",
            "thumbnail": "/assets/designs/floral_soft_thumb.webp",
            "preview": "/assets/designs/floral_soft_preview.webp"
        },
        {
            "id": "divine_temple",
            "name": "Divine Temple",
            "description": "Warm ivory and gold with sacred temple aesthetics",
            "thumbnail": "/assets/designs/divine_temple_thumb.webp",
            "preview": "/assets/designs/divine_temple_preview.webp"
        },
        {
            "id": "modern_minimal",
            "name": "Modern Minimal",
            "description": "Clean white and gray with contemporary design",
            "thumbnail": "/assets/designs/modern_minimal_thumb.webp",
            "preview": "/assets/designs/modern_minimal_preview.webp"
        },
        {
            "id": "cinematic_luxury",
            "name": "Cinematic Luxury",
            "description": "Dark gradient with gold accents and premium feel",
            "thumbnail": "/assets/designs/cinematic_luxury_thumb.webp",
            "preview": "/assets/designs/cinematic_luxury_preview.webp"
        }
    ]
    return designs


@api_router.get("/config/deities")
async def get_deities():
    """Get all available deity options"""
    deities = [
        {
            "id": "none",
            "name": "No Religious Theme",
            "description": "Secular invitation without deity imagery",
            "thumbnail": "/assets/deities/none.svg"
        },
        {
            "id": "ganesha",
            "name": "Lord Ganesha",
            "description": "Remover of obstacles, auspicious beginning",
            "thumbnail": "/assets/deities/ganesha_thumb.webp",
            "languages": ["english", "telugu", "hindi"]
        },
        {
            "id": "venkateswara_padmavati",
            "name": "Lord Venkateswara & Padmavati",
            "description": "Divine couple symbolizing eternal love",
            "thumbnail": "/assets/deities/venkateswara_padmavati_thumb.webp",
            "languages": ["english", "telugu", "hindi"]
        },
        {
            "id": "shiva_parvati",
            "name": "Lord Shiva & Parvati",
            "description": "Perfect union of masculine and feminine energy",
            "thumbnail": "/assets/deities/shiva_parvati_thumb.webp",
            "languages": ["english", "telugu", "hindi"]
        },
        {
            "id": "lakshmi_vishnu",
            "name": "Lakshmi & Vishnu",
            "description": "Wealth, prosperity, and harmony",
            "thumbnail": "/assets/deities/lakshmi_vishnu_thumb.webp",
            "languages": ["english", "telugu", "hindi"]
        }
    ]
    return deities


@api_router.get("/config/languages")
async def get_languages():
    """Get available language configuration"""
    languages = [
        {
            "code": "english",
            "name": "English",
            "nativeName": "English",
            "rtl": False
        },
        {
            "code": "telugu",
            "name": "Telugu",
            "nativeName": "తెలుగు",
            "rtl": False
        },
        {
            "code": "hindi",
            "name": "Hindi",
            "nativeName": "हिन्दी",
            "rtl": False
        }
    ]
    return languages



# ==================== GUEST ROOM LOOKUP (Find My Room) ====================
# NOTE: The actual route handler is defined earlier (right after the public
# /invite/{slug} block) to win FastAPI's order-based route matching against
# `/invite/{slug}/{event_type}`. This section header remains for navigability.



# ==================== PHASE 11: QR CODE & CALENDAR ROUTES ====================

@api_router.get("/invite/{slug}/qr")
async def generate_qr_code(slug: str):
    """PHASE 11: Generate QR code for invitation link"""
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    # Build invitation URL
    invitation_url = f"https://wedding-mate-1.preview.emergentagent.com/invite/{slug}"
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(invitation_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return StreamingResponse(img_bytes, media_type="image/png")


@api_router.get("/invite/{slug}/calendar")
async def download_calendar(slug: str, event_id: Optional[str] = None):
    """PHASE 11: Generate .ics calendar file for wedding events.

    If `event_id` is provided, only that single event is exported (used by the
    per-event "Add to Calendar" pill on the live timeline).
    """
    profile = await db.profiles.find_one({"slug": slug}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    if not await check_profile_active(profile):
        raise HTTPException(status_code=410, detail="This invitation link has expired")
    
    # Convert date string if needed
    if isinstance(profile.get('event_date'), str):
        profile['event_date'] = datetime.fromisoformat(profile['event_date'])
    
    # Get events (optionally filtered to a single event_id)
    events = profile.get('events', []) or []
    if event_id:
        events = [e for e in events if e.get('event_id') == event_id]
        if not events:
            raise HTTPException(status_code=404, detail="Event not found for this invitation")
    
    # Build .ics file content
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Wedding Invitation//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]
    
    # If events exist, use those; otherwise use main event_date
    if events and len(events) > 0:
        for event in events:
            if not event.get('visible', True):
                continue
            
            # Parse event date and time
            event_date = datetime.strptime(event['date'], '%Y-%m-%d')
            start_time_parts = event['start_time'].split(':')
            event_datetime = event_date.replace(
                hour=int(start_time_parts[0]),
                minute=int(start_time_parts[1])
            )
            
            # End time (default to 2 hours later if not specified)
            if event.get('end_time'):
                end_time_parts = event['end_time'].split(':')
                end_datetime = event_date.replace(
                    hour=int(end_time_parts[0]),
                    minute=int(end_time_parts[1])
                )
            else:
                end_datetime = event_datetime + timedelta(hours=2)
            
            # Format dates for .ics
            dtstart = event_datetime.strftime('%Y%m%dT%H%M%S')
            dtend = end_datetime.strftime('%Y%m%dT%H%M%S')
            
            ics_lines.extend([
                "BEGIN:VEVENT",
                f"UID:{event.get('event_id', str(uuid.uuid4()))}@wedding-invitation",
                f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                f"SUMMARY:{event['name']} - {profile['groom_name']} & {profile['bride_name']}",
                f"LOCATION:{event['venue_name']}, {event['venue_address']}",
                f"DESCRIPTION:{event.get('description', '')}",
                "STATUS:CONFIRMED",
                "END:VEVENT"
            ])
    else:
        # Use main event_date
        event_datetime = profile['event_date']
        end_datetime = event_datetime + timedelta(hours=4)
        
        dtstart = event_datetime.strftime('%Y%m%dT%H%M%S')
        dtend = end_datetime.strftime('%Y%m%dT%H%M%S')
        
        ics_lines.extend([
            "BEGIN:VEVENT",
            f"UID:{profile['id']}@wedding-invitation",
            f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{profile['event_type'].title()} - {profile['groom_name']} & {profile['bride_name']}",
            f"LOCATION:{profile['venue']}, {profile.get('city', '')}",
            f"DESCRIPTION:Join us for our {profile['event_type']}",
            "STATUS:CONFIRMED",
            "END:VEVENT"
        ])
    
    ics_lines.append("END:VCALENDAR")
    ics_content = "\r\n".join(ics_lines)
    
    # Return as downloadable file
    from fastapi.responses import Response
    filename = f"wedding-{profile['groom_name']}-{profile['bride_name']}.ics".replace(" ", "-").lower()
    
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# ============================================================================
# PHASE 22: EVENT-WISE BACKGROUND & DESIGN ENGINE API ENDPOINTS
# ============================================================================

@api_router.get("/designs", response_model=DesignConfigResponse)
async def get_design_configurations(
    event_type: Optional[str] = None
):
    """
    Get all available design configurations, optionally filtered by event type
    
    Query Parameters:
    - event_type: Filter designs by event type (engagement, haldi, mehendi, marriage, reception)
    
    Returns list of design configurations with preview images and metadata
    """
    try:
        if event_type:
            # Validate and convert event type
            try:
                event_type_enum = EventType(event_type.lower())
                designs = get_designs_by_event_type(event_type_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid event_type. Must be one of: engagement, haldi, mehendi, marriage, reception"
                )
        else:
            designs = get_all_designs()
        
        return DesignConfigResponse(
            designs=designs,
            total=len(designs)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching design configurations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch design configurations")


@api_router.get("/designs/{design_id}", response_model=DesignConfig)
async def get_design_by_id_endpoint(design_id: str):
    """
    Get specific design configuration by ID
    
    Path Parameters:
    - design_id: Unique design identifier (e.g., "design_1")
    
    Returns complete design configuration including colors, preview, and metadata
    """
    try:
        design = get_design_by_id(design_id)
        
        if not design:
            raise HTTPException(
                status_code=404,
                detail=f"Design with ID '{design_id}' not found"
            )
        
        return design
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching design {design_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch design configuration")


@api_router.put("/admin/events/{event_id}/background")
async def update_event_background(
    event_id: str,
    background_request: UpdateEventBackgroundRequest,
    admin: Admin = Depends(get_current_admin)
):
    """
    Update background design for a specific event
    
    Path Parameters:
    - event_id: Event identifier
    
    Body:
    - background_design_id: Selected design ID
    - background_type: Rendering type (css, image, hybrid)
    - color_palette: Color scheme {primary, secondary, accent}
    
    Validates design compatibility with event type and lord decoration settings
    """
    try:
        # Find profile containing this event
        profile = await db.profiles.find_one({
            "events.event_id": event_id
        })
        
        if not profile:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Check admin authorization
        if profile['admin_id'] != admin.admin_id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this event")
        
        # Find the specific event
        event_index = None
        current_event = None
        for idx, event in enumerate(profile.get('events', [])):
            if event['event_id'] == event_id:
                event_index = idx
                current_event = event
                break
        
        if current_event is None:
            raise HTTPException(status_code=404, detail="Event not found in profile")
        
        # Validate design exists
        design = get_design_by_id(background_request.background_design_id)
        if not design:
            raise HTTPException(
                status_code=404,
                detail=f"Design '{background_request.background_design_id}' not found"
            )
        
        # Validate design compatibility with event
        event_type = EventType(current_event['event_type'])
        show_lord = current_event.get('show_lord', True)
        
        is_valid, message = validate_design_for_event(
            background_request.background_design_id,
            event_type,
            show_lord
        )
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        # Validate color palette
        required_colors = ['primary', 'secondary', 'accent']
        for color in required_colors:
            if color not in background_request.color_palette:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required color: {color}"
                )
        
        # Update event background
        update_result = await db.profiles.update_one(
            {"id": profile['id'], "events.event_id": event_id},
            {
                "$set": {
                    f"events.{event_index}.background_design_id": background_request.background_design_id,
                    f"events.{event_index}.background_type": background_request.background_type,
                    f"events.{event_index}.color_palette": background_request.color_palette,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update event background")
        
        # Create audit log
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": admin.admin_id,
            "action": "update_event_background",
            "resource_type": "event",
            "resource_id": event_id,
            "details": {
                "design_id": background_request.background_design_id,
                "background_type": background_request.background_type,
                "event_type": current_event['event_type']
            },
            "timestamp": datetime.now(timezone.utc),
            "ip_address": None
        })
        
        return {
            "success": True,
            "message": "Event background updated successfully",
            "event_id": event_id,
            "design_id": background_request.background_design_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating event background: {e}")
        raise HTTPException(status_code=500, detail="Failed to update event background")


@api_router.get("/admin/events/{event_id}/default-design")
async def get_default_design_for_event_endpoint(
    event_id: str,
    admin: Admin = Depends(get_current_admin)
):
    """
    Get the recommended default design for a specific event
    
    Returns the default design based on event type
    """
    try:
        # Find profile containing this event
        profile = await db.profiles.find_one({
            "events.event_id": event_id
        })
        
        if not profile:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Check admin authorization
        if profile['admin_id'] != admin.admin_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this event")
        
        # Find the specific event
        current_event = None
        for event in profile.get('events', []):
            if event['event_id'] == event_id:
                current_event = event
                break
        
        if current_event is None:
            raise HTTPException(status_code=404, detail="Event not found in profile")
        
        # Get default design for this event type
        event_type = EventType(current_event['event_type'])
        default_design = get_default_design_for_event(event_type)
        
        if not default_design:
            raise HTTPException(status_code=404, detail="No default design found for this event type")
        
        return default_design
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching default design: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch default design")


# ============================================================================
# PHASE 23: LORD IMAGE ENGINE & PLACEMENT RULES API ENDPOINTS
# ============================================================================

@api_router.get("/lords", response_model=LordLibraryResponse)
async def get_lord_library(
    event_type: Optional[str] = None
):
    """
    Get all available lord images from the library, optionally filtered by event type
    
    Query Parameters:
    - event_type: Filter lords by event type (engagement, marriage, reception)
    
    Returns list of lord configurations with images and metadata
    
    Rules:
    - Engagement, Marriage, Reception: All lords available
    - Haldi, Mehendi: Empty list (lords not allowed)
    """
    try:
        if event_type:
            # Validate and convert event type
            try:
                event_type_enum = EventType(event_type.lower())
                
                # Haldi and Mehendi cannot have lords
                if event_type_enum in [EventType.HALDI, EventType.MEHENDI]:
                    return LordLibraryResponse(lords=[], total=0)
                
                lords = get_lords_by_event_type(event_type_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid event_type. Must be one of: engagement, haldi, mehendi, marriage, reception"
                )
        else:
            lords = get_all_lords()
        
        return LordLibraryResponse(
            lords=lords,
            total=len(lords)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lord library: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch lord library")


@api_router.get("/lords/{lord_id}", response_model=LordLibrary)
async def get_lord_by_id_endpoint(lord_id: str):
    """
    Get specific lord configuration by ID
    
    Path Parameters:
    - lord_id: Unique lord identifier (e.g., "ganesha")
    
    Returns complete lord configuration including images and metadata
    """
    try:
        lord = get_lord_by_id(lord_id)
        
        if not lord:
            raise HTTPException(
                status_code=404,
                detail=f"Lord with ID '{lord_id}' not found"
            )
        
        return lord
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lord {lord_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch lord configuration")


@api_router.put("/admin/events/{event_id}/lord-settings")
async def update_event_lord_settings(
    event_id: str,
    lord_settings: UpdateEventLordSettingsRequest,
    admin: Admin = Depends(get_current_admin)
):
    """
    PHASE 23: Update lord settings for a specific event
    
    Path Parameters:
    - event_id: Unique event identifier
    
    Request Body:
    - lord_enabled: Enable/disable lord image
    - lord_id: Lord identifier from library (optional if disabled)
    - lord_display_mode: "hero_only" or "section_based"
    - lord_visibility_duration: Duration in seconds (1-10)
    
    Rules:
    - Engagement, Marriage, Reception: Lords allowed
    - Haldi, Mehendi: Lord forced disabled (returns error)
    - Auto-applies Ganesha as default if lord_id not provided
    """
    try:
        # Find profile containing this event
        profile = await db.profiles.find_one({
            "events.event_id": event_id
        })
        
        if not profile:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Check admin authorization
        if profile['admin_id'] != admin.admin_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this event")
        
        # Find the specific event and its index
        current_event = None
        event_index = -1
        for idx, event in enumerate(profile.get('events', [])):
            if event['event_id'] == event_id:
                current_event = event
                event_index = idx
                break
        
        if current_event is None:
            raise HTTPException(status_code=404, detail="Event not found in profile")
        
        # Get event type
        event_type = EventType(current_event['event_type'])
        
        # PHASE 23: Validate lord settings based on event type
        if event_type in [EventType.HALDI, EventType.MEHENDI]:
            if lord_settings.lord_enabled:
                raise HTTPException(
                    status_code=400,
                    detail=f"Lord images are not allowed for {event_type.value} events"
                )
        
        # Validate lord_id if provided and enabled
        if lord_settings.lord_enabled and lord_settings.lord_id:
            # Check if lord exists
            lord = get_lord_by_id(lord_settings.lord_id)
            if not lord:
                raise HTTPException(
                    status_code=400,
                    detail=f"Lord with ID '{lord_settings.lord_id}' not found"
                )
            
            # Check if lord is allowed for this event type
            if not is_lord_allowed_for_event(lord_settings.lord_id, event_type):
                raise HTTPException(
                    status_code=400,
                    detail=f"Lord '{lord.name}' is not allowed for {event_type.value} events"
                )
        
        # If enabled but no lord_id provided, use default (Ganesha)
        final_lord_id = lord_settings.lord_id
        if lord_settings.lord_enabled and not final_lord_id:
            default_lord = get_default_lord()
            final_lord_id = default_lord.lord_id if default_lord else "ganesha"
        
        # Update event lord settings
        update_result = await db.profiles.update_one(
            {"id": profile['id'], "events.event_id": event_id},
            {
                "$set": {
                    f"events.{event_index}.lord_enabled": lord_settings.lord_enabled,
                    f"events.{event_index}.lord_id": final_lord_id if lord_settings.lord_enabled else None,
                    f"events.{event_index}.lord_display_mode": lord_settings.lord_display_mode,
                    f"events.{event_index}.lord_visibility_duration": lord_settings.lord_visibility_duration,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update event lord settings")
        
        # Create audit log
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": admin.admin_id,
            "action": "update_event_lord_settings",
            "resource_type": "event",
            "resource_id": event_id,
            "details": {
                "lord_enabled": lord_settings.lord_enabled,
                "lord_id": final_lord_id,
                "lord_display_mode": lord_settings.lord_display_mode,
                "lord_visibility_duration": lord_settings.lord_visibility_duration,
                "event_type": current_event['event_type']
            },
            "timestamp": datetime.now(timezone.utc),
            "ip_address": None
        })
        
        return {
            "success": True,
            "message": "Event lord settings updated successfully",
            "event_id": event_id,
            "lord_enabled": lord_settings.lord_enabled,
            "lord_id": final_lord_id,
            "lord_display_mode": lord_settings.lord_display_mode,
            "lord_visibility_duration": lord_settings.lord_visibility_duration
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating event lord settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update event lord settings")


@api_router.get("/admin/events/{event_id}/default-lord")
async def get_default_lord_for_event_endpoint(
    event_id: str,
    admin: Admin = Depends(get_current_admin)
):
    """
    Get the default lord for a specific event
    
    Returns Ganesha as the default lord for allowed events
    Returns null for Haldi and Mehendi events
    """
    try:
        # Find profile containing this event
        profile = await db.profiles.find_one({
            "events.event_id": event_id
        })
        
        if not profile:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Check admin authorization
        if profile['admin_id'] != admin.admin_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this event")
        
        # Find the specific event
        current_event = None
        for event in profile.get('events', []):
            if event['event_id'] == event_id:
                current_event = event
                break
        
        if current_event is None:
            raise HTTPException(status_code=404, detail="Event not found in profile")
        
        # Get event type
        event_type = EventType(current_event['event_type'])
        
        # Haldi and Mehendi cannot have lords
        if event_type in [EventType.HALDI, EventType.MEHENDI]:
            return None
        
        # Get default lord (Ganesha)
        default_lord = get_default_lord()
        
        if not default_lord:
            raise HTTPException(status_code=404, detail="No default lord found")
        
        return default_lord
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching default lord: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch default lord")


# ============================================================================
# PHASE 24: VIDEO & MUSIC EXPERIENCE API ENDPOINTS
# ============================================================================

@api_router.post("/admin/events/{event_id}/upload-hero-video")
async def upload_hero_video(
    event_id: str,
    file: UploadFile = File(...),
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 24: Upload hero background video for event
    - Max 10MB
    - Formats: MP4, WebM
    - Auto-generates thumbnail from first frame
    - Stores in /app/uploads/videos/{profile_id}/{event_type}/
    - Duration recommendation: 5-8 seconds (warning only, not enforced)
    """
    # Validate file format
    if not file.content_type or not file.content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="File must be a video (MP4 or WebM)")
    
    allowed_formats = ['video/mp4', 'video/webm']
    if file.content_type not in allowed_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid video format. Allowed: MP4, WebM. Got: {file.content_type}"
        )
    
    # Read file content
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    
    # Validate file size (10MB limit)
    if file_size_mb > 10:
        raise HTTPException(
            status_code=400,
            detail=f"File size {file_size_mb:.2f}MB exceeds 10MB limit"
        )
    
    # Find profile containing this event
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Find the event
    events = profile.get('events', [])
    event = None
    event_index = -1
    
    for idx, evt in enumerate(events):
        if evt.get('event_id') == event_id:
            event = evt
            event_index = idx
            break
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Create video directory
    profile_id = profile['id']
    event_type = event.get('event_type', 'unknown')
    video_dir = Path(f"/app/uploads/videos/{profile_id}/{event_type}")
    video_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    video_id = str(uuid.uuid4())
    file_extension = 'mp4' if file.content_type == 'video/mp4' else 'webm'
    video_filename = f"hero_{video_id}.{file_extension}"
    video_path = video_dir / video_filename
    
    # Save video file
    with open(video_path, 'wb') as f:
        f.write(content)
    
    # Generate thumbnail (extract first frame if possible, otherwise skip)
    thumbnail_url = None
    try:
        # Try to generate thumbnail using PIL (works for some video formats)
        # This is a basic implementation; for production, use ffmpeg
        thumbnail_filename = f"hero_{video_id}_thumb.jpg"
        thumbnail_path = video_dir / thumbnail_filename
        
        # For now, we'll skip auto-generation and use a default poster
        # In production, use ffmpeg: ffmpeg -i video.mp4 -ss 00:00:01 -vframes 1 output.jpg
        thumbnail_url = None  # Will be handled by browser's poster attribute
        
    except Exception as e:
        logger.warning(f"Could not generate thumbnail: {e}")
        thumbnail_url = None
    
    video_url = f"/uploads/videos/{profile_id}/{event_type}/{video_filename}"
    
    # Delete old hero video if exists
    old_video_url = event.get('hero_video_url')
    if old_video_url:
        try:
            old_video_path = Path(f"/app{old_video_url}")
            if old_video_path.exists():
                old_video_path.unlink()
            # Delete old thumbnail if exists
            old_thumbnail_url = event.get('hero_video_thumbnail')
            if old_thumbnail_url:
                old_thumbnail_path = Path(f"/app{old_thumbnail_url}")
                if old_thumbnail_path.exists():
                    old_thumbnail_path.unlink()
        except Exception as e:
            logger.warning(f"Could not delete old hero video: {e}")
    
    # Update event with video URL
    events[event_index]['hero_video_url'] = video_url
    events[event_index]['hero_video_thumbnail'] = thumbnail_url
    events[event_index]['hero_video_enabled'] = True
    
    # Update profile
    await db.profiles.update_one(
        {"id": profile_id},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "hero_video_uploaded",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {
            "profile_id": profile_id,
            "video_url": video_url,
            "file_size_mb": round(file_size_mb, 2)
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Hero video uploaded successfully",
        "video_url": video_url,
        "thumbnail_url": thumbnail_url,
        "file_size_mb": round(file_size_mb, 2)
    }


@api_router.post("/admin/events/{event_id}/upload-message-video")
async def upload_message_video(
    event_id: str,
    file: UploadFile = File(...),
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 24: Upload message video (bride/groom video) for event
    - Max 10MB
    - Formats: MP4, WebM
    - Duration recommendation: max 30 seconds (warning only, not enforced)
    """
    # Validate file format
    if not file.content_type or not file.content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="File must be a video (MP4 or WebM)")
    
    allowed_formats = ['video/mp4', 'video/webm']
    if file.content_type not in allowed_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid video format. Allowed: MP4, WebM. Got: {file.content_type}"
        )
    
    # Read file content
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    
    # Validate file size (10MB limit)
    if file_size_mb > 10:
        raise HTTPException(
            status_code=400,
            detail=f"File size {file_size_mb:.2f}MB exceeds 10MB limit"
        )
    
    # Find profile containing this event
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Find the event
    events = profile.get('events', [])
    event = None
    event_index = -1
    
    for idx, evt in enumerate(events):
        if evt.get('event_id') == event_id:
            event = evt
            event_index = idx
            break
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Create video directory
    profile_id = profile['id']
    event_type = event.get('event_type', 'unknown')
    video_dir = Path(f"/app/uploads/videos/{profile_id}/{event_type}")
    video_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    video_id = str(uuid.uuid4())
    file_extension = 'mp4' if file.content_type == 'video/mp4' else 'webm'
    video_filename = f"message_{video_id}.{file_extension}"
    video_path = video_dir / video_filename
    
    # Save video file
    with open(video_path, 'wb') as f:
        f.write(content)
    
    video_url = f"/uploads/videos/{profile_id}/{event_type}/{video_filename}"
    
    # Delete old message video if exists
    old_video_url = event.get('message_video_url')
    if old_video_url:
        try:
            old_video_path = Path(f"/app{old_video_url}")
            if old_video_path.exists():
                old_video_path.unlink()
        except Exception as e:
            logger.warning(f"Could not delete old message video: {e}")
    
    # Update event with video URL
    events[event_index]['message_video_url'] = video_url
    events[event_index]['message_video_enabled'] = True
    
    # Update profile
    await db.profiles.update_one(
        {"id": profile_id},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "message_video_uploaded",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {
            "profile_id": profile_id,
            "video_url": video_url,
            "file_size_mb": round(file_size_mb, 2)
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Message video uploaded successfully",
        "video_url": video_url,
        "file_size_mb": round(file_size_mb, 2)
    }


@api_router.post("/admin/events/{event_id}/upload-music")
async def upload_background_music(
    event_id: str,
    file: UploadFile = File(...),
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 24: Upload background music for event
    - Max 5MB
    - Format: MP3 only
    """
    # Validate file format
    if not file.content_type or file.content_type not in ['audio/mpeg', 'audio/mp3']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid audio format. Only MP3 allowed. Got: {file.content_type}"
        )
    
    # Read file content
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    
    # Validate file size (5MB limit)
    if file_size_mb > 5:
        raise HTTPException(
            status_code=400,
            detail=f"File size {file_size_mb:.2f}MB exceeds 5MB limit"
        )
    
    # Find profile containing this event
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Find the event
    events = profile.get('events', [])
    event = None
    event_index = -1
    
    for idx, evt in enumerate(events):
        if evt.get('event_id') == event_id:
            event = evt
            event_index = idx
            break
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Create music directory
    profile_id = profile['id']
    event_type = event.get('event_type', 'unknown')
    music_dir = Path(f"/app/uploads/music/{profile_id}/{event_type}")
    music_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    music_id = str(uuid.uuid4())
    music_filename = f"bg_music_{music_id}.mp3"
    music_path = music_dir / music_filename
    
    # Save music file
    with open(music_path, 'wb') as f:
        f.write(content)
    
    music_url = f"/uploads/music/{profile_id}/{event_type}/{music_filename}"
    
    # Delete old music if exists
    old_music_url = event.get('background_music_url')
    if old_music_url:
        try:
            old_music_path = Path(f"/app{old_music_url}")
            if old_music_path.exists():
                old_music_path.unlink()
        except Exception as e:
            logger.warning(f"Could not delete old music: {e}")
    
    # Update event with music URL
    events[event_index]['background_music_url'] = music_url
    events[event_index]['background_music_enabled'] = True
    
    # Update profile
    await db.profiles.update_one(
        {"id": profile_id},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "background_music_uploaded",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {
            "profile_id": profile_id,
            "music_url": music_url,
            "file_size_mb": round(file_size_mb, 2)
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Background music uploaded successfully",
        "music_url": music_url,
        "file_size_mb": round(file_size_mb, 2)
    }


@api_router.delete("/admin/events/{event_id}/hero-video")
async def delete_hero_video(
    event_id: str,
    admin_id: str = Depends(get_current_admin)
):
    """PHASE 24: Delete hero video from event"""
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    events = profile.get('events', [])
    event_index = -1
    
    for idx, evt in enumerate(events):
        if evt.get('event_id') == event_id:
            event_index = idx
            break
    
    if event_index == -1:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event = events[event_index]
    video_url = event.get('hero_video_url')
    
    if not video_url:
        raise HTTPException(status_code=404, detail="No hero video found")
    
    # Delete video file
    try:
        video_path = Path(f"/app{video_url}")
        if video_path.exists():
            video_path.unlink()
        
        # Delete thumbnail if exists
        thumbnail_url = event.get('hero_video_thumbnail')
        if thumbnail_url:
            thumbnail_path = Path(f"/app{thumbnail_url}")
            if thumbnail_path.exists():
                thumbnail_path.unlink()
    except Exception as e:
        logger.warning(f"Could not delete video files: {e}")
    
    # Update event
    events[event_index]['hero_video_url'] = None
    events[event_index]['hero_video_thumbnail'] = None
    events[event_index]['hero_video_enabled'] = False
    
    await db.profiles.update_one(
        {"id": profile['id']},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "hero_video_deleted",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {"profile_id": profile['id']},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Hero video deleted successfully"}


@api_router.delete("/admin/events/{event_id}/message-video")
async def delete_message_video(
    event_id: str,
    admin_id: str = Depends(get_current_admin)
):
    """PHASE 24: Delete message video from event"""
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    events = profile.get('events', [])
    event_index = -1
    
    for idx, evt in enumerate(events):
        if evt.get('event_id') == event_id:
            event_index = idx
            break
    
    if event_index == -1:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event = events[event_index]
    video_url = event.get('message_video_url')
    
    if not video_url:
        raise HTTPException(status_code=404, detail="No message video found")
    
    # Delete video file
    try:
        video_path = Path(f"/app{video_url}")
        if video_path.exists():
            video_path.unlink()
    except Exception as e:
        logger.warning(f"Could not delete video file: {e}")
    
    # Update event
    events[event_index]['message_video_url'] = None
    events[event_index]['message_video_enabled'] = False
    
    await db.profiles.update_one(
        {"id": profile['id']},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "message_video_deleted",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {"profile_id": profile['id']},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Message video deleted successfully"}


@api_router.delete("/admin/events/{event_id}/music")
async def delete_background_music(
    event_id: str,
    admin_id: str = Depends(get_current_admin)
):
    """PHASE 24: Delete background music from event"""
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    events = profile.get('events', [])
    event_index = -1
    
    for idx, evt in enumerate(events):
        if evt.get('event_id') == event_id:
            event_index = idx
            break
    
    if event_index == -1:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event = events[event_index]
    music_url = event.get('background_music_url')
    
    if not music_url:
        raise HTTPException(status_code=404, detail="No background music found")
    
    # Delete music file
    try:
        music_path = Path(f"/app{music_url}")
        if music_path.exists():
            music_path.unlink()
    except Exception as e:
        logger.warning(f"Could not delete music file: {e}")
    
    # Update event
    events[event_index]['background_music_url'] = None
    events[event_index]['background_music_enabled'] = False
    
    await db.profiles.update_one(
        {"id": profile['id']},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "background_music_deleted",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {"profile_id": profile['id']},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Background music deleted successfully"}


@api_router.patch("/admin/events/{event_id}/toggle-hero-video")
async def toggle_hero_video(
    event_id: str,
    enabled: bool,
    admin_id: str = Depends(get_current_admin)
):
    """PHASE 24: Toggle hero video enable/disable"""
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    events = profile.get('events', [])
    event_index = -1
    
    for idx, evt in enumerate(events):
        if evt.get('event_id') == event_id:
            event_index = idx
            break
    
    if event_index == -1:
        raise HTTPException(status_code=404, detail="Event not found")
    
    events[event_index]['hero_video_enabled'] = enabled
    
    await db.profiles.update_one(
        {"id": profile['id']},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "hero_video_toggled",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {"profile_id": profile['id'], "enabled": enabled},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": f"Hero video {'enabled' if enabled else 'disabled'} successfully"}


@api_router.patch("/admin/events/{event_id}/toggle-message-video")
async def toggle_message_video(
    event_id: str,
    enabled: bool,
    admin_id: str = Depends(get_current_admin)
):
    """PHASE 24: Toggle message video enable/disable"""
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    events = profile.get('events', [])
    event_index = -1
    
    for idx, evt in enumerate(events):
        if evt.get('event_id') == event_id:
            event_index = idx
            break
    
    if event_index == -1:
        raise HTTPException(status_code=404, detail="Event not found")
    
    events[event_index]['message_video_enabled'] = enabled
    
    await db.profiles.update_one(
        {"id": profile['id']},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "message_video_toggled",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {"profile_id": profile['id'], "enabled": enabled},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": f"Message video {'enabled' if enabled else 'disabled'} successfully"}


@api_router.patch("/admin/events/{event_id}/toggle-music")
async def toggle_background_music(
    event_id: str,
    enabled: bool,
    admin_id: str = Depends(get_current_admin)
):
    """PHASE 24: Toggle background music enable/disable"""
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    events = profile.get('events', [])
    event_index = -1
    
    for idx, evt in enumerate(events):
        if evt.get('event_id') == event_id:
            event_index = idx
            break
    
    if event_index == -1:
        raise HTTPException(status_code=404, detail="Event not found")
    
    events[event_index]['background_music_enabled'] = enabled
    
    await db.profiles.update_one(
        {"id": profile['id']},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "background_music_toggled",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {"profile_id": profile['id'], "enabled": enabled},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": f"Background music {'enabled' if enabled else 'disabled'} successfully"}



# ==================== PHASE 25: GUEST ENGAGEMENT ENGINE ====================

@api_router.post("/events/{event_id}/wishes")
async def create_guest_wish(
    event_id: str,
    wish_data: GuestWishCreate,
    request: Request
):
    """
    PHASE 25: Create a guest wish for an event
    
    Public endpoint with rate limiting (max 5 wishes per IP per day)
    """
    # Get client IP
    ip_address = get_client_ip(request)
    
    # Check rate limit (max 5 wishes per IP per day)
    rate_allowed = await check_rate_limit(ip_address, "wishes", 5)
    if not rate_allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 5 wishes per day."
        )
    
    # Find profile containing this event
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0, "id": 1, "events": 1}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Find the specific event and check if wishes are enabled
    event = None
    for evt in profile.get('events', []):
        if evt.get('event_id') == event_id:
            event = evt
            break
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if not event.get('wishes_enabled', True):
        raise HTTPException(
            status_code=403,
            detail="Wishes are disabled for this event"
        )
    
    # Basic profanity filter
    if contains_profanity(wish_data.message):
        raise HTTPException(
            status_code=400,
            detail="Message contains inappropriate content"
        )
    
    # Create guest wish
    guest_wish = GuestWish(
        event_id=event_id,
        profile_id=profile['id'],
        guest_name=wish_data.guest_name,
        message=wish_data.message,
        emoji=wish_data.emoji,
        ip_address=ip_address
    )
    
    # Convert to dict and serialize
    doc = guest_wish.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.guest_wishes.insert_one(doc)
    
    # Update rate limit count
    await db.rate_limits.update_one(
        {
            "ip_address": ip_address,
            "endpoint": "wishes",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        },
        {"$inc": {"count": 1}},
        upsert=False
    )
    
    return {
        "message": "Wish created successfully",
        "wish": GuestWishResponse(**guest_wish.model_dump())
    }


@api_router.get("/admin/events/{event_id}/wishes")
async def get_event_wishes(
    event_id: str,
    limit: int = 50,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 25 + PHASE 32: Get all wishes for an event
    
    SECURITY FIX: Changed to admin-only endpoint
    Guests should not be able to view all wishes - only approved ones show on public invitation
    """
    wishes = await db.guest_wishes.find(
        {"event_id": event_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Convert datetime strings
    for wish in wishes:
        if isinstance(wish.get('created_at'), str):
            wish['created_at'] = datetime.fromisoformat(wish['created_at'])
    
    return {
        "wishes": [GuestWishResponse(**wish) for wish in wishes],
        "total": len(wishes)
    }


@api_router.delete("/admin/wishes/{wish_id}")
async def delete_guest_wish(
    wish_id: str,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 25: Admin delete a guest wish
    """
    result = await db.guest_wishes.delete_one({"id": wish_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Wish not found")
    
    return {"message": "Wish deleted successfully"}


@api_router.post("/events/{event_id}/reactions")
async def create_guest_reaction(
    event_id: str,
    reaction_data: GuestReactionCreate,
    request: Request
):
    """
    PHASE 25: Add/update guest reaction for an event
    
    Public endpoint - one reaction per device (IP address)
    """
    # Get client IP
    ip_address = get_client_ip(request)
    
    # Find profile containing this event
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0, "id": 1, "events": 1}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Find the specific event and check if reactions are enabled
    event = None
    for evt in profile.get('events', []):
        if evt.get('event_id') == event_id:
            event = evt
            break
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if not event.get('reactions_enabled', True):
        raise HTTPException(
            status_code=403,
            detail="Reactions are disabled for this event"
        )
    
    # Check if IP already reacted today
    existing_reaction = await db.guest_reactions.find_one({
        "event_id": event_id,
        "ip_address": ip_address
    })
    
    if existing_reaction:
        # Update existing reaction
        await db.guest_reactions.update_one(
            {"id": existing_reaction['id']},
            {
                "$set": {
                    "reaction_type": reaction_data.reaction_type,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        return {
            "message": "Reaction updated successfully",
            "reaction_type": reaction_data.reaction_type
        }
    else:
        # Create new reaction
        guest_reaction = GuestReaction(
            event_id=event_id,
            profile_id=profile['id'],
            reaction_type=reaction_data.reaction_type,
            ip_address=ip_address
        )
        
        doc = guest_reaction.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        
        await db.guest_reactions.insert_one(doc)
        
        return {
            "message": "Reaction created successfully",
            "reaction_type": reaction_data.reaction_type
        }


@api_router.get("/events/{event_id}/reactions")
async def get_event_reactions(event_id: str):
    """
    PHASE 25: Get reaction statistics for an event
    
    Public endpoint - returns aggregate counts only
    """
    reactions = await db.guest_reactions.find(
        {"event_id": event_id},
        {"_id": 0, "reaction_type": 1}
    ).to_list(1000)
    
    # Count reactions by type
    love_count = sum(1 for r in reactions if r.get('reaction_type') == 'love')
    blessings_count = sum(1 for r in reactions if r.get('reaction_type') == 'blessings')
    excited_count = sum(1 for r in reactions if r.get('reaction_type') == 'excited')
    
    return GuestReactionStats(
        event_id=event_id,
        love_count=love_count,
        blessings_count=blessings_count,
        excited_count=excited_count,
        total_reactions=len(reactions)
    )


@api_router.patch("/admin/events/{event_id}/engagement-settings")
async def update_event_engagement_settings(
    event_id: str,
    settings: UpdateEventEngagementSettingsRequest,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 25: Update engagement settings for an event
    
    Admin endpoint - toggle wishes, reactions, countdown
    """
    # Find profile containing this event
    profile = await db.profiles.find_one(
        {"events.event_id": event_id},
        {"_id": 0}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Find the event and update settings
    events = profile.get('events', [])
    event_found = False
    
    for evt in events:
        if evt.get('event_id') == event_id:
            event_found = True
            
            if settings.wishes_enabled is not None:
                evt['wishes_enabled'] = settings.wishes_enabled
            if settings.reactions_enabled is not None:
                evt['reactions_enabled'] = settings.reactions_enabled
            if settings.countdown_enabled is not None:
                evt['countdown_enabled'] = settings.countdown_enabled
            
            break
    
    if not event_found:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Update profile
    await db.profiles.update_one(
        {"id": profile['id']},
        {
            "$set": {
                "events": events,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "event_engagement_settings_updated",
        "resource_type": "event",
        "resource_id": event_id,
        "admin_id": admin_id,
        "details": {
            "profile_id": profile['id'],
            "settings": settings.model_dump(exclude_none=True)
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Engagement settings updated successfully",
        "settings": {
            "wishes_enabled": evt.get('wishes_enabled'),
            "reactions_enabled": evt.get('reactions_enabled'),
            "countdown_enabled": evt.get('countdown_enabled')
        }
    }


# ==========================================
# PHASE 26: AI-POWERED PERSONALIZATION
# ==========================================

@api_router.post("/translate", response_model=TranslationResponse)
async def translate_content(
    request_data: TranslationRequest,
    req: Request
):
    """
    PHASE 26: Translate content to target language using AI
    
    Guest endpoint - Rate limited to 10 requests per minute per IP
    Supports: English (en), Telugu (te), Hindi (hi), Tamil (ta)
    """
    # Get client IP for rate limiting
    client_ip = req.client.host
    
    # Check rate limit
    if not check_translation_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Translation rate limit exceeded. Please try again in a minute."
        )
    
    # Generate content hash for cache lookup
    content_hash = hashlib.md5(
        f"{request_data.content}_{request_data.target_language}".encode()
    ).hexdigest()
    
    # Check cache first
    cached_translation = await db.translation_cache.find_one(
        {
            "content_hash": content_hash,
            "target_language": request_data.target_language,
            "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
        },
        {"_id": 0}
    )
    
    if cached_translation:
        return TranslationResponse(
            original_content=request_data.content,
            translated_content=cached_translation['translated_content'],
            source_language="en",
            target_language=request_data.target_language,
            cached=True
        )
    
    # Translate using AI
    try:
        translated_text = await ai_service.translate_content(
            content=request_data.content,
            target_language=request_data.target_language,
            context=request_data.context
        )
        
        # Cache the translation (expires in 7 days)
        cache_entry = {
            "id": str(uuid.uuid4()),
            "content_hash": content_hash,
            "original_language": "en",
            "target_language": request_data.target_language,
            "original_content": request_data.content,
            "translated_content": translated_text,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        }
        
        await db.translation_cache.insert_one(cache_entry)
        
        return TranslationResponse(
            original_content=request_data.content,
            translated_content=translated_text,
            source_language="en",
            target_language=request_data.target_language,
            cached=False
        )
    
    except Exception as e:
        logger.error(f"Translation error: {e}")
        # Return original content as fallback
        return TranslationResponse(
            original_content=request_data.content,
            translated_content=request_data.content,
            source_language="en",
            target_language=request_data.target_language,
            cached=False
        )


@api_router.post("/admin/generate-event-description", response_model=GenerateDescriptionResponse)
async def generate_event_description(
    request_data: GenerateDescriptionRequest,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 26: Generate event description using AI
    
    Admin endpoint - Rate limited to 5 requests per hour per admin
    """
    # Check rate limit
    if not check_admin_generation_rate_limit(admin_id):
        raise HTTPException(
            status_code=429,
            detail="AI generation rate limit exceeded. Please try again later (5 requests per hour)."
        )
    
    # Generate description using AI
    try:
        description = await ai_service.generate_event_description(
            event_type=request_data.event_type,
            couple_names=request_data.couple_names,
            date=request_data.date,
            venue=request_data.venue
        )
        
        # Create audit log
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "action": "ai_description_generated",
            "resource_type": "event",
            "resource_id": None,
            "admin_id": admin_id,
            "details": {
                "event_type": request_data.event_type,
                "description_length": len(description)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return GenerateDescriptionResponse(
            description=description,
            event_type=request_data.event_type
        )
    
    except Exception as e:
        logger.error(f"Description generation error: {e}")
        # Return fallback description
        return GenerateDescriptionResponse(
            description=f"Join us to celebrate this beautiful {request_data.event_type} ceremony.",
            event_type=request_data.event_type
        )


@api_router.get("/rsvp-suggestions", response_model=RSVPSuggestionsResponse)
async def get_rsvp_suggestions(
    event_type: str = "marriage",
    guest_name: Optional[str] = None
):
    """
    PHASE 26: Get AI-generated RSVP message suggestions
    
    Guest endpoint - No authentication required
    Returns 3 contextual message suggestions
    """
    try:
        suggestions = await ai_service.generate_rsvp_suggestions(
            event_type=event_type,
            guest_name=guest_name
        )
        
        return RSVPSuggestionsResponse(suggestions=suggestions)
    
    except Exception as e:
        logger.error(f"RSVP suggestions error: {e}")
        # Return fallback suggestions
        return RSVPSuggestionsResponse(
            suggestions=[
                "Can't wait to celebrate with you! 🎉",
                "Blessings to the beautiful couple ❤️",
                "Excited for your special day! 💐"
            ]
        )


@api_router.get("/admin/guest-insights/{profile_id}", response_model=GuestInsightsResponse)
async def get_guest_insights(
    profile_id: str,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 26: Get AI-generated guest segment insights
    
    Admin endpoint - Analyzes RSVP data and provides insights
    """
    # Get profile
    profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Get all RSVPs for this profile
    rsvps = await db.rsvps.find({"profile_id": profile_id}, {"_id": 0}).to_list(length=None)
    
    # Calculate statistics
    total_rsvps = len(rsvps)
    confirmed = sum(1 for r in rsvps if r.get('status') == 'confirmed')
    declined = sum(1 for r in rsvps if r.get('status') == 'declined')
    pending = sum(1 for r in rsvps if r.get('status') == 'pending')
    with_messages = sum(1 for r in rsvps if r.get('message') and len(r.get('message', '').strip()) > 0)
    
    # Calculate early and late responses
    # Get the profile creation date as reference
    profile_created = datetime.fromisoformat(profile.get('created_at', datetime.now(timezone.utc).isoformat()))
    early_responses = 0
    late_responses = 0
    
    for rsvp in rsvps:
        rsvp_time = datetime.fromisoformat(rsvp.get('created_at', datetime.now(timezone.utc).isoformat()))
        time_diff = (rsvp_time - profile_created).total_seconds() / 3600  # hours
        
        if time_diff <= 24:
            early_responses += 1
        elif time_diff > 72:
            late_responses += 1
    
    # Prepare data for AI insights
    rsvp_data = {
        'total': total_rsvps,
        'confirmed': confirmed,
        'declined': declined,
        'pending': pending,
        'early_responses': early_responses,
        'late_responses': late_responses,
        'with_messages': with_messages
    }
    
    # Generate insights using AI
    try:
        insights_text = await ai_service.generate_guest_insights(rsvp_data)
    except Exception as e:
        logger.error(f"Guest insights generation error: {e}")
        # Fallback insights
        confirmed_rate = (confirmed / max(total_rsvps, 1)) * 100
        insights_text = f"You have received {total_rsvps} RSVPs so far, with {confirmed_rate:.0f}% confirming attendance."
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "guest_insights_generated",
        "resource_type": "profile",
        "resource_id": profile_id,
        "admin_id": admin_id,
        "details": {
            "total_rsvps": total_rsvps,
            "confirmed": confirmed
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return GuestInsightsResponse(
        profile_id=profile_id,
        total_rsvps=total_rsvps,
        confirmed=confirmed,
        declined=declined,
        pending=pending,
        early_responses=early_responses,
        late_responses=late_responses,
        with_messages=with_messages,
        insights_text=insights_text,
        generated_at=datetime.now(timezone.utc)
    )


@api_router.get("/languages")
async def get_supported_languages():
    """
    PHASE 26: Get list of supported languages for translation
    
    Public endpoint - Returns language codes and names
    """
    return {
        "languages": [
            {"code": code, "name": name}
            for code, name in SUPPORTED_LANGUAGES.items()
        ],
        "default": "en"
    }


# ==================== PHASE 27: POST-WEDDING VALUE (COMBINED) ====================

@api_router.put("/admin/profiles/{profile_id}/thank-you")
async def create_or_update_thank_you_message(
    profile_id: str,
    thank_you_data: ThankYouMessageCreate,
    admin_token: str = Header(..., alias="Authorization")
):
    """
    PHASE 27: Create or update thank you message for a profile
    
    Admin endpoint - Couple can send thank-you message after wedding
    """
    try:
        # Extract token
        token = admin_token.replace("Bearer ", "")
        admin = verify_admin_token(token)
        
        # Verify profile exists
        profile = await profiles_collection.find_one({"id": profile_id})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Check if thank you message already exists
        existing_thank_you = await db.thank_you_messages.find_one({"profile_id": profile_id})
        
        now = datetime.now(timezone.utc)
        
        # Determine if message should be published
        # Published if: enabled AND (no scheduled date OR scheduled date has passed)
        is_published = thank_you_data.enabled
        if thank_you_data.scheduled_date:
            is_published = is_published and (now >= thank_you_data.scheduled_date)
        
        if existing_thank_you:
            # Update existing
            update_data = {
                "enabled": thank_you_data.enabled,
                "message_type": thank_you_data.message_type,
                "message_text": thank_you_data.message_text,
                "video_url": thank_you_data.video_url,
                "video_thumbnail": thank_you_data.video_thumbnail,
                "scheduled_date": thank_you_data.scheduled_date,
                "is_published": is_published,
                "updated_at": now
            }
            
            await db.thank_you_messages.update_one(
                {"profile_id": profile_id},
                {"$set": update_data}
            )
            
            thank_you_id = existing_thank_you["id"]
        else:
            # Create new
            thank_you = ThankYouMessage(
                profile_id=profile_id,
                enabled=thank_you_data.enabled,
                message_type=thank_you_data.message_type,
                message_text=thank_you_data.message_text,
                video_url=thank_you_data.video_url,
                video_thumbnail=thank_you_data.video_thumbnail,
                scheduled_date=thank_you_data.scheduled_date,
                is_published=is_published,
                created_at=now,
                updated_at=now
            )
            
            await db.thank_you_messages.insert_one(thank_you.model_dump())
            thank_you_id = thank_you.id
        
        # Create audit log
        await audit_logs_collection.insert_one(
            AuditLog(
                action="thank_you_message_update",
                admin_id=admin["id"],
                profile_id=profile_id,
                profile_slug=profile["slug"],
                details={
                    "message_type": thank_you_data.message_type,
                    "enabled": thank_you_data.enabled,
                    "scheduled": thank_you_data.scheduled_date is not None
                }
            ).model_dump()
        )
        
        return {
            "message": "Thank you message saved successfully",
            "id": thank_you_id,
            "is_published": is_published
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving thank you message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/profiles/{profile_id}/thank-you")
async def get_thank_you_message_admin(
    profile_id: str,
    admin_token: str = Header(..., alias="Authorization")
):
    """
    PHASE 27: Get thank you message for admin view
    
    Admin endpoint - View and manage thank you message
    """
    try:
        # Extract token
        token = admin_token.replace("Bearer ", "")
        verify_admin_token(token)
        
        # Get thank you message
        thank_you = await db.thank_you_messages.find_one({"profile_id": profile_id})
        
        if not thank_you:
            return {
                "exists": False,
                "message": "No thank you message created yet"
            }
        
        return ThankYouMessageResponse(**thank_you)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching thank you message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/profiles/{slug_url}/thank-you")
async def get_thank_you_message_public(slug_url: str):
    """
    PHASE 27: Get thank you message for public view
    
    Public endpoint - Guests can view thank you message if published
    """
    try:
        # Get profile
        profile = await profiles_collection.find_one({"slug": slug_url})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Get thank you message
        thank_you = await db.thank_you_messages.find_one({
            "profile_id": profile["id"],
            "is_published": True
        })
        
        if not thank_you:
            return {
                "exists": False,
                "message": "No thank you message available"
            }
        
        return ThankYouMessageResponse(**thank_you)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching public thank you message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/admin/profiles/{profile_id}/upload-album-media")
async def upload_wedding_album_media(
    profile_id: str,
    files: List[UploadFile] = File(...),
    captions: Optional[str] = Form(None),  # JSON string of captions
    admin_token: str = Header(..., alias="Authorization")
):
    """
    PHASE 27: Upload wedding album photos/videos
    
    Admin endpoint - Upload final wedding photos/videos for album
    Max 50 media items per profile
    """
    try:
        # Extract token
        token = admin_token.replace("Bearer ", "")
        admin = verify_admin_token(token)
        
        # Verify profile exists
        profile = await profiles_collection.find_one({"id": profile_id})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Check existing media count
        existing_count = await db.wedding_album_media.count_documents({"profile_id": profile_id})
        if existing_count + len(files) > 50:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum 50 media items allowed. Current: {existing_count}, Attempting to add: {len(files)}"
            )
        
        # Parse captions if provided
        captions_dict = {}
        if captions:
            import json
            try:
                captions_dict = json.loads(captions)
            except:
                pass
        
        uploaded_media = []
        upload_dir = f"/app/uploads/album/{profile_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        for idx, file in enumerate(files):
            # Validate file type
            file_ext = file.filename.split('.')[-1].lower()
            if file_ext in ['jpg', 'jpeg', 'png', 'webp']:
                media_type = "photo"
                allowed = True
            elif file_ext in ['mp4', 'webm', 'mov']:
                media_type = "video"
                allowed = True
            else:
                continue  # Skip unsupported files
            
            # Read file
            file_content = await file.read()
            file_size = len(file_content)
            
            # Validate file size (max 10MB for photos, 50MB for videos)
            max_size = 50 * 1024 * 1024 if media_type == "video" else 10 * 1024 * 1024
            if file_size > max_size:
                continue  # Skip oversized files
            
            # Generate unique filename
            file_id = str(uuid.uuid4())[:8]
            filename = f"{file_id}_{file.filename}"
            file_path = os.path.join(upload_dir, filename)
            
            # Process and save file
            if media_type == "photo":
                # Convert to WebP for photos
                from PIL import Image
                import io
                
                img = Image.open(io.BytesIO(file_content))
                
                # Resize if too large
                if img.width > 2000:
                    ratio = 2000 / img.width
                    new_size = (2000, int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Save as WebP
                webp_filename = filename.rsplit('.', 1)[0] + '.webp'
                webp_path = os.path.join(upload_dir, webp_filename)
                img.save(webp_path, 'WEBP', quality=85)
                
                media_url = f"/uploads/album/{profile_id}/{webp_filename}"
                thumbnail_url = None
            else:
                # Save video as-is
                with open(file_path, 'wb') as f:
                    f.write(file_content)
                
                media_url = f"/uploads/album/{profile_id}/{filename}"
                # TODO: Generate video thumbnail
                thumbnail_url = None
            
            # Get caption for this file
            caption = captions_dict.get(file.filename, None)
            
            # Get next order number
            max_order = await db.wedding_album_media.find_one(
                {"profile_id": profile_id},
                sort=[("order", -1)]
            )
            next_order = (max_order["order"] + 1) if max_order else 0
            
            # Create media record
            media = WeddingAlbumMedia(
                profile_id=profile_id,
                media_type=media_type,
                media_url=media_url,
                thumbnail_url=thumbnail_url,
                caption=caption,
                order=next_order,
                file_size=file_size
            )
            
            await db.wedding_album_media.insert_one(media.model_dump())
            uploaded_media.append(media.model_dump())
        
        # Create audit log
        await audit_logs_collection.insert_one(
            AuditLog(
                action="wedding_album_upload",
                admin_id=admin["id"],
                profile_id=profile_id,
                profile_slug=profile["slug"],
                details={
                    "files_uploaded": len(uploaded_media),
                    "total_album_items": existing_count + len(uploaded_media)
                }
            ).model_dump()
        )
        
        return {
            "message": f"Uploaded {len(uploaded_media)} media items successfully",
            "uploaded": len(uploaded_media),
            "total": existing_count + len(uploaded_media)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading album media: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/profiles/{profile_id}/album-media")
async def get_album_media_admin(
    profile_id: str,
    admin_token: str = Header(..., alias="Authorization")
):
    """
    PHASE 27: Get wedding album media for admin view
    
    Admin endpoint - View and manage album media
    """
    try:
        # Extract token
        token = admin_token.replace("Bearer ", "")
        verify_admin_token(token)
        
        # Get album media sorted by order
        media_cursor = db.wedding_album_media.find(
            {"profile_id": profile_id}
        ).sort("order", 1)
        
        media_list = await media_cursor.to_list(length=100)
        
        return {
            "media": [WeddingAlbumMediaResponse(**m) for m in media_list],
            "total": len(media_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching album media: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/profiles/{slug_url}/album-media")
async def get_album_media_public(slug_url: str):
    """
    PHASE 27: Get wedding album media for public view
    
    Public endpoint - Guests can view album (read-only, lifetime access)
    """
    try:
        # Get profile
        profile = await profiles_collection.find_one({"slug": slug_url})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Get album media sorted by order
        media_cursor = db.wedding_album_media.find(
            {"profile_id": profile["id"]}
        ).sort("order", 1)
        
        media_list = await media_cursor.to_list(length=100)
        
        return {
            "media": [WeddingAlbumMediaResponse(**m) for m in media_list],
            "total": len(media_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching public album media: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/admin/profiles/{profile_id}/album-media/{media_id}")
async def delete_album_media(
    profile_id: str,
    media_id: str,
    admin_token: str = Header(..., alias="Authorization")
):
    """
    PHASE 27: Delete wedding album media
    
    Admin endpoint - Delete photo/video from album
    """
    try:
        # Extract token
        token = admin_token.replace("Bearer ", "")
        admin = verify_admin_token(token)
        
        # Get media
        media = await db.wedding_album_media.find_one({
            "id": media_id,
            "profile_id": profile_id
        })
        
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")
        
        # Delete file from filesystem
        media_path = f"/app{media['media_url']}"
        if os.path.exists(media_path):
            os.remove(media_path)
        
        # Delete from database
        await db.wedding_album_media.delete_one({"id": media_id})
        
        # Create audit log
        profile = await profiles_collection.find_one({"id": profile_id})
        await audit_logs_collection.insert_one(
            AuditLog(
                action="wedding_album_delete",
                admin_id=admin["id"],
                profile_id=profile_id,
                profile_slug=profile["slug"] if profile else None,
                details={"media_id": media_id, "media_type": media["media_type"]}
            ).model_dump()
        )
        
        return {"message": "Media deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting album media: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/profiles/{slug_url}/memory-mode")
async def check_memory_mode(slug_url: str):
    """
    PHASE 27: Check if invitation is in memory mode
    
    Public endpoint - Determines if wedding has passed and memory mode should activate
    Memory mode: RSVP disabled, countdown hidden, focus on photos/videos/thank you
    """
    try:
        # Get profile
        profile = await profiles_collection.find_one({"slug": slug_url})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Check if any events exist
        if not profile.get("events") or len(profile["events"]) == 0:
            return MemoryModeStatus(
                is_memory_mode=False,
                message="No events scheduled yet"
            )
        
        # Get current date (date only, no time)
        from datetime import date
        today = date.today()
        
        # Find the latest event date
        latest_event_date = None
        for event in profile["events"]:
            if event.get("visible", True):
                event_date_str = event.get("date")
                if event_date_str:
                    try:
                        # Parse yyyy-mm-dd format
                        event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
                        if latest_event_date is None or event_date > latest_event_date:
                            latest_event_date = event_date
                    except:
                        continue
        
        if latest_event_date is None:
            return MemoryModeStatus(
                is_memory_mode=False,
                message="No valid event dates found"
            )
        
        # Check if wedding has passed (compare dates only)
        is_memory_mode = today > latest_event_date
        
        if is_memory_mode:
            days_since = (today - latest_event_date).days
            return MemoryModeStatus(
                is_memory_mode=True,
                wedding_completed_date=datetime.combine(latest_event_date, datetime.min.time()),
                days_since_wedding=days_since,
                message=f"Wedding completed {days_since} day{'s' if days_since != 1 else ''} ago"
            )
        else:
            days_until = (latest_event_date - today).days
            return MemoryModeStatus(
                is_memory_mode=False,
                message=f"Wedding is in {days_until} day{'s' if days_until != 1 else ''}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking memory mode: {str(e)}")


# ============================================
# PHASE 28: VIRAL SHARING & GROWTH ENGINE
# ============================================

@api_router.get("/profiles/{slug_url}/share-metadata", response_model=ShareMetadata)
async def get_share_metadata(slug_url: str):
    """
    PHASE 28: Get share metadata for full wedding invitation
    
    Returns metadata for social sharing preview including title, description, 
    image, and URL. Used by frontend to generate rich previews.
    
    Public endpoint - no authentication required.
    """
    try:
        # Get profile
        profile = await db.profiles.find_one({"slug_url": slug_url})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Get bride and groom names
        bride_name = profile.get('bride_name', 'Bride')
        groom_name = profile.get('groom_name', 'Groom')
        
        # Get earliest wedding date
        events = profile.get('events', [])
        event_dates = []
        for event in events:
            if event.get('event_enabled') and event.get('event_date'):
                try:
                    if isinstance(event['event_date'], str):
                        event_date = datetime.fromisoformat(event['event_date'].replace('Z', '+00:00'))
                    else:
                        event_date = event['event_date']
                    event_dates.append(event_date)
                except:
                    continue
        
        # Format date
        date_str = ""
        if event_dates:
            earliest_date = min(event_dates)
            date_str = earliest_date.strftime("%B %d, %Y")
        
        # Get preview image (use bride/groom photo or first event photo)
        image_url = None
        if profile.get('bride_photo'):
            image_url = profile['bride_photo']
        elif profile.get('groom_photo'):
            image_url = profile['groom_photo']
        else:
            # Try to get first event gallery image
            for event in events:
                if event.get('gallery_enabled') and event.get('gallery_images'):
                    gallery = event['gallery_images']
                    if gallery and len(gallery) > 0:
                        image_url = gallery[0].get('image_url')
                        break
        
        # Build URL
        base_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        full_url = f"{base_url}/invitation/{slug_url}"
        
        # Create metadata
        return ShareMetadata(
            title=f"Join us for the wedding of {bride_name} & {groom_name}",
            description=f"We're getting married{' on ' + date_str if date_str else ''}! Join us in celebrating our special day.",
            url=full_url,
            image_url=image_url,
            event_date=date_str if date_str else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating share metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/events/{event_id}/share-metadata", response_model=ShareMetadata)
async def get_event_share_metadata(event_id: str):
    """
    PHASE 28: Get share metadata for specific event
    
    Returns metadata for sharing individual event on social platforms.
    
    Public endpoint - no authentication required.
    """
    try:
        # Find profile with this event
        profile = await db.profiles.find_one({
            "events.event_id": event_id
        })
        
        if not profile:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Find the specific event
        event = None
        for e in profile.get('events', []):
            if e.get('event_id') == event_id:
                event = e
                break
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Get event details
        event_type = event.get('event_type', 'event').title()
        bride_name = profile.get('bride_name', 'Bride')
        groom_name = profile.get('groom_name', 'Groom')
        
        # Get event date
        date_str = ""
        if event.get('event_date'):
            try:
                if isinstance(event['event_date'], str):
                    event_date = datetime.fromisoformat(event['event_date'].replace('Z', '+00:00'))
                else:
                    event_date = event['event_date']
                date_str = event_date.strftime("%B %d, %Y at %I:%M %p")
            except:
                pass
        
        # Get venue
        venue = event.get('venue', '')
        
        # Get preview image (event gallery or profile photos)
        image_url = None
        if event.get('gallery_enabled') and event.get('gallery_images'):
            gallery = event['gallery_images']
            if gallery and len(gallery) > 0:
                image_url = gallery[0].get('image_url')
        
        if not image_url:
            image_url = profile.get('bride_photo') or profile.get('groom_photo')
        
        # Build URL
        base_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        full_url = f"{base_url}/invitation/{profile['slug_url']}?event={event_id}"
        
        # Create metadata
        description = f"{event_type} ceremony of {bride_name} & {groom_name}"
        if date_str:
            description += f" on {date_str}"
        if venue:
            description += f" at {venue}"
        
        return ShareMetadata(
            title=f"{event_type} - {bride_name} & {groom_name}",
            description=description,
            url=full_url,
            image_url=image_url,
            event_type=event_type,
            event_date=date_str if date_str else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating event share metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/profiles/{slug_url}/qr-code", response_model=QRCodeResponse)
async def generate_profile_qr_code(
    slug_url: str,
    size: int = 300
):
    """
    PHASE 28: Generate QR code for full wedding invitation
    
    Creates a QR code that guests can scan to view the full invitation.
    Returns base64 encoded PNG image.
    
    Public endpoint - no authentication required (for guest convenience).
    Admins can use this to download QR codes for print materials.
    
    Args:
        slug_url: Profile slug URL
        size: QR code size in pixels (100-1000, default 300)
    """
    try:
        # Validate size
        if size < 100 or size > 1000:
            raise HTTPException(status_code=400, detail="Size must be between 100 and 1000")
        
        # Verify profile exists
        profile = await db.profiles.find_one({"slug_url": slug_url})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Build URL
        base_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        full_url = f"{base_url}/invitation/{slug_url}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction
            box_size=10,
            border=4,
        )
        qr.add_data(full_url)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Resize to requested size
        img = img.resize((size, size), PILImage.Resampling.LANCZOS)
        
        # Convert to base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Create filename
        bride_name = profile.get('bride_name', 'bride').replace(' ', '_').lower()
        groom_name = profile.get('groom_name', 'groom').replace(' ', '_').lower()
        filename = f"wedding_qr_{bride_name}_{groom_name}.png"
        
        return QRCodeResponse(
            qr_code_base64=img_base64,
            download_filename=filename,
            url=full_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/events/{event_id}/qr-code", response_model=QRCodeResponse)
async def generate_event_qr_code(
    event_id: str,
    size: int = 300
):
    """
    PHASE 28: Generate QR code for specific event
    
    Creates a QR code for individual event that links directly to that event
    on the invitation page.
    
    Public endpoint - no authentication required.
    
    Args:
        event_id: Event ID
        size: QR code size in pixels (100-1000, default 300)
    """
    try:
        # Validate size
        if size < 100 or size > 1000:
            raise HTTPException(status_code=400, detail="Size must be between 100 and 1000")
        
        # Find profile with this event
        profile = await db.profiles.find_one({
            "events.event_id": event_id
        })
        
        if not profile:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Find the specific event
        event = None
        for e in profile.get('events', []):
            if e.get('event_id') == event_id:
                event = e
                break
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Build URL
        base_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        full_url = f"{base_url}/invitation/{profile['slug_url']}?event={event_id}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(full_url)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Resize to requested size
        img = img.resize((size, size), PILImage.Resampling.LANCZOS)
        
        # Convert to base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Create filename
        event_type = event.get('event_type', 'event').lower()
        bride_name = profile.get('bride_name', 'bride').replace(' ', '_').lower()
        groom_name = profile.get('groom_name', 'groom').replace(' ', '_').lower()
        filename = f"wedding_qr_{event_type}_{bride_name}_{groom_name}.png"
        
        return QRCodeResponse(
            qr_code_base64=img_base64,
            download_filename=filename,
            url=full_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating event QR code: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PHASE 29E: ADMIN SAFETY NETS & RECOVERY ====================

async def save_profile_version(profile_id: str, admin_id: str, version_type: str = "manual_save"):
    """
    PHASE 29E: Save a profile version snapshot
    
    Creates a snapshot of the current profile state for rollback capability.
    Maintains only the last 5 versions per profile.
    """
    try:
        # Get current profile data
        profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
        if not profile:
            return None
        
        # Get current version count
        version_count = await db.profile_versions.count_documents({"profile_id": profile_id})
        next_version = version_count + 1
        
        # Create version snapshot
        version = ProfileVersion(
            profile_id=profile_id,
            version_number=next_version,
            snapshot_data=profile,
            admin_id=admin_id,
            version_type=version_type
        )
        
        # Convert to dict and serialize dates
        version_dict = version.model_dump()
        version_dict['created_at'] = version_dict['created_at'].isoformat()
        
        # Insert version
        await db.profile_versions.insert_one(version_dict)
        
        # Keep only last 5 versions - delete older ones
        versions = await db.profile_versions.find(
            {"profile_id": profile_id}
        ).sort("version_number", -1).to_list(length=100)
        
        if len(versions) > 5:
            # Delete versions beyond the last 5
            old_version_ids = [v['id'] for v in versions[5:]]
            await db.profile_versions.delete_many({"id": {"$in": old_version_ids}})
        
        return version_dict
        
    except Exception as e:
        logger.error(f"Error saving profile version: {str(e)}")
        return None


@api_router.post("/admin/profiles/{profile_id}/versions")
async def create_profile_version(
    profile_id: str,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 29E: Manually save a profile version snapshot
    
    Creates a version snapshot of the current profile state.
    Used when admin explicitly wants to save a checkpoint.
    """
    try:
        version = await save_profile_version(profile_id, admin_id, "manual_save")
        
        if not version:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return {"message": "Version saved successfully", "version_id": version['id']}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating profile version: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/profiles/{profile_id}/versions", response_model=ProfileVersionListResponse)
async def get_profile_versions(
    profile_id: str,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 29E: Get version history for a profile
    
    Returns list of all saved versions (up to last 5) for the profile.
    Used to show version history UI and enable rollback.
    """
    try:
        # Verify profile exists
        profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Get versions sorted by version number (newest first)
        versions_cursor = db.profile_versions.find(
            {"profile_id": profile_id}
        ).sort("version_number", -1)
        
        versions_list = await versions_cursor.to_list(length=5)
        
        # Convert dates
        for v in versions_list:
            if isinstance(v.get('created_at'), str):
                v['created_at'] = datetime.fromisoformat(v['created_at'])
        
        # Get current version number
        current_version = len(versions_list)
        
        return ProfileVersionListResponse(
            versions=[ProfileVersionResponse(**v) for v in versions_list],
            total=len(versions_list),
            current_version=current_version
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profile versions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/admin/profiles/{profile_id}/restore")
async def restore_profile_version(
    profile_id: str,
    restore_request: RestoreVersionRequest,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 29E: Restore profile from a version snapshot
    
    Rolls back the profile to a previous version state.
    Creates a new version before restoring (for undo capability).
    """
    try:
        # Get the version to restore
        version = await db.profile_versions.find_one(
            {"id": restore_request.version_id, "profile_id": profile_id},
            {"_id": 0}
        )
        
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
        
        # Save current state before restoring (for undo)
        await save_profile_version(profile_id, admin_id, "auto_save")
        
        # Restore the snapshot data
        snapshot_data = version['snapshot_data']
        snapshot_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Update profile with snapshot data
        await db.profiles.update_one(
            {"id": profile_id},
            {"$set": snapshot_data}
        )
        
        # Log audit action
        await log_audit_action(
            action="profile_restore",
            admin_id=admin_id,
            profile_id=profile_id,
            profile_slug=snapshot_data.get('slug'),
            details={
                "restored_from_version": version['version_number'],
                "version_type": version['version_type']
            }
        )
        
        return {
            "message": "Profile restored successfully",
            "restored_version": version['version_number']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring profile version: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




# ============================================
# PHASE 30: ANALYTICS, INSIGHTS & GUEST INTELLIGENCE
# ============================================

import httpx
from collections import defaultdict

# In-memory cache for IP geolocation (prevents hitting API limits)
ip_location_cache: Dict[str, Dict[str, Optional[str]]] = {}

async def get_ip_location(ip_address: str) -> Dict[str, Optional[str]]:
    """
    Get country and city for an IP address using ipapi.co
    Uses in-memory cache to reduce API calls
    Gracefully fails if API limit exceeded
    """
    # Return cached result if exists
    if ip_address in ip_location_cache:
        return ip_location_cache[ip_address]
    
    # Check MongoDB cache
    cached = await db.ip_location_cache.find_one({"ip_address": ip_address})
    if cached:
        result = {
            "country": cached.get("country"),
            "city": cached.get("city")
        }
        ip_location_cache[ip_address] = result
        return result
    
    # Fetch from API
    result = {"country": None, "city": None}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"https://ipapi.co/{ip_address}/json/")
            if response.status_code == 200:
                data = response.json()
                result["country"] = data.get("country_name")
                result["city"] = data.get("city")
                
                # Cache in MongoDB
                await db.ip_location_cache.insert_one({
                    "ip_address": ip_address,
                    "country": result["country"],
                    "city": result["city"],
                    "cached_at": datetime.now(timezone.utc)
                })
    except Exception as e:
        logger.warning(f"Failed to get location for IP {ip_address}: {str(e)}")
    
    # Cache in memory
    ip_location_cache[ip_address] = result
    return result


async def is_admin_session(session_id: str) -> bool:
    """Check if session belongs to logged-in admin"""
    # Simple check: if session has made admin API calls recently, it's admin
    # This prevents admin's own views from being tracked
    # For now, we'll track all views unless explicitly filtered on frontend
    return False


@api_router.post("/analytics/track", status_code=201)
async def track_analytics_event(
    request: AnalyticsTrackRequest,
    req: Request
):
    """
    Track analytics events from guest interactions
    Does NOT track admin views
    Privacy-focused: no cookies, no personal data
    """
    try:
        # Get IP address from request
        ip_address = req.client.host if req.client else "unknown"
        
        # Skip if this is an admin session (implement your admin detection logic)
        # For now, we'll accept all tracking and filter in summary
        
        # For PAGE_VIEW events, create ViewAnalytics record
        if request.event_type == AnalyticsEventType.PAGE_VIEW:
            # Get location data
            location = await get_ip_location(ip_address)
            
            # Check if unique visitor (first time seeing this session)
            existing_view = await db.view_analytics.find_one({
                "session_id": request.session_id,
                "profile_id": request.profile_id
            })
            is_unique = existing_view is None
            
            view_data = {
                "id": str(uuid.uuid4()),
                "profile_id": request.profile_id,
                "event_id": request.event_id,
                "session_id": request.session_id,
                "ip_address": ip_address,
                "country": location["country"],
                "city": location["city"],
                "device_type": request.device_type,
                "user_agent": request.user_agent,
                "viewed_at": datetime.now(timezone.utc),
                "is_unique_visitor": is_unique
            }
            await db.view_analytics.insert_one(view_data)
        
        # For all events, create EngagementAnalytics record
        engagement_data = {
            "id": str(uuid.uuid4()),
            "profile_id": request.profile_id,
            "event_id": request.event_id,
            "session_id": request.session_id,
            "event_type": request.event_type,
            "event_metadata": request.event_metadata,
            "time_spent_seconds": request.time_spent_seconds,
            "timestamp": datetime.now(timezone.utc)
        }
        await db.engagement_analytics.insert_one(engagement_data)
        
        return {"message": "Event tracked successfully"}
        
    except Exception as e:
        logger.error(f"Error tracking analytics: {str(e)}")
        # Don't fail the request if analytics fails
        return {"message": "Event tracking skipped"}


@api_router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    profile_id: str,
    event_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: Admin = Depends(get_current_admin)
):
    """
    Get comprehensive analytics summary for admin dashboard
    Filters by profile, event, and date range
    """
    try:
        # Verify admin owns this profile
        profile = await db.profiles.find_one({"id": profile_id})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        if profile["admin_id"] != admin["id"]:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # PHASE 33: Check analytics feature access
        if not has_feature(profile, Feature.ANALYTICS_BASIC):
            raise HTTPException(
                status_code=403,
                detail="Analytics feature not available on FREE plan. Please upgrade to SILVER or higher to access analytics."
            )
        
        # Build query filters
        view_filter = {"profile_id": profile_id}
        engagement_filter = {"profile_id": profile_id}
        
        if event_id:
            view_filter["event_id"] = event_id
            engagement_filter["event_id"] = event_id
        
        # Parse dates
        date_filter = {}
        if start_date:
            date_filter["$gte"] = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        if end_date:
            date_filter["$lte"] = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        
        if date_filter:
            view_filter["viewed_at"] = date_filter
            engagement_filter["timestamp"] = date_filter
        
        # === VIEW ANALYTICS ===
        views = list(await db.view_analytics.find(view_filter).to_list(length=10000))
        
        total_views = len(views)
        unique_visitors = len(set(v["session_id"] for v in views if v.get("is_unique_visitor")))
        repeat_visitors = total_views - unique_visitors
        
        # Device breakdown
        mobile_views = len([v for v in views if v.get("device_type") == "mobile"])
        desktop_views = len([v for v in views if v.get("device_type") == "desktop"])
        tablet_views = len([v for v in views if v.get("device_type") == "tablet"])
        
        # Top countries
        country_counts = defaultdict(int)
        for v in views:
            if v.get("country"):
                country_counts[v["country"]] += 1
        top_countries = [{"country": k, "count": v} for k, v in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:10]]
        
        # Top cities
        city_counts = defaultdict(int)
        for v in views:
            if v.get("city"):
                city_counts[v["city"]] += 1
        top_cities = [{"city": k, "count": v} for k, v in sorted(city_counts.items(), key=lambda x: x[1], reverse=True)[:10]]
        
        # Views by date
        date_counts = defaultdict(int)
        for v in views:
            date_str = v["viewed_at"].strftime("%Y-%m-%d")
            date_counts[date_str] += 1
        views_by_date = [{"date": k, "count": v} for k, v in sorted(date_counts.items())]
        
        view_analytics = ViewAnalyticsData(
            total_views=total_views,
            unique_visitors=unique_visitors,
            repeat_visitors=repeat_visitors,
            mobile_views=mobile_views,
            desktop_views=desktop_views,
            tablet_views=tablet_views,
            top_countries=top_countries,
            top_cities=top_cities,
            views_by_date=views_by_date
        )
        
        # === ENGAGEMENT ANALYTICS ===
        engagements = list(await db.engagement_analytics.find(engagement_filter).to_list(length=10000))
        
        gallery_opens = len([e for e in engagements if e["event_type"] == "gallery_opened"])
        video_plays = len([e for e in engagements if e["event_type"] == "video_played"])
        music_unmutes = len([e for e in engagements if e["event_type"] == "music_unmuted"])
        map_opens = len([e for e in engagements if e["event_type"] == "map_opened"])
        rsvp_submissions = len([e for e in engagements if e["event_type"] == "rsvp_submitted"])
        scroll_25 = len([e for e in engagements if e["event_type"] == "scroll_25"])
        scroll_50 = len([e for e in engagements if e["event_type"] == "scroll_50"])
        scroll_75 = len([e for e in engagements if e["event_type"] == "scroll_75"])
        scroll_100 = len([e for e in engagements if e["event_type"] == "scroll_100"])
        
        # Average time spent
        time_spent_values = [e["time_spent_seconds"] for e in engagements if e.get("time_spent_seconds")]
        avg_time_spent = sum(time_spent_values) / len(time_spent_values) if time_spent_values else None
        
        engagement_analytics = EngagementAnalyticsData(
            gallery_opens=gallery_opens,
            video_plays=video_plays,
            music_unmutes=music_unmutes,
            map_opens=map_opens,
            rsvp_submissions=rsvp_submissions,
            scroll_25_percent=scroll_25,
            scroll_50_percent=scroll_50,
            scroll_75_percent=scroll_75,
            scroll_100_percent=scroll_100,
            avg_time_spent_seconds=avg_time_spent
        )
        
        # === RSVP ANALYTICS ===
        rsvp_filter = {"profile_id": profile_id}
        if event_id:
            rsvp_filter["event_id"] = event_id
        
        rsvps = list(await db.rsvps.find(rsvp_filter).to_list(length=10000))
        
        total_rsvps = len(rsvps)
        conversion_rate = (total_rsvps / total_views * 100) if total_views > 0 else 0
        
        accepted_count = len([r for r in rsvps if r.get("status") == "accepted"])
        declined_count = len([r for r in rsvps if r.get("status") == "declined"])
        pending_count = len([r for r in rsvps if r.get("status") == "pending"])
        
        # RSVP by event
        event_rsvp_counts = defaultdict(lambda: {"accepted": 0, "declined": 0, "pending": 0})
        for r in rsvps:
            event_id_key = r.get("event_id", "unknown")
            status = r.get("status", "pending")
            event_rsvp_counts[event_id_key][status] += 1
        
        # Get event names
        rsvp_by_event = []
        for eid, counts in event_rsvp_counts.items():
            event = await db.event_invitations.find_one({"id": eid})
            event_name = event.get("event_name", "Unknown Event") if event else "Unknown Event"
            rsvp_by_event.append({
                "event_id": eid,
                "event_name": event_name,
                "accepted": counts["accepted"],
                "declined": counts["declined"],
                "pending": counts["pending"]
            })
        
        # Peak RSVP time
        rsvp_time_counts = defaultdict(int)
        for r in rsvps:
            if r.get("created_at"):
                dt = r["created_at"]
                date_str = dt.strftime("%Y-%m-%d")
                hour = dt.hour
                key = f"{date_str}_{hour}"
                rsvp_time_counts[key] += 1
        
        peak_rsvp_time = None
        if rsvp_time_counts:
            peak_key = max(rsvp_time_counts, key=rsvp_time_counts.get)
            date_str, hour_str = peak_key.split("_")
            peak_rsvp_time = {
                "date": date_str,
                "hour": int(hour_str),
                "count": rsvp_time_counts[peak_key]
            }
        
        rsvp_analytics = RSVPAnalyticsData(
            total_views=total_views,
            total_rsvps=total_rsvps,
            conversion_rate=round(conversion_rate, 2),
            accepted_count=accepted_count,
            declined_count=declined_count,
            pending_count=pending_count,
            rsvp_by_event=rsvp_by_event,
            peak_rsvp_time=peak_rsvp_time
        )
        
        # Build response
        return AnalyticsSummaryResponse(
            profile_id=profile_id,
            date_range={
                "start": start_date,
                "end": end_date
            },
            views=view_analytics,
            engagement=engagement_analytics,
            rsvp=rsvp_analytics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/analytics/export")
async def export_analytics_csv(
    profile_id: str,
    event_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: Admin = Depends(get_current_admin)
):
    """
    Export analytics data as CSV file
    Includes views, engagement, and RSVP data
    """
    try:
        # Verify admin owns this profile
        profile = await db.profiles.find_one({"id": profile_id})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        if profile["admin_id"] != admin["id"]:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Get summary data
        summary = await get_analytics_summary(
            profile_id=profile_id,
            event_id=event_id,
            start_date=start_date,
            end_date=end_date,
            admin=admin
        )
        
        # Build CSV content
        csv_lines = []
        csv_lines.append("Wedding Invitation Analytics Report")
        csv_lines.append(f"Profile ID: {profile_id}")
        csv_lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        csv_lines.append("")
        
        # Views
        csv_lines.append("VIEW ANALYTICS")
        csv_lines.append(f"Total Views,{summary.views.total_views}")
        csv_lines.append(f"Unique Visitors,{summary.views.unique_visitors}")
        csv_lines.append(f"Repeat Visitors,{summary.views.repeat_visitors}")
        csv_lines.append(f"Mobile Views,{summary.views.mobile_views}")
        csv_lines.append(f"Desktop Views,{summary.views.desktop_views}")
        csv_lines.append(f"Tablet Views,{summary.views.tablet_views}")
        csv_lines.append("")
        
        # Top countries
        csv_lines.append("TOP COUNTRIES")
        csv_lines.append("Country,Views")
        for item in summary.views.top_countries:
            csv_lines.append(f"{item['country']},{item['count']}")
        csv_lines.append("")
        
        # Engagement
        csv_lines.append("ENGAGEMENT ANALYTICS")
        csv_lines.append(f"Gallery Opens,{summary.engagement.gallery_opens}")
        csv_lines.append(f"Video Plays,{summary.engagement.video_plays}")
        csv_lines.append(f"Music Unmutes,{summary.engagement.music_unmutes}")
        csv_lines.append(f"Map Opens,{summary.engagement.map_opens}")
        csv_lines.append(f"RSVP Submissions,{summary.engagement.rsvp_submissions}")
        csv_lines.append(f"Scrolled 25%,{summary.engagement.scroll_25_percent}")
        csv_lines.append(f"Scrolled 50%,{summary.engagement.scroll_50_percent}")
        csv_lines.append(f"Scrolled 75%,{summary.engagement.scroll_75_percent}")
        csv_lines.append(f"Scrolled 100%,{summary.engagement.scroll_100_percent}")
        if summary.engagement.avg_time_spent_seconds:
            csv_lines.append(f"Avg Time Spent (seconds),{summary.engagement.avg_time_spent_seconds:.1f}")
        csv_lines.append("")
        
        # RSVP
        csv_lines.append("RSVP ANALYTICS")
        csv_lines.append(f"Total RSVPs,{summary.rsvp.total_rsvps}")
        csv_lines.append(f"Conversion Rate,{summary.rsvp.conversion_rate}%")
        csv_lines.append(f"Accepted,{summary.rsvp.accepted_count}")
        csv_lines.append(f"Declined,{summary.rsvp.declined_count}")
        csv_lines.append(f"Pending,{summary.rsvp.pending_count}")
        csv_lines.append("")
        
        # RSVP by event
        csv_lines.append("RSVP BY EVENT")
        csv_lines.append("Event,Accepted,Declined,Pending")
        for item in summary.rsvp.rsvp_by_event:
            csv_lines.append(f"{item['event_name']},{item['accepted']},{item['declined']},{item['pending']}")
        
        csv_content = "\n".join(csv_lines)
        
        # Return as downloadable file
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=analytics_{profile_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PHASE 31: SEO, SOCIAL SHARING & DISCOVERY
# ============================================================================

@app.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    """
    PHASE 31: Serve robots.txt
    - Block admin pages from indexing
    - Allow public invitation pages
    """
    robots_content = """User-agent: *
Disallow: /admin
Disallow: /admin/*
Disallow: /dashboard
Disallow: /dashboard/*
Disallow: /api/
Allow: /invite/
Allow: /invitation/
Sitemap: {}/sitemap.xml
"""
    # Get the base URL from environment or use default
    base_url = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
    # Remove /api suffix if present
    base_url = base_url.replace('/api', '')
    
    robots_content = robots_content.format(base_url)
    
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=robots_content, media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    """
    PHASE 31: Generate dynamic sitemap.xml
    - Include only public, active, non-expired profiles with SEO enabled
    - Update automatically when profiles are published/unpublished
    """
    try:
        # Get base URL
        base_url = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
        # Remove /api suffix if present and ensure it's the frontend URL
        base_url = base_url.replace('/api', '').replace(':8001', ':3000')
        
        # Get all active, public profiles with SEO enabled
        now = datetime.now(timezone.utc)
        profiles = await db.profiles.find({
            "is_active": True,
            "$or": [
                {"expires_at": {"$gt": now}},
                {"expires_at": None}
            ],
            "seo_settings.seo_enabled": {"$ne": False}  # Default is True
        }).to_list(length=1000)
        
        # Build sitemap XML
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        
        for profile in profiles:
            slug = profile.get('slug')
            updated_at = profile.get('updated_at', profile.get('created_at', datetime.now(timezone.utc)))
            
            # Format date for sitemap (YYYY-MM-DD)
            lastmod = updated_at.strftime('%Y-%m-%d') if isinstance(updated_at, datetime) else datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
            # Main invitation URL
            xml_lines.append('  <url>')
            xml_lines.append(f'    <loc>{base_url}/invite/{slug}</loc>')
            xml_lines.append(f'    <lastmod>{lastmod}</lastmod>')
            xml_lines.append('    <changefreq>weekly</changefreq>')
            xml_lines.append('    <priority>0.8</priority>')
            xml_lines.append('  </url>')
        
        xml_lines.append('</urlset>')
        
        sitemap_content = '\n'.join(xml_lines)
        
        from fastapi.responses import Response
        return Response(content=sitemap_content, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error generating sitemap: {str(e)}")
        # Return empty sitemap on error
        empty_sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
        from fastapi.responses import Response
        return Response(content=empty_sitemap, media_type="application/xml")


# ============================================================================
# PHASE 32: SECURITY & ACCESS CONTROL
# ============================================================================

@api_router.post("/captcha/generate")
async def generate_captcha():
    """
    PHASE 32: Generate a simple math CAPTCHA challenge
    Returns: {challenge_id, challenge_text}
    """
    try:
        # Generate random math challenge (addition or subtraction)
        num1 = random.randint(1, 20)
        num2 = random.randint(1, 20)
        operation = random.choice(['+', '-'])
        
        if operation == '+':
            answer = num1 + num2
            challenge_text = f"{num1} + {num2}"
        else:
            # Ensure non-negative results
            if num1 < num2:
                num1, num2 = num2, num1
            answer = num1 - num2
            challenge_text = f"{num1} - {num2}"
        
        # Hash the answer
        answer_hash = hashlib.sha256(str(answer).encode()).hexdigest()
        
        # Create challenge record
        challenge = CaptchaChallenge(
            challenge=challenge_text,
            answer=answer_hash
        )
        
        # Store in database
        doc = challenge.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['expires_at'] = doc['expires_at'].isoformat()
        await db.captcha_challenges.insert_one(doc)
        
        return {
            "challenge_id": challenge.id,
            "challenge": challenge_text
        }
    
    except Exception as e:
        logger.error(f"Error generating CAPTCHA: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate CAPTCHA")


@api_router.post("/captcha/verify")
async def verify_captcha(verify_request: CaptchaVerifyRequest):
    """
    PHASE 32: Verify CAPTCHA answer
    Returns: {valid: bool}
    """
    try:
        # Find challenge
        challenge = await db.captcha_challenges.find_one(
            {"id": verify_request.challenge_id},
            {"_id": 0}
        )
        
        if not challenge:
            return {"valid": False, "message": "Challenge not found or expired"}
        
        # Check if expired
        expires_at = datetime.fromisoformat(challenge['expires_at'])
        if expires_at < datetime.now(timezone.utc):
            await db.captcha_challenges.delete_one({"id": verify_request.challenge_id})
            return {"valid": False, "message": "Challenge expired"}
        
        # Verify answer
        provided_hash = hashlib.sha256(str(verify_request.answer).encode()).hexdigest()
        is_valid = provided_hash == challenge['answer']
        
        # Delete challenge after verification (one-time use)
        await db.captcha_challenges.delete_one({"id": verify_request.challenge_id})
        
        return {"valid": is_valid}
    
    except Exception as e:
        logger.error(f"Error verifying CAPTCHA: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to verify CAPTCHA")


@api_router.post("/event/{event_id}/verify-access")
async def verify_event_access(
    event_id: str,
    passcode: Optional[str] = None,
    request: Request = None
):
    """
    PHASE 32: Verify access to private event
    Returns: {allowed: bool, requires_passcode: bool, message: str}
    """
    try:
        # Get client IP
        ip_address = get_client_ip(request) if request else "unknown"
        
        # Find event
        profile = await db.profiles.find_one(
            {"events.event_id": event_id},
            {"_id": 0, "events.$": 1}
        )
        
        if not profile or not profile.get('events'):
            raise ErrorResponse.not_found("Event not found")
        
        event = profile['events'][0]
        
        # Check access
        access_result = check_event_access(event, passcode, ip_address)
        
        if access_result["allowed"]:
            return {
                "allowed": True,
                "requires_passcode": False,
                "message": "Access granted"
            }
        else:
            return {
                "allowed": False,
                "requires_passcode": access_result["requires_passcode"],
                "message": access_result["reason"],
                "remaining_attempts": access_result.get("remaining_attempts", 0),
                "blocked_until": access_result.get("blocked_until").isoformat() if access_result.get("blocked_until") else None
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying event access: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to verify access")


async def check_submission_attempts(ip_address: str, device_id: Optional[str], endpoint: str, slug: str) -> dict:
    """
    PHASE 32: Check if CAPTCHA is required based on failed submission attempts
    Returns: {requires_captcha: bool, failed_attempts: int}
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Check recent failed attempts (last 1 hour)
    hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    
    query = {
        "ip_address": ip_address,
        "endpoint": endpoint,
        "slug": slug,
        "success": False,
        "created_at": {"$gte": hour_ago}
    }
    
    # Also check device_id if provided
    if device_id:
        query["$or"] = [
            {"ip_address": ip_address},
            {"device_id": device_id}
        ]
    
    failed_attempts = await db.submission_attempts.count_documents(query)
    
    # Require CAPTCHA after 2 failed attempts
    requires_captcha = failed_attempts >= 2
    
    return {
        "requires_captcha": requires_captcha,
        "failed_attempts": failed_attempts
    }


async def track_submission_attempt(
    ip_address: str,
    device_id: Optional[str],
    endpoint: str,
    slug: str,
    success: bool,
    requires_captcha: bool
):
    """
    PHASE 32: Track submission attempt for CAPTCHA triggering
    """
    attempt = SubmissionAttempt(
        ip_address=ip_address,
        device_id=device_id,
        endpoint=endpoint,
        slug=slug,
        success=success,
        requires_captcha=requires_captcha
    )
    
    doc = attempt.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.submission_attempts.insert_one(doc)


@api_router.get("/check-captcha-required")
async def check_captcha_required(
    endpoint: str,
    slug: str,
    device_id: Optional[str] = None,
    request: Request = None
):
    """
    PHASE 32: Check if CAPTCHA is required for this user/device
    """
    try:
        ip_address = get_client_ip(request) if request else "unknown"
        
        result = await check_submission_attempts(ip_address, device_id, endpoint, slug)
        
        return result
    
    except Exception as e:
        logger.error(f"Error checking CAPTCHA requirement: {str(e)}")
        return {"requires_captcha": False, "failed_attempts": 0}




# ============================================================================
# PHASE 33: MONETIZATION & PREMIUM PLANS
# ============================================================================

@api_router.get("/admin/profiles/{profile_id}/plan", response_model=PlanInfoResponse)
async def get_profile_plan(
    profile_id: str,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 33: Get plan information for a profile
    Admin only endpoint
    """
    try:
        # Get profile
        profile = await db.profiles.find_one({"id": profile_id})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Get plan info
        plan_type = profile.get('plan_type', 'FREE')
        plan_expires_at = profile.get('plan_expires_at')
        
        # Calculate days remaining
        days_remaining = None
        is_expired = False
        if plan_expires_at and plan_type != 'FREE':
            if isinstance(plan_expires_at, str):
                expiry_date = datetime.fromisoformat(plan_expires_at.replace('Z', '+00:00'))
            else:
                expiry_date = plan_expires_at
            
            now = datetime.now(timezone.utc)
            if expiry_date < now:
                is_expired = True
                days_remaining = 0
            else:
                days_remaining = (expiry_date - now).days
        
        # Get plan details
        plan_details = get_plan_info(plan_type if not is_expired else 'FREE')
        
        return PlanInfoResponse(
            current_plan=plan_type if not is_expired else 'FREE',
            plan_expires_at=plan_expires_at,
            days_remaining=days_remaining,
            is_expired=is_expired,
            features=plan_details.get('features', []),
            limitations=plan_details.get('limitations', []),
            upgrade_available=(plan_type != 'PLATINUM' or is_expired)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plan info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting plan info: {str(e)}")


@api_router.post("/admin/profiles/{profile_id}/plan")
async def update_profile_plan(
    profile_id: str,
    plan_update: UpdatePlanRequest,
    admin_id: str = Depends(get_current_admin)
):
    """
    PHASE 33: Update profile plan (admin only)
    Mock payment - directly updates plan in database
    """
    try:
        # Get profile
        profile = await db.profiles.find_one({"id": profile_id})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Validate plan type
        valid_plans = ['FREE', 'SILVER', 'GOLD', 'PLATINUM']
        if plan_update.plan_type not in valid_plans:
            raise HTTPException(status_code=400, detail="Invalid plan type")
        
        # Update plan
        update_data = {
            "plan_type": plan_update.plan_type,
            "plan_expires_at": plan_update.plan_expires_at.isoformat() if plan_update.plan_expires_at else None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.profiles.update_one(
            {"id": profile_id},
            {"$set": update_data}
        )
        
        # Log admin action
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": admin_id,
            "profile_id": profile_id,
            "action": "plan_update",
            "details": {
                "new_plan": plan_update.plan_type,
                "expires_at": plan_update.plan_expires_at.isoformat() if plan_update.plan_expires_at else None
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "message": f"Plan updated to {plan_update.plan_type}",
            "plan_type": plan_update.plan_type,
            "plan_expires_at": plan_update.plan_expires_at
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating plan: {str(e)}")


@api_router.get("/profiles/{profile_id}/features", response_model=FeatureFlagsResponse)
async def get_profile_features(profile_id: str):
    """
    PHASE 33: Get feature flags for a profile
    Public endpoint - used by frontend to determine feature availability
    """
    try:
        # Get profile
        profile = await db.profiles.find_one({"id": profile_id})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Get feature flags
        feature_flags = get_feature_flags(profile)
        gallery_limit = get_gallery_limit(profile)
        watermark_required = requires_watermark(profile)
        
        plan_type = profile.get('plan_type', 'FREE')
        
        # Check if plan expired
        plan_expires_at = profile.get('plan_expires_at')
        if plan_expires_at and plan_type != 'FREE':
            if isinstance(plan_expires_at, str):
                expiry_date = datetime.fromisoformat(plan_expires_at.replace('Z', '+00:00'))
            else:
                expiry_date = plan_expires_at
            
            if expiry_date < datetime.now(timezone.utc):
                plan_type = 'FREE'
        
        return FeatureFlagsResponse(
            plan_type=plan_type,
            feature_flags=feature_flags,
            gallery_limit=gallery_limit,
            requires_watermark=watermark_required
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting feature flags: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting feature flags: {str(e)}")


@api_router.get("/plans/info")
async def get_all_plans_info():
    """
    PHASE 33: Get information about all available plans
    Public endpoint for displaying plan options
    """
    try:
        plans = {}
        for plan_type in ['FREE', 'SILVER', 'GOLD', 'PLATINUM']:
            plans[plan_type] = get_plan_info(plan_type)
        
        return {
            "plans": plans,
            "currency": "INR",  # Can be made configurable
            "prices": {
                "FREE": 0,
                "SILVER": 999,   # Mock prices
                "GOLD": 1999,
                "PLATINUM": 3999
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting plans info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting plans info: {str(e)}")



# ============================================================================
# PHASE 34: PAYMENT & PLAN ACTIVATION
# ============================================================================

# Plan pricing configuration (in paise - 100 paise = 1 INR)
PLAN_PRICING = {
    "SILVER": {
        "amount": 99900,  # ₹999
        "duration_days": 30,
        "name": "Silver Plan",
        "description": "Background music, Gallery (10 images), Basic analytics"
    },
    "GOLD": {
        "amount": 199900,  # ₹1999
        "duration_days": 30,
        "name": "Gold Plan", 
        "description": "Video, Gallery (50 images), Advanced analytics, Passcode"
    },
    "PLATINUM": {
        "amount": 399900,  # ₹3999
        "duration_days": 30,
        "name": "Platinum Plan",
        "description": "All features, AI translation, Unlimited gallery"
    }
}


@api_router.post("/payments/create-order", response_model=CreatePaymentOrderResponse)
async def create_payment_order(
    request: CreatePaymentOrderRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    PHASE 34: Create a Razorpay payment order
    
    Security:
    - Requires authentication
    - Validates plan type
    - Creates order in Razorpay
    - Stores payment record in database
    """
    try:
        # Check if Razorpay client is initialized
        if razorpay_client is None:
            raise HTTPException(
                status_code=503,
                detail="Payment gateway not configured. Please contact administrator."
            )
        
        # Validate profile exists
        profile = await db.profiles.find_one({"profile_id": request.profile_id})
        if not profile:
            raise ErrorResponse.not_found(f"Profile {request.profile_id} not found")
        
        # Get plan pricing
        plan_config = PLAN_PRICING.get(request.plan_type)
        if not plan_config:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid plan type: {request.plan_type}"
            )
        
        # Create Razorpay order
        razorpay_order = razorpay_client.order.create({
            "amount": plan_config["amount"],
            "currency": "INR",
            "payment_capture": 1,  # Auto capture
            "notes": {
                "profile_id": request.profile_id,
                "plan_type": request.plan_type,
                "admin_id": current_admin.get("admin_id", "")
            }
        })
        
        # Create payment record in database
        payment_id = f"pay_{uuid.uuid4().hex[:16]}"
        payment_data = {
            "payment_id": payment_id,
            "profile_id": request.profile_id,
            "admin_id": current_admin.get("admin_id"),
            "plan_type": request.plan_type,
            "amount": plan_config["amount"],
            "currency": "INR",
            "payment_status": "created",
            "razorpay_order_id": razorpay_order["id"],
            "razorpay_payment_id": None,
            "razorpay_signature": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "payment_method": None,
            "error_message": None
        }
        
        await db.payments.insert_one(payment_data)
        
        # Log audit trail
        await db.audit_logs.insert_one({
            "admin_id": current_admin.get("admin_id"),
            "action": "payment_order_created",
            "resource_type": "payment",
            "resource_id": payment_id,
            "details": f"Created payment order for {request.plan_type} plan",
            "timestamp": datetime.now(timezone.utc)
        })
        
        return CreatePaymentOrderResponse(
            order_id=razorpay_order["id"],
            amount=plan_config["amount"],
            currency="INR",
            razorpay_key_id=RAZORPAY_KEY_ID,
            payment_id=payment_id,
            profile_id=request.profile_id,
            plan_type=request.plan_type
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment order: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating payment order: {str(e)}"
        )


@api_router.post("/payments/verify", response_model=VerifyPaymentResponse)
async def verify_payment(
    request: VerifyPaymentRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    PHASE 34: Verify Razorpay payment and activate plan
    
    Security Rules:
    - NEVER trust frontend payment success
    - ALL verification MUST be server-side
    - Prevent replay attacks with signature verification
    - Idempotent payment handling
    """
    try:
        # Check if Razorpay client is initialized
        if razorpay_client is None:
            raise HTTPException(
                status_code=503,
                detail="Payment gateway not configured. Please contact administrator."
            )
        
        # Find payment record
        payment = await db.payments.find_one({"payment_id": request.payment_id})
        if not payment:
            raise ErrorResponse.not_found("Payment record not found")
        
        # Check if already processed (idempotent handling)
        if payment.get("payment_status") == "success":
            # Already processed, return existing result
            profile = await db.profiles.find_one({"profile_id": payment["profile_id"]})
            return VerifyPaymentResponse(
                success=True,
                message="Payment already verified and plan activated",
                payment_status="success",
                plan_activated=True,
                plan_expires_at=profile.get("plan_expires_at")
            )
        
        # CRITICAL: Verify Razorpay signature (server-side verification)
        try:
            # Generate expected signature
            generated_signature = hmac.new(
                RAZORPAY_KEY_SECRET.encode('utf-8'),
                f"{request.razorpay_order_id}|{request.razorpay_payment_id}".encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            if generated_signature != request.razorpay_signature:
                # Signature mismatch - potential fraud
                await db.payments.update_one(
                    {"payment_id": request.payment_id},
                    {
                        "$set": {
                            "payment_status": "failed",
                            "error_message": "Signature verification failed",
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
                
                raise HTTPException(
                    status_code=400,
                    detail="Payment verification failed. Invalid signature."
                )
            
        except Exception as e:
            logger.error(f"Signature verification error: {str(e)}")
            await db.payments.update_one(
                {"payment_id": request.payment_id},
                {
                    "$set": {
                        "payment_status": "failed",
                        "error_message": f"Signature verification error: {str(e)}",
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            raise HTTPException(
                status_code=400,
                detail="Payment verification failed"
            )
        
        # Signature verified - Fetch payment details from Razorpay
        try:
            razorpay_payment = razorpay_client.payment.fetch(request.razorpay_payment_id)
            payment_method = razorpay_payment.get("method", "unknown")
        except Exception as e:
            logger.warning(f"Could not fetch payment details: {str(e)}")
            payment_method = "unknown"
        
        # Update payment record
        await db.payments.update_one(
            {"payment_id": request.payment_id},
            {
                "$set": {
                    "payment_status": "success",
                    "razorpay_payment_id": request.razorpay_payment_id,
                    "razorpay_signature": request.razorpay_signature,
                    "payment_method": payment_method,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # ACTIVATE PLAN - Calculate expiry date
        plan_config = PLAN_PRICING.get(payment["plan_type"])
        plan_expires_at = datetime.now(timezone.utc) + timedelta(days=plan_config["duration_days"])
        
        # Update profile with new plan
        await db.profiles.update_one(
            {"profile_id": payment["profile_id"]},
            {
                "$set": {
                    "plan_type": payment["plan_type"],
                    "plan_expires_at": plan_expires_at,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # Log audit trail
        await db.audit_logs.insert_one({
            "admin_id": payment.get("admin_id"),
            "action": "plan_activated_via_payment",
            "resource_type": "profile",
            "resource_id": payment["profile_id"],
            "details": f"Activated {payment['plan_type']} plan via payment {request.payment_id}",
            "timestamp": datetime.now(timezone.utc)
        })
        
        logger.info(f"✅ Plan activated: {payment['plan_type']} for profile {payment['profile_id']}")
        
        return VerifyPaymentResponse(
            success=True,
            message=f"{payment['plan_type']} plan activated successfully",
            payment_status="success",
            plan_activated=True,
            plan_expires_at=plan_expires_at,
            invoice_url=None  # TODO: Generate invoice PDF
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        
        # Mark payment as failed
        try:
            await db.payments.update_one(
                {"payment_id": request.payment_id},
                {
                    "$set": {
                        "payment_status": "failed",
                        "error_message": str(e),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
        except:
            pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Error verifying payment: {str(e)}"
        )


@api_router.get("/payments/history/{profile_id}", response_model=PaymentHistoryResponse)
async def get_payment_history(
    profile_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """
    PHASE 34: Get payment history for a profile
    
    Returns all payment transactions for the profile
    """
    try:
        # Find all payments for this profile
        payments_cursor = db.payments.find(
            {"profile_id": profile_id}
        ).sort("created_at", -1)
        
        payments_list = []
        async for payment in payments_cursor:
            # Remove MongoDB _id
            payment.pop("_id", None)
            
            # Convert datetime to ISO string
            if payment.get("created_at"):
                payment["created_at"] = payment["created_at"].isoformat()
            if payment.get("updated_at"):
                payment["updated_at"] = payment["updated_at"].isoformat()
            
            # Add display amount (convert paise to rupees)
            payment["display_amount"] = f"₹{payment['amount'] / 100:.2f}"
            
            payments_list.append(payment)
        
        return PaymentHistoryResponse(
            payments=payments_list,
            total=len(payments_list)
        )
    
    except Exception as e:
        logger.error(f"Error getting payment history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting payment history: {str(e)}"
        )


@api_router.get("/payments/{payment_id}")
async def get_payment_details(
    payment_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """
    PHASE 34: Get details of a specific payment
    """
    try:
        payment = await db.payments.find_one({"payment_id": payment_id})
        if not payment:
            raise ErrorResponse.not_found("Payment not found")
        
        # Remove MongoDB _id
        payment.pop("_id", None)
        
        # Convert datetime to ISO string
        if payment.get("created_at"):
            payment["created_at"] = payment["created_at"].isoformat()
        if payment.get("updated_at"):
            payment["updated_at"] = payment["updated_at"].isoformat()
        
        # Add display amount
        payment["display_amount"] = f"₹{payment['amount'] / 100:.2f}"
        
        return payment
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting payment details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting payment details: {str(e)}"
        )


# ============================================================================
# PHASE 35: REFERRAL, CREDITS & VIRAL GROWTH ENGINE
# ============================================================================

# Credit pricing configuration
CREDIT_CONFIG = {
    "feature_unlock_7days": 100,  # 100 credits for 7-day feature unlock
    "plan_extension_1day": 50,  # 50 credits per day
    "referral_reward_completed": 200,  # 200 credits per completed referral
    "referral_reward_signup": 50,  # 50 credits when someone signs up
    "credits_expire_months": 12,  # Credits expire after 12 months
    "min_spend_amount": 50,  # Minimum 50 credits per transaction
}


def generate_referral_code(profile_id: str) -> str:
    """Generate unique referral code"""
    # Use first 4 chars of profile_id + 4 random chars
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{profile_id[:4].upper()}{random_suffix}"


async def check_referral_abuse(referrer_profile_id: str, user_ip: str, device_fingerprint: str) -> bool:
    """
    Check for referral abuse patterns
    Returns True if abuse detected
    """
    # Check if same IP used for referrer
    referrer_profile = await db.profiles.find_one({"id": referrer_profile_id})
    
    # Check recent referrals from same IP (within 24 hours)
    yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
    same_ip_count = await db.referrals.count_documents({
        "referred_user_ip": user_ip,
        "created_at": {"$gte": yesterday}
    })
    
    if same_ip_count >= 3:
        logger.warning(f"Referral abuse: IP {user_ip} used {same_ip_count} times in 24h")
        return True
    
    # Check same device fingerprint
    if device_fingerprint:
        same_device_count = await db.referrals.count_documents({
            "referred_user_device_fingerprint": device_fingerprint,
            "created_at": {"$gte": yesterday}
        })
        
        if same_device_count >= 2:
            logger.warning(f"Referral abuse: Device {device_fingerprint} used {same_device_count} times")
            return True
    
    return False


async def award_referral_credits(referrer_profile_id: str, referral_id: str, credits: int):
    """Award credits to referrer"""
    try:
        # Get or create credit wallet
        wallet = await db.credit_wallets.find_one({"profile_id": referrer_profile_id})
        
        if not wallet:
            # Create new wallet
            wallet = {
                "profile_id": referrer_profile_id,
                "balance": credits,
                "earned_total": credits,
                "spent_total": 0,
                "expired_total": 0,
                "last_updated": datetime.now(timezone.utc)
            }
            await db.credit_wallets.insert_one(wallet)
        else:
            # Update existing wallet
            await db.credit_wallets.update_one(
                {"profile_id": referrer_profile_id},
                {
                    "$inc": {
                        "balance": credits,
                        "earned_total": credits
                    },
                    "$set": {
                        "last_updated": datetime.now(timezone.utc)
                    }
                }
            )
        
        # Create transaction record
        transaction = {
            "transaction_id": f"txn_{uuid.uuid4().hex[:16]}",
            "profile_id": referrer_profile_id,
            "type": "referral_reward",
            "amount": credits,
            "balance_after": wallet.get("balance", 0) + credits,
            "description": f"Referral reward for referral {referral_id}",
            "metadata": {"referral_id": referral_id},
            "created_at": datetime.now(timezone.utc)
        }
        await db.credit_transactions.insert_one(transaction)
        
        logger.info(f"✅ Awarded {credits} credits to profile {referrer_profile_id}")
        
    except Exception as e:
        logger.error(f"Error awarding credits: {str(e)}")


@api_router.post("/profiles/{profile_id}/referral-code", response_model=ReferralCodeResponse)
async def create_or_get_referral_code(
    profile_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """
    PHASE 35: Generate or get existing referral code for a profile
    """
    try:
        # Verify profile exists
        profile = await db.profiles.find_one({"id": profile_id})
        if not profile:
            raise ErrorResponse.not_found("Profile not found")
        
        # Check if referral code already exists
        existing_referral = await db.referrals.find_one({
            "referrer_profile_id": profile_id,
            "referred_profile_id": None  # Code not yet used
        })
        
        if existing_referral:
            referral_code = existing_referral["referral_code"]
        else:
            # Generate new unique code
            while True:
                referral_code = generate_referral_code(profile_id)
                # Check if code already exists
                existing = await db.referrals.find_one({"referral_code": referral_code})
                if not existing:
                    break
            
            # Create referral record
            referral_data = {
                "referral_id": f"ref_{uuid.uuid4().hex[:16]}",
                "referrer_profile_id": profile_id,
                "referrer_admin_id": current_admin.get("admin_id"),
                "referred_profile_id": None,
                "referral_code": referral_code,
                "status": "pending",
                "reward_credits": 0,
                "created_at": datetime.now(timezone.utc)
            }
            await db.referrals.insert_one(referral_data)
        
        # Get referral stats
        total_referrals = await db.referrals.count_documents({
            "referrer_profile_id": profile_id
        })
        
        completed_referrals = await db.referrals.count_documents({
            "referrer_profile_id": profile_id,
            "status": "completed"
        })
        
        pending_referrals = await db.referrals.count_documents({
            "referrer_profile_id": profile_id,
            "status": "pending"
        })
        
        # Get total credits earned from referrals
        wallet = await db.credit_wallets.find_one({"profile_id": profile_id})
        total_credits = wallet.get("earned_total", 0) if wallet else 0
        
        # Build referral URL
        slug = profile.get("slug", "")
        base_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
        referral_url = f"{base_url}/invite/{slug}?ref={referral_code}"
        referral_short = f"{base_url}/?ref={referral_code}"
        
        return ReferralCodeResponse(
            referral_code=referral_code,
            referral_url=referral_url,
            referral_link_short=referral_short,
            total_referrals=total_referrals,
            completed_referrals=completed_referrals,
            pending_referrals=pending_referrals,
            total_credits_earned=total_credits
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating referral code: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating referral code: {str(e)}"
        )


@api_router.get("/profiles/{profile_id}/referral-code", response_model=ReferralCodeResponse)
async def get_referral_code(
    profile_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """
    PHASE 35: Get existing referral code
    """
    return await create_or_get_referral_code(profile_id, current_admin)


@api_router.post("/referrals/apply")
async def apply_referral_code(
    request: ApplyReferralRequest
):
    """
    PHASE 35: Apply referral code when creating new profile
    No authentication required - called during profile creation
    """
    try:
        # Find referral code
        referral = await db.referrals.find_one({
            "referral_code": request.referral_code.upper()
        })
        
        if not referral:
            raise ErrorResponse.not_found("Invalid referral code")
        
        # Check if code already used
        if referral.get("referred_profile_id"):
            raise ErrorResponse.bad_request("Referral code already used")
        
        # Prevent self-referral
        if referral["referrer_profile_id"] == request.profile_id:
            raise ErrorResponse.bad_request("Cannot use your own referral code")
        
        # Check for abuse
        if request.user_ip and request.device_fingerprint:
            is_abuse = await check_referral_abuse(
                referral["referrer_profile_id"],
                request.user_ip,
                request.device_fingerprint
            )
            
            if is_abuse:
                logger.warning(f"Referral abuse detected for code {request.referral_code}")
                raise ErrorResponse.bad_request("Referral validation failed")
        
        # Update referral record
        await db.referrals.update_one(
            {"referral_id": referral["referral_id"]},
            {
                "$set": {
                    "referred_profile_id": request.profile_id,
                    "status": "completed",
                    "reward_credits": CREDIT_CONFIG["referral_reward_completed"],
                    "referred_user_ip": request.user_ip,
                    "referred_user_device_fingerprint": request.device_fingerprint,
                    "completed_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # Award credits to referrer
        await award_referral_credits(
            referral["referrer_profile_id"],
            referral["referral_id"],
            CREDIT_CONFIG["referral_reward_completed"]
        )
        
        # Also give credits to new user
        await award_referral_credits(
            request.profile_id,
            referral["referral_id"],
            CREDIT_CONFIG["referral_reward_signup"]
        )
        
        logger.info(f"✅ Referral applied: {request.referral_code} -> {request.profile_id}")
        
        return {
            "success": True,
            "message": f"Referral applied! You earned {CREDIT_CONFIG['referral_reward_signup']} credits!",
            "credits_earned": CREDIT_CONFIG["referral_reward_signup"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying referral: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error applying referral: {str(e)}"
        )


@api_router.get("/profiles/{profile_id}/referrals", response_model=ReferralStatsResponse)
async def get_referral_stats(
    profile_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """
    PHASE 35: Get referral statistics for a profile
    """
    try:
        # Get all referrals
        referrals_cursor = db.referrals.find({
            "referrer_profile_id": profile_id
        }).sort("created_at", -1).limit(10)
        
        referrals_list = []
        async for ref in referrals_cursor:
            ref.pop("_id", None)
            if ref.get("created_at"):
                ref["created_at"] = ref["created_at"].isoformat()
            if ref.get("completed_at"):
                ref["completed_at"] = ref["completed_at"].isoformat()
            referrals_list.append(ref)
        
        # Get stats
        total = await db.referrals.count_documents({"referrer_profile_id": profile_id})
        completed = await db.referrals.count_documents({
            "referrer_profile_id": profile_id,
            "status": "completed"
        })
        pending = await db.referrals.count_documents({
            "referrer_profile_id": profile_id,
            "status": "pending"
        })
        
        # Get credits earned
        wallet = await db.credit_wallets.find_one({"profile_id": profile_id})
        credits_earned = wallet.get("earned_total", 0) if wallet else 0
        
        return ReferralStatsResponse(
            total_referrals=total,
            completed_referrals=completed,
            pending_referrals=pending,
            total_credits_earned=credits_earned,
            recent_referrals=referrals_list
        )
    
    except Exception as e:
        logger.error(f"Error getting referral stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting referral stats: {str(e)}"
        )


@api_router.get("/profiles/{profile_id}/credits", response_model=CreditWalletResponse)
async def get_credit_wallet(
    profile_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """
    PHASE 35: Get credit wallet balance and history
    """
    try:
        # Get wallet
        wallet = await db.credit_wallets.find_one({"profile_id": profile_id})
        
        if not wallet:
            # Create empty wallet
            wallet = {
                "profile_id": profile_id,
                "balance": 0,
                "earned_total": 0,
                "spent_total": 0,
                "expired_total": 0,
                "last_updated": datetime.now(timezone.utc)
            }
            await db.credit_wallets.insert_one(wallet)
        
        # Get recent transactions
        transactions_cursor = db.credit_transactions.find({
            "profile_id": profile_id
        }).sort("created_at", -1).limit(10)
        
        transactions_list = []
        async for txn in transactions_cursor:
            txn.pop("_id", None)
            if txn.get("created_at"):
                txn["created_at"] = txn["created_at"].isoformat()
            transactions_list.append(txn)
        
        return CreditWalletResponse(
            balance=wallet.get("balance", 0),
            earned_total=wallet.get("earned_total", 0),
            spent_total=wallet.get("spent_total", 0),
            expired_total=wallet.get("expired_total", 0),
            recent_transactions=transactions_list
        )
    
    except Exception as e:
        logger.error(f"Error getting credit wallet: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting credit wallet: {str(e)}"
        )


@api_router.post("/profiles/{profile_id}/credits/spend", response_model=SpendCreditsResponse)
async def spend_credits(
    profile_id: str,
    request: SpendCreditsRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    PHASE 35: Spend credits to unlock features or extend plan
    """
    try:
        # Get wallet
        wallet = await db.credit_wallets.find_one({"profile_id": profile_id})
        
        if not wallet or wallet.get("balance", 0) <= 0:
            raise ErrorResponse.bad_request("Insufficient credits")
        
        credits_to_spend = 0
        benefit_description = ""
        benefit_expires_at = None
        
        if request.spend_type == "feature_unlock":
            # Unlock a feature for 7 days
            credits_to_spend = CREDIT_CONFIG["feature_unlock_7days"]
            benefit_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            benefit_description = f"Unlocked {request.feature_name} for 7 days"
            
        elif request.spend_type == "plan_extension":
            # Extend plan by X days
            days = request.extension_days or 1
            credits_to_spend = CREDIT_CONFIG["plan_extension_1day"] * days
            benefit_expires_at = datetime.now(timezone.utc) + timedelta(days=days)
            benefit_description = f"Extended plan by {days} day(s)"
        
        # Check sufficient balance
        if wallet.get("balance", 0) < credits_to_spend:
            raise ErrorResponse.bad_request(
                f"Insufficient credits. Need {credits_to_spend}, have {wallet.get('balance', 0)}"
            )
        
        # Deduct credits
        new_balance = wallet["balance"] - credits_to_spend
        await db.credit_wallets.update_one(
            {"profile_id": profile_id},
            {
                "$inc": {
                    "spent_total": credits_to_spend
                },
                "$set": {
                    "balance": new_balance,
                    "last_updated": datetime.now(timezone.utc)
                }
            }
        )
        
        # Create transaction
        transaction = {
            "transaction_id": f"txn_{uuid.uuid4().hex[:16]}",
            "profile_id": profile_id,
            "type": request.spend_type,
            "amount": -credits_to_spend,
            "balance_after": new_balance,
            "description": benefit_description,
            "metadata": {
                "feature_name": request.feature_name,
                "extension_days": request.extension_days
            },
            "created_at": datetime.now(timezone.utc)
        }
        await db.credit_transactions.insert_one(transaction)
        
        # Apply benefit
        if request.spend_type == "plan_extension":
            # Extend current plan
            profile = await db.profiles.find_one({"profile_id": profile_id})
            current_expiry = profile.get("plan_expires_at")
            
            if current_expiry:
                new_expiry = current_expiry + timedelta(days=request.extension_days)
            else:
                new_expiry = benefit_expires_at
            
            await db.profiles.update_one(
                {"profile_id": profile_id},
                {"$set": {"plan_expires_at": new_expiry}}
            )
            benefit_expires_at = new_expiry
        
        logger.info(f"✅ Spent {credits_to_spend} credits for {profile_id}: {benefit_description}")
        
        return SpendCreditsResponse(
            success=True,
            message=benefit_description,
            credits_spent=credits_to_spend,
            new_balance=new_balance,
            benefit_expires_at=benefit_expires_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error spending credits: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error spending credits: {str(e)}"
        )


@api_router.get("/profiles/{profile_id}/credits/transactions")
async def get_credit_transactions(
    profile_id: str,
    limit: int = 50,
    current_admin: dict = Depends(get_current_admin)
):
    """
    PHASE 35: Get credit transaction history
    """
    try:
        transactions_cursor = db.credit_transactions.find({
            "profile_id": profile_id
        }).sort("created_at", -1).limit(limit)
        
        transactions_list = []
        async for txn in transactions_cursor:
            txn.pop("_id", None)
            if txn.get("created_at"):
                txn["created_at"] = txn["created_at"].isoformat()
            transactions_list.append(txn)
        
        return {
            "transactions": transactions_list,
            "total": len(transactions_list)
        }
    
    except Exception as e:
        logger.error(f"Error getting transactions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting transactions: {str(e)}"
        )


@api_router.post("/admin/referrals/override")
async def admin_referral_override(
    request: AdminReferralOverrideRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    PHASE 35: Admin override for referral abuse or manual credit grants
    """
    try:
        referral = await db.referrals.find_one({"referral_id": request.referral_id})
        if not referral:
            raise ErrorResponse.not_found("Referral not found")
        
        if request.action == "approve":
            # Manually approve a pending referral
            await db.referrals.update_one(
                {"referral_id": request.referral_id},
                {"$set": {"status": "completed"}}
            )
            
        elif request.action == "reject":
            # Reject/cancel a referral
            await db.referrals.update_one(
                {"referral_id": request.referral_id},
                {"$set": {"status": "cancelled"}}
            )
            
        elif request.action == "grant_credits":
            # Manually grant credits
            if not request.credits_amount:
                raise ErrorResponse.bad_request("credits_amount required")
            
            await award_referral_credits(
                referral["referrer_profile_id"],
                request.referral_id,
                request.credits_amount
            )
            
        elif request.action == "revoke_credits":
            # Revoke credits (deduct)
            if not request.credits_amount:
                raise ErrorResponse.bad_request("credits_amount required")
            
            await db.credit_wallets.update_one(
                {"profile_id": referral["referrer_profile_id"]},
                {
                    "$inc": {
                        "balance": -request.credits_amount,
                        "spent_total": request.credits_amount
                    }
                }
            )
        
        # Log audit
        await db.audit_logs.insert_one({
            "admin_id": current_admin.get("admin_id"),
            "action": f"referral_override_{request.action}",
            "resource_type": "referral",
            "resource_id": request.referral_id,
            "details": request.reason,
            "timestamp": datetime.now(timezone.utc)
        })
        
        return {
            "success": True,
            "message": f"Referral {request.action} completed"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in admin override: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error in admin override: {str(e)}"
        )


@api_router.get("/credit-config")
async def get_credit_config():
    """
    PHASE 35: Get credit pricing configuration (public endpoint)
    """
    return CREDIT_CONFIG



@api_router.get("/public/photographer-stats")
async def get_public_photographer_stats():
    """Live read-only counters for the homepage Photographer Advantages banner.

    Returns:
      - published_total          : how many photographer-owned weddings are live
      - photographers_total      : active (non-trashed) photographer accounts
      - bonus_credits_granted    : total credits awarded by loyalty tier bonuses

    No auth. Used by the public LandingPage to keep the homepage numbers in
    sync with what the studio is actually doing.
    """
    try:
        # Photographer-owned weddings that are currently published.
        published_total = await db.wedding_profiles.count_documents({
            "is_published": True,
            "is_deleted": {"$ne": True},
            "is_trashed": {"$ne": True},
        })
    except Exception:
        published_total = 0

    try:
        # Active photographer accounts (super-admin / regular admin).
        # Exclude soft-deleted / suspended rows.
        photographers_total = await db.admins.count_documents({
            "$or": [{"deleted_at": {"$exists": False}}, {"deleted_at": None}],
            "$and": [
                {"$or": [{"is_suspended": False}, {"is_suspended": {"$exists": False}}]},
            ],
        })
    except Exception:
        photographers_total = 0

    # Bonus credits granted across all credit-pack purchases (loyalty tiers).
    bonus_credits_granted = 0
    try:
        cursor = db.credit_purchases.aggregate([
            {"$match": {"credited": True, "bonus_credits": {"$gt": 0}}},
            {"$group": {"_id": None, "total": {"$sum": "$bonus_credits"}}},
        ])
        async for row in cursor:
            bonus_credits_granted = int(row.get("total") or 0)
            break
    except Exception:
        bonus_credits_granted = 0

    return {
        "published_total": published_total,
        "photographers_total": photographers_total,
        "bonus_credits_granted": bonus_credits_granted,
    }



@api_router.get("/public/referral-code/{profile_id}")
async def get_public_referral_code(profile_id: str):
    """
    PHASE 35: Get referral code for public display (no auth required)
    Returns only the referral code for guest CTA display
    """
    try:
        # Find the referral code for this profile
        referral = await db.referrals.find_one({
            "referrer_profile_id": profile_id
        })
        
        if referral and referral.get("referral_code"):
            return {
                "referral_code": referral["referral_code"],
                "profile_id": profile_id
            }
        
        # If no referral code exists, generate one
        # This allows guest CTAs to work even if admin hasn't accessed referrals yet
        referral_code = generate_referral_code(profile_id)
        
        # Check if code is unique
        existing = await db.referrals.find_one({"referral_code": referral_code})
        if existing:
            # Code collision, add random suffix
            referral_code = f"{referral_code}{random.randint(10, 99)}"
        
        # Get profile to find admin_id
        profile = await db.profiles.find_one({"id": profile_id})
        if not profile:
            raise ErrorResponse.not_found("Profile not found")
        
        # Create referral record
        referral_data = {
            "referral_id": f"ref_{uuid.uuid4().hex[:16]}",
            "referrer_profile_id": profile_id,
            "referrer_admin_id": profile.get("admin_id", "unknown"),
            "referred_profile_id": None,
            "referral_code": referral_code,
            "status": "pending",
            "reward_credits": 0,
            "created_at": datetime.now(timezone.utc)
        }
        await db.referrals.insert_one(referral_data)
        
        return {
            "referral_code": referral_code,
            "profile_id": profile_id
        }
    
    except Exception as e:
        logger.error(f"Error getting public referral code: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting referral code: {str(e)}"
        )


# ==========================================
# PHASE 34: DESIGN SYSTEM & THEME ENGINE
# ==========================================

@api_router.get("/themes")
async def get_all_themes(
    plan_type: Optional[str] = None
):
    """
    PHASE 34: Get all available themes
    Optionally filter by plan type to show only accessible themes
    """
    from theme_constants import get_all_themes_preview, get_themes_by_plan, MASTER_THEMES
    
    try:
        if plan_type:
            # Filter themes by plan access
            accessible_theme_ids = get_themes_by_plan(plan_type)
            all_themes = get_all_themes_preview()
            filtered_themes = [t for t in all_themes if t['id'] in accessible_theme_ids]
            
            return {
                "themes": filtered_themes,
                "total": len(filtered_themes),
                "plan_type": plan_type
            }
        else:
            # Return all themes
            all_themes = get_all_themes_preview()
            return {
                "themes": all_themes,
                "total": len(all_themes)
            }
    
    except Exception as e:
        logger.error(f"Error getting themes: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting themes: {str(e)}"
        )


@api_router.get("/themes/{theme_id}")
async def get_theme_details(theme_id: str):
    """
    PHASE 34: Get detailed theme configuration
    """
    from theme_constants import get_theme_by_id
    
    try:
        theme = get_theme_by_id(theme_id)
        if not theme:
            raise ErrorResponse.not_found(f"Theme '{theme_id}' not found")
        
        return {
            "theme": theme,
            "success": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting theme details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting theme details: {str(e)}"
        )


@api_router.get("/profiles/{profile_id}/theme")
async def get_profile_theme(
    profile_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """
    PHASE 34: Get current theme settings for a profile
    """
    from theme_constants import get_theme_by_id
    
    try:
        profile = await db.profiles.find_one({"id": profile_id})
        if not profile:
            raise ErrorResponse.not_found("Profile not found")
        
        # Get theme settings or use defaults
        theme_settings = profile.get("theme_settings", {
            "theme_id": "royal_heritage",
            "animation_level": "subtle",
            "glassmorphism_enabled": True,
            "color_overrides": {},
            "hero_type": "static"
        })
        
        # Get full theme data
        theme_data = get_theme_by_id(theme_settings.get("theme_id", "royal_heritage"))
        
        return {
            "theme_settings": theme_settings,
            "theme_data": theme_data,
            "profile_id": profile_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile theme: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting profile theme: {str(e)}"
        )


@api_router.put("/profiles/{profile_id}/theme")
async def update_profile_theme(
    profile_id: str,
    theme_update: ThemeUpdateRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    PHASE 34: Update theme settings for a profile
    Includes plan-based access control
    """
    from theme_constants import can_use_theme, is_valid_theme, get_theme_by_id
    from feature_gating import get_plan_info
    
    try:
        # Get profile
        profile = await db.profiles.find_one({"id": profile_id})
        if not profile:
            raise ErrorResponse.not_found("Profile not found")
        
        # Validate theme exists
        if not is_valid_theme(theme_update.theme_id):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid theme ID: {theme_update.theme_id}"
            )
        
        # Check plan-based access
        user_plan = profile.get("plan_type", "FREE")
        if not can_use_theme(theme_update.theme_id, user_plan):
            theme_data = get_theme_by_id(theme_update.theme_id)
            required_plan = theme_data.get("planRequired", "PLATINUM")
            raise HTTPException(
                status_code=403,
                detail=f"This theme requires {required_plan} plan or higher"
            )
        
        # Get current theme settings or create new
        theme_settings = profile.get("theme_settings", {})
        
        # Update only provided fields
        update_data = {}
        if theme_update.theme_id:
            update_data["theme_settings.theme_id"] = theme_update.theme_id
        if theme_update.animation_level is not None:
            update_data["theme_settings.animation_level"] = theme_update.animation_level
        if theme_update.glassmorphism_enabled is not None:
            update_data["theme_settings.glassmorphism_enabled"] = theme_update.glassmorphism_enabled
        if theme_update.color_overrides is not None:
            update_data["theme_settings.color_overrides"] = theme_update.color_overrides
        if theme_update.hero_type is not None:
            update_data["theme_settings.hero_type"] = theme_update.hero_type
        
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        # Update profile
        result = await db.profiles.update_one(
            {"id": profile_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to update theme settings"
            )
        
        # Get updated theme settings
        updated_profile = await db.profiles.find_one({"id": profile_id})
        updated_theme_settings = updated_profile.get("theme_settings", {})
        
        # Audit log
        await db.audit_logs.insert_one({
            "log_id": f"audit_{uuid.uuid4().hex[:16]}",
            "admin_id": current_admin.get("admin_id"),
            "profile_id": profile_id,
            "action": "update_theme",
            "details": {
                "theme_id": theme_update.theme_id,
                "animation_level": theme_update.animation_level,
                "glassmorphism_enabled": theme_update.glassmorphism_enabled
            },
            "timestamp": datetime.now(timezone.utc)
        })
        
        return {
            "success": True,
            "message": "Theme settings updated successfully",
            "theme_settings": updated_theme_settings
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating theme: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating theme: {str(e)}"
        )


@api_router.post("/themes/preview")
async def preview_theme(
    preview_request: ThemePreviewRequest
):
    """
    PHASE 34: Get theme preview data (no auth required)
    Used by admin for live preview before applying
    """
    from theme_constants import get_theme_by_id
    
    try:
        theme = get_theme_by_id(preview_request.theme_id)
        if not theme:
            raise ErrorResponse.not_found(f"Theme '{preview_request.theme_id}' not found")
        
        # Return theme with preview settings
        return {
            "theme": theme,
            "preview_settings": {
                "animation_level": preview_request.animation_level,
                "glassmorphism_enabled": preview_request.glassmorphism_enabled
            },
            "success": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing theme: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error previewing theme: {str(e)}"
        )


@api_router.get("/themes/accessible/{profile_id}")
async def get_accessible_themes(
    profile_id: str
):
    """
    PHASE 34: Get themes accessible to a profile based on their plan
    Public endpoint for guest view (shows locked vs unlocked)
    """
    from theme_constants import get_all_themes_preview, get_themes_by_plan
    
    try:
        # Get profile plan
        profile = await db.profiles.find_one({"id": profile_id})
        if not profile:
            raise ErrorResponse.not_found("Profile not found")
        
        user_plan = profile.get("plan_type", "FREE")
        
        # Get all themes
        all_themes = get_all_themes_preview()
        
        # Get accessible theme IDs
        accessible_ids = set(get_themes_by_plan(user_plan))
        
        # Mark themes as locked/unlocked
        for theme in all_themes:
            theme['accessible'] = theme['id'] in accessible_ids
            theme['locked'] = theme['id'] not in accessible_ids
        
        return {
            "themes": all_themes,
            "user_plan": user_plan,
            "accessible_count": len(accessible_ids),
            "total_count": len(all_themes)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting accessible themes: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting accessible themes: {str(e)}"
        )


# ==========================================
# PHASE 36: TEMPLATE MARKETPLACE & CREATOR ECOSYSTEM
# ==========================================

# ======================
# PUBLIC MARKETPLACE ENDPOINTS
# ======================

@api_router.get("/templates")
async def browse_templates(
    category: Optional[str] = None,
    event_type: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    is_free: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    search: Optional[str] = None,
    sort_by: str = "popular",
    page: int = 1,
    page_size: int = 20
):
    """
    PHASE 36: Browse template marketplace with filters
    Public endpoint - no auth required
    """
    try:
        # Build filter query
        query = {"status": TemplateStatus.APPROVED.value}
        
        if category:
            query["category"] = category
        
        if event_type:
            query["event_types"] = event_type
        
        if is_free is not None:
            if is_free:
                query["price"] = 0
            else:
                query["price"] = {"$gt": 0}
        
        if min_price is not None or max_price is not None:
            price_query = {}
            if min_price is not None:
                price_query["$gte"] = min_price
            if max_price is not None:
                price_query["$lte"] = max_price
            query["price"] = price_query
        
        if is_featured is not None:
            query["is_featured"] = is_featured
        
        if search:
            # Search in name, description, and tags
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
                {"tags": {"$regex": search, "$options": "i"}}
            ]
        
        # Determine sort order
        sort_field = "view_count"  # Default popular
        sort_order = -1  # Descending
        
        if sort_by == "newest":
            sort_field = "created_at"
        elif sort_by == "price_low":
            sort_field = "price"
            sort_order = 1  # Ascending
        elif sort_by == "price_high":
            sort_field = "price"
        elif sort_by == "rating":
            sort_field = "rating_average"
        
        # Get total count
        total = await db.templates.count_documents(query)
        
        # Get paginated results
        skip = (page - 1) * page_size
        cursor = db.templates.find(query, {"_id": 0}).sort(sort_field, sort_order).skip(skip).limit(page_size)
        templates = await cursor.to_list(length=page_size)
        
        # Remove sensitive data from public view
        for template in templates:
            # Keep only public fields
            template.pop('design_config', None)  # Don't expose full config until purchase
            template.pop('theme_config', None)
            template.pop('layout_structure', None)
        
        return {
            "templates": templates,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (skip + len(templates)) < total
        }
    
    except Exception as e:
        logger.error(f"Error browsing templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to browse templates")


@api_router.get("/templates/{template_id}")
async def get_template_details(template_id: str, profile_id: Optional[str] = None):
    """
    PHASE 36: Get detailed template information
    Public endpoint - full config only if purchased
    """
    try:
        # Get template
        template = await db.templates.find_one(
            {"template_id": template_id},
            {"_id": 0}
        )
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Check if template is approved (unless it's the creator viewing)
        if template.get('status') != TemplateStatus.APPROVED.value:
            raise HTTPException(status_code=404, detail="Template not available")
        
        # Increment view count
        await db.templates.update_one(
            {"template_id": template_id},
            {"$inc": {"view_count": 1}}
        )
        
        # Check if purchased
        is_purchased = False
        if profile_id:
            purchase = await db.template_purchases.find_one({
                "template_id": template_id,
                "profile_id": profile_id
            })
            is_purchased = purchase is not None
        
        # If not purchased and not free, hide full config
        if not is_purchased and template.get('price', 0) > 0:
            template.pop('design_config', None)
            template.pop('theme_config', None)
            template.pop('layout_structure', None)
        
        # Get creator info
        creator = None
        if template.get('creator_id'):
            creator_doc = await db.creator_profiles.find_one(
                {"creator_id": template['creator_id']},
                {"_id": 0, "display_name": 1, "avatar_url": 1, "is_verified": 1, "verification_badge": 1}
            )
            creator = creator_doc
        
        return {
            "template": template,
            "is_purchased": is_purchased,
            "creator": creator
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get template details")


@api_router.post("/templates/{template_id}/purchase")
async def purchase_template(
    template_id: str,
    purchase_request: TemplatePurchaseRequest
):
    """
    PHASE 36: Purchase a template
    Supports: Free templates, Credits, Razorpay, Hybrid payment
    """
    try:
        # Get template
        template = await db.templates.find_one(
            {"template_id": template_id, "status": TemplateStatus.APPROVED.value},
            {"_id": 0}
        )
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not available")
        
        profile_id = purchase_request.profile_id
        
        # Check if already purchased
        existing_purchase = await db.template_purchases.find_one({
            "template_id": template_id,
            "profile_id": profile_id
        })
        
        if existing_purchase:
            return {
                "success": True,
                "message": "Template already purchased",
                "purchase": existing_purchase,
                "remaining_amount": 0,
                "payment_required": False
            }
        
        price = template.get('price', 0)
        
        # FREE TEMPLATE
        if price == 0:
            purchase = TemplatePurchase(
                template_id=template_id,
                profile_id=profile_id,
                original_price=0,
                credits_used=0,
                amount_paid=0,
                creator_id=template['creator_id'],
                creator_earnings=0,
                platform_fee=0,
                payment_method="free"
            )
            
            doc = purchase.model_dump()
            doc['purchased_at'] = doc['purchased_at'].isoformat()
            await db.template_purchases.insert_one(doc)
            
            # Update template purchase count
            await db.templates.update_one(
                {"template_id": template_id},
                {"$inc": {"purchase_count": 1}}
            )
            
            return {
                "success": True,
                "message": "Free template added to your collection",
                "purchase": doc,
                "remaining_amount": 0,
                "payment_required": False
            }
        
        # PAID TEMPLATE with CREDITS
        credits_to_use = purchase_request.credits_to_use if purchase_request.use_credits else 0
        
        if credits_to_use > 0:
            # Get credit wallet
            wallet = await db.credit_wallets.find_one({"profile_id": profile_id})
            
            if not wallet:
                raise HTTPException(status_code=400, detail="Credit wallet not found")
            
            if wallet['balance'] < credits_to_use:
                raise HTTPException(status_code=400, detail="Insufficient credits")
            
            # Cap credits to price (can't use more credits than price)
            credits_to_use = min(credits_to_use, price)
        
        remaining_amount = price - credits_to_use
        
        # If fully paid with credits
        if remaining_amount <= 0:
            # Deduct credits
            await db.credit_wallets.update_one(
                {"profile_id": profile_id},
                {
                    "$inc": {
                        "balance": -credits_to_use,
                        "spent_total": credits_to_use
                    },
                    "$push": {
                        "transactions": {
                            "transaction_id": str(uuid.uuid4()),
                            "type": CreditTransactionType.SPENT.value,
                            "amount": -credits_to_use,
                            "balance_after": wallet['balance'] - credits_to_use,
                            "description": f"Template purchase: {template['name']}",
                            "metadata": {"template_id": template_id},
                            "created_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                }
            )
            
            # Calculate creator earnings
            creator_percentage = 70  # Default 70% to creator
            creator_doc = await db.creator_profiles.find_one({"creator_id": template['creator_id']})
            if creator_doc:
                creator_percentage = creator_doc.get('payout_percentage', 70)
            
            creator_earnings = int(price * creator_percentage / 100)
            platform_fee = price - creator_earnings
            
            # Create purchase record
            purchase = TemplatePurchase(
                template_id=template_id,
                profile_id=profile_id,
                original_price=price,
                credits_used=credits_to_use,
                amount_paid=0,
                creator_id=template['creator_id'],
                creator_earnings=creator_earnings,
                platform_fee=platform_fee,
                payment_method="credits"
            )
            
            doc = purchase.model_dump()
            doc['purchased_at'] = doc['purchased_at'].isoformat()
            await db.template_purchases.insert_one(doc)
            
            # Update creator earnings
            await db.creator_profiles.update_one(
                {"creator_id": template['creator_id']},
                {
                    "$inc": {
                        "total_earnings": creator_earnings,
                        "pending_payout": creator_earnings,
                        "total_sales": 1
                    }
                }
            )
            
            # Update template stats
            await db.templates.update_one(
                {"template_id": template_id},
                {"$inc": {"purchase_count": 1}}
            )
            
            return {
                "success": True,
                "message": "Template purchased successfully with credits",
                "purchase": doc,
                "remaining_amount": 0,
                "payment_required": False
            }
        
        # REQUIRES RAZORPAY PAYMENT (partial or full)
        # Create Razorpay order
        try:
            order = razorpay_client.order.create({
                "amount": remaining_amount * 100,  # Razorpay amount in paise
                "currency": "INR",
                "receipt": f"template_{template_id}_{profile_id}",
                "notes": {
                    "template_id": template_id,
                    "profile_id": profile_id,
                    "credits_used": credits_to_use,
                    "type": "template_purchase"
                }
            })
            
            # Store pending payment
            payment_doc = {
                "payment_id": str(uuid.uuid4()),
                "razorpay_order_id": order['id'],
                "template_id": template_id,
                "profile_id": profile_id,
                "amount": remaining_amount,
                "credits_used": credits_to_use,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.template_payments.insert_one(payment_doc)
            
            return {
                "success": True,
                "message": "Payment required to complete purchase",
                "purchase": None,
                "remaining_amount": remaining_amount,
                "payment_required": True,
                "payment_order_id": order['id'],
                "razorpay_key_id": RAZORPAY_KEY_ID
            }
            
        except Exception as e:
            logger.error(f"Error creating Razorpay order: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create payment order")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error purchasing template: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to purchase template")


@api_router.get("/profiles/{profile_id}/templates")
async def get_purchased_templates(profile_id: str):
    """
    PHASE 36: Get all templates purchased by a profile
    """
    try:
        # Get all purchases for this profile
        purchases = await db.template_purchases.find(
            {"profile_id": profile_id},
            {"_id": 0}
        ).to_list(length=100)
        
        if not purchases:
            return {"templates": [], "total": 0}
        
        # Get template details
        template_ids = [p['template_id'] for p in purchases]
        templates = await db.templates.find(
            {"template_id": {"$in": template_ids}},
            {"_id": 0}
        ).to_list(length=100)
        
        return {
            "templates": templates,
            "total": len(templates),
            "purchases": purchases
        }
    
    except Exception as e:
        logger.error(f"Error getting purchased templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get purchased templates")


# ======================
# CREATOR ENDPOINTS
# ======================

@api_router.post("/creator/register")
async def register_as_creator(
    creator_request: CreatorProfileCreate,
    admin: Admin = Depends(get_current_admin)
):
    """
    PHASE 36: Register as a template creator
    Requires admin authentication
    """
    try:
        admin_id = admin['admin_id']
        
        # Check if already registered
        existing = await db.creator_profiles.find_one({"admin_id": admin_id})
        if existing:
            return {
                "success": False,
                "message": "Already registered as creator",
                "creator": existing
            }
        
        # Create creator profile
        creator = CreatorProfile(
            admin_id=admin_id,
            display_name=creator_request.display_name,
            bio=creator_request.bio,
            avatar_url=creator_request.avatar_url,
            website_url=creator_request.website_url,
            social_links=creator_request.social_links
        )
        
        doc = creator.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.creator_profiles.insert_one(doc)
        
        return {
            "success": True,
            "message": "Creator profile created successfully",
            "creator": doc
        }
    
    except Exception as e:
        logger.error(f"Error registering creator: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to register creator")


@api_router.get("/creator/profile")
async def get_creator_profile(admin: Admin = Depends(get_current_admin)):
    """
    PHASE 36: Get current creator profile
    """
    try:
        admin_id = admin['admin_id']
        
        creator = await db.creator_profiles.find_one(
            {"admin_id": admin_id},
            {"_id": 0}
        )
        
        if not creator:
            raise HTTPException(status_code=404, detail="Creator profile not found. Please register first.")
        
        # Get creator's templates
        templates = await db.templates.find(
            {"creator_id": creator['creator_id']},
            {"_id": 0}
        ).to_list(length=100)
        
        return {
            "creator": creator,
            "templates": templates
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting creator profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get creator profile")


@api_router.post("/creator/templates")
async def create_template(
    template_request: TemplateCreate,
    admin: Admin = Depends(get_current_admin)
):
    """
    PHASE 36: Create a new template (creator only)
    """
    try:
        admin_id = admin['admin_id']
        
        # Get creator profile
        creator = await db.creator_profiles.find_one({"admin_id": admin_id})
        if not creator:
            raise HTTPException(status_code=403, detail="Not registered as creator. Please register first.")
        
        if creator['status'] != CreatorStatus.ACTIVE.value:
            raise HTTPException(status_code=403, detail="Creator account is not active")
        
        # Prepare template data for validation
        template_data = {
            "name": template_request.name,
            "description": template_request.description,
            "preview_images": template_request.preview_images,
            "category": template_request.category,
            "design_config": template_request.design_config,
            "theme_config": template_request.theme_config,
            "layout_structure": template_request.layout_structure
        }
        
        # Validate and sanitize template
        is_valid, issues, quality_score = validate_template(template_data)
        
        if not is_valid:
            return {
                "success": False,
                "message": "Template validation failed",
                "issues": issues,
                "quality_score": quality_score
            }
        
        # Sanitize template for storage
        sanitized_data = sanitize_template_for_storage(template_data)
        
        # Calculate performance score
        performance_score = calculate_performance_score(sanitized_data)
        
        # Create template
        template = Template(
            name=template_request.name,
            description=template_request.description,
            preview_images=template_request.preview_images,
            demo_url=template_request.demo_url,
            thumbnail=template_request.thumbnail,
            price=template_request.price,
            creator_id=creator['creator_id'],
            creator_name=creator['display_name'],
            category=template_request.category,
            event_types=template_request.event_types,
            tags=template_request.tags,
            design_config=sanitized_data['design_config'],
            theme_config=sanitized_data['theme_config'],
            layout_structure=template_request.layout_structure,
            status=TemplateStatus.DRAFT,  # Start as draft
            performance_score=performance_score,
            has_passed_security=True  # Passed our validation
        )
        
        doc = template.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.templates.insert_one(doc)
        
        # Update creator stats
        await db.creator_profiles.update_one(
            {"creator_id": creator['creator_id']},
            {"$inc": {"total_templates": 1}}
        )
        
        return {
            "success": True,
            "message": "Template created successfully",
            "template": doc,
            "quality_score": quality_score,
            "performance_score": performance_score
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create template")


@api_router.get("/creator/templates")
async def get_creator_templates(admin: Admin = Depends(get_current_admin)):
    """
    PHASE 36: Get all templates created by current creator
    """
    try:
        admin_id = admin['admin_id']
        
        creator = await db.creator_profiles.find_one({"admin_id": admin_id})
        if not creator:
            raise HTTPException(status_code=403, detail="Not registered as creator")
        
        templates = await db.templates.find(
            {"creator_id": creator['creator_id']},
            {"_id": 0}
        ).sort("created_at", -1).to_list(length=100)
        
        return {
            "templates": templates,
            "total": len(templates)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting creator templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get creator templates")


@api_router.put("/creator/templates/{template_id}")
async def update_template(
    template_id: str,
    template_update: TemplateUpdate,
    admin: Admin = Depends(get_current_admin)
):
    """
    PHASE 36: Update template (creator only, must own template)
    """
    try:
        admin_id = admin['admin_id']
        
        # Get creator profile
        creator = await db.creator_profiles.find_one({"admin_id": admin_id})
        if not creator:
            raise HTTPException(status_code=403, detail="Not registered as creator")
        
        # Get template and verify ownership
        template = await db.templates.find_one({
            "template_id": template_id,
            "creator_id": creator['creator_id']
        })
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found or access denied")
        
        # Prepare update data
        update_data = {k: v for k, v in template_update.model_dump().items() if v is not None}
        
        if not update_data:
            return {"success": False, "message": "No fields to update"}
        
        # If design/theme config is being updated, re-validate
        if any(k in update_data for k in ['design_config', 'theme_config', 'layout_structure']):
            validation_data = {
                "name": update_data.get('name', template['name']),
                "design_config": update_data.get('design_config', template['design_config']),
                "theme_config": update_data.get('theme_config', template['theme_config']),
                "layout_structure": update_data.get('layout_structure', template['layout_structure'])
            }
            
            is_valid, issues, quality_score = validate_template(validation_data)
            if not is_valid:
                return {
                    "success": False,
                    "message": "Template validation failed",
                    "issues": issues
                }
            
            # Sanitize updated data
            sanitized = sanitize_template_for_storage(validation_data)
            update_data['design_config'] = sanitized['design_config']
            update_data['theme_config'] = sanitized['theme_config']
            update_data['performance_score'] = calculate_performance_score(sanitized)
        
        update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Update template
        await db.templates.update_one(
            {"template_id": template_id},
            {"$set": update_data}
        )
        
        # Get updated template
        updated_template = await db.templates.find_one(
            {"template_id": template_id},
            {"_id": 0}
        )
        
        return {
            "success": True,
            "message": "Template updated successfully",
            "template": updated_template
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update template")


@api_router.put("/creator/templates/{template_id}/submit")
async def submit_template_for_review(
    template_id: str,
    admin: Admin = Depends(get_current_admin)
):
    """
    PHASE 36: Submit template for admin review
    """
    try:
        admin_id = admin['admin_id']
        
        creator = await db.creator_profiles.find_one({"admin_id": admin_id})
        if not creator:
            raise HTTPException(status_code=403, detail="Not registered as creator")
        
        # Get template
        template = await db.templates.find_one({
            "template_id": template_id,
            "creator_id": creator['creator_id']
        })
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        if template['status'] == TemplateStatus.PENDING_REVIEW.value:
            return {"success": False, "message": "Template is already pending review"}
        
        if template['status'] == TemplateStatus.APPROVED.value:
            return {"success": False, "message": "Template is already approved"}
        
        # Update status to pending review
        await db.templates.update_one(
            {"template_id": template_id},
            {
                "$set": {
                    "status": TemplateStatus.PENDING_REVIEW.value,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        return {
            "success": True,
            "message": "Template submitted for review"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting template: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit template")


@api_router.get("/creator/earnings")
async def get_creator_earnings(admin: Admin = Depends(get_current_admin)):
    """
    PHASE 36: Get creator earnings analytics
    """
    try:
        admin_id = admin['admin_id']
        
        creator = await db.creator_profiles.find_one({"admin_id": admin_id})
        if not creator:
            raise HTTPException(status_code=403, detail="Not registered as creator")
        
        creator_id = creator['creator_id']
        
        # Get earnings by template
        pipeline = [
            {"$match": {"creator_id": creator_id}},
            {"$group": {
                "_id": "$template_id",
                "total_earnings": {"$sum": "$creator_earnings"},
                "sales_count": {"$count": {}}
            }},
            {"$sort": {"total_earnings": -1}}
        ]
        
        earnings_by_template = await db.template_purchases.aggregate(pipeline).to_list(length=100)
        
        # Enhance with template names
        for item in earnings_by_template:
            template = await db.templates.find_one(
                {"template_id": item['_id']},
                {"_id": 0, "name": 1}
            )
            item['template_name'] = template['name'] if template else "Unknown"
        
        # Calculate monthly earnings
        now = datetime.now(timezone.utc)
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        
        this_month_purchases = await db.template_purchases.find({
            "creator_id": creator_id,
            "purchased_at": {"$gte": this_month_start.isoformat()}
        }).to_list(length=1000)
        
        last_month_purchases = await db.template_purchases.find({
            "creator_id": creator_id,
            "purchased_at": {
                "$gte": last_month_start.isoformat(),
                "$lt": this_month_start.isoformat()
            }
        }).to_list(length=1000)
        
        this_month_earnings = sum(p.get('creator_earnings', 0) for p in this_month_purchases)
        last_month_earnings = sum(p.get('creator_earnings', 0) for p in last_month_purchases)
        
        return {
            "total_earnings": creator.get('total_earnings', 0),
            "pending_payout": creator.get('pending_payout', 0),
            "this_month_earnings": this_month_earnings,
            "last_month_earnings": last_month_earnings,
            "total_sales": creator.get('total_sales', 0),
            "earnings_by_template": earnings_by_template
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting creator earnings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get creator earnings")


# ======================
# ADMIN ENDPOINTS
# ======================

@api_router.get("/admin/templates")
async def admin_list_all_templates(
    status: Optional[str] = None,
    admin: Admin = Depends(get_current_admin)
):
    """
    PHASE 36: Admin - List all templates with filters
    """
    try:
        query = {}
        if status:
            query["status"] = status
        
        templates = await db.templates.find(query, {"_id": 0}).sort("created_at", -1).to_list(length=200)
        
        return {
            "templates": templates,
            "total": len(templates)
        }
    
    except Exception as e:
        logger.error(f"Error listing templates (admin): {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list templates")


@api_router.put("/admin/templates/{template_id}/review")
async def admin_review_template(
    template_id: str,
    review_request: AdminTemplateReviewRequest,
    admin: Admin = Depends(get_current_admin)
):
    """
    PHASE 36: Admin - Approve/reject/suspend template
    """
    try:
        admin_id = admin['admin_id']
        action = review_request.action
        
        # Get template
        template = await db.templates.find_one({"template_id": template_id})
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        update_data = {
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if action == "approve":
            update_data["status"] = TemplateStatus.APPROVED.value
            update_data["approved_at"] = datetime.now(timezone.utc).isoformat()
            update_data["approved_by"] = admin_id
            update_data["rejection_reason"] = None
            
            # Update creator stats
            await db.creator_profiles.update_one(
                {"creator_id": template['creator_id']},
                {"$inc": {"approved_templates": 1}}
            )
        
        elif action == "reject":
            update_data["status"] = TemplateStatus.REJECTED.value
            update_data["rejection_reason"] = review_request.rejection_reason
        
        elif action == "suspend":
            update_data["status"] = TemplateStatus.SUSPENDED.value
            update_data["rejection_reason"] = review_request.rejection_reason
        
        # Update template
        await db.templates.update_one(
            {"template_id": template_id},
            {"$set": update_data}
        )
        
        # Log audit trail
        audit_log = {
            "log_id": str(uuid.uuid4()),
            "admin_id": admin_id,
            "action": f"template_{action}",
            "details": {
                "template_id": template_id,
                "template_name": template['name'],
                "reason": review_request.rejection_reason
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.audit_logs.insert_one(audit_log)
        
        return {
            "success": True,
            "message": f"Template {action}d successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing template: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to review template")


@api_router.put("/admin/templates/{template_id}/featured")
async def admin_set_featured_template(
    template_id: str,
    is_featured: bool,
    featured_order: int = 0,
    admin: Admin = Depends(get_current_admin)
):
    """
    PHASE 36: Admin - Set template as featured
    """
    try:
        # Update template
        await db.templates.update_one(
            {"template_id": template_id},
            {
                "$set": {
                    "is_featured": is_featured,
                    "featured_order": featured_order,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        return {
            "success": True,
            "message": f"Template {'featured' if is_featured else 'unfeatured'} successfully"
        }
    
    except Exception as e:
        logger.error(f"Error setting featured template: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to set featured template")


@api_router.put("/admin/creators/{creator_id}/status")
async def admin_manage_creator(
    creator_id: str,
    action_request: AdminCreatorActionRequest,
    admin: Admin = Depends(get_current_admin)
):
    """
    PHASE 36: Admin - Suspend/ban/activate/verify creator
    """
    try:
        admin_id = admin['admin_id']
        action = action_request.action
        
        creator = await db.creator_profiles.find_one({"creator_id": creator_id})
        if not creator:
            raise HTTPException(status_code=404, detail="Creator not found")
        
        update_data = {
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if action == "suspend":
            update_data["status"] = CreatorStatus.SUSPENDED.value
            update_data["suspension_reason"] = action_request.reason
        
        elif action == "ban":
            update_data["status"] = CreatorStatus.BANNED.value
            update_data["suspension_reason"] = action_request.reason
            
            # Also suspend all their templates
            await db.templates.update_many(
                {"creator_id": creator_id},
                {"$set": {"status": TemplateStatus.SUSPENDED.value}}
            )
        
        elif action == "activate":
            update_data["status"] = CreatorStatus.ACTIVE.value
            update_data["suspension_reason"] = None
        
        elif action == "verify":
            update_data["is_verified"] = True
            update_data["verification_badge"] = "verified"
        
        # Update creator
        await db.creator_profiles.update_one(
            {"creator_id": creator_id},
            {"$set": update_data}
        )
        
        # Log audit trail
        audit_log = {
            "log_id": str(uuid.uuid4()),
            "admin_id": admin_id,
            "action": f"creator_{action}",
            "details": {
                "creator_id": creator_id,
                "creator_name": creator['display_name'],
                "reason": action_request.reason
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.audit_logs.insert_one(audit_log)
        
        return {
            "success": True,
            "message": f"Creator {action}d successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error managing creator: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to manage creator")


@api_router.get("/admin/marketplace/stats")
async def admin_marketplace_stats(admin: Admin = Depends(get_current_admin)):
    """
    PHASE 36: Admin - Get marketplace statistics
    """
    try:
        # Template stats
        total_templates = await db.templates.count_documents({})
        approved_templates = await db.templates.count_documents({"status": TemplateStatus.APPROVED.value})
        pending_templates = await db.templates.count_documents({"status": TemplateStatus.PENDING_REVIEW.value})
        
        # Creator stats
        total_creators = await db.creator_profiles.count_documents({})
        active_creators = await db.creator_profiles.count_documents({"status": CreatorStatus.ACTIVE.value})
        
        # Sales stats
        total_purchases = await db.template_purchases.count_documents({})
        total_revenue = await db.template_purchases.aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$amount_paid"}}}
        ]).to_list(length=1)
        
        total_revenue_value = total_revenue[0]['total'] if total_revenue else 0
        
        # Top templates
        top_templates = await db.templates.find(
            {"status": TemplateStatus.APPROVED.value},
            {"_id": 0, "template_id": 1, "name": 1, "purchase_count": 1, "view_count": 1, "rating_average": 1}
        ).sort("purchase_count", -1).limit(10).to_list(length=10)
        
        return {
            "templates": {
                "total": total_templates,
                "approved": approved_templates,
                "pending_review": pending_templates
            },
            "creators": {
                "total": total_creators,
                "active": active_creators
            },
            "sales": {
                "total_purchases": total_purchases,
                "total_revenue": total_revenue_value
            },
            "top_templates": top_templates
        }
    
    except Exception as e:
        logger.error(f"Error getting marketplace stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get marketplace stats")


        
        return {
            "referral_code": referral_code,
            "profile_id": profile_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting public referral code: {str(e)}")
        # Return empty if fails - guest CTA will hide
        return {"referral_code": None, "profile_id": profile_id}




# ==========================================
# PHASE 37: WEDDING OWNERSHIP, DRAFT SYSTEM & PUBLISH WORKFLOW
# ==========================================

@api_router.post("/weddings")
async def create_wedding(
    request: Dict[str, Any],
    current_admin: dict = Depends(get_current_admin)
):
    """
    Create a new wedding in DRAFT status
    """
    try:
        admin_id = current_admin
        title = request.get('title')
        slug = request.get('slug')
        description = request.get('description')
        wedding_date = request.get('wedding_date')
        
        if not title or not slug:
            raise HTTPException(status_code=400, detail="Title and slug are required")
        
        # Convert wedding_date string to datetime if provided
        if wedding_date and isinstance(wedding_date, str):
            from dateutil import parser
            wedding_date = parser.parse(wedding_date)
        
        result = await wedding_lifecycle_service.create_wedding(
            admin_id=admin_id,
            title=title,
            slug=slug,
            description=description,
            wedding_date=wedding_date
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating wedding: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.put("/weddings/{wedding_id}")
async def update_wedding(
    wedding_id: str,
    request: Dict[str, Any],
    current_admin: dict = Depends(get_current_admin)
):
    """
    Update wedding details
    Allowed in DRAFT, READY, or PUBLISHED status
    """
    try:
        admin_id = current_admin
        
        # Extract fields from request
        title = request.get('title')
        description = request.get('description')
        wedding_date = request.get('wedding_date')
        selected_design_key = request.get('selected_design_key')
        selected_features = request.get('selected_features')
        groom_name = request.get('groom_name')
        bride_name = request.get('bride_name')
        event_date = request.get('event_date')
        venue = request.get('venue')
        
        # Convert date strings to datetime if provided
        if wedding_date and isinstance(wedding_date, str):
            from dateutil import parser
            wedding_date = parser.parse(wedding_date)
        if event_date and isinstance(event_date, str):
            from dateutil import parser
            event_date = parser.parse(event_date)
        
        result = await wedding_lifecycle_service.update_wedding(
            wedding_id=wedding_id,
            admin_id=admin_id,
            title=title,
            description=description,
            wedding_date=wedding_date,
            selected_design_key=selected_design_key,
            selected_features=selected_features,
            groom_name=groom_name,
            bride_name=bride_name,
            event_date=event_date,
            venue=venue
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating wedding: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/weddings/estimate-cost")
async def estimate_wedding_cost(
    request: Dict[str, Any],
    current_admin: dict = Depends(get_current_admin)
):
    """
    Estimate credit cost for a wedding configuration
    Does not deduct credits - preview only
    """
    try:
        design_key = request.get('design_key', '')
        selected_features = request.get('selected_features', [])
        # 2026-09 — Optional invitation_category so non-wedding estimates
        # (baby_birthday / half_saree / puberty / dhoti) use the right
        # pricing source. Defaults to "wedding" for backwards compat.
        invitation_category = (request.get('invitation_category') or 'wedding').lower()
        # Optional explicit expiry tier id — resolves credits server-side
        tier_id = request.get('expiry_tier') or ''
        tier_credits = 0
        if tier_id:
            tier_doc = await db['expiry_tiers'].find_one({'id': tier_id})
            if tier_doc and isinstance(tier_doc.get('credits'), (int, float)):
                tier_credits = int(tier_doc['credits'])
        cost_breakdown = await wedding_lifecycle_service.calculate_cost_for_wedding(
            {
                'invitation_category': invitation_category,
                'selected_design_key': design_key,
                'selected_features': selected_features,
            },
            expiry_tier_credits=tier_credits,
            user_type="photographer",
        )

        return {
            'success': True,
            'cost_breakdown': cost_breakdown
        }
    except Exception as e:
        logger.error(f"Error estimating cost: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/weddings")
async def get_admin_weddings(
    status: Optional[str] = None,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Get all weddings owned by current admin
    Optional filtering by status
    """
    try:
        admin_id = current_admin
        
        query = {'admin_id': admin_id}
        if status:
            query['status'] = status
        
        weddings_cursor = db['profiles'].find(query, {'_id': 0}).sort('created_at', -1)
        weddings = await weddings_cursor.to_list(length=None)
        
        # Get admin credits for UI display
        admin = await db['admins'].find_one({'id': admin_id})
        total_credits = admin.get('total_credits', 0)
        used_credits = admin.get('used_credits', 0)
        available_credits = total_credits - used_credits
        
        # Enrich weddings with credit estimates for drafts (category-aware)
        for wedding in weddings:
            if wedding.get('status') in ['draft', 'ready']:
                cost_breakdown = await wedding_lifecycle_service.calculate_cost_for_wedding(
                    wedding,
                    expiry_tier_credits=0,
                    user_type="photographer",
                )
                wedding['estimated_cost'] = cost_breakdown['total']
                wedding['cost_breakdown'] = cost_breakdown
        
        return {
            'success': True,
            'weddings': weddings,
            'total_count': len(weddings),
            'admin_credits': {
                'total': total_credits,
                'used': used_credits,
                'available': available_credits
            }
        }
    except Exception as e:
        logger.error(f"Error getting weddings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/weddings/{wedding_id}")
async def get_wedding_details(
    wedding_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Get detailed wedding information
    Includes credit estimation and ready status
    """
    try:
        admin_id = current_admin
        admin_doc = await db['admins'].find_one({'id': admin_id})
        role = admin_doc.get('role', 'admin') if admin_doc else 'admin'
        
        # Super admin can access all, regular admin only own
        query = {'id': wedding_id}
        if role != 'super_admin':
            query['admin_id'] = admin_id
        
        wedding = await db['profiles'].find_one(query, {'_id': 0})
        if not wedding:
            raise HTTPException(status_code=404, detail="Wedding not found")
        
        # Calculate credit cost (category-aware)
        cost_breakdown = await wedding_lifecycle_service.calculate_cost_for_wedding(
            wedding,
            expiry_tier_credits=0,
            user_type="photographer",
        )
        
        # Check ready status
        is_ready, missing_fields = await wedding_lifecycle_service.check_ready_status(wedding)
        
        # Get admin credits
        admin = await db['admins'].find_one({'id': wedding.get('admin_id')})
        total_credits = admin.get('total_credits', 0) if admin else 0
        used_credits = admin.get('used_credits', 0) if admin else 0
        available_credits = total_credits - used_credits
        
        return {
            'success': True,
            'wedding': wedding,
            'cost_breakdown': cost_breakdown,
            'is_ready': is_ready,
            'missing_fields': missing_fields,
            'can_publish': is_ready and available_credits >= cost_breakdown['total'],
            'admin_credits': {
                'total': total_credits,
                'used': used_credits,
                'available': available_credits
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting wedding details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.put("/weddings/{wedding_id}/status")
async def update_wedding_status(
    wedding_id: str,
    request: Dict[str, str],
    current_admin: dict = Depends(get_current_admin)
):
    """
    Update wedding status (DRAFT -> READY -> PUBLISHED -> ARCHIVED)
    """
    try:
        admin_id = current_admin
        new_status = request.get('status')
        
        if new_status not in ['draft', 'ready', 'published', 'archived']:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        wedding = await db['profiles'].find_one({
            'id': wedding_id,
            'admin_id': admin_id
        })
        
        if not wedding:
            raise HTTPException(status_code=404, detail="Wedding not found")
        
        current_status = wedding.get('status', 'draft')
        
        # Validate status transition
        valid_transitions = {
            'draft': ['ready'],
            'ready': ['draft', 'published'],
            'published': ['archived'],
            'archived': []
        }
        
        if new_status not in valid_transitions.get(current_status, []):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from {current_status} to {new_status}"
            )
        
        # For READY status, validate required fields
        if new_status == 'ready':
            is_ready, missing_fields = await wedding_lifecycle_service.check_ready_status(wedding)
            if not is_ready:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot mark as ready. Missing: {', '.join(missing_fields)}"
                )
        
        # Update status
        await db['profiles'].update_one(
            {'id': wedding_id},
            {
                '$set': {
                    'status': new_status,
                    'updated_at': datetime.now(timezone.utc)
                }
            }
        )
        
        return {
            'success': True,
            'wedding_id': wedding_id,
            'old_status': current_status,
            'new_status': new_status,
            'message': f'Wedding status updated to {new_status}'
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating wedding status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/weddings/{wedding_id}/publish")
async def publish_wedding(
    wedding_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Publish a wedding - deducts credits atomically
    This is the main publish endpoint
    """
    try:
        admin_id = current_admin
        
        result = await wedding_lifecycle_service.publish_wedding(
            wedding_id,
            admin_id
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error publishing wedding: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/weddings/{wedding_id}/upgrade")
async def upgrade_wedding_features(
    wedding_id: str,
    request: Dict[str, Any],
    current_admin: dict = Depends(get_current_admin)
):
    """
    Upgrade published wedding with new design or features
    Deducts only the difference in credits
    """
    try:
        admin_id = current_admin
        new_design_key = request.get('design_key')
        new_features = request.get('selected_features')
        
        result = await wedding_lifecycle_service.upgrade_wedding_features(
            wedding_id,
            admin_id,
            new_design_key,
            new_features
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error upgrading wedding: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/weddings/{wedding_id}/archive")
async def archive_wedding(
    wedding_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Archive a wedding - no credit refund
    """
    try:
        admin_id = current_admin
        
        result = await wedding_lifecycle_service.archive_wedding(
            wedding_id,
            admin_id
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error archiving wedding: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/weddings/{wedding_id}/slug/validate")
async def validate_slug(
    wedding_id: str,
    request: Dict[str, str],
    current_admin: dict = Depends(get_current_admin)
):
    """
    Validate slug uniqueness
    """
    try:
        slug = request.get('slug', '')
        
        if not slug:
            return {'valid': False, 'message': 'Slug is required'}
        
        is_unique, error_message = await wedding_lifecycle_service.validate_slug_uniqueness(
            slug,
            exclude_wedding_id=wedding_id
        )
        
        return {
            'valid': is_unique,
            'message': error_message if not is_unique else 'Slug is available'
        }
    except Exception as e:
        logger.error(f"Error validating slug: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/features/registry")
async def get_feature_registry(
    category: Optional[str] = None,
    tier: Optional[str] = None
):
    """
    Get available features with credit costs
    Public endpoint for feature discovery
    """
    try:
        from feature_registry import FeatureRegistry
        registry = FeatureRegistry()
        
        features = registry.get_enabled_features()
        
        # Filter by category if provided
        if category:
            features = [f for f in features if f.category.value == category]
        
        # Filter by tier if provided
        if tier:
            features = [f for f in features if f.tier.value == tier]
        
        # Convert to dict for JSON response
        features_list = [f.model_dump() for f in features]
        
        return {
            'success': True,
            'features': features_list,
            'total_count': len(features_list)
        }
    except Exception as e:
        logger.error(f"Error getting feature registry: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SPRINT 4: AI STORY COMPOSER ====================
# Claude Sonnet 4.5 via Emergent Universal Key (emergentintegrations)

from pydantic import BaseModel as _AIBaseModel
import uuid as _ai_uuid

class AIStoryRequest(_AIBaseModel):
    kind: str = "invitation"  # invitation | love_story | event_intro | thank_you | vows
    bride: str
    groom: str
    theme: str = "royal_mughal"
    tone: str = "cinematic_royal"
    language: str = "English"
    event_name: str = ""
    notes: str = ""
    # 2026-07 — Model picker. "claude" (default) or "gemini".
    model: str = "claude"


def _build_ai_prompt(req: AIStoryRequest) -> str:
    kind_briefs = {
        "invitation":  "Write a short premium invitation paragraph (4-6 sentences) that warmly requests the recipient's presence at the wedding.",
        "love_story":  "Write a heartfelt 'how we met' love story (6-8 sentences) for an Indian wedding invitation.",
        "event_intro": "Write a 2-3 sentence elegant introduction for the event named below.",
        "thank_you":   "Write a tender thank-you note to wedding guests (3-5 sentences).",
        "vows":        "Write personal wedding vows (4-6 sentences) the groom might say to the bride.",
    }
    brief = kind_briefs.get(req.kind, kind_briefs["invitation"])
    tone_hints = {
        "cinematic_royal":    "Tone: cinematic, royal, slow, emotionally rich. Think Sanjay Leela Bhansali film. Use 'thou-shalt-not-be-cheesy' restraint.",
        "modern_minimal":     "Tone: modern, minimal, dignified. Short sentences. No purple prose.",
        "poetic_traditional": "Tone: poetic, traditional, gentle metaphor. May include one Sanskrit/Urdu phrase if natural (with English meaning).",
        "playful_punjabi":    "Tone: warm and playful with Punjabi cultural warmth. Still elegant. Avoid clichés.",
    }
    tone_hint = tone_hints.get(req.tone, tone_hints["cinematic_royal"])
    return (
        f"You are an award-winning Indian wedding copywriter. "
        f"{brief}\n\n"
        f"Couple: {req.bride} (bride) & {req.groom} (groom).\n"
        f"Theme: {req.theme.replace('_', ' ').title()}.\n"
        f"Event: {req.event_name or 'Wedding'}.\n"
        f"Language: write the output in {req.language}.\n"
        f"{tone_hint}\n"
        f"Additional context from the photographer: {req.notes or 'none'}.\n\n"
        f"Rules:\n"
        f"- Do NOT include any greeting like 'Dear guests' unless asked.\n"
        f"- Do NOT use emojis or hashtags.\n"
        f"- Do NOT mention you are an AI.\n"
        f"- Output ONLY the final prose, no headings, no quotes around it.\n"
        f"- Keep cinematic restraint — luxurious, never tacky."
    )


@api_router.post("/admin/ai/story")
async def ai_generate_story(req: AIStoryRequest, admin_id: str = Depends(get_current_admin)):
    """Generate cinematic Indian wedding copy via Claude Sonnet 4.5."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI service is not configured.")
    if not req.bride or not req.groom:
        raise HTTPException(status_code=400, detail="Bride and groom names are required.")
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        session_id = f"ai-story-{admin_id}-{_ai_uuid.uuid4()}"
        # Route to chosen provider via the Emergent Universal Key.
        # Default = Claude Sonnet 4.5 (matches the UI eyebrow text).
        chosen = (req.model or "claude").lower().strip()
        if chosen in ("gemini", "google", "gemini-2.5-flash"):
            provider, model_name = "gemini", "gemini-2.5-flash"
        else:
            provider, model_name = "anthropic", "claude-sonnet-4-5-20250929"
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=(
                "You are MAJA, a refined Indian wedding copywriter. "
                "You write cinematic, emotional, restrained prose. "
                "You never write cheesy, generic, or template-style copy."
            ),
        ).with_model(provider, model_name)

        prompt = _build_ai_prompt(req)
        message = UserMessage(text=prompt)
        story_text = await chat.send_message(message)

        # Persist a short audit record (best-effort, never blocks response)
        try:
            await db.ai_story_logs.insert_one({
                "id": str(_ai_uuid.uuid4()),
                "admin_id": admin_id,
                "kind": req.kind,
                "bride": req.bride,
                "groom": req.groom,
                "theme": req.theme,
                "tone": req.tone,
                "language": req.language,
                "model": f"{provider}:{model_name}",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as _e:
            logger.warning(f"ai_story_logs insert failed: {_e}")

        return {"story": str(story_text).strip(), "model": f"{provider}:{model_name}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI story generation failed: {e}")
        err_msg = str(e).lower()
        if "budget" in err_msg or "exceeded" in err_msg or "quota" in err_msg or "rate" in err_msg:
            raise HTTPException(
                status_code=503,
                detail="The AI muse is resting briefly. Please try again in a moment, or top up your Universal Key balance in Profile → Universal Key."
            )
        raise HTTPException(status_code=502, detail=f"AI service is temporarily unavailable. Please try again. ({str(e)[:120]})")


# ──────────────────────────────────────────────────────────────────────
# AUTO-TRANSLATE — Gemini-powered translation of an invitation's text
# fields into every language the photographer enabled in Features.
# Stored on the profile under translations: {language: {field: value}}
# ──────────────────────────────────────────────────────────────────────
TRANSLATABLE_FIELDS = [
    "bride_name", "groom_name", "venue", "venue_address", "story",
    "wedding_invitation_text", "welcome_message",
]


@api_router.post("/admin/profiles/{profile_id}/translate")
async def auto_translate_profile(
    profile_id: str,
    admin_id: str = Depends(get_current_admin),
):
    """Translate this wedding's main text fields into every additional
    language the photographer enabled (couple.languages list).
    Uses Gemini-2.5-flash via the Emergent Universal LLM Key."""
    profile = await db.profiles.find_one({"id": profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.get("admin_id") != admin_id:
        # super_admin override
        admin_doc = await db.admins.find_one({"id": admin_id})
        if not admin_doc or admin_doc.get("role") not in ("super_admin", "SUPER_ADMIN"):
            raise HTTPException(status_code=403, detail="Not your profile")

    ts_maja = (profile.get("theme_settings") or {}).get("maja") or {}
    additional_languages = ts_maja.get("languages") or profile.get("languages") or []
    main_language = (profile.get("language") or ["english"])
    if isinstance(main_language, list):
        main_language = main_language[0] if main_language else "english"
    languages = [l for l in additional_languages if str(l).lower() != str(main_language).lower()]
    if not languages:
        return {"translations": {}, "skipped": True, "reason": "No additional languages to translate."}

    # Gather payload
    payload = {f: profile.get(f) for f in TRANSLATABLE_FIELDS if profile.get(f)}
    if not payload:
        return {"translations": {}, "skipped": True, "reason": "No translatable fields populated."}

    api_key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not api_key:
        raise HTTPException(status_code=503, detail="LLM key not configured")

    from emergentintegrations.llm.chat import LlmChat, UserMessage
    translations: Dict[str, Dict[str, str]] = {}
    for lang in languages:
        session_id = f"translate-{profile_id}-{lang}-{_ai_uuid.uuid4()}"
        try:
            chat = LlmChat(
                api_key=api_key,
                session_id=session_id,
                system_message=(
                    f"You are a professional translator. Translate the following Indian wedding invitation "
                    f"fields from {main_language} into {lang}. Preserve names of people exactly. "
                    f"Keep tone respectful and elegant. Return ONLY a valid JSON object with the same keys."
                ),
            ).with_model("gemini", "gemini-2.5-flash")
            user_msg = UserMessage(text=json.dumps(payload, ensure_ascii=False))
            raw = await chat.send_message(user_msg)
            text = str(raw).strip()
            # Strip markdown fences if any
            if text.startswith("```"):
                text = text.strip("`").lstrip("json").strip()
                # remove any remaining backticks line
                if text.endswith("```"):
                    text = text[:-3].strip()
            try:
                obj = json.loads(text)
            except Exception:
                # crude fallback: keep raw under a single key
                obj = {"_raw": text}
            translations[str(lang).lower()] = obj
        except Exception as e:
            logger.warning(f"Translate {lang} failed: {e}")
            translations[str(lang).lower()] = {"_error": str(e)[:200]}

    await db.profiles.update_one(
        {"id": profile_id},
        {"$set": {"translations": translations, "translations_updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"translations": translations, "languages": list(translations.keys()), "skipped": False}


@api_router.get("/admin/profiles/{profile_id}/translations")
async def get_profile_translations(
    profile_id: str,
    admin_id: str = Depends(get_current_admin),
):
    profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0, "translations": 1, "translations_updated_at": 1})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "translations": profile.get("translations", {}),
        "updated_at": profile.get("translations_updated_at"),
    }


# ──────────────────────────────────────────────────────────────────────
# EXPIRY TIERS — link-lifetime tiers exposed to the publish step
# Admin-configurable via /api/admin/expiry-tiers (PUT)
# ──────────────────────────────────────────────────────────────────────
@api_router.get("/admin/expiry-tiers")
async def list_expiry_tiers(admin_id: str = Depends(get_current_admin)):
    """List all expiry tiers. Photographers see these in the publish step."""
    if await db.expiry_tiers.count_documents({}) == 0:
        defaults = [
            {"id": "1_month",  "label": "1 Month",  "days": 30,  "credits": 1, "order": 1},
            {"id": "3_months", "label": "3 Months", "days": 90,  "credits": 2, "order": 2},
            {"id": "6_months", "label": "6 Months", "days": 180, "credits": 3, "order": 3},
            {"id": "1_year",   "label": "1 Year",   "days": 365, "credits": 5, "order": 4},
        ]
        await db.expiry_tiers.insert_many(defaults)
    docs = await db.expiry_tiers.find({}, {"_id": 0}).sort("order", 1).to_list(50)
    return {"tiers": docs}


class ExpiryTierIn(_AIBaseModel):
    id: str
    label: str
    days: int
    credits: int
    order: int = 0


@api_router.put("/admin/expiry-tiers")
async def update_expiry_tiers(payload: List[ExpiryTierIn], admin_id: str = Depends(require_super_admin)):
    """Replace the full list of expiry tiers (super-admin only)."""
    docs = [t.model_dump() for t in payload]
    await db.expiry_tiers.delete_many({})
    if docs:
        await db.expiry_tiers.insert_many(docs)
    out = await db.expiry_tiers.find({}, {"_id": 0}).sort("order", 1).to_list(50)
    return {"tiers": out, "count": len(out)}


# Alias for legacy reference: maps (slug, ip, device_id, endpoint) → (ip, device_id, endpoint, slug)
async def check_submission_captcha_required(slug, ip_address, device_id, endpoint):
    return await check_submission_attempts(ip_address, device_id, endpoint, slug)

# =====================================================================
# Phase 38 — Premium features (Live Photo Wall, AI Suite, WhatsApp,
# Digital Shagun, Travel deep links, Smart RSVP, Analytics v2)
# =====================================================================
from premium_features import build_premium_router
from emergentintegrations.llm.chat import LlmChat, UserMessage as _PremiumUserMsg


async def _premium_ai_chat(system_msg: str, session_id: str, user_text: str) -> str:
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")
    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=system_msg,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    resp = await chat.send_message(_PremiumUserMsg(text=user_text))
    return str(resp)


premium_router = build_premium_router(
    db=db,
    get_current_admin=get_current_admin,
    require_admin=require_admin,
    ai_chat_factory=_premium_ai_chat,
)
app.include_router(premium_router)

# =====================================================================
# Bucket 1 — Admin Dashboard v2 (pagination, bulk actions, trash, tags,
# quick-edit, quick-stats, CSV export, notifications)
# =====================================================================
from admin_dashboard_v2 import build_admin_dashboard_v2_router
import aws_service
app.include_router(build_admin_dashboard_v2_router(
    db=db,
    require_admin=require_admin,
    log_audit_action=log_audit_action,
    wedding_lifecycle_service=wedding_lifecycle_service,
    credit_service=credit_service,
    aws_service=aws_service,
))

# Bucket 2 — Super Admin v2 (revenue/leaderboard/coupons/broadcast/settings/CMS/
# theme-rollout/impersonate/refund/login-history) + public CMS read endpoints.
from super_admin_v2 import build_super_admin_v2_router
_sa_v2_router, _public_cms_router = build_super_admin_v2_router(
    db=db,
    require_super_admin=require_super_admin,
    require_admin=require_admin,
    create_access_token=create_access_token,
    log_audit_action=log_audit_action,
)
app.include_router(_sa_v2_router)
app.include_router(_public_cms_router)

# =====================================================================
# Prompt 14 — Personalized Guest Experience
# =====================================================================
from guest_features import build_guest_router
guest_router = build_guest_router(db=db, require_admin=require_admin)
app.include_router(guest_router, prefix="/api")

# =====================================================================
# Prompt 05 + 13 — Live Photo Gallery with WebSocket
# =====================================================================
from live_gallery_features import build_live_gallery_router
# Built later, after user_auth defines get_current_public_user so the host-side
# (user) live-gallery routes can be auth'd. See block below.

# =====================================================================
# Prompt 07 — Guest Wishes Wall + Moderation
# =====================================================================
from wishes_features import build_wishes_router
wishes_router = build_wishes_router(db=db, require_admin=require_admin)
app.include_router(wishes_router)

# =====================================================================
# Prompt 16 — Analytics deep-dive (heatmap, funnel, geography, AI insights)
# =====================================================================
from analytics_extras import build_analytics_extras_router
analytics_extras_router = build_analytics_extras_router(
    db=db, require_admin=require_admin, ai_chat_factory=_premium_ai_chat
)
app.include_router(analytics_extras_router)

# =====================================================================
# Music — 20 curated CC0 background music presets
# =====================================================================
from music_library import build_music_library_router
app.include_router(build_music_library_router(), prefix="/api")

# =====================================================================
# Monetization — credit packs, Razorpay top-up, super-admin photographer detail
# =====================================================================
from monetization_features import build_monetization_router
monetization_router = build_monetization_router(
    db=db,
    require_admin=require_admin,
    require_super_admin=require_super_admin,
    credit_service=credit_service,
    razorpay_client=razorpay_client,
)
app.include_router(monetization_router)

# =====================================================================
# Public-user Auth — normal end-users (wedding guests) signup/login + Google
# =====================================================================
from user_auth import build_user_auth_router
user_auth_router, get_current_public_user = build_user_auth_router(
    db=db,
    password_hasher=get_password_hash,
    password_verifier=verify_password,
)
app.include_router(user_auth_router)

# Now that get_current_public_user exists, build the live-gallery router so
# user-facing (host) live-photo endpoints can authenticate the calling user.
live_gallery_router = build_live_gallery_router(
    db=db, require_admin=require_admin, get_current_user=get_current_public_user,
)
app.include_router(live_gallery_router)

# =====================================================================
# User Features — design-pricing, user credit purchase, user-created invitations
# =====================================================================
from user_features import build_user_features_router
user_features_router = build_user_features_router(
    db=db,
    require_super_admin=require_super_admin,
    get_current_public_user=get_current_public_user,
    razorpay_client=razorpay_client,
    sanitize_html=sanitize_html,
    generate_slug=generate_slug,
    calculate_expiry_date=calculate_expiry_date,
    calculate_invitation_expires_at=calculate_invitation_expires_at,
)
app.include_router(user_features_router)

# =====================================================================
# Celebration Translation — Gemini-backed translation (credit-gated)
# =====================================================================
from celebration_translation import build_celebration_translation_router
celebration_translation_router = build_celebration_translation_router(
    db=db,
    get_current_admin=require_admin,
    get_current_user=get_current_public_user,
    credit_service=credit_service,
)
app.include_router(celebration_translation_router, prefix="/api")

# =====================================================================
# Pricing & Discounts — theme bundle pricing + coupon codes
# =====================================================================
from pricing_features import build_pricing_router
pricing_router = build_pricing_router(
    db=db,
    require_super_admin=require_super_admin,
    get_current_public_user=get_current_public_user,
)
app.include_router(pricing_router)

# =====================================================================
# Sprint 8 — Smart Venue / Per-event maps / What3Words / Live ETA
# =====================================================================
from map_features import build_map_router
map_router = build_map_router(db=db, get_current_admin=get_current_admin)
app.include_router(map_router)

# =====================================================================
# Sprint 9 — Gift Registry (couple-controlled, optional)
# =====================================================================
from gift_registry import build_gift_router
gift_router = build_gift_router(db=db, get_current_admin=get_current_admin)
app.include_router(gift_router)

# =====================================================================
# Sprint 10 — Live AI Photo Gallery (S3 + Rekognition + CloudFront)
# =====================================================================
from gallery_features import (build_gallery_router, cleanup_expired_galleries,
                                cleanup_expired_selfies)
gallery_router = build_gallery_router(db=db, get_current_admin=get_current_admin)
app.include_router(gallery_router)

# Wedding Gallery Privacy — access codes, trusted-device tokens, rate-limited unlock
from gallery_privacy import build_privacy_router
gallery_privacy_router = build_privacy_router(
    db=db,
    get_current_admin=get_current_admin,
    get_password_hash=get_password_hash,
    verify_password=verify_password,
)
app.include_router(gallery_privacy_router)

# =====================================================================
# Invitation Viewer V2 — long-scroll wedding invitation builder & viewer
# =====================================================================
from invitation_v2 import build_invitation_v2_router
invitation_v2_router = build_invitation_v2_router(db=db, get_current_admin=get_current_admin)
app.include_router(invitation_v2_router)

# =====================================================================
# Music Library — Enhanced 60-song music library with categories
# =====================================================================
from music_library import build_music_library_router
music_library_router = build_music_library_router()
app.include_router(music_library_router, prefix="/api")

# =====================================================================
# Story Service — AI-powered story generation using Gemini
# =====================================================================
from story_service import story_service

@api_router.post("/generate-love-story")
async def generate_love_story_endpoint(
    request: Dict[str, Any],
    current_admin: dict = Depends(get_current_admin)
):
    """Generate personalized love story using Gemini AI"""
    try:
        bride_name = request.get("bride_name", "")
        groom_name = request.get("groom_name", "")
        story_prompt = request.get("story_prompt")
        tone = request.get("tone", "romantic")
        
        if not bride_name or not groom_name:
            raise HTTPException(status_code=400, detail="Bride and groom names are required")
        
        story = await story_service.generate_love_story(
            bride_name=bride_name,
            groom_name=groom_name,
            story_prompt=story_prompt,
            tone=tone
        )
        
        return {
            "success": True,
            "story": story
        }
    except Exception as e:
        logger.error(f"Error generating love story: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/generate-event-description")
async def generate_event_description_endpoint(
    request: Dict[str, Any],
    current_admin: dict = Depends(get_current_admin)
):
    """Generate event description using Gemini AI"""
    try:
        event_type = request.get("event_type", "")
        bride_name = request.get("bride_name", "")
        groom_name = request.get("groom_name", "")
        date = request.get("date")
        venue = request.get("venue")
        
        if not event_type or not bride_name or not groom_name:
            raise HTTPException(status_code=400, detail="Event type and couple names are required")
        
        description = await story_service.generate_event_description(
            event_type=event_type,
            bride_name=bride_name,
            groom_name=groom_name,
            date=date,
            venue=venue
        )
        
        return {
            "success": True,
            "description": description
        }
    except Exception as e:
        logger.error(f"Error generating event description: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================================
# Super Admin Management — Credit packages, design pricing, user management
# =====================================================================
from super_admin_service import build_super_admin_router
super_admin_router = build_super_admin_router(
    db=db,
    get_current_admin=get_current_admin,
    require_super_admin=require_super_admin,
    credit_service=credit_service
)
app.include_router(super_admin_router)

# =====================================================================
# Enhanced Admin Pricing — Features, Durations, Themes, Monthly Packs
# =====================================================================
from enhanced_admin_service import build_enhanced_admin_router
enhanced_admin_router = build_enhanced_admin_router(
    db=db,
    require_super_admin=require_super_admin
)
app.include_router(enhanced_admin_router)

# =====================================================================
# Restructured Admin Panel — Hierarchical pricing (User/Photographer)
# =====================================================================
from restructured_admin_service import build_restructured_admin_router
restructured_admin_router = build_restructured_admin_router(
    db=db,
    require_super_admin=require_super_admin
)
app.include_router(restructured_admin_router)

# =====================================================================
# User Purchase Flow — Browse, calculate, and purchase designs
# =====================================================================
from user_purchase_service import build_user_purchase_router
user_purchase_router = build_user_purchase_router(
    db=db,
    get_current_admin=get_current_admin,
    credit_service=credit_service
)
app.include_router(user_purchase_router)

# =====================================================================
# Canonical Credit System endpoints (spec-compliant)
#   /api/super-admin/credits/{add,deduct,adjust,gift,refund}
#   /api/super-admin/admins/{admin_id}/{balance,ledger}
#   /api/account/{credits,ledger}
# =====================================================================
from credit_system_routes import build_credit_system_router
credit_system_router = build_credit_system_router(
    db=db,
    require_super_admin=require_super_admin,
    get_current_admin=get_current_admin,
)
app.include_router(credit_system_router)

# Gift-code redemption (sits on top of /credits/gift):
from gift_code_routes import build_gift_code_router
gift_code_router = build_gift_code_router(
    db=db,
    require_super_admin=require_super_admin,
    get_current_admin=get_current_admin,
)
app.include_router(gift_code_router)

# Photographer referral codes (viral growth on top of gift-code infra):
from photographer_referrals import build_photographer_referral_router
photographer_referral_router = build_photographer_referral_router(
    db=db,
    require_super_admin=require_super_admin,
    get_current_admin=get_current_admin,
)
app.include_router(photographer_referral_router)

# Boot-time seed: idempotently insert default durations + features + mixed-theme
# so a fresh DB exposes a working purchase flow before the super-admin opens
# the pricing editor. Existing rows are NOT overwritten (the seed only inserts
# when its target collections are empty).
@app.on_event("startup")
async def _seed_credit_system_defaults():
    try:
        # Seed the user-facing purchase catalogue (expiry tiers + addons) ONCE
        # at boot so the public endpoints never race on a cold first request.
        from user_features import seed_user_purchase_catalog
        await seed_user_purchase_catalog(db)
    except Exception as e:
        logger.warning("[credit-system] user-catalog seed failed: %s", e)
    try:
        from enhanced_pricing_models import DurationOption, MixedThemePricing
        if await db.duration_options.count_documents({}) == 0:
            defaults = [
                DurationOption(duration_id="1day",       label="1 Day",     days=1,
                               user_credits=2,  photographer_credits=1).dict(),
                DurationOption(duration_id="7days",      label="7 Days",    days=7,
                               user_credits=8,  photographer_credits=4).dict(),
                DurationOption(duration_id="30days",     label="30 Days",   days=30,
                               user_credits=20, photographer_credits=10).dict(),
                DurationOption(duration_id="unlimited",  label="Unlimited", days=None,
                               user_credits=50, photographer_credits=25).dict(),
            ]
            await db.duration_options.insert_many(defaults)
            logger.info("[credit-system] seeded %d default duration options", len(defaults))
        if await db.mixed_theme_pricing.count_documents({}) == 0:
            await db.mixed_theme_pricing.insert_one(
                MixedThemePricing(user_additional_credits=50,
                                  photographer_additional_credits=30).dict()
            )
            logger.info("[credit-system] seeded default mixed-theme pricing")
    except Exception as e:
        logger.warning("[credit-system] default seed failed: %s", e)


@app.on_event("startup")
async def _ensure_financial_safety_indexes():
    """
    Create unique indexes that backstop the atomic financial fixes
    (Razorpay verify-payment, gift-code redeem). Idempotent.
    """
    try:
        # Razorpay: prevent the same payment_id from being credited twice
        # under any code path. Sparse so historical rows without the field
        # don't all collide.
        await db.payment_records.create_index(
            [("razorpay_payment_id", 1)],
            unique=True,
            sparse=True,
            name="uniq_razorpay_payment_id",
        )
        logger.info("[indexes] payment_records.razorpay_payment_id unique index ready")
    except Exception as e:
        logger.warning("[indexes] payment_records index failed: %s", e)

    try:
        # Gift codes: per-account redemption uniqueness (atomic per_account_limit=1).
        await db.gift_code_redemptions.create_index(
            [("code", 1), ("admin_id", 1)],
            unique=True,
            name="uniq_gift_redemption_per_account",
        )
        logger.info("[indexes] gift_code_redemptions.(code,admin_id) unique index ready")
    except Exception as e:
        logger.warning("[indexes] gift_code_redemptions index failed: %s", e)


@app.on_event("startup")
async def _seed_super_admin_pricing_defaults():
    """Seed the Super-Admin Pricing Hub collections with sensible defaults so
    every consumer surface (LandingPage, photographer panel, design picker, …)
    has values to read from on day one.  Idempotent — only inserts when empty.
    """
    try:
        now = datetime.now(timezone.utc)

        # ---- Theme prices (audience-aware, credits) ----------------
        THEMES = [
            ("royal_mughal", 5, 3),
            ("south_indian_temple", 4, 2),
            ("modern_minimal", 3, 2),
            ("beach_destination", 4, 2),
            ("punjabi_sangeet", 5, 3),
            ("bengali_traditional", 4, 2),
            ("christian_elegant", 4, 2),
            ("muslim_nikah", 4, 2),
            ("kerala_heritage", 5, 3),
            ("rajputana_royal", 6, 4),
        ]
        if await db.pricing_theme_prices.count_documents({}) == 0:
            rows = []
            for tid, user_c, photog_c in THEMES:
                rows.append({"id": str(uuid.uuid4()), "audience": "normal_user",
                             "theme_id": tid, "base_price": user_c,
                             "discount_enabled": False, "updated_at": now})
                rows.append({"id": str(uuid.uuid4()), "audience": "photographer",
                             "theme_id": tid, "base_price": photog_c,
                             "discount_enabled": False, "updated_at": now})
            await db.pricing_theme_prices.insert_many(rows)
            logger.info("[pricing-hub] seeded %d theme price rows", len(rows))

        # ---- Option prices (audience-aware, credits) ---------------
        OPTIONS = [
            # (option_key, user_credits, photographer_credits, free_for_photog)
            ("rsvp_basic", 0, 0, True),
            ("ai_story", 1, 1, False),
            ("live_gallery", 3, 2, False),
            ("ai_selfie_guests", 2, 1, False),
            ("background_music", 1, 0, True),
            ("multi_track_music", 2, 1, False),
            ("guest_messages", 1, 0, True),
            ("gift_registry", 1, 1, False),
            ("live_streaming", 5, 3, False),
            ("transport_help", 1, 1, False),
            ("guest_accommodation", 1, 1, False),
            ("dress_code", 0, 0, True),
            ("event_timeline", 0, 0, True),
            ("countdown_timer", 1, 0, True),
        ]
        if await db.pricing_option_prices.count_documents({}) == 0:
            rows = []
            for okey, user_c, photog_c, photog_free in OPTIONS:
                rows.append({"id": str(uuid.uuid4()), "audience": "normal_user",
                             "option_key": okey, "base_price": user_c,
                             "discount_enabled": False, "is_free": (user_c == 0),
                             "updated_at": now})
                rows.append({"id": str(uuid.uuid4()), "audience": "photographer",
                             "option_key": okey, "base_price": photog_c,
                             "discount_enabled": False,
                             "is_free": photog_free or (photog_c == 0),
                             "updated_at": now})
            await db.pricing_option_prices.insert_many(rows)
            logger.info("[pricing-hub] seeded %d option price rows", len(rows))

        # ---- Credit packs (audience-aware, rupees) -----------------
        if await db.pricing_credit_packs.count_documents({"audience": "normal_user"}) == 0:
            packs = [
                {"label": "Free",     "credits": 5,   "base_price": 0},
                {"label": "Silver",   "credits": 25,  "base_price": 99},
                {"label": "Gold",     "credits": 75,  "base_price": 249},
                {"label": "Platinum", "credits": 200, "base_price": 599},
            ]
            for p in packs:
                p.update({"id": str(uuid.uuid4()), "audience": "normal_user",
                          "discount_enabled": False, "is_active": True,
                          "created_at": now, "updated_at": now})
            await db.pricing_credit_packs.insert_many(packs)
            logger.info("[pricing-hub] seeded %d normal_user credit packs", len(packs))

        if await db.pricing_credit_packs.count_documents({"audience": "photographer"}) == 0:
            packs = [
                {"label": "Starter",  "credits": 25,  "base_price": 79},
                {"label": "Studio",   "credits": 100, "base_price": 299},
                {"label": "Atelier",  "credits": 300, "base_price": 799},
                {"label": "Maestro",  "credits": 750, "base_price": 1799},
            ]
            for p in packs:
                p.update({"id": str(uuid.uuid4()), "audience": "photographer",
                          "discount_enabled": False, "is_active": True,
                          "created_at": now, "updated_at": now})
            await db.pricing_credit_packs.insert_many(packs)
            logger.info("[pricing-hub] seeded %d photographer credit packs", len(packs))

        # ---- Photographer subscription plans -----------------------
        if await db.pricing_subscription_plans.count_documents({}) == 0:
            plans = [
                {"name": "Boutique",  "credits_per_month": 100, "duration_days": 30, "base_price": 499},
                {"name": "Studio",    "credits_per_month": 300, "duration_days": 30, "base_price": 1199},
                {"name": "Atelier",   "credits_per_month": 800, "duration_days": 30, "base_price": 2499},
            ]
            for p in plans:
                p.update({"id": str(uuid.uuid4()), "is_active": True,
                          "discount_enabled": False, "updated_at": now})
            await db.pricing_subscription_plans.insert_many(plans)
            logger.info("[pricing-hub] seeded %d subscription plans", len(plans))

    except Exception as e:
        logger.warning("[pricing-hub] default seed failed: %s", e)



# =====================================================================
# Razorpay Payment Integration — Credit purchases
# =====================================================================
from razorpay_credit_service import build_razorpay_credit_router
razorpay_credit_router = build_razorpay_credit_router(
    db=db,
    get_current_admin=get_current_admin,
    credit_service=credit_service
)
app.include_router(razorpay_credit_router)

# Daily cleanup jobs (3am IST + hourly selfie purge)
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    import pytz as _pytz
    _ist = _pytz.timezone("Asia/Kolkata")
    _gallery_scheduler = AsyncIOScheduler(timezone=_ist)

    async def _daily_gallery_cleanup():
        await cleanup_expired_galleries(db)

    async def _hourly_selfie_cleanup():
        await cleanup_expired_selfies(db)

    _gallery_scheduler.add_job(_daily_gallery_cleanup,
        CronTrigger(hour=3, minute=0, timezone=_ist), id="gallery_daily")
    _gallery_scheduler.add_job(_hourly_selfie_cleanup,
        CronTrigger(minute=15, timezone=_ist), id="selfie_hourly")

    @app.on_event("startup")
    async def _start_gallery_scheduler():
        try:
            _gallery_scheduler.start()
            logger.info("[gallery] scheduler started (daily 3am IST + hourly selfie)")
        except Exception as e:
            logger.warning("[gallery] scheduler start failed: %s", e)

    @app.on_event("shutdown")
    async def _stop_gallery_scheduler():
        try:
            _gallery_scheduler.shutdown(wait=False)
        except Exception:
            pass
except Exception as _e:
    try:
        logger.warning("APScheduler init failed: %s", _e)
    except Exception:
        print(f"APScheduler init failed: {_e}")

# Include the router in the main app
app.include_router(api_router)

# Super Admin Pricing Hub (audience-aware, unified)
import super_admin_pricing as _sap
_sap.attach(db)
app.include_router(_sap.router)
app.include_router(_sap.public_router)
app.include_router(_sap.photographer_tier_router)

# PHASE 32: Add security middleware (order matters - apply in reverse order of execution)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(BotDetectionMiddleware)
app.add_middleware(AbusePreventionMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


# Background task: per-hour expiry sweep for event invitation links
import asyncio as _asyncio_for_sweep

@app.on_event("startup")
async def _start_invitation_expiry_sweep():
    try:
        _asyncio_for_sweep.create_task(_expiry_sweep_loop())
        logger.info("Event invitation expiry sweeper started (hourly).")
    except Exception as e:
        logger.warning(f"Could not start expiry sweeper: {e}")