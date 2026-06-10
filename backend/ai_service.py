"""
PHASE 26: AI-Powered Personalization Engine
AI Service Layer using Emergent LLM Universal Key

This service provides:
1. Content translation (English, Telugu, Hindi, Tamil)
2. Event description generation
3. RSVP message suggestions
4. Guest segment insights
"""

import os
from typing import List, Dict, Optional, Literal
from datetime import datetime, timedelta
import asyncio
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

# Load environment variables
load_dotenv()

# Supported languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "te": "Telugu",
    "hi": "Hindi",
    "ta": "Tamil"
}

# Rate limit tracking (in-memory for MVP, use Redis in production)
translation_rate_limits = {}  # {ip: [timestamp1, timestamp2, ...]}
admin_generation_limits = {}  # {admin_id: [timestamp1, timestamp2, ...]}


class AIService:
    """Abstracted AI service using Emergent LLM Universal Key"""
    
    def __init__(self):
        self.api_key = os.getenv("EMERGENT_LLM_KEY")
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            print("⚠️  EMERGENT_LLM_KEY not found. AI features will be disabled.")
        
        # Default to GPT-5.1 (recommended by playbook)
        self.provider = "openai"
        self.model = "gpt-5.1"
    
    def _create_chat_session(self, system_message: str, session_id: str) -> LlmChat:
        """Create a new LLM chat session"""
        chat = LlmChat(
            api_key=self.api_key,
            session_id=session_id,
            system_message=system_message
        )
        chat.with_model(self.provider, self.model)
        return chat
    
    async def translate_content(
        self, 
        content: str, 
        target_language: str,
        context: str = "wedding invitation"
    ) -> str:
        """
        Translate content to target language
        
        Args:
            content: Text to translate
            target_language: Target language code (en, te, hi, ta)
            context: Context for better translation (default: wedding invitation)
        
        Returns:
            Translated text
        """
        if not self.enabled:
            return content  # Return original content if AI is disabled
        
        if target_language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {target_language}")
        
        # If already in English and target is English, return as-is
        if target_language == "en":
            return content
        
        language_name = SUPPORTED_LANGUAGES[target_language]
        
        system_message = f"""You are a professional translator specializing in Indian wedding invitations.
Translate the given text to {language_name} while:
- Maintaining cultural sensitivity and respect
- Preserving formatting (line breaks, punctuation)
- Using appropriate formal language for weddings
- Keeping names, dates, and places in original language when culturally appropriate
- Only return the translated text, no explanations"""
        
        session_id = f"translation_{target_language}_{datetime.now().timestamp()}"
        chat = self._create_chat_session(system_message, session_id)
        
        user_message = UserMessage(
            text=f"Translate this {context} text to {language_name}:\n\n{content}"
        )
        
        try:
            response = await chat.send_message(user_message)
            return response.strip()
        except Exception as e:
            # Fallback: return original content if translation fails
            print(f"Translation error: {e}")
            return content
    
    async def generate_event_description(
        self,
        event_type: str,
        couple_names: Optional[str] = None,
        date: Optional[str] = None,
        venue: Optional[str] = None
    ) -> str:
        """
        Generate elegant event description using AI
        
        Args:
            event_type: Type of event (engagement, haldi, mehendi, marriage, reception)
            couple_names: Names of couple (optional)
            date: Event date (optional)
            venue: Event venue (optional)
        
        Returns:
            AI-generated event description
        """
        if not self.enabled:
            # Return a default description if AI is disabled
            return f"Join us for a beautiful {event_type} celebration."
        
        system_message = """You are a creative wedding invitation content writer.
Generate elegant, short, and heartfelt event descriptions for Indian weddings.
Keep descriptions:
- Maximum 2-3 sentences
- Culturally appropriate
- Professional yet warm
- Inclusive and respectful
- No emojis or excessive punctuation
Only return the description text, no explanations."""
        
        # Build context
        context_parts = []
        if couple_names:
            context_parts.append(f"Couple: {couple_names}")
        if date:
            context_parts.append(f"Date: {date}")
        if venue:
            context_parts.append(f"Venue: {venue}")
        
        context_str = "\n".join(context_parts) if context_parts else "No additional details"
        
        prompt = f"""Generate a short elegant description for a {event_type} event.

{context_str}

Create a 2-3 sentence description that captures the essence and joy of this special occasion."""
        
        session_id = f"description_{event_type}_{datetime.now().timestamp()}"
        chat = self._create_chat_session(system_message, session_id)
        
        user_message = UserMessage(text=prompt)
        
        try:
            response = await chat.send_message(user_message)
            return response.strip()
        except Exception as e:
            # Fallback description
            print(f"Description generation error: {e}")
            return f"Join us to celebrate this beautiful {event_type} ceremony."
    
    async def generate_rsvp_suggestions(
        self,
        event_type: str = "marriage",
        guest_name: Optional[str] = None
    ) -> List[str]:
        """
        Generate 3 RSVP message suggestions
        
        Args:
            event_type: Type of event
            guest_name: Name of guest (optional, for personalization)
        
        Returns:
            List of 3 suggested messages
        """
        system_message = """You are an expert at generating warm, appropriate RSVP messages for Indian weddings.
Generate exactly 3 short, heartfelt messages that guests can use when RSVPing.
Each message should be:
- Maximum 15 words
- Culturally appropriate
- Include relevant emojis
- Warm and genuine
- Different in tone (excited, blessing, formal)

Return ONLY the 3 messages, one per line, no numbering or extra text."""
        
        prompt = f"""Generate 3 RSVP message suggestions for a {event_type} event.
Each message should be unique in tone and sentiment.
Include appropriate emojis."""
        
        session_id = f"rsvp_{event_type}_{datetime.now().timestamp()}"
        chat = self._create_chat_session(system_message, session_id)
        
        user_message = UserMessage(text=prompt)
        
        try:
            response = await chat.send_message(user_message)
            suggestions = [line.strip() for line in response.split('\n') if line.strip()]
            
            # Ensure we have exactly 3 suggestions
            if len(suggestions) < 3:
                # Add fallback messages
                fallback_messages = [
                    "Can't wait to celebrate with you! 🎉",
                    "Blessings to the beautiful couple ❤️",
                    "Excited for your special day! 💐"
                ]
                suggestions.extend(fallback_messages[len(suggestions):3])
            
            return suggestions[:3]
        except Exception as e:
            # Fallback suggestions
            print(f"RSVP suggestions error: {e}")
            return [
                "Can't wait to celebrate with you! 🎉",
                "Blessings to the beautiful couple ❤️",
                "Excited for your special day! 💐"
            ]
    
    async def generate_guest_insights(
        self,
        rsvp_data: Dict[str, any]
    ) -> str:
        """
        Generate guest segment insights from RSVP data
        
        Args:
            rsvp_data: Dictionary with RSVP statistics
                {
                    'total': int,
                    'confirmed': int,
                    'declined': int,
                    'pending': int,
                    'early_responses': int,  # Responses within 24 hours
                    'late_responses': int,   # Responses after 3 days
                    'with_messages': int,    # RSVPs with personal messages
                }
        
        Returns:
            AI-generated insights text
        """
        system_message = """You are a data analyst for wedding planning.
Generate brief, actionable insights from RSVP data.
Keep insights:
- Maximum 2-3 sentences
- Positive and helpful
- Focus on patterns and timing
- Professional tone
Only return the insight text, no explanations."""
        
        prompt = f"""Analyze this RSVP data and provide a brief insight:

Total RSVPs: {rsvp_data.get('total', 0)}
Confirmed: {rsvp_data.get('confirmed', 0)}
Declined: {rsvp_data.get('declined', 0)}
Pending: {rsvp_data.get('pending', 0)}
Early responses (within 24h): {rsvp_data.get('early_responses', 0)}
Late responses (after 3 days): {rsvp_data.get('late_responses', 0)}
RSVPs with messages: {rsvp_data.get('with_messages', 0)}

Generate a 2-3 sentence insight highlighting key patterns or trends."""
        
        session_id = f"insights_{datetime.now().timestamp()}"
        chat = self._create_chat_session(system_message, session_id)
        
        user_message = UserMessage(text=prompt)
        
        try:
            response = await chat.send_message(user_message)
            return response.strip()
        except Exception as e:
            # Fallback insight
            print(f"Insights generation error: {e}")
            confirmed_rate = (rsvp_data.get('confirmed', 0) / max(rsvp_data.get('total', 1), 1)) * 100
            return f"You have received {rsvp_data.get('total', 0)} RSVPs so far, with {confirmed_rate:.0f}% confirming attendance."


