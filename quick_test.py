#!/usr/bin/env python3
"""
Quick test to check remaining endpoints and get summary
"""

import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8001"
AUTH_TOKEN = None

async def test_remaining_endpoints():
    """Test remaining endpoints quickly"""
    
    # Login first
    async with aiohttp.ClientSession() as session:
        # Login
        login_data = {
            "username": "ayurveda_practitioner",
            "password": "secure123"
        }
        async with session.post(f"{BASE_URL}/api/auth/login", json=login_data) as response:
            if response.status == 200:
                data = await response.json()
                auth_token = data.get("access_token")
                headers = {"Authorization": f"Bearer {auth_token}"}
                print("✅ Authentication successful")
            else:
                print("❌ Authentication failed")
                return
        
        # Test Dashboard AI Insights
        try:
            async with session.get(f"{BASE_URL}/api/dashboard/ai-insights", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Dashboard AI Insights working")
                else:
                    print(f"❌ Dashboard AI Insights failed: {response.status}")
        except Exception as e:
            print(f"❌ Dashboard AI Insights error: {e}")
        
        # Test Dashboard Stats
        try:
            async with session.get(f"{BASE_URL}/api/dashboard/stats", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Dashboard Stats working - {data.get('available_foods', 0)} foods available")
                else:
                    print(f"❌ Dashboard Stats failed: {response.status}")
        except Exception as e:
            print(f"❌ Dashboard Stats error: {e}")

if __name__ == "__main__":
    asyncio.run(test_remaining_endpoints())