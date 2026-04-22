"""
Phase 3: Calendar Booking
Integrates with Cal.com to schedule discovery calls
"""

import os
import httpx
from datetime import datetime, timedelta
from typing import Dict, Optional


async def book_discovery_call(prospect_email: str = None, 
                              prospect_phone: str = None,
                              company_name: str = None,
                              trace_id: str = None) -> Dict:
    """
    Book discovery call via Cal.com
    """
    calcom_url = os.getenv('CALCOM_API_URL', 'http://localhost:3000')
    
    # Get available slots (next 7 days, business hours)
    slots = await get_available_slots()
    
    if not slots:
        return {
            'success': False,
            'error': 'No available slots found',
            'booking_url': None
        }
    
    # Use first available slot
    selected_slot = slots[0]
    
    # Create booking
    booking_result = await create_calcom_booking(
        email=prospect_email or prospect_phone,
        start_time=selected_slot,
        attendee_name=company_name or "Prospect"
    )
    
    return {
        'success': True,
        'booking_url': booking_result.get('booking_url'),
        'start_time': selected_slot,
        'trace_id': trace_id
    }


async def get_available_slots() -> list:
    """
    Fetch available slots from Cal.com API
    Returns list of ISO timestamps
    """
    calcom_url = os.getenv('CALCOM_API_URL', 'http://localhost:3000')
    api_key = os.getenv('CALCOM_API_KEY', 'demo-key')
    
    # For demo, return sample slots
    # In production, call Cal.com API
    now = datetime.now()
    slots = []
    
    for day in range(1, 4):  # Next 3 days
        for hour in [14, 15, 16]:  # 2PM, 3PM, 4PM
            slot_time = now + timedelta(days=day, hours=hour - now.hour, minutes=-now.minute)
            if slot_time > now:
                slots.append(slot_time.isoformat())
    
    return slots[:5]  # Return 5 slots


async def create_calcom_booking(email: str, start_time: str, attendee_name: str) -> Dict:
    """
    Create actual booking in Cal.com
    """
    calcom_url = os.getenv('CALCOM_API_URL', 'http://localhost:3000')
    api_key = os.getenv('CALCOM_API_KEY', 'demo-key')
    
    # For demo, simulate successful booking
    # In production, make real API call
    
    return {
        'booking_url': f"{calcom_url}/booking/{attendee_name.lower().replace(' ', '-')}-{datetime.now().timestamp()}",
        'booking_id': f"bk_{int(datetime.now().timestamp())}",
        'start_time': start_time,
        'attendees': [email]
    }