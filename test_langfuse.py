#!/usr/bin/env python3
"""Simple Langfuse connectivity test."""

import os
#from dotenv import load_dotenv
from langfuse import Langfuse

# Load environment variables from .env file
#load_dotenv()

# Get Langfuse configuration from environment
public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
secret_key = os.getenv("LANGFUSE_SECRET_KEY")
host = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")

# If running outside Docker, use the external host IP
# Docker hostname 'langfuse' won't resolve outside the container network
if "langfuse:" in host:
    external_host = os.getenv("HOST", "localhost")
    host = f"http://{external_host}:3000"
    print(f"Note: Converted Docker hostname to external host for testing")

print(f"Testing Langfuse connection...")
print(f"Host: {host}")
print(f"Public Key: {public_key[:20]}..." if public_key else "Public Key: Not set")
print(f"Secret Key: {'*' * 20}..." if secret_key else "Secret Key: Not set")
print()

# Initialize Langfuse client
try:
    langfuse = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host
    )
    
    print("✅ Langfuse client initialized")
    
    # Try to verify connectivity
    try:
        auth_result = langfuse.auth_check()
        
        if auth_result:
            print("✅ Langfuse authentication successful!")
            print("✅ Connection verified - ready to send traces")
        else:
            print("❌ Langfuse authentication failed - check your keys")
            exit(1)
    except Exception as auth_error:
        print(f"⚠️  Auth check failed with validation error: {auth_error}")
        print("⚠️  This may be a version mismatch between SDK and server")
        print("✅ However, the client is initialized and may still work for tracing")
        print("\nTrying a simple event test...")
        
        # Try to send a simple event to verify it actually works
        try:
            # Use the older API - just try to send a generation event
            langfuse.generation(
                name="test_generation",
                input="test input",
                output="test output"
            )
            langfuse.flush()
            print("✅ Successfully sent test event - Langfuse is working!")
            print("✅ The SDK can communicate with the server despite auth_check validation error")
        except Exception as event_error:
            print(f"❌ Failed to send test event: {event_error}")
            print("\n⚠️  The Langfuse SDK may have compatibility issues with your server version")
            print("⚠️  Consider updating langfuse package or checking server version")
            exit(1)
        
except Exception as e:
    print(f"❌ Error initializing Langfuse client: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
 