#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Ayurvedic Practice Management System
Tests all authentication, food search, and AI-powered analysis endpoints
"""

import asyncio
import aiohttp
import json
import sys
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8001"
TEST_USER = {
    "username": "ayurveda_practitioner",
    "email": "practitioner@ayurveda.com", 
    "password": "secure123",
    "full_name": "Dr. Ayurveda Practitioner",
    "practice_name": "Holistic Ayurveda Clinic",
    "license_number": "AYU2024001"
}

class BackendTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.test_results = []
        self.food_items = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_result(self, test_name: str, success: bool, message: str, details: Any = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} - {test_name}: {message}")
        if details and not success:
            logger.error(f"Details: {details}")
    
    async def test_health_check(self):
        """Test basic API health"""
        try:
            async with self.session.get(f"{BASE_URL}/") as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_result("Health Check", True, f"API is running: {data.get('message')}")
                    return True
                else:
                    self.log_result("Health Check", False, f"API returned status {response.status}")
                    return False
        except Exception as e:
            self.log_result("Health Check", False, f"Connection failed: {str(e)}")
            return False
    
    async def test_user_registration(self):
        """Test user registration endpoint"""
        try:
            async with self.session.post(
                f"{BASE_URL}/api/auth/register",
                json=TEST_USER
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    self.log_result("User Registration", True, "User registered successfully")
                    return True
                elif response.status == 400:
                    # User might already exist, try login
                    self.log_result("User Registration", True, "User already exists (expected)")
                    return await self.test_user_login()
                else:
                    error_data = await response.text()
                    self.log_result("User Registration", False, f"Registration failed with status {response.status}", error_data)
                    return False
        except Exception as e:
            self.log_result("User Registration", False, f"Registration request failed: {str(e)}")
            return False
    
    async def test_user_login(self):
        """Test user login endpoint"""
        try:
            login_data = {
                "username": TEST_USER["username"],
                "password": TEST_USER["password"]
            }
            async with self.session.post(
                f"{BASE_URL}/api/auth/login",
                json=login_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    self.log_result("User Login", True, "Login successful")
                    return True
                else:
                    error_data = await response.text()
                    self.log_result("User Login", False, f"Login failed with status {response.status}", error_data)
                    return False
        except Exception as e:
            self.log_result("User Login", False, f"Login request failed: {str(e)}")
            return False
    
    def get_auth_headers(self):
        """Get authorization headers"""
        if not self.auth_token:
            return {}
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    async def test_food_search(self):
        """Test food search API endpoint"""
        try:
            headers = self.get_auth_headers()
            search_queries = ["rice", "dal", "chicken", "vegetable"]
            
            for query in search_queries:
                async with self.session.get(
                    f"{BASE_URL}/api/foods/search",
                    params={"query": query, "limit": 5},
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data:
                            self.food_items.extend(data[:2])  # Store some food items for later tests
                            self.log_result(f"Food Search - {query}", True, f"Found {len(data)} food items")
                        else:
                            self.log_result(f"Food Search - {query}", False, "No food items found")
                    else:
                        error_data = await response.text()
                        self.log_result(f"Food Search - {query}", False, f"Search failed with status {response.status}", error_data)
                        return False
            
            return len(self.food_items) > 0
            
        except Exception as e:
            self.log_result("Food Search", False, f"Search request failed: {str(e)}")
            return False
    
    async def test_ai_food_analysis(self):
        """Test AI-powered food analysis endpoint"""
        if not self.food_items:
            self.log_result("AI Food Analysis", False, "No food items available for testing")
            return False
        
        try:
            headers = self.get_auth_headers()
            food_item = self.food_items[0]
            food_id = food_item.get("id")
            
            # Test different constitutions and seasons
            test_cases = [
                {"constitution": "vata", "season": "winter"},
                {"constitution": "pitta", "season": "summer"},
                {"constitution": "kapha", "season": "spring"},
                {"constitution": None, "season": "monsoon"}
            ]
            
            for case in test_cases:
                params = {"season": case["season"]}
                if case["constitution"]:
                    params["constitution"] = case["constitution"]
                
                async with self.session.get(
                    f"{BASE_URL}/api/foods/{food_id}/ai-analysis",
                    params=params,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        ai_analysis = data.get("ai_analysis", {})
                        
                        # Check if AI analysis has expected structure
                        has_dosha_analysis = "dosha_analysis" in ai_analysis
                        has_recommendations = "personalized_recommendations" in ai_analysis
                        
                        test_name = f"AI Analysis - {case['constitution'] or 'no_constitution'}/{case['season']}"
                        if has_dosha_analysis and has_recommendations:
                            self.log_result(test_name, True, "AI analysis returned structured data")
                        else:
                            self.log_result(test_name, False, "AI analysis missing expected structure", ai_analysis)
                    else:
                        error_data = await response.text()
                        test_name = f"AI Analysis - {case['constitution'] or 'no_constitution'}/{case['season']}"
                        self.log_result(test_name, False, f"AI analysis failed with status {response.status}", error_data)
                        return False
            
            return True
            
        except Exception as e:
            self.log_result("AI Food Analysis", False, f"AI analysis request failed: {str(e)}")
            return False
    
    async def test_food_improvement_suggestions(self):
        """Test food improvement suggestions endpoint"""
        try:
            headers = self.get_auth_headers()
            
            # Create test data for problematic foods
            test_data = {
                "problematic_foods": [
                    {
                        "food_name": "White Rice",
                        "issue": "High glycemic index, may aggravate kapha"
                    },
                    {
                        "food_name": "Fried Foods",
                        "issue": "Heavy, oily, difficult to digest"
                    }
                ],
                "season": "winter"
            }
            
            async with self.session.post(
                f"{BASE_URL}/api/foods/improvement-suggestions",
                json=test_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    suggestions = data.get("improvement_suggestions", {})
                    
                    if suggestions:
                        self.log_result("Food Improvement Suggestions", True, "AI suggestions generated successfully")
                        return True
                    else:
                        self.log_result("Food Improvement Suggestions", False, "No suggestions returned", data)
                        return False
                else:
                    error_data = await response.text()
                    self.log_result("Food Improvement Suggestions", False, f"Request failed with status {response.status}", error_data)
                    return False
                    
        except Exception as e:
            self.log_result("Food Improvement Suggestions", False, f"Request failed: {str(e)}")
            return False
    
    async def test_seasonal_recommendations(self):
        """Test seasonal food recommendations endpoint"""
        if not self.food_items:
            self.log_result("Seasonal Recommendations", False, "No food items available for testing")
            return False
        
        try:
            headers = self.get_auth_headers()
            food_item = self.food_items[0]
            food_id = food_item.get("id")
            
            seasons = ["winter", "spring", "monsoon", "autumn"]
            constitutions = ["vata", "pitta", "kapha"]
            
            for season in seasons:
                for constitution in constitutions:
                    params = {
                        "target_season": season,
                        "constitution": constitution
                    }
                    
                    async with self.session.get(
                        f"{BASE_URL}/api/foods/{food_id}/seasonal-recommendations",
                        params=params,
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Check for expected fields
                            has_suitability = "seasonal_suitability" in data
                            has_modifications = "preparation_modifications" in data
                            
                            test_name = f"Seasonal Recommendations - {season}/{constitution}"
                            if has_suitability or has_modifications:
                                self.log_result(test_name, True, "Seasonal recommendations generated")
                            else:
                                self.log_result(test_name, False, "Missing expected recommendation fields", data)
                        else:
                            error_data = await response.text()
                            test_name = f"Seasonal Recommendations - {season}/{constitution}"
                            self.log_result(test_name, False, f"Request failed with status {response.status}", error_data)
                            return False
            
            return True
            
        except Exception as e:
            self.log_result("Seasonal Recommendations", False, f"Request failed: {str(e)}")
            return False
    
    async def test_dashboard_ai_insights(self):
        """Test dashboard AI insights endpoint"""
        try:
            headers = self.get_auth_headers()
            
            async with self.session.get(
                f"{BASE_URL}/api/dashboard/ai-insights",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Check for expected fields
                    has_season = "current_season" in data
                    has_distribution = "dosha_distribution" in data
                    has_tips = "seasonal_tips" in data
                    
                    if has_season and has_distribution:
                        self.log_result("Dashboard AI Insights", True, f"Dashboard insights generated for {data.get('current_season')} season")
                        return True
                    else:
                        self.log_result("Dashboard AI Insights", False, "Missing expected insight fields", data)
                        return False
                else:
                    error_data = await response.text()
                    self.log_result("Dashboard AI Insights", False, f"Request failed with status {response.status}", error_data)
                    return False
                    
        except Exception as e:
            self.log_result("Dashboard AI Insights", False, f"Request failed: {str(e)}")
            return False
    
    async def test_dashboard_stats(self):
        """Test dashboard statistics endpoint"""
        try:
            headers = self.get_auth_headers()
            
            async with self.session.get(
                f"{BASE_URL}/api/dashboard/stats",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Check for expected fields
                    expected_fields = ["total_clients", "active_diet_plans", "available_foods"]
                    missing_fields = [field for field in expected_fields if field not in data]
                    
                    if not missing_fields:
                        self.log_result("Dashboard Stats", True, f"Dashboard stats retrieved: {data.get('available_foods')} foods available")
                        return True
                    else:
                        self.log_result("Dashboard Stats", False, f"Missing fields: {missing_fields}", data)
                        return False
                else:
                    error_data = await response.text()
                    self.log_result("Dashboard Stats", False, f"Request failed with status {response.status}", error_data)
                    return False
                    
        except Exception as e:
            self.log_result("Dashboard Stats", False, f"Request failed: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all backend tests in sequence"""
        logger.info("🚀 Starting comprehensive backend API testing...")
        
        # Core functionality tests
        tests = [
            ("Health Check", self.test_health_check),
            ("User Registration/Login", self.test_user_registration),
            ("Food Search API", self.test_food_search),
            ("AI Food Analysis", self.test_ai_food_analysis),
            ("Food Improvement Suggestions", self.test_food_improvement_suggestions),
            ("Seasonal Recommendations", self.test_seasonal_recommendations),
            ("Dashboard AI Insights", self.test_dashboard_ai_insights),
            ("Dashboard Stats", self.test_dashboard_stats)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n📋 Running: {test_name}")
            try:
                success = await test_func()
                if success:
                    passed += 1
            except Exception as e:
                self.log_result(test_name, False, f"Test execution failed: {str(e)}")
        
        # Print summary
        logger.info(f"\n📊 TEST SUMMARY")
        logger.info(f"{'='*50}")
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {total - passed}")
        logger.info(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Print detailed results
        logger.info(f"\n📋 DETAILED RESULTS")
        logger.info(f"{'='*50}")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            logger.info(f"{status} {result['test']}: {result['message']}")
        
        return passed, total

async def main():
    """Main test execution"""
    async with BackendTester() as tester:
        passed, total = await tester.run_all_tests()
        
        # Exit with appropriate code
        if passed == total:
            logger.info("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            logger.error(f"\n💥 {total - passed} tests failed!")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())