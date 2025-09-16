"""
AI-powered Ayurvedic dietary analysis using Emergent LLM integration
"""
import os
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import logging
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class AyurvedicAIAnalyzer:
    """AI-powered analyzer for Ayurvedic dietary recommendations"""
    
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not self.api_key:
            raise ValueError("EMERGENT_LLM_KEY not found in environment variables")
        
        # Initialize LLM chat with system message
        self.system_message = """You are an expert Ayurvedic practitioner and nutritionist with deep knowledge of traditional Indian medicine, nutrition science, and food therapy. Your expertise includes:

1. **Dosha Analysis**: Understanding how different foods affect Vata, Pitta, and Kapha constitutions
2. **Seasonal Nutrition**: Recommending foods based on seasonal changes and their effects on doshas
3. **Food Combinations**: Knowledge of compatible and incompatible food combinations (Viruddha Ahara)
4. **Therapeutic Properties**: Understanding the medicinal properties of foods and spices
5. **Individual Constitution**: Personalizing recommendations based on individual Prakriti and Vikriti

**Your Response Format:**
Always provide responses in the following JSON structure:
{
  "overall_score": 85,
  "dosha_analysis": {
    "vata_effect": "balancing/aggravating/neutral",
    "pitta_effect": "balancing/aggravating/neutral", 
    "kapha_effect": "balancing/aggravating/neutral",
    "explanation": "Detailed explanation of dosha effects"
  },
  "nutritional_assessment": {
    "strengths": ["list of nutritional benefits"],
    "concerns": ["list of potential issues"],
    "analysis": "Detailed nutritional analysis"
  },
  "ayurvedic_properties": {
    "rasa": ["taste classifications"],
    "virya": "heating/cooling/neutral",
    "vipaka": "post-digestive effect",
    "prabhava": "special therapeutic effect if any"
  },
  "seasonal_guidance": {
    "best_seasons": ["seasons when this food is most beneficial"],
    "seasonal_modifications": "How to modify preparation based on season"
  },
  "food_interactions": {
    "beneficial_combinations": ["foods that combine well"],
    "avoid_combinations": ["foods to avoid combining with"],
    "timing_recommendations": "Best time to consume"
  },
  "personalized_recommendations": {
    "for_vata_constitution": "specific advice for vata types",
    "for_pitta_constitution": "specific advice for pitta types", 
    "for_kapha_constitution": "specific advice for kapha types"
  },
  "improvement_suggestions": [
    {
      "issue": "identified problem",
      "solution": "ayurvedic solution",
      "foods_to_add": ["specific foods to include"],
      "herbs_spices": ["therapeutic herbs/spices"],
      "preparation_method": "how to prepare/consume"
    }
  ]
}

**Guidelines:**
- Base recommendations on authentic Ayurvedic principles
- Consider both traditional wisdom and modern nutritional science
- Provide practical, actionable advice
- Explain the 'why' behind each recommendation
- Be culturally sensitive to Indian dietary practices
- Consider digestive fire (Agni) in recommendations
"""

    async def _get_chat_instance(self, session_id: str) -> LlmChat:
        """Get a configured LLM chat instance"""
        chat = LlmChat(
            api_key=self.api_key,
            session_id=session_id,
            system_message=self.system_message
        )
        # Use GPT-4o for best analysis quality
        chat.with_model("openai", "gpt-4o")
        return chat

    async def analyze_single_food(
        self, 
        food_item: Dict[str, Any],
        user_constitution: Optional[Dict[str, Any]] = None,
        current_season: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze a single food item with AI-powered Ayurvedic analysis"""
        
        try:
            session_id = f"food_analysis_{food_item.get('id', 'unknown')}_{datetime.now().timestamp()}"
            chat = await self._get_chat_instance(session_id)
            
            # Prepare context for analysis
            context = {
                "food_name": food_item.get('food_name', ''),
                "nutrition_per_100g": food_item.get('nutrition_per_100g', {}),
                "current_ayurvedic_properties": food_item.get('ayurvedic_properties', {}),
                "ingredients": food_item.get('ingredients', []),
                "category": food_item.get('category', ''),
                "user_constitution": user_constitution,
                "current_season": current_season or "spring"
            }
            
            prompt = f"""
Analyze this Indian food item with comprehensive Ayurvedic and nutritional assessment:

**Food Details:**
- Name: {context['food_name']}
- Category: {context['category']}
- Nutrition (per 100g): {context['nutrition_per_100g']}
- Current Ayurvedic Classification: {context['current_ayurvedic_properties']}
- Ingredients: {context['ingredients']}

**User Context:**
- Constitution: {context['user_constitution']}
- Current Season: {context['current_season']}

Please provide a comprehensive analysis following the JSON format specified in your system instructions. Focus on:
1. Accurate dosha effects based on ingredients and preparation
2. Seasonal appropriateness
3. Food combination guidance
4. Specific recommendations for improvement
5. Constitutional suitability

Ensure your analysis is detailed, practical, and rooted in authentic Ayurvedic principles.
"""
            
            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            # Parse JSON response
            import json
            try:
                analysis = json.loads(response)
                return analysis
            except json.JSONDecodeError:
                # Fallback parsing if response isn't pure JSON
                logger.warning(f"Failed to parse JSON response for {food_item.get('food_name')}")
                return self._create_fallback_analysis(food_item, response)
                
        except Exception as e:
            logger.error(f"AI analysis failed for {food_item.get('food_name')}: {e}")
            return self._create_error_analysis(food_item, str(e))

    async def analyze_diet_plan(
        self,
        diet_plan: Dict[str, Any],
        client_profile: Dict[str, Any],
        current_season: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze complete diet plan with AI recommendations"""
        
        try:
            session_id = f"diet_analysis_{diet_plan.get('id', 'unknown')}_{datetime.now().timestamp()}"
            chat = await self._get_chat_instance(session_id)
            
            prompt = f"""
Analyze this complete diet plan for an Ayurvedic client:

**Client Profile:**
- Age: {client_profile.get('age')}
- Gender: {client_profile.get('gender')}
- Primary Dosha: {client_profile.get('primary_dosha')}
- Secondary Dosha: {client_profile.get('secondary_dosha')}
- Health Goals: {client_profile.get('health_goals', [])}
- Dietary Restrictions: {client_profile.get('dietary_restrictions', [])}
- Medical Conditions: {client_profile.get('medical_conditions', [])}

**Diet Plan:**
- Duration: {diet_plan.get('duration_days')} days
- Meals: {diet_plan.get('meals', [])}
- Current Season: {current_season or 'spring'}

Please provide a comprehensive diet plan analysis with:
1. Overall plan suitability for the client's constitution
2. Seasonal appropriateness of food choices
3. Nutritional balance assessment
4. Dosha balancing effectiveness
5. Specific improvements for better health outcomes
6. Day-wise recommendations
7. Food combination issues to address
8. Additional foods/herbs to include

Respond in JSON format with detailed explanations and practical recommendations.
"""
            
            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            import json
            try:
                analysis = json.loads(response)
                return analysis
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse diet plan analysis JSON")
                return self._create_fallback_diet_analysis(diet_plan, response)
                
        except Exception as e:
            logger.error(f"Diet plan analysis failed: {e}")
            return self._create_error_diet_analysis(diet_plan, str(e))

    async def get_food_improvement_suggestions(
        self,
        problematic_foods: List[Dict[str, Any]], 
        client_constitution: Dict[str, Any],
        current_season: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get specific suggestions for improving problematic foods in diet"""
        
        try:
            session_id = f"improvement_{datetime.now().timestamp()}"
            chat = await self._get_chat_instance(session_id)
            
            food_list = [f"- {food.get('food_name')}: {food.get('issue', 'General concern')}" 
                        for food in problematic_foods]
            
            prompt = f"""
Based on these problematic foods in the client's diet, provide specific Ayurvedic improvement strategies:

**Client Constitution:**
- Primary Dosha: {client_constitution.get('primary_dosha')}
- Secondary Dosha: {client_constitution.get('secondary_dosha')}
- Health Goals: {client_constitution.get('health_goals', [])}
- Current Season: {current_season or 'spring'}

**Problematic Foods:**
{chr(10).join(food_list)}

For each problematic food, provide:
1. Why it's problematic for this constitution
2. How to modify preparation to make it suitable
3. Alternative foods that serve the same nutritional purpose
4. Specific spices/herbs to add for better digestion
5. Best timing for consumption
6. Complementary foods to pair with

Respond in JSON format with detailed, actionable recommendations.
"""
            
            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            import json
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"improvements": response, "error": "Failed to parse JSON"}
                
        except Exception as e:
            logger.error(f"Improvement suggestions failed: {e}")
            return {"error": str(e), "suggestions": "Unable to generate AI recommendations"}

    def _create_fallback_analysis(self, food_item: Dict[str, Any], ai_response: str) -> Dict[str, Any]:
        """Create fallback analysis when JSON parsing fails"""
        return {
            "overall_score": 75,
            "dosha_analysis": {
                "explanation": ai_response[:500] + "..." if len(ai_response) > 500 else ai_response
            },
            "ai_generated": True,
            "parsing_issue": True,
            "food_name": food_item.get('food_name', 'Unknown')
        }

    def _create_error_analysis(self, food_item: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Create error analysis when AI fails"""
        return {
            "overall_score": 50,
            "error": f"AI analysis failed: {error}",
            "dosha_analysis": {
                "explanation": "Unable to generate AI-powered analysis. Using basic Ayurvedic principles."
            },
            "food_name": food_item.get('food_name', 'Unknown')
        }

    def _create_fallback_diet_analysis(self, diet_plan: Dict[str, Any], ai_response: str) -> Dict[str, Any]:
        """Create fallback diet analysis when JSON parsing fails"""
        return {
            "overall_assessment": ai_response[:1000] + "..." if len(ai_response) > 1000 else ai_response,
            "ai_generated": True,
            "parsing_issue": True,
            "plan_name": diet_plan.get('plan_name', 'Unknown Plan')
        }

    def _create_error_diet_analysis(self, diet_plan: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Create error diet analysis when AI fails"""
        return {
            "error": f"Diet analysis failed: {error}",
            "overall_assessment": "Unable to generate AI-powered diet analysis.",
            "plan_name": diet_plan.get('plan_name', 'Unknown Plan')
        }


# Utility functions for seasonal determination
def get_current_season() -> str:
    """Determine current season based on month (Indian seasonal calendar)"""
    month = datetime.now().month
    if month in [12, 1, 2]:
        return "winter"  # Shishira
    elif month in [3, 4, 5]:
        return "spring"  # Vasanta
    elif month in [6, 7, 8]:
        return "monsoon"  # Varsha
    elif month in [9, 10, 11]:
        return "autumn"  # Sharad
    else:
        return "spring"  # Default

# Global analyzer instance
_analyzer = None

def get_analyzer() -> AyurvedicAIAnalyzer:
    """Get global analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = AyurvedicAIAnalyzer()
    return _analyzer