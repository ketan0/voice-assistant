#!/usr/bin/env python3
"""
Test script to verify environment variable loading with python-dotenv
"""

import os
from dotenv import load_dotenv

def test_env_loading():
    """Test environment variable loading"""
    print("🔍 Testing environment variable loading with python-dotenv")
    print("=" * 60)
    
    # Load environment variables
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"✅ Found {env_file} file")
        load_dotenv(env_file)
    else:
        print(f"❌ No {env_file} file found")
        print(f"💡 Create one by copying .env.example to .env")
        return False
    
    # Test required variables
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API key",
        "OPENAI_PROJECT_ID": "OpenAI Project ID", 
        "OPENAI_WEBHOOK_SECRET": "OpenAI Webhook Secret",
        "TWILIO_ACCOUNT_SID": "Twilio Account SID",
        "TWILIO_AUTH_TOKEN": "Twilio Auth Token"
    }
    
    print("\n📋 Environment Variables Status:")
    print("-" * 40)
    
    all_present = True
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if value:
            # Mask sensitive values
            if len(value) > 8:
                masked_value = f"{value[:4]}...{value[-4:]}"
            else:
                masked_value = "***"
            print(f"✅ {var_name}: {masked_value}")
        else:
            print(f"❌ {var_name}: Not set")
            all_present = False
    
    # Test optional variables
    optional_vars = {
        "PORT": "Server port (default: 8000)",
        "DEBUG": "Debug mode (default: false)"
    }
    
    print("\n🔧 Optional Configuration:")
    print("-" * 30)
    
    for var_name, description in optional_vars.items():
        value = os.getenv(var_name)
        if value:
            print(f"✅ {var_name}: {value}")
        else:
            print(f"⚪ {var_name}: Using default")
    
    print("\n" + "=" * 60)
    
    if all_present:
        print("🎉 All required environment variables are set!")
        print("🚀 Ready to start the voice assistant")
        return True
    else:
        print("⚠️  Some required environment variables are missing")
        print("📝 Please update your .env file")
        return False

def show_sample_env():
    """Show a sample .env file"""
    print("\n📄 Sample .env file content:")
    print("-" * 30)
    print("""
# OpenAI Configuration
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_PROJECT_ID=proj_your-project-id
OPENAI_WEBHOOK_SECRET=your-webhook-secret

# Twilio Configuration  
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-auth-token-here

# Server Configuration (optional)
PORT=8000
DEBUG=false
""")

if __name__ == "__main__":
    success = test_env_loading()
    
    if not success:
        show_sample_env()
        print("\n💡 Copy .env.example to .env and fill in your actual values")
        exit(1)
    else:
        print("\n✨ Environment configuration test passed!")
        exit(0)