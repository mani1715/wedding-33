"""
MAJA Creations — AWS Service Layer (Sprint 10)
==============================================
Wraps S3, Rekognition, CloudFront signed URLs, and Pillow thumbs.
Each wedding gets its own Rekognition FaceCollection.
All S3 objects are tagged with `expire-at` for lifecycle cleanup.

Configured via /app/backend/.env:
  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
  AWS_S3_BUCKET
  AWS_CLOUDFRONT_DOMAIN, AWS_CLOUDFRONT_KEY_PAIR_ID, AWS_CLOUDFRONT_PRIVATE_KEY_PATH
  FACE_MATCH_CONFIDENCE_THRESHOLD (default 90)
"""
import os
import io
import logging
import datetime as _dt
from typing import Optional, List, Dict, Any
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.signers import CloudFrontSigner
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from PIL import Image, ImageOps

logger = logging.getLogger("aws_service")


# ============================================================
#  Lazy singletons
# ============================================================
_boto_cfg = Config(retries={"max_attempts": 3, "mode": "adaptive"},
                   max_pool_connections=20)

_s3 = None
_rekognition = None
_cf_signer = None


def _aws_kwargs() -> Dict[str, Any]:
    return {
        "region_name": os.environ.get("AWS_REGION", "ap-south-1"),
        "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY"),
        "config": _boto_cfg,
    }


def s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", **_aws_kwargs())
    return _s3


def rekognition():
    global _rekognition
    if _rekognition is None:
        _rekognition = boto3.client("rekognition", **_aws_kwargs())
    return _rekognition


def cf_signer() -> Optional[CloudFrontSigner]:
    global _cf_signer
    if _cf_signer is not None:
        return _cf_signer
    key_path = os.environ.get("AWS_CLOUDFRONT_PRIVATE_KEY_PATH")
    key_pair_id = os.environ.get("AWS_CLOUDFRONT_KEY_PAIR_ID")
    if not key_path or not key_pair_id or not os.path.exists(key_path):
        logger.warning("CloudFront signer not configured (key missing). Falling back to S3 presigned URLs.")
        return None
    with open(key_path, "rb") as fh:
        private_key = serialization.load_pem_private_key(fh.read(),
                                                          password=None,
                                                          backend=default_backend())

    def rsa_signer(message: bytes) -> bytes:
        return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())

    _cf_signer = CloudFrontSigner(key_pair_id, rsa_signer)
    return _cf_signer


def bucket() -> str:
    return os.environ.get("AWS_S3_BUCKET", "")


def cloudfront_domain() -> str:
    return os.environ.get("AWS_CLOUDFRONT_DOMAIN", "")


