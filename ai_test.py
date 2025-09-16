#!/usr/bin/env python3
"""
Test AI analysis endpoint specifically
"""

import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8001"

async def test_ai_analysis():
    """Test AI analysis endpoint"""
    
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
        
        # Get a food item first
        async with session.get(f"{BASE_URL}/api/foods/search", params={"query": "rice", "limit": 1}, headers=headers) as response:
            if response.status == 200:
                foods = await response.json()
                if foods:
                    food_id = foods[0]["id"]
                    print(f"✅ Got food item: {foods[0]['food_name']}")
                    
                    # Test AI analysis
                    params = {"constitution": "vata", "season": "winter"}
                    async with session.get(f"{BASE_URL}/api/foods/{food_id}/ai-analysis", params=params, headers=headers) as ai_response:
                        if ai_response.status == 200:
                            ai_data = await ai_response.json()
                            ai_analysis = ai_data.get("ai_analysis", {})
                            print(f"✅ AI Analysis successful")
                            print(f"Analysis keys: {list(ai_analysis.keys())}")
                            
                            # Check if it's a parsing issue
                            if "parsing_issue" in ai_analysis:
                                print("⚠️  JSON parsing issue detected - AI is working but response format needs fixing")
                                print("Raw explanation preview:", ai_analysis.get("dosha_analysis", {}).get("explanation", "")[:200])
                            else:
                                print("✅ AI Analysis structure is correct")
                        else:
                            error_text = await ai_response.text()
                            print(f"❌ AI Analysis failed: {ai_response.status}")
                            print(f"Error: {error_text}")
                else:
                    print("❌ No food items found")
            else:
                print("❌ Food search failed")

if __name__ == "__main__":
    asyncio.run(test_ai_analysis())