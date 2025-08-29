#!/usr/bin/env python3
"""
Debug script to explore Composio tools format and structure
"""

import os
import json
from dotenv import load_dotenv
from composio import Composio

# Load environment variables
load_dotenv()

def main():
    print("🔧 Composio Tools Debug Script")
    print("=" * 50)
    
    # Check if API key is available
    api_key = os.getenv("COMPOSIO_API_KEY")
    if not api_key:
        print("❌ COMPOSIO_API_KEY not found in environment")
        print("💡 Please add COMPOSIO_API_KEY to your .env file")
        return
    
    print(f"✅ Found COMPOSIO_API_KEY: {api_key[:10]}...")
    
    # Initialize Composio
    try:
        composio = Composio()
        print("✅ Composio client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Composio: {e}")
        return
    
    # Test user ID (must be UUID format)
    user_id = "00000000-0000-0000-0000-000000000000"
    
    # Test different toolkits
    toolkits_to_test = [
        ["GMAIL"]
    ]
    
    for toolkit_list in toolkits_to_test:
        print(f"\n📋 Testing toolkit: {toolkit_list}")
        print("-" * 30)
        
        try:
            tools = composio.tools.get(user_id=user_id, toolkits=toolkit_list)
            
            print(f"✅ Retrieved {len(tools)} tools")
            print(f"📊 Tools type: {type(tools)}")
            
            if tools:
                # Print first tool structure
                first_tool = tools[0]
                print(f"\n🔍 First tool structure:")
                print(f"Type: {type(first_tool)}")
                print(f"Keys: {list(first_tool.keys()) if isinstance(first_tool, dict) else 'Not a dict'}")
                
                # Pretty print the first tool
                print(f"\n📄 First tool content:")
                print(json.dumps(first_tool, indent=2, default=str))
                
                # Print summary of all tools
                print(f"\n📝 All tools summary:")
                for i, tool in enumerate(tools[:5]):  # First 5 tools only
                    if isinstance(tool, dict):
                        name = tool.get('function', {}).get('name', tool.get('name', 'Unknown'))
                        description = tool.get('function', {}).get('description', tool.get('description', 'No description'))
                        print(f"  {i+1}. {name}: {description[:60]}...")
                    else:
                        print(f"  {i+1}. {tool}")
                
                if len(tools) > 5:
                    print(f"  ... and {len(tools) - 5} more tools")
                    
            else:
                print("⚠️ No tools returned")
                
        except Exception as e:
            print(f"❌ Error retrieving tools for {toolkit_list}: {e}")
            print(f"Error type: {type(e)}")
    
    print(f"\n🎯 Complete tools dump for github + slack:")
    print("=" * 60)
    try:
        tools = composio.tools.get(user_id=user_id, toolkits=["github", "slack"])
        print(json.dumps(tools, indent=2, default=str))
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()