# ============================================================
#  S3 helpers
# ============================================================
def upload_bytes(key: str, data: bytes, content_type: str,
                  tags: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Upload raw bytes to S3 with optional object tags."""
    tag_str = "&".join(f"{k}={quote(str(v))}" for k, v in (tags or {}).items())
    kwargs = dict(Bucket=bucket(), Key=key, Body=data, ContentType=content_type)
    if tag_str:
        kwargs["Tagging"] = tag_str
    s3().put_object(**kwargs)
    return {"bucket": bucket(), "key": key, "size": len(data)}


def delete_prefix(prefix: str) -> int:
    """Delete every object under prefix. Returns count deleted."""
    paginator = s3().get_paginator("list_objects_v2")
    deleted = 0
    for page in paginator.paginate(Bucket=bucket(), Prefix=prefix):
        contents = page.get("Contents") or []
        if not contents:
            continue
        batch = [{"Key": o["Key"]} for o in contents]
        # delete_objects supports max 1000 per call
        for i in range(0, len(batch), 1000):
            resp = s3().delete_objects(Bucket=bucket(),
                                       Delete={"Objects": batch[i:i + 1000]})
            deleted += len(resp.get("Deleted") or [])
    return deleted


def generate_signed_url(key: str, expiry_seconds: int = 3600) -> str:
    """Prefer CloudFront signed URL; fall back to S3 presigned GET."""
    signer = cf_signer()
    if signer and cloudfront_domain():
        url = f"https://{cloudfront_domain()}/{key}"
        expire_at = _dt.datetime.utcnow() + _dt.timedelta(seconds=expiry_seconds)
        return signer.generate_presigned_url(url, date_less_than=expire_at)
    # Fallback — S3 presigned URL (works for testing without CF config)
    return s3().generate_presigned_url("get_object",
                                        Params={"Bucket": bucket(), "Key": key},
                                        ExpiresIn=expiry_seconds)


# ============================================================
#  Pillow helpers
# ============================================================
def is_valid_image(data: bytes) -> bool:
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
        return True
    except Exception:
        return False


def make_thumbnail(data: bytes, target_w: int = 400, jpeg_quality: int = 85) -> bytes:
    """Generate JPEG thumbnail (RGB) at target_w pixels wide, preserving aspect."""
    with Image.open(io.BytesIO(data)) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            mask = im.split()[-1] if im.mode == "RGBA" else None
            bg.paste(im, mask=mask)
            im = bg
        elif im.mode != "RGB":
            im = im.convert("RGB")
        ratio = target_w / float(im.width)
        new_h = int(im.height * ratio)
        im = im.resize((target_w, new_h), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=jpeg_quality, optimize=True)
        return out.getvalue()


def image_dimensions(data: bytes) -> Dict[str, int]:
    try:
        with Image.open(io.BytesIO(data)) as im:
            return {"width": im.width, "height": im.height}
    except Exception:
        return {"width": 0, "height": 0}


# ============================================================
#  Rekognition helpers
# ============================================================
def create_face_collection(collection_id: str) -> Dict[str, Any]:
    try:
        resp = rekognition().create_collection(CollectionId=collection_id)
        return {"created": True, "arn": resp.get("CollectionArn")}
    except rekognition().exceptions.ResourceAlreadyExistsException:
        return {"created": False, "already_exists": True}


def delete_face_collection(collection_id: str) -> bool:
    try:
        rekognition().delete_collection(CollectionId=collection_id)
        return True
    except rekognition().exceptions.ResourceNotFoundException:
        return False
    except ClientError as e:
        logger.error("delete_face_collection error: %s", e)
        return False


def index_photo_faces(collection_id: str, s3_key: str,
                       external_image_id: str, max_faces: int = 15) -> Dict[str, Any]:
    """Index all faces in an S3 photo into a collection."""
    try:
        resp = rekognition().index_faces(
            CollectionId=collection_id,
            Image={"S3Object": {"Bucket": bucket(), "Name": s3_key}},
            ExternalImageId=external_image_id,
            DetectionAttributes=["DEFAULT"],
            QualityFilter="AUTO",
            MaxFaces=max_faces,
        )
        face_records = resp.get("FaceRecords") or []
        return {
            "ok": True,
            "face_count": len(face_records),
            "face_ids": [r["Face"]["FaceId"] for r in face_records],
        }
    except rekognition().exceptions.InvalidParameterException:
        # no faces detected
        return {"ok": True, "face_count": 0, "face_ids": []}
    except ClientError as e:
        logger.error("index_photo_faces error: %s", e)
        return {"ok": False, "error": str(e)[:200]}


def search_faces_by_selfie(collection_id: str, selfie_bytes: bytes,
                            threshold: Optional[float] = None,
                            max_faces: int = 100) -> Dict[str, Any]:
    """Search for faces in a collection matching the selfie image bytes."""
    if threshold is None:
        try:
            threshold = float(os.environ.get("FACE_MATCH_CONFIDENCE_THRESHOLD", "90"))
        except ValueError:
            threshold = 90.0
    try:
        resp = rekognition().search_faces_by_image(
            CollectionId=collection_id,
            Image={"Bytes": selfie_bytes},
            MaxFaces=max_faces,
            FaceMatchThreshold=threshold,
            QualityFilter="AUTO",
        )
        matches = resp.get("FaceMatches") or []
        # Deduplicate by ExternalImageId (= photo_id) — best similarity wins
        best: Dict[str, float] = {}
        for m in matches:
            ext = m["Face"].get("ExternalImageId") or ""
            sim = float(m.get("Similarity") or 0.0)
            if ext and sim > best.get(ext, 0.0):
                best[ext] = sim
        sorted_matches = sorted(best.items(), key=lambda kv: kv[1], reverse=True)
        return {
            "ok": True,
            "match_count": len(sorted_matches),
            "matches": [{"photo_id": pid, "similarity": sim} for pid, sim in sorted_matches],
        }
    except rekognition().exceptions.InvalidParameterException:
        return {"ok": False, "error": "no_face_in_selfie",
                "message": "We couldn't find a clear face in your selfie. Please try again with better lighting."}
    except ClientError as e:
        logger.error("search_faces error: %s", e)
        return {"ok": False, "error": str(e)[:200]}


# ============================================================
#  Misc helpers
# ============================================================
def is_configured() -> bool:
    return bool(os.environ.get("AWS_ACCESS_KEY_ID")
                and os.environ.get("AWS_SECRET_ACCESS_KEY")
                and bucket())


def healthcheck() -> Dict[str, Any]:
    """Lightweight self-test — returns status of each AWS piece."""
    status = {"configured": is_configured(), "bucket": bucket(),
              "region": os.environ.get("AWS_REGION"),
              "cf_signer": bool(cf_signer()),
              "cf_domain": cloudfront_domain() or None}
    if not is_configured():
        return status
    try:
        s3().head_bucket(Bucket=bucket())
        status["s3_reachable"] = True
    except ClientError as e:
        status["s3_reachable"] = False
        status["s3_error"] = str(e)[:200]
    try:
        rekognition().list_collections(MaxResults=1)
        status["rekognition_reachable"] = True
    except ClientError as e:
        status["rekognition_reachable"] = False
        status["rekognition_error"] = str(e)[:200]
    return status
