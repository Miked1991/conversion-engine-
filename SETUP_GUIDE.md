# Conversion Engine Setup Guide

## Overview
The Conversion Engine is an AI-powered B2B sales outreach system that automates lead enrichment, personalized email outreach, conversation handling, meeting booking, and CRM synchronization.

## Prerequisites
- Python 3.11+
- PostgreSQL (optional, for production)
- Redis (optional, for production)
- ngrok (for local webhook testing)

## Quick Start

### 1. Clone and Setup Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys
1. Copy `.env.example` to `.env`
2. Sign up for required services and add your API keys:

#### Required Services:
- **Resend** (Email): https://resend.com
  - Free tier: 100 emails/day
  - Verify your sending domain
  - Add verified email to `RESEND_FROM_EMAIL`

- **OpenRouter** (LLM): https://openrouter.ai
  - Add credits ($5-10 for testing)
  - Supports multiple models (GPT-4, Claude, etc.)

- **HubSpot** (CRM): https://developers.hubspot.com
  - Free tier available
  - Create private app for API access

#### Optional Services:
- **Langfuse** (Observability): https://langfuse.com
- **Cal.com** (Scheduling): https://cal.com
- **Africa's Talking** (SMS): https://africastalking.com

### 3. Run the Application
```bash
# Start the FastAPI server
uvicorn agent.main:app --reload --port 8000

# In another terminal, expose webhooks with ngrok
ngrok http 8000
```

### 4. Update Webhook URLs
Add your ngrok URL to `.env`:
```
WEBHOOK_BASE_URL=https://your-ngrok-id.ngrok.io
```

## API Configuration Details

### Resend (Email Service)
1. Sign up at https://resend.com
2. Add and verify your domain
3. Create API key in dashboard
4. Update `.env`:
   ```
   RESEND_API_KEY="re_xxxxx"
   RESEND_FROM_EMAIL="Sales <sales@yourdomain.com>"
   ```

### OpenRouter (LLM Provider)
1. Sign up at https://openrouter.ai
2. Add credits (minimum $5)
3. Create API key
4. Update `.env`:
   ```
   OPENROUTER_API_KEY="sk-or-v1-xxxxx"
   DEV_MODEL="openai/gpt-4-turbo-preview"
   ```

### HubSpot (CRM)
1. Create HubSpot developer account
2. Create a private app
3. Grant necessary scopes:
   - `crm.objects.contacts.read`
   - `crm.objects.contacts.write`
   - `crm.objects.companies.read`
   - `crm.objects.companies.write`
4. Copy access token to `.env`:
   ```
   HUBSPOT_ACCESS_TOKEN="pat-na1-xxxxx"
   ```

### Langfuse (Optional - Observability)
1. Sign up at https://langfuse.com
2. Create new project
3. Copy keys to `.env`:
   ```
   LANGFUSE_PUBLIC_KEY="pk-lf-xxxxx"
   LANGFUSE_SECRET_KEY="sk-lf-xxxxx"
   ```

### Cal.com (Optional - Scheduling)
1. Use cloud version or self-host
2. Create API key in settings
3. Update `.env`:
   ```
   CALCOM_API_URL="https://api.cal.com/v1"
   CALCOM_API_KEY="cal_xxxxx"
   ```

## Testing the System

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. Simulate Email Webhook
```bash
curl -X POST http://localhost:8000/webhooks/email \
  -H "Content-Type: application/json" \
  -d '{
    "from": "prospect@example.com",
    "subject": "Re: Your recent funding",
    "text": "Tell me more about your solution",
    "thread_id": "thread_123"
  }'
```

### 3. Check Logs
- Application logs in terminal
- Traces in `eval/trace_log.jsonl`
- Scores in `eval/score_log.json`

## Production Deployment

### Recommended: Deploy on Render (Free Tier)

