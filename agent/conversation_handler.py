"""
Phase 2: Conversation Handling
Processes replies, manages state, qualifies leads
"""

from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class ConversationState:
    """State for an active conversation"""
    trace_id: str
    prospect_email: str
    company_name: str
    current_channel: str = 'email'
    turn_count: int = 0
    qualification_status: str = 'pending'  # pending, qualified, not_qualified, booked
    icp_segment: Optional[int] = None
    ai_maturity_score: Optional[int] = None
    last_intent: Optional[str] = None
    last_activity_at: datetime = field(default_factory=datetime.now)


async def process_reply(state: ConversationState, message: str, 
                        channel: str = 'email', trace_id: str = None) -> Dict:
    """
    Process inbound reply from prospect
    """
    # Update state
    state.turn_count += 1
    state.last_activity_at = datetime.now()
    state.current_channel = channel
    
    # Classify intent
    intent = await classify_intent(message)
    state.last_intent = intent
    
    # Generate response based on intent
    response = await generate_response(state, message, intent)
    
    # Check if qualified (after 3-5 turns)
    if state.turn_count >= 3 and intent in ['interested', 'pricing']:
        qualification_status = 'qualified'
    elif intent == 'stop':
        qualification_status = 'not_qualified'
    else:
        qualification_status = state.qualification_status
    
    return {
        'intent': intent,
        'response': response,
        'qualification_status': qualification_status,
        'turn_count': state.turn_count
    }


async def classify_intent(message: str) -> str:
    """
    Classify prospect intent from message text
    Returns: interested, skeptical, pricing, stop, other
    """
    message_lower = message.lower()
    
    # Stop commands
    if any(word in message_lower for word in ['stop', 'unsubscribe', 'remove', 'opt out']):
        return 'stop'
    
    # Pricing questions
    if any(word in message_lower for word in ['cost', 'price', 'pricing', 'how much', 'rate', 'fee']):
        return 'pricing'
    
    # Interested signals
    if any(word in message_lower for word in ['interested', 'tell me more', 'details', 'call', 'meeting', 'yes', 'sure']):
        return 'interested'
    
    # Skeptical signals
    if any(word in message_lower for word in ['not sure', 'doubt', 'really', 'prove', 'show me', 'scam']):
        return 'skeptical'
    
    return 'other'


async def generate_response(state: ConversationState, message: str, intent: str) -> str:
    """
    Generate appropriate response based on intent
    """
    
    if intent == 'stop':
        return ("I've unsubscribed you from all future communications. "
                "You won't receive any more messages from Tenacious. "
                "Reply START if you change your mind.")
    
    elif intent == 'pricing':
        return ("Our pricing varies by engagement type and duration. "
                "Talent outsourcing typically ranges from $240K-$720K annually for a team of 3-12 engineers. "
                "Project consulting is $80K-$300K for time-boxed deliveries. "
                "Would you like me to have a delivery lead share a custom quote?")
    
    elif intent == 'interested':
        if state.turn_count <= 2:
            return ("Glad to hear you're interested! Could you share what specific engineering needs you have right now? "
                    "We have Python, Go, data, and ML engineers available.")
        else:
            return ("Perfect. I'll send you a Cal.com link to book a 15-minute discovery call with our delivery lead. "
                    "What time zone are you in? (US, Europe, or East Africa)")
    
    elif intent == 'skeptical':
        return ("I understand the skepticism. Happy to share case studies of similar companies we've worked with. "
                "What specific concerns do you have? Happy to address them directly.")
    
    else:  # other
        return ("Thanks for your reply. To better understand if we can help, could you share a bit about your current engineering capacity needs? "
                "We specialize in Python, Go, data engineering, and ML infrastructure.")