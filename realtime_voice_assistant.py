"""
Twilio-OpenAI Realtime Voice Assistant Backend

This application integrates Twilio with OpenAI's Realtime API to create a phone-based voice assistant.
The flow is: Phone Call → Twilio → OpenAI SIP → Webhook → WebSocket Real-time Conversation
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional

import requests
import websockets
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import Response, JSONResponse
from contextlib import asynccontextmanager
from openai import OpenAI, InvalidWebhookSignatureError
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call import Function
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse
import uvicorn
from dotenv import load_dotenv
import composio
from composio import Composio

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store active WebSocket connections
active_connections: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for FastAPI"""
    # Startup
    logger.info("Starting Twilio-OpenAI Realtime Voice Assistant")
    
    # Validate environment variables with helpful messages
    required_vars = {
        "OPENAI_API_KEY": "Get this from https://platform.openai.com/api-keys",
        "OPENAI_PROJECT_ID": "Find this in your OpenAI project settings (starts with 'proj_')",
        "OPENAI_WEBHOOK_SECRET": "Set this up in your OpenAI webhook configuration",
        "TWILIO_ACCOUNT_SID": "Get this from your Twilio Console (starts with 'AC')",
        "TWILIO_AUTH_TOKEN": "Get this from your Twilio Console"
    }
    
    # Optional environment variables
    optional_vars = {
        "COMPOSIO_API_KEY": "Get this from https://app.composio.dev for tool calling"
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"  ❌ {var}: {description}")
        else:
            # Mask sensitive values in logs
            value = os.getenv(var)
            if len(value) > 8:
                masked_value = f"{value[:4]}...{value[-4:]}"
            else:
                masked_value = "***"
            logger.info(f"✅ {var}: {masked_value}")
    
    if missing_vars:
        logger.error("❌ Missing required environment variables:")
        for var_info in missing_vars:
            logger.error(var_info)
        logger.error("💡 Please create a .env file with the required variables")
        logger.error("📝 You can copy .env.example and fill in your values")
        raise RuntimeError("Missing required environment variables")
    
    # Check optional variables
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            masked_value = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
            logger.info(f"✅ {var}: {masked_value}")
        else:
            logger.info(f"⚪ {var}: Not set (optional) - {description}")
    
    logger.info("🎉 All environment variables configured correctly!")
    logger.info(f"🔧 Tool calling {'enabled' if composio_tools else 'disabled'}")
    yield
    
    # Shutdown
    logger.info("Shutting down voice assistant")
    # Close any remaining WebSocket connections
    for call_id, connection in active_connections.items():
        try:
            if hasattr(connection, 'close'):
                await connection.close()
        except Exception as e:
            logger.error(f"Error closing connection for call {call_id}: {e}")
    active_connections.clear()

app = FastAPI(
    title="Twilio-OpenAI Realtime Voice Assistant",
    description="Phone-based voice assistant using Twilio and OpenAI's Realtime API",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize clients
openai_client = OpenAI(
    webhook_secret=os.environ.get("OPENAI_WEBHOOK_SECRET")
)

twilio_client = TwilioClient(
    os.environ.get("TWILIO_ACCOUNT_SID"),
    os.environ.get("TWILIO_AUTH_TOKEN")
)

# Initialize Composio
composio_client = Composio()

# Get tools from Composio
composio_tools = []
try:
    if os.getenv("COMPOSIO_API_KEY"):
        composio_tools = composio_client.tools.get(
            user_id=os.environ.get("COMPOSIO_USER_ID"), 
            toolkits=["GMAIL"]
        )
        logger.info(f"Loaded {len(composio_tools)} Composio tools")
    else:
        logger.warning("COMPOSIO_API_KEY not set, tool calling disabled")
except Exception as e:
    logger.error(f"Failed to load Composio tools: {e}")
    composio_tools = []

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")

AUTH_HEADER = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json"
}

# Configuration for OpenAI Realtime API (without tools)
CALL_ACCEPT_CONFIG = {
    "type": "realtime",
    "instructions": """You are a helpful voice assistant. You can:
    - Answer questions and provide information
    - Help with tasks and planning
    - Have natural conversations
    - Transfer calls if needed
    - Use tools to help with tasks when available
    
    Be conversational, friendly, and concise in your responses.""",
    "model": "gpt-realtime",
    # "voice": "alloy",
    # "turn_detection": {
    #     "type": "server_vad",
    #     "threshold": 0.5,
    #     "prefix_padding_ms": 300,
    #     "silence_duration_ms": 200
    # },
    # "input_audio_format": "pcm16",
    # "output_audio_format": "pcm16",
    # "input_audio_transcription": {
    #     "model": "whisper-1"
    # }
}

# Initial response to greet callers
GREETING_RESPONSE = {
    "type": "response.create",
    "response": {
        "instructions": (
            "Greet the caller warmly and ask how you can help them today. "
            "Keep it brief and natural."
        )
    }
}