# Rate limiting functions
def check_translation_rate_limit(ip_address: str) -> bool:
    """
    Check if IP address is within translation rate limit
    Limit: 10 requests per minute
    
    Returns:
        True if within limit, False if exceeded
    """
    current_time = datetime.now()
    minute_ago = current_time - timedelta(minutes=1)
    
    # Clean old timestamps
    if ip_address in translation_rate_limits:
        translation_rate_limits[ip_address] = [
            ts for ts in translation_rate_limits[ip_address] 
            if ts > minute_ago
        ]
    else:
        translation_rate_limits[ip_address] = []
    
    # Check limit
    if len(translation_rate_limits[ip_address]) >= 10:
        return False
    
    # Add current request
    translation_rate_limits[ip_address].append(current_time)
    return True


def check_admin_generation_rate_limit(admin_id: str) -> bool:
    """
    Check if admin is within AI generation rate limit
    Limit: 5 requests per hour
    
    Returns:
        True if within limit, False if exceeded
    """
    current_time = datetime.now()
    hour_ago = current_time - timedelta(hours=1)
    
    # Clean old timestamps
    if admin_id in admin_generation_limits:
        admin_generation_limits[admin_id] = [
            ts for ts in admin_generation_limits[admin_id] 
            if ts > hour_ago
        ]
    else:
        admin_generation_limits[admin_id] = []
    
    # Check limit
    if len(admin_generation_limits[admin_id]) >= 5:
        return False
    
    # Add current request
    admin_generation_limits[admin_id].append(current_time)
    return True


# Initialize AI service
ai_service = AIService()
