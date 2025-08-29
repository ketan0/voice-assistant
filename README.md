# Twilio-OpenAI Realtime Voice Assistant

A high-performance phone-based voice assistant built with FastAPI that integrates Twilio with OpenAI's Realtime API to enable natural voice conversations over traditional phone calls.

## How It Works

1. **Phone Call** → Caller dials your Twilio phone number
2. **Twilio** → Routes the call via SIP to OpenAI's endpoint
3. **OpenAI SIP** → Triggers webhook to your backend
4. **Backend** → Accepts the call and establishes WebSocket connection
5. **Real-time Conversation** → Natural voice interaction with OpenAI's assistant

## Setup Instructions

### 1. OpenAI Configuration

1. Go to [platform.openai.com](https://platform.openai.com)
2. Create a new project or use existing one
3. Note your Project ID (starts with `proj_`)
4. Generate an API key
5. Set up a webhook endpoint for realtime calls:
   - URL: `https://your-domain.com/webhook/openai`
   - Events: `realtime.call.incoming`

### 2. Twilio Configuration

1. Sign up for [Twilio](https://www.twilio.com)
2. Purchase a phone number
3. Configure the phone number webhook:
   - Webhook URL: `https://your-domain.com/webhook/twilio`
   - HTTP Method: POST

### 3. Environment Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Fill in your credentials:
   ```bash
   # OpenAI
   OPENAI_API_KEY=sk-your-key-here
   OPENAI_PROJECT_ID=proj_your-project-id
   OPENAI_WEBHOOK_SECRET=your-webhook-secret
   
   # Twilio
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your-auth-token
   ```

### 4. Install Dependencies

Using uv (recommended):
```bash
uv sync
```

Or with pip:
```bash
pip install -r requirements.txt
```

### 5. Run the Application

Development:
```bash
# Using the provided script (recommended)
./run.sh

# Or directly with uv
uv run python realtime_voice_assistant.py

# Or with uvicorn directly
uv run uvicorn realtime_voice_assistant:app --reload
```

Production with Uvicorn:
```bash
uv run uvicorn realtime_voice_assistant:app --host 0.0.0.0 --port 8000 --workers 4
```

Alternative production with Gunicorn:
```bash
uv run gunicorn realtime_voice_assistant:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Deployment

### Using ngrok for Testing

For local development, use ngrok to expose your local server:

```bash
# Install ngrok
npm install -g ngrok

# Expose local server
ngrok http 8000
```

Use the ngrok URLs for your webhook endpoints:
- OpenAI webhook: `https://abc123.ngrok.io/webhook/openai`
- Twilio webhook: `https://abc123.ngrok.io/webhook/twilio`

### Production Deployment

Deploy to any cloud platform (Heroku, Railway, DigitalOcean, etc.):

1. Set environment variables on your platform
2. Ensure your domain has SSL/TLS (required for webhooks)
3. Update webhook URLs to use your production domain
4. Scale appropriately for expected call volume

## API Endpoints

FastAPI provides automatic interactive API documentation:
- **Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)

### Available Endpoints:
- `GET /status` - Health check and configuration status
- `GET /calls` - List active calls
- `POST /webhook/twilio` - Twilio call webhook (accepts form data)
- `POST /webhook/openai` - OpenAI realtime webhook (accepts JSON)
- `POST /call/{call_id}/refer` - Transfer call to another number
- `POST /call/{call_id}/reject` - Reject an incoming call

## Configuration Options

### Assistant Personality

Modify the `CALL_ACCEPT_CONFIG` in `realtime_voice_assistant.py`:

```python
CALL_ACCEPT_CONFIG = {
    "type": "realtime",
    "instructions": "Your custom assistant instructions here...",
    "model": "gpt-4o-realtime-preview-2024-12-17",
    "voice": "alloy",  # Options: alloy, echo, fable, onyx, nova, shimmer
    # ... other config options
}
```

### Voice Options

Available voice options:
- `alloy` - Balanced, neutral
- `echo` - Male voice
- `fable` - British accent
- `onyx` - Deep, male voice
- `nova` - Female voice
- `shimmer` - Soft, female voice

## Troubleshooting

### Common Issues

1. **Webhook signature validation fails**
   - Verify `OPENAI_WEBHOOK_SECRET` is correct
   - Ensure webhook URL is accessible and using HTTPS

2. **Twilio call doesn't connect**
   - Check Twilio webhook URL configuration
   - Verify phone number is configured correctly
   - Check server logs for errors

3. **WebSocket connection fails**
   - Ensure `OPENAI_API_KEY` has proper permissions
   - Check network connectivity to OpenAI's servers
   - Verify project ID is correct

### Logs

The application logs important events:
- Incoming calls and routing
- WebSocket connection status
- Real-time conversation events
- Errors and warnings

Monitor logs for debugging:
```bash
tail -f app.log
```

## Features

- ✅ **High-performance FastAPI backend** with async support
- ✅ **Automatic API documentation** (Swagger UI + ReDoc)
- ✅ **Real-time voice conversations** with OpenAI's latest models
- ✅ **Natural language processing** and understanding
- ✅ **Call transfer/referral support** during conversations
- ✅ **Multiple voice options** (6 different voices)
- ✅ **Comprehensive conversation logging** and monitoring
- ✅ **Health monitoring endpoints** with detailed status
- ✅ **Robust error handling** and recovery
- ✅ **Production-ready** with proper async handling

## Security Considerations

- Always use HTTPS for webhook endpoints
- Validate webhook signatures
- Keep API keys secure and rotate regularly
- Monitor for unusual call patterns
- Implement rate limiting for production use

## Support

For issues and questions:
1. **Check the interactive API docs** at `http://localhost:8000/docs`
2. **Review server logs** for error messages and debugging info
3. **Verify environment variables** are set correctly in your `.env` file
4. **Test webhook endpoints** using the provided test script: `python test_webhooks.py`
5. **Check service status** at OpenAI and Twilio status pages
6. **Use the `/status` endpoint** to verify configuration health

### FastAPI Advantages:
- **Better async performance** for handling multiple concurrent calls
- **Automatic request validation** and error responses
- **Interactive API documentation** for easy testing and debugging
- **Type hints and Pydantic models** for better code quality
- **WebSocket support** natively built-in for real-time features