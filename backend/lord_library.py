"""
PHASE 23: Lord Image Library Registry

Centralized registry of lord/deity images with metadata.
Defines which events can use each lord image and provides helper functions.
"""

from typing import List, Optional
from models import LordLibrary, EventType


# Lord Library Data
LORD_LIBRARY_DATA = [
    {
        "lord_id": "ganesha",
        "name": "Lord Ganesha",
        "description": "Remover of obstacles, auspicious beginning",
        "image_webp": "/assets/deities/ganesha_desktop.webp",
        "image_webp_mobile": "/assets/deities/ganesha_mobile.webp",
        "image_png_fallback": "/assets/deities/ganesha_desktop.jpg",
        "thumbnail": "/assets/deities/ganesha_thumb.webp",
        "allowed_events": [EventType.ENGAGEMENT, EventType.MARRIAGE, EventType.RECEPTION],
        "default_position": "center",
        "is_default": True,
        "order": 1
    },
    {
        "lord_id": "venkateswara_padmavati",
        "name": "Lord Venkateswara & Padmavati",
        "description": "Divine couple symbolizing eternal love",
        "image_webp": "/assets/deities/venkateswara_padmavati_desktop.webp",
        "image_webp_mobile": "/assets/deities/venkateswara_padmavati_mobile.webp",
        "image_png_fallback": "/assets/deities/venkateswara_padmavati_desktop.jpg",
        "thumbnail": "/assets/deities/venkateswara_padmavati_thumb.webp",
        "allowed_events": [EventType.ENGAGEMENT, EventType.MARRIAGE, EventType.RECEPTION],
        "default_position": "center",
        "is_default": False,
        "order": 2
    },
    {
        "lord_id": "shiva_parvati",
        "name": "Lord Shiva & Parvati",
        "description": "Perfect union of masculine and feminine energy",
        "image_webp": "/assets/deities/shiva_parvati_desktop.webp",
        "image_webp_mobile": "/assets/deities/shiva_parvati_mobile.webp",
        "image_png_fallback": "/assets/deities/shiva_parvati_desktop.jpg",
        "thumbnail": "/assets/deities/shiva_parvati_thumb.webp",
        "allowed_events": [EventType.ENGAGEMENT, EventType.MARRIAGE, EventType.RECEPTION],
        "default_position": "center",
        "is_default": False,
        "order": 3
    },
    {
        "lord_id": "lakshmi_vishnu",
        "name": "Lakshmi & Vishnu",
        "description": "Wealth, prosperity, and harmony",
        "image_webp": "/assets/deities/lakshmi_vishnu_desktop.webp",
        "image_webp_mobile": "/assets/deities/lakshmi_vishnu_mobile.webp",
        "image_png_fallback": "/assets/deities/lakshmi_vishnu_desktop.jpg",
        "thumbnail": "/assets/deities/lakshmi_vishnu_thumb.webp",
        "allowed_events": [EventType.ENGAGEMENT, EventType.MARRIAGE, EventType.RECEPTION],
        "default_position": "center",
        "is_default": False,
        "order": 4
    }
]


def get_all_lords() -> List[LordLibrary]:
    """
    Get all lords from the library
    
    Returns:
        List of LordLibrary objects
    """
    return [LordLibrary(**lord_data) for lord_data in LORD_LIBRARY_DATA]


def get_lords_by_event_type(event_type: EventType) -> List[LordLibrary]:
    """
    Get lords filtered by event type
    
    Args:
        event_type: EventType enum value
        
    Returns:
        List of LordLibrary objects that are allowed for the event type
    """
    all_lords = get_all_lords()
    return [lord for lord in all_lords if event_type in lord.allowed_events]


def get_lord_by_id(lord_id: str) -> Optional[LordLibrary]:
    """
    Get a specific lord by ID
    
    Args:
        lord_id: Unique lord identifier
        
    Returns:
        LordLibrary object or None if not found
    """
    all_lords = get_all_lords()
    for lord in all_lords:
        if lord.lord_id == lord_id:
            return lord
    return None


def get_default_lord() -> LordLibrary:
    """
    Get the default lord (Ganesha)
    
    Returns:
        Default LordLibrary object (Ganesha)
    """
    all_lords = get_all_lords()
    for lord in all_lords:
        if lord.is_default:
            return lord
    # Fallback to first lord if no default found
    return all_lords[0] if all_lords else None


def is_lord_allowed_for_event(lord_id: str, event_type: EventType) -> bool:
    """
    Check if a lord is allowed for a specific event type
    
    Args:
        lord_id: Unique lord identifier
        event_type: EventType enum value
        
    Returns:
        True if lord is allowed for the event type, False otherwise
    """
    lord = get_lord_by_id(lord_id)
    if not lord:
        return False
    return event_type in lord.allowed_events
