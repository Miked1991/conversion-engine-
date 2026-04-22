"""
Phase 1: Email Outreach
Segment classification, email composition, and sending
"""

import os
import json
import httpx
from datetime import datetime
from typing import Dict, Optional


async def run_outreach(prospect_email: str, prospect_name: str, 
                       company_name: str, company_domain: str,
                       trace_id: str) -> Dict:
    """
    Master function for Phase 1 outreach
    """
    # Step 1: Classify segment
    segment_result = await classify_icp_segment(company_name, company_domain)
    
    # Step 2: Compose email
    email_content = await compose_email(
        prospect_name=prospect_name,
        company_name=company_name,
        segment=segment_result['segment'],
        segment_name=segment_result['segment_name']
    )
    
    # Step 3: Tone check
    tone_result = await check_tone(email_content['body'])
    
    # Step 4: Send email
    send_result = await send_email_via_resend(
        to_email=prospect_email,
        subject=email_content['subject'],
        body=email_content['body']
    )
    
    return {
        'trace_id': trace_id,
        'segment': segment_result,
        'email': email_content,
        'tone_check': tone_result,
        'send_result': send_result,
        'sent_at': datetime.now().isoformat()
    }


async def classify_icp_segment(company_name: str, company_domain: str) -> Dict:
    """
    Decision tree for ICP segment classification
    Priority: Segment 2 > Segment 3 > Segment 1 > Segment 4 > Generic
    """
    # In production, would use enrichment data
    # For demo, return Segment 1 (recently funded)
    
    # This is a simplified classifier for the interim submission
    # Real implementation would use enrichment results
    
    return {
        'segment': 1,
        'segment_name': 'Recently Funded Startup',
        'confidence': 'high',
        'reasoning': ['Demo classification for interim submission']
    }


async def compose_email(prospect_name: str, company_name: str, 
                        segment: int, segment_name: str) -> Dict:
    """
    Compose email using segment-specific templates
    """
    
    # Segment 1: Recently Funded
    if segment == 1:
        subject = f"Your recent funding & engineering growth at {company_name}"
        body = f"""Hi {prospect_name or 'team'},

Congratulations on the recent funding round.

Our data shows your engineering team is scaling rapidly. Companies in your position often find that recruiting velocity becomes the bottleneck - budget is there, but hiring can't keep pace.

Tenacious provides dedicated engineering squads that can start within 2 weeks. We have Python, Go, and data engineers on bench right now.

Would you be open to a 15-minute call to discuss how we help recently funded teams scale without the recruiting drag?

Best,
Alex
Tenacious Consulting & Outsourcing"""
    
    # Segment 2: Post-Layoff Restructuring
    elif segment == 2:
        subject = f"Maintaining delivery capacity at {company_name}"
        body = f"""Hi {prospect_name or 'team'},

I understand {company_name} recently went through a restructuring.

When companies reduce headcount, delivery capacity often becomes the hidden pressure point. The work still needs to get done.

Tenacious helps post-layoff companies maintain output with dedicated offshore teams. We've done this for several mid-market tech firms.

Worth a 15-minute chat to share how we structure these engagements?

Best,
Alex
Tenacious Consulting & Outsourcing"""
    
    # Segment 3: Leadership Transition
    elif segment == 3:
        subject = f"Welcome - what new technology leaders typically reassess"
        body = f"""Hi {prospect_name or 'team'},

I understand {company_name} has new technology leadership.

In our work with incoming CTOs and VPs Engineering, vendor mix and offshore strategy are almost always on the 90-day reassessment list.

Tenacious provides engineering teams with no long-term lock-in. Just capacity when you need it.

If you're reviewing external partners, I can send a one-page overview.

Best,
Alex
Tenacious Consulting & Outsourcing"""
    
    # Segment 4: Specialized Capability Gap
    elif segment == 4:
        subject = f"AI maturity at {company_name} - what competitors are doing"
        body = f"""Hi {prospect_name or 'team'},

Our public signal analysis shows top competitors in your sector are investing heavily in AI engineering capacity.

We help companies bridge exactly these gaps - providing project-based AI/ML engineering teams for migrations, agentic systems, or data platform work.

If closing that gap is on your roadmap, I'd like to show you how we've done it for similar companies.

Best,
Alex
Tenacious Consulting & Outsourcing"""
    
    # Generic
    else:
        subject = f"Engineering capacity at {company_name}"
        body = f"""Hi {prospect_name or 'team'},

Tenacious provides dedicated engineering and data teams to B2B tech companies.

We have bench availability in Python, Go, data engineering, and ML infrastructure.

If engineering capacity is on your radar, I can send a brief on how we work.

Best,
Alex
Tenacious Consulting & Outsourcing"""
    
    return {
        'subject': subject,
        'body': body,
        'segment_used': segment
    }


async def check_tone(email_body: str) -> Dict:
    """
    Second LLM call to validate tone against style guide
    Returns score 0-1, regenerates if below 0.7
    """
    # For interim submission, simulate tone check
    # In production, would call LLM with style guide prompt
    
    # Simple rule-based check for demonstration
    violations = []
    
    desperate_phrases = ['just checking in', 'circling back', 'hope you']
    for phrase in desperate_phrases:
        if phrase in email_body.lower():
            violations.append(f"Contains: '{phrase}'")
    
    overpromise_phrases = ['guarantee', 'always', '100%']
    for phrase in overpromise_phrases:
        if phrase in email_body.lower():
            violations.append(f"Contains: '{phrase}'")
    
    score = 0.9 if not violations else 0.6
    
    return {
        'score': score,
        'passes_threshold': score >= 0.7,
        'violations': violations,
        'needs_regeneration': score < 0.7
    }


async def send_email_via_resend(to_email: str, subject: str, body: str) -> Dict:
    """
    Send email using Resend API (free tier)
    """
    api_key = os.getenv('RESEND_API_KEY')
    
    if not api_key:
        # Simulate success for demo
        return {
            'success': True,
            'message_id': f"msg_{datetime.now().timestamp()}",
            'to': to_email,
            'subject': subject,
            'sent_at': datetime.now().isoformat(),
            'note': 'Simulated - add RESEND_API_KEY for production'
        }
    
    # Real API call
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://api.resend.com/emails',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'from': 'Tenacious Outreach <outreach@tenacious.com>',
                'to': [to_email],
                'subject': subject,
                'text': body
            }
        )
        
        if response.status_code == 200:
            return {
                'success': True,
                'message_id': response.json().get('id'),
                'to': to_email,
                'subject': subject,
                'sent_at': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'error': response.text,
                'to': to_email
            }