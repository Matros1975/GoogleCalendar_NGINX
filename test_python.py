#!/usr/bin/env python3
print("✅ Python is working!")
print(f"Python version: {__import__('sys').version}")
print(f"Python executable: {__import__('sys').executable}")

# Test imports
try:
    import requests
    print("✅ requests module available")
except ImportError:
    print("❌ requests module not available")

try:
    import json
    print("✅ json module available")
except ImportError:
    print("❌ json module not available")

print("🎯 Ready for MCP testing!")