def convert_composio_tools_to_realtime_format(composio_tools):
    """Convert Composio tools to Realtime API format"""
    realtime_tools = []
    for tool in composio_tools:
        if isinstance(tool, dict) and "function" in tool:
            realtime_tool = {
                "type": "function",
                "name": tool["function"].get("name"),
                "description": tool["function"].get("description", ""),
                "parameters": tool["function"].get("parameters", {})
            }
            realtime_tools.append(realtime_tool)
    return realtime_tools


async def handle_websocket_connection(call_id: str):
    """Handle WebSocket connection for a specific call"""
    websocket_url = f"wss://api.openai.com/v1/realtime?call_id={call_id}"
    
    try:
        logger.info(f"Connecting to WebSocket for call {call_id}")
        
        async with websockets.connect(
            websocket_url,
            additional_headers=AUTH_HEADER,
        ) as websocket:
            
            # Store the connection
            active_connections[call_id] = websocket
            # Send session update with tools if available
            logger.info(f"Sending session.update with {len(composio_tools)} tools")
            if composio_tools:
                logger.info(f"Converting {len(composio_tools)} Composio tools to Realtime API format")
                realtime_tools = convert_composio_tools_to_realtime_format(composio_tools)
                session_update = {
                    "type": "session.update",
                    "session": {
                        "type": "realtime",
                        "tools": realtime_tools,
                        "tool_choice": "auto"
                    }
                }
                await websocket.send(json.dumps(session_update))
                logger.info(f"Sent session.update with {len(realtime_tools)} tools")
            
            # Send initial greeting
            await websocket.send(json.dumps(GREETING_RESPONSE))
            logger.info(f"Sent greeting for call {call_id}")
            
            # Listen for messages
            while True:
                try:
                    message = await websocket.recv()
                    event = json.loads(message)
                    
                    logger.info(f"Call {call_id} - Event: {event.get('type', 'unknown')}")
                    
                    # Handle different event types
                    await handle_realtime_event(call_id, event)
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.info(f"WebSocket connection closed for call {call_id}")
                    break
                except Exception as e:
                    logger.error(f"Error processing WebSocket message for call {call_id}: {e}")
                    
    except Exception as e:
        logger.error(f"WebSocket connection error for call {call_id}: {e}")
    finally:
        # Clean up
        if call_id in active_connections:
            del active_connections[call_id]
        logger.info(f"Cleaned up connection for call {call_id}")


async def handle_realtime_event(call_id: str, event: Dict[str, Any]):
    """Handle different types of events from the Realtime API"""
    event_type = event.get("type")
    
    if event_type == "conversation.item.created":
        # Log conversation items
        item = event.get("item", {})
        if item.get("type") == "message":
            content = item.get("content", [])
            for content_part in content:
                if content_part.get("type") == "input_text":
                    logger.info(f"Call {call_id} - User said: {content_part.get('text', '')}")
                elif content_part.get("type") == "text":
                    logger.info(f"Call {call_id} - Assistant said: {content_part.get('text', '')}")
    
    elif event_type == "response.audio_transcript.delta":
        # Log assistant speech in real-time
        delta = event.get("delta", "")
        if delta:
            logger.info(f"Call {call_id} - Assistant speaking: {delta}")
    
    elif event_type == "input_audio_buffer.speech_started":
        logger.info(f"Call {call_id} - User started speaking")
    
    elif event_type == "input_audio_buffer.speech_stopped":
        logger.info(f"Call {call_id} - User stopped speaking")
    
    elif event_type == "response.function_call_arguments.done":
        # Handle function call completion
        await handle_function_call(call_id, event)
    
    elif event_type == "error":
        error = event.get("error", {})
        logger.error(f"Call {call_id} - Realtime API error: {error}")


async def handle_function_call(call_id: str, event: Dict[str, Any]):
    """Handle function call events from Realtime API"""
    try:
        # Extract function call details
        call_id_event = event.get("call_id")
        name = event.get("name", "")
        arguments = event.get("arguments", "{}")
        
        logger.info(f"Call {call_id} - Function call: {name} with args: {arguments}")
        
        # Only execute if we have tools available
        if not composio_tools:
            logger.warning(f"Call {call_id} - Function call {name} requested but no tools available")
            return
        
        # Create a proper OpenAI ChatCompletion response for Composio
        tool_call = ChatCompletionMessageToolCall(
            id=call_id_event or f"call_{call_id}",
            type="function",
            function=Function(
                name=name,
                arguments=arguments
            )
        )
        
        message = ChatCompletionMessage(
            role="assistant",
            content=None,
            tool_calls=[tool_call]
        )
        
        choice = Choice(
            finish_reason="tool_calls",
            index=0,
            message=message
        )
        
        chat_completion = ChatCompletion(
            id=f"chatcmpl_{call_id}",
            choices=[choice],
            created=int(asyncio.get_event_loop().time()),
            model="gpt-realtime",
            object="chat.completion"
        )
        
        # Execute the function call via Composio
        result = composio_client.provider.handle_tool_calls(
            user_id=HARDCODED_USER_ID,
            response=chat_completion
        )
        
        logger.info(f"Call {call_id} - Function result: {result}")
        
        # Send the result back through WebSocket
        if call_id in active_connections:
            websocket = active_connections[call_id]
            result_message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id_event,
                    "output": json.dumps(result) if result else "Function executed successfully"
                }
            }
            await websocket.send(json.dumps(result_message))
            logger.info(f"Call {call_id} - Sent function result back to WebSocket")
        
    except Exception as e:
        logger.error(f"Call {call_id} - Error handling function call: {e}")
        # Send error back through WebSocket
        if call_id in active_connections:
            websocket = active_connections[call_id]
            error_message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": event.get("call_id"),
                    "output": f"Error executing function: {str(e)}"
                }
            }
            try:
                await websocket.send(json.dumps(error_message))
            except Exception as send_error:
                logger.error(f"Call {call_id} - Failed to send error message: {send_error}")