Render is the recommended platform for your webhook backend because it:
- ✅ Supports FastAPI and Python natively
- ✅ Provides a stable public URL (no ngrok needed)
- ✅ Free tier available (no credit card required)
- ✅ Handles all webhook integrations (Resend, Africa's Talking, Cal.com, HubSpot)

#### Step 1: Prepare Your Repository
1. Create a `render.yaml` or push to GitHub
2. Create `Procfile` in root directory:
```
web: uvicorn agent.main:app --host 0.0.0.0 --port $PORT
```

3. Ensure `requirements.txt` is up to date:
```bash
pip freeze > requirements.txt
```

#### Step 2: Deploy to Render
1. Go to https://render.com
2. Sign up (free account, no credit card needed)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Configure the service:
   - **Name**: `conversion-engine-webhooks`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn agent.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
6. Click "Create Web Service"

#### Step 3: Add Environment Variables
In Render dashboard:
1. Go to your service → Environment
2. Add all variables from `.env`:
   ```
   RESEND_API_KEY=re_xxxxx
   RESEND_FROM_EMAIL=Sales <sales@yourdomain.com>
   HUBSPOT_ACCESS_TOKEN=pat-na1-xxxxx
   OPENROUTER_API_KEY=sk-or-v1-xxxxx
   LANGFUSE_PUBLIC_KEY=pk-lf-xxxxx
   LANGFUSE_SECRET_KEY=sk-lf-xxxxx
   CALCOM_API_URL=https://api.cal.com/v1
   CALCOM_API_KEY=cal_xxxxx
   AFRICA_TALKING_USERNAME=sandbox
   AFRICA_TALKING_API_KEY=atsk_xxxxx
   WEBHOOK_BASE_URL=https://your-render-url.onrender.com
   DEV_MODEL=qwen/qwen-2.5-72b-instruct
   EVAL_MODEL=anthropic/claude-3-5-sonnet
   TEMPERATURE=0.7
   MAX_COST_PER_LEAD=5.0
   DAILY_VOICE_BUDGET=3.0
   ```
3. Click "Save changes"

#### Step 4: Get Your Public URL
- Render generates: `https://your-service-name.onrender.com`
- Use this URL for all webhook configurations

#### Step 5: Register Webhooks Across All Integrations

**Resend - Email Reply Handling:**
1. Go to https://resend.com/webhooks
2. Add webhook: `https://your-service-name.onrender.com/webhooks/email`
3. Subscribe to: "email.sent", "email.delivered", "email.bounced"

**Africa's Talking - SMS Callbacks:**
1. Go to Africa's Talking dashboard → Messaging → Webhook URL
2. Set: `https://your-service-name.onrender.com/webhooks/sms`
3. Enable SMS delivery reports

**Cal.com - Booking Events:**
1. Go to Cal.com → Settings → Webhooks
2. Add: `https://your-service-name.onrender.com/webhooks/booking`
3. Subscribe to: "BOOKING_CREATED", "BOOKING_CANCELLED"

**HubSpot - (Optional) Sync Confirmations:**
1. Go to HubSpot → Settings → Webhooks
2. Add: `https://your-service-name.onrender.com/webhooks/hubspot`

#### Step 6: Monitor Logs
- View real-time logs in Render dashboard
- Monitor webhook deliveries in each provider's dashboard
- Check `eval/trace_log.jsonl` for trace history

### Alternative Deployment Options

If you prefer other platforms:

**Docker-based:**
- **Cloud Run** (Google Cloud): $0.15/million requests, no free tier for compute
- **Heroku**: Pricing changed, recommending Render instead
- **Railway**: Similar to Render, also has free tier

**Serverless:**
- **AWS Lambda**: Use Mangum adapter, pay per request
- **Vercel**: Node.js focused, less ideal for Python/FastAPI

### Production Database Setup (Optional)
For production with persistent state:
```
# Add to Render environment variables
DATABASE_URL=postgresql://user:pass@host/dbname
REDIS_URL=redis://localhost:6379

# Or use Render's managed databases
# PostgreSQL: $15/month
# Redis: $6/month
```

## Troubleshooting

### Missing API Keys
- Check logs for "Missing API keys" warnings
- System will simulate responses without keys

### Webhook Not Receiving
- Ensure ngrok is running
- Update WEBHOOK_BASE_URL in .env
- Check provider webhook configuration

### LLM Errors
- Verify OpenRouter credits
- Check model availability
- Review rate limits

## Next Steps

1. **Implement Missing Features**:
   - Complete enrichment pipeline
   - Add real LLM integration
   - Implement SMS handling
   - Complete Cal.com integration

2. **Add Monitoring**:
   - Set up Langfuse dashboards
   - Configure alerts
   - Track conversion metrics

3. **Optimize Performance**:
   - Implement caching
   - Add rate limiting
   - Optimize LLM prompts

4. **Scale Operations**:
   - Add more ICP segments
   - Expand email templates
   - Implement A/B testing
