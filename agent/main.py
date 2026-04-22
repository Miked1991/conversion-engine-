"""
Main orchestrator for The Conversion Engine
Acts as the central router for all incoming messages
"""

import os
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import all services
from agent.enrichment_pipeline import enrich_prospect
from agent.email_outreach import run_outreach
from agent.conversation_handler import process_reply, ConversationState
from agent.booking_handler import book_discovery_call
from agent.hubspot_sync import sync_to_hubspot
from agent.langfuse_logger import log_trace, get_logger

# Initialize FastAPI
app = FastAPI(title="Conversion Engine", version="1.0.0")

# Global state store (in production, use Redis)
conversation_states = {}

# Logger
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Conversion Engine starting up...")
    
    # Verify all API keys are present
    required_keys = ['RESEND_API_KEY', 'HUBSPOT_ACCESS_TOKEN']
    missing = [k for k in required_keys if not os.getenv(k)]
    if missing:
        logger.warning(f"Missing API keys: {missing}")
    
    yield
    
    logger.info("Conversion Engine shutting down...")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    """API root - returns information about the Conversion Engine"""
    return {
        "name": "Conversion Engine",
        "version": "1.0.0",
        "description": "Central router for all incoming messages and prospect lifecycle management",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "webhooks": "/webhooks/email"
        }
    }


@app.get("/health")
async def health_check():
    """Liveness probe for orchestrator"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_conversations": len(conversation_states)
    }


@app.post("/webhooks/email")
async def handle_email_webhook(request: Request):
    """
    Receive email replies from Resend/MailerSend
    """
    try:
        body = await request.json()
        logger.info(f"Received email webhook: {body.get('message_id', 'unknown')}")
        
        # Extract prospect info
        prospect_email = body.get('from')
        subject = body.get('subject', '')
        message_text = body.get('text', '')
        thread_id = body.get('thread_id', str(uuid.uuid4()))
        
        # Generate or retrieve trace ID
        trace_id = str(uuid.uuid4())
        
        # Check if this is a new conversation
        state_key = f"conv:{prospect_email}"
        
        if state_key not in conversation_states:
            # New conversation - need enrichment first
            logger.info(f"New conversation from {prospect_email}")
            
            # Run enrichment (Phase 0)
            enrichment_result = await enrich_prospect(
                company_name=extract_company_from_email(prospect_email),
                company_domain=extract_domain_from_email(prospect_email)
            )
            
            # Create new conversation state
            state = ConversationState(
                trace_id=trace_id,
                prospect_email=prospect_email,
                company_name=enrichment_result.get('company_name'),
                current_channel='email',
                turn_count=0,
                qualification_status='pending'
            )
            conversation_states[state_key] = state
            
            # Send first email (Phase 1)
            outreach_result = await run_outreach(
                prospect_email=prospect_email,
                prospect_name=extract_name_from_email(prospect_email),
                company_name=enrichment_result.get('company_name'),
                company_domain=enrichment_result.get('company_domain'),
                trace_id=trace_id
            )
            
            # Log to Langfuse
            await log_trace(trace_id, 'email_sent', outreach_result)
            
            return {"status": "first_email_sent", "trace_id": trace_id}
        
        else:
            # Existing conversation - process reply
            state = conversation_states[state_key]
            
            # Process the reply (Phase 2)
            reply_result = await process_reply(
                state=state,
                message=message_text,
                trace_id=state.trace_id
            )
            
            # If qualified, book call (Phase 3)
            if reply_result.get('qualification_status') == 'qualified':
                booking_result = await book_discovery_call(
                    prospect_email=prospect_email,
                    company_name=state.company_name,
                    trace_id=state.trace_id
                )
                
                # Sync to HubSpot (Phase 4)
                await sync_to_hubspot(
                    contact_email=prospect_email,
                    company_name=state.company_name,
                    segment=state.icp_segment,
                    ai_score=state.ai_maturity_score,
                    meeting_booked=True,
                    meeting_url=booking_result.get('booking_url'),
                    trace_id=state.trace_id
                )
                
                # Update state
                state.qualification_status = 'booked'
                conversation_states[state_key] = state
                
                return {"status": "booked", "booking_url": booking_result.get('booking_url')}
            
            # Log to Langfuse
            await log_trace(state.trace_id, 'reply_processed', reply_result)
            
            return {"status": "reply_processed", "trace_id": state.trace_id}
    
    except Exception as e:
        logger.error(f"Error processing email webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/sms")
async def handle_sms_webhook(request: Request):
    """
    Receive SMS from Africa's Talking sandbox
    Only for warm leads who have already replied to email
    """
    try:
        body = await request.json()
        logger.info(f"Received SMS webhook: {body.get('id', 'unknown')}")
        
        # Extract prospect info
        prospect_phone = body.get('from')
        message_text = body.get('text', '')
        
        # Check for STOP command
        if message_text.upper().strip() in ['STOP', 'UNSUBSCRIBE', 'STOPALL']:
            # Remove from conversation states
            state_key = f"conv:{prospect_phone}"
            if state_key in conversation_states:
                del conversation_states[state_key]
            
            # Log opt-out to HubSpot
            await sync_to_hubspot(
                contact_email=None,
                company_name=None,
                segment=None,
                ai_score=None,
                meeting_booked=False,
                opt_out=True,
                trace_id=str(uuid.uuid4())
            )
            
            return {"status": "unsubscribed"}
        
        # Find existing conversation by phone number
        state_key = f"conv:{prospect_phone}"
        
        if state_key not in conversation_states:
            return {"status": "no_active_conversation", "message": "Please reply to email first"}
        
        state = conversation_states[state_key]
        
        # Process SMS reply (same as email)
        reply_result = await process_reply(
            state=state,
            message=message_text,
            channel='sms',
            trace_id=state.trace_id
        )
        
        # If qualified, book call
        if reply_result.get('qualification_status') == 'qualified':
            booking_result = await book_discovery_call(
                prospect_phone=prospect_phone,
                company_name=state.company_name,
                trace_id=state.trace_id
            )
            
            await sync_to_hubspot(
                contact_phone=prospect_phone,
                company_name=state.company_name,
                meeting_booked=True,
                meeting_url=booking_result.get('booking_url'),
                trace_id=state.trace_id
            )
        
        await log_trace(state.trace_id, 'sms_reply_processed', reply_result)
        
        return {"status": "sms_processed", "trace_id": state.trace_id}
    
    except Exception as e:
        logger.error(f"Error processing SMS webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def extract_company_from_email(email: str) -> str:
    """Extract company name from email domain"""
    domain = email.split('@')[-1]
    # Remove .com, .io, etc.
    company = domain.split('.')[0]
    return company.capitalize()


def extract_domain_from_email(email: str) -> str:
    """Extract domain from email"""
    return email.split('@')[-1]


def extract_name_from_email(email: str) -> str:
    """Extract first name from email local part"""
    local = email.split('@')[0]
    # Handle dot separators
    parts = local.replace('.', ' ').split()
    return parts[0].capitalize() if parts else "Team"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)