@app.post("/webhook/twilio")
async def twilio_webhook(
    request: Request,
    From: str = Form(...),
    To: str = Form(...),
    CallSid: str = Form(...),
    CallStatus: str = Form(None),
    Direction: str = Form(None)
):
    """Handle incoming calls from Twilio and route them to OpenAI"""
    try:
        logger.info(f"Twilio call from {From} to {To}, CallSid: {CallSid}")
        
        # Create TwiML response to redirect to OpenAI SIP
        response = VoiceResponse()
        
        # Route the call to OpenAI's SIP endpoint
        sip_uri = f"sip:{OPENAI_PROJECT_ID}@sip.api.openai.com;transport=tls"
        response.dial(sip_uri)
        
        logger.info(f"Routing call {CallSid} to OpenAI SIP: {sip_uri}")
        
        return Response(content=str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error handling Twilio webhook: {e}")
        response = VoiceResponse()
        response.say("Sorry, there was an error processing your call. Please try again later.")
        return Response(content=str(response), media_type="application/xml")


@app.post("/webhook/openai")
async def openai_webhook(request: Request):
    """Handle incoming call events from OpenAI Realtime API"""
    try:
        # Get raw body and headers
        body = await request.body()
        headers = dict(request.headers)
        
        # Verify webhook signature
        event = openai_client.webhooks.unwrap(body, headers)
        
        if event.type == "realtime.call.incoming":
            call_id = event.data.call_id
            logger.info(f"Incoming OpenAI call: {call_id}")
            
            # Accept the call
            accept_url = f"https://api.openai.com/v1/realtime/calls/{call_id}/accept"
            
            response = requests.post(
                accept_url,
                headers=AUTH_HEADER,
                json=CALL_ACCEPT_CONFIG
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully accepted call {call_id}")
                
                # Start WebSocket connection as async task
                asyncio.create_task(handle_websocket_connection(call_id))
                
            else:
                logger.error(f"Failed to accept call {call_id}: {response.text}")
            
            return Response(status_code=200)
            
        else:
            logger.info(f"Received OpenAI event: {event.type}")
            return Response(status_code=200)
            
    except InvalidWebhookSignatureError as e:
        logger.error(f"Invalid webhook signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error handling OpenAI webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


@app.post("/call/{call_id}/refer")
async def refer_call(call_id: str, request: Request):
    """Redirect a call to another number"""
    try:
        data = await request.json()
        target_uri = data.get("target_uri")
        
        if not target_uri:
            raise HTTPException(status_code=400, detail="target_uri is required")
        
        refer_url = f"https://api.openai.com/v1/realtime/calls/{call_id}/refer"
        
        response = requests.post(
            refer_url,
            headers=AUTH_HEADER,
            json={"target_uri": target_uri}
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully referred call {call_id} to {target_uri}")
            return {"success": True}
        else:
            logger.error(f"Failed to refer call {call_id}: {response.text}")
            raise HTTPException(status_code=500, detail="Failed to refer call")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error referring call {call_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


@app.post("/call/{call_id}/reject")
async def reject_call(call_id: str):
    """Reject an incoming call"""
    try:
        reject_url = f"https://api.openai.com/v1/realtime/calls/{call_id}/reject"
        
        response = requests.post(reject_url, headers=AUTH_HEADER)
        
        if response.status_code == 200:
            logger.info(f"Successfully rejected call {call_id}")
            return {"success": True}
        else:
            logger.error(f"Failed to reject call {call_id}: {response.text}")
            raise HTTPException(status_code=500, detail="Failed to reject call")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting call {call_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


@app.get("/status")
async def status():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_calls": len(active_connections),
        "openai_configured": bool(OPENAI_API_KEY and OPENAI_PROJECT_ID),
        "twilio_configured": bool(os.environ.get("TWILIO_ACCOUNT_SID"))
    }


@app.get("/calls")
async def list_calls():
    """List active calls"""
    return {
        "active_calls": list(active_connections.keys())
    }


if __name__ == "__main__":
    # Environment validation is now handled in the lifespan function
    # which provides better error messages and startup validation
    
    # Run the FastAPI app with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="info" if os.getenv("DEBUG", "False").lower() != "true" else "debug"
    )