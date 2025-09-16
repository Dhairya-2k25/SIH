from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import motor.motor_asyncio
import os
import jwt
import bcrypt
import uuid
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from enum import Enum
import logging
from pathlib import Path
from dotenv import load_dotenv
from ayurvedic_ai_analyzer import get_analyzer, get_current_season

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Ayurvedic Practice Management & Nutrition Analysis",
    description="Comprehensive cloud-based system for Ayurvedic dietitians with Indian food database",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


security = HTTPBearer()
JWT_SECRET = "ayurvedic_practice_secret_key_2024"
JWT_ALGORITHM = "HS256"


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client.ayurvedic_practice

# Enums for Ayurvedic principles
class DoshaType(str, Enum):
    VATA = "vata"
    PITTA = "pitta" 
    KAPHA = "kapha"

class RasaType(str, Enum):
    SWEET = "sweet"
    SOUR = "sour"
    SALTY = "salty"
    PUNGENT = "pungent"
    BITTER = "bitter"
    ASTRINGENT = "astringent"

class ViryaType(str, Enum):
    HEATING = "heating"
    COOLING = "cooling"
    NEUTRAL = "neutral"

# Pydantic Models
class UserRegistration(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2, max_length=100)
    practice_name: Optional[str] = None
    license_number: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class User(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    practice_name: Optional[str] = None
    license_number: Optional[str] = None
    created_at: datetime

class ClientProfile(BaseModel):
    id: str
    name: str
    age: int
    gender: str
    height: float  # cm
    weight: float  # kg
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    primary_dosha: DoshaType
    secondary_dosha: Optional[DoshaType] = None
    health_goals: List[str] = []
    dietary_restrictions: List[str] = []
    medical_conditions: List[str] = []
    created_at: datetime
    practitioner_id: str

class PrakritiAssessment(BaseModel):
    client_id: str
    assessment_date: datetime
    vata_score: int = Field(..., ge=0, le=100)
    pitta_score: int = Field(..., ge=0, le=100) 
    kapha_score: int = Field(..., ge=0, le=100)
    primary_dosha: DoshaType
    secondary_dosha: Optional[DoshaType] = None
    assessment_notes: Optional[str] = None

class NutritionInfo(BaseModel):
    energy_kcal: float
    protein_g: float
    fat_g: float
    carb_g: float
    fiber_g: float
    calcium_mg: float
    iron_mg: float
    vitamin_c_mg: float

class AyurvedicProperties(BaseModel):
    primary_rasa: List[RasaType]
    virya: ViryaType
    dosha_effects: Dict[str, str]  # vata, pitta, kapha effects
    therapeutic_properties: List[str] = []

class FoodItem(BaseModel):
    id: str
    food_code: str
    food_name: str
    food_name_local: Optional[str] = None
    category: str
    source: str  # ASC, BFP, OSR
    nutrition_per_100g: NutritionInfo
    nutrition_per_serving: Optional[NutritionInfo] = None
    serving_size: Optional[str] = None
    ayurvedic_properties: AyurvedicProperties
    ingredients: Optional[List[Dict[str, Any]]] = None

class DietPlan(BaseModel):
    id: str
    client_id: str
    practitioner_id: str
    plan_name: str
    duration_days: int
    meals: List[Dict[str, Any]]  # breakfast, lunch, dinner, snacks
    total_nutrition: NutritionInfo
    ayurvedic_guidelines: List[str]
    created_at: datetime
    status: str = "active"

def _sum_nutrition(nutrients: List[NutritionInfo]) -> NutritionInfo:
    """Aggregate a list of NutritionInfo into a single total."""
    total = {
        "energy_kcal": 0.0,
        "protein_g": 0.0,
        "fat_g": 0.0,
        "carb_g": 0.0,
        "fiber_g": 0.0,
        "calcium_mg": 0.0,
        "iron_mg": 0.0,
        "vitamin_c_mg": 0.0,
    }
    for n in nutrients:
        total["energy_kcal"] += n.energy_kcal
        total["protein_g"] += n.protein_g
        total["fat_g"] += n.fat_g
        total["carb_g"] += n.carb_g
        total["fiber_g"] += n.fiber_g
        total["calcium_mg"] += n.calcium_mg
        total["iron_mg"] += n.iron_mg
        total["vitamin_c_mg"] += n.vitamin_c_mg
    return NutritionInfo(**total)

# Authentication Functions
def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"username": username})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(
            id=str(user["_id"]),
            username=user["username"],
            email=user["email"],
            full_name=user["full_name"],
            practice_name=user.get("practice_name"),
            license_number=user.get("license_number"),
            created_at=user["created_at"]
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Ayurvedic Analysis Functions
def determine_primary_rasa(food_name: str, nutrition: Dict[str, float]) -> List[RasaType]:
    """Determine primary taste (rasa) based on food name and nutrition"""
    food_lower = food_name.lower()
    primary_rasa = []
    
    # Sweet foods
    if any(word in food_lower for word in ['sweet', 'sugar', 'jaggery', 'honey', 'milk', 'rice', 'wheat']):
        primary_rasa.append(RasaType.SWEET)
    elif nutrition.get('carb_g', 0) > 50:  # High carb = sweet
        primary_rasa.append(RasaType.SWEET)
    
    # Sour foods  
    if any(word in food_lower for word in ['lemon', 'lime', 'tamarind', 'yogurt', 'buttermilk']):
        primary_rasa.append(RasaType.SOUR)
    
    # Salty foods
    if any(word in food_lower for word in ['salt', 'pickle']):
        primary_rasa.append(RasaType.SALTY)
    elif nutrition.get('sodium_mg', 0) > 500:
        primary_rasa.append(RasaType.SALTY)
    
    # Pungent foods
    if any(word in food_lower for word in ['ginger', 'garlic', 'onion', 'chili', 'pepper', 'mustard']):
        primary_rasa.append(RasaType.PUNGENT)
    
    # Bitter foods
    if any(word in food_lower for word in ['bitter', 'neem', 'fenugreek', 'turmeric', 'spinach']):
        primary_rasa.append(RasaType.BITTER)
    
    # Astringent foods
    if any(word in food_lower for word in ['pomegranate', 'cranberry', 'beans', 'lentil']):
        primary_rasa.append(RasaType.ASTRINGENT)
    elif nutrition.get('protein_g', 0) > 15:  # High protein tends to be astringent
        primary_rasa.append(RasaType.ASTRINGENT)
    
    return primary_rasa if primary_rasa else [RasaType.SWEET]

def determine_virya(food_name: str, nutrition: Dict[str, float]) -> ViryaType:
    """Determine heating/cooling property (virya)"""
    food_lower = food_name.lower()
    
    # Heating foods
    if any(word in food_lower for word in ['ginger', 'garlic', 'onion', 'chili', 'pepper', 'mustard', 'sesame']):
        return ViryaType.HEATING
    
    # Cooling foods
    if any(word in food_lower for word in ['cucumber', 'mint', 'coconut', 'melon', 'yogurt', 'milk']):
        return ViryaType.COOLING
    
    # High fat content tends to be heating
    if nutrition.get('fat_g', 0) > 15:
        return ViryaType.HEATING
    
    return ViryaType.NEUTRAL

def analyze_dosha_effects(food_name: str, nutrition: Dict[str, float], rasa: List[RasaType], virya: ViryaType) -> Dict[str, str]:
    """Analyze effects on the three doshas"""
    effects = {
        "vata": "neutral",
        "pitta": "neutral", 
        "kapha": "neutral"
    }
    
    # Rasa effects on doshas
    for r in rasa:
        if r == RasaType.SWEET:
            effects["vata"] = "decreases"
            effects["kapha"] = "increases"
        elif r == RasaType.SOUR:
            effects["pitta"] = "increases"
            effects["vata"] = "decreases"
        elif r == RasaType.SALTY:
            effects["pitta"] = "increases"
            effects["kapha"] = "increases"
        elif r == RasaType.PUNGENT:
            effects["vata"] = "increases"
            effects["pitta"] = "increases"
            effects["kapha"] = "decreases"
        elif r == RasaType.BITTER:
            effects["vata"] = "increases"
            effects["pitta"] = "decreases"
            effects["kapha"] = "decreases"
        elif r == RasaType.ASTRINGENT:
            effects["vata"] = "increases"
            effects["kapha"] = "decreases"
    
    # Virya effects
    if virya == ViryaType.HEATING:
        effects["pitta"] = "increases"
        if effects["vata"] == "neutral":
            effects["vata"] = "decreases"
    elif virya == ViryaType.COOLING:
        effects["pitta"] = "decreases"
        if effects["kapha"] == "neutral":
            effects["kapha"] = "increases"
    
    return effects

# Data Loading Functions
async def load_indb_data():
    """Load INDB data into MongoDB"""
    try:
        # Check if data already loaded
        count = await db.foods.count_documents({})
        if count > 0:
            logger.info(f"INDB data already loaded: {count} documents")
            return
        
        logger.info("Loading INDB data...")
        
        # Resolve data file paths flexibly for local/dev and docker
        def resolve_path(filename: str) -> str:
            candidates = []
            # 1) DATA_DIR env override
            data_dir = os.environ.get("DATA_DIR")
            if data_dir:
                candidates.append(os.path.join(data_dir, filename))
            # 2) Project root (two levels up from this file)
            here = Path(__file__).resolve()
            project_root = here.parents[1]
            candidates.append(str(project_root / filename))
            # 3) Original docker path
            candidates.append(os.path.join("/app", filename))
            for p in candidates:
                if os.path.exists(p):
                    return p
            raise FileNotFoundError(f"Could not find {filename} in: {', '.join(candidates)}")

        # Read Excel files
        indb_df = pd.read_excel(resolve_path('INDB.xlsx'))
        recipes_df = pd.read_excel(resolve_path('recipes.xlsx'))
        names_df = pd.read_excel(resolve_path('recipes_names.xlsx'))
        
        # Process main INDB data
        foods_to_insert = []
        
        for _, row in indb_df.iterrows():
            try:
                # Basic nutrition info per 100g
                nutrition_100g = NutritionInfo(
                    energy_kcal=float(row.get('energy_kcal', 0) or 0),
                    protein_g=float(row.get('protein_g', 0) or 0),
                    fat_g=float(row.get('fat_g', 0) or 0),
                    carb_g=float(row.get('carb_g', 0) or 0),
                    fiber_g=float(row.get('fibre_g', 0) or 0),
                    calcium_mg=float(row.get('calcium_mg', 0) or 0),
                    iron_mg=float(row.get('iron_mg', 0) or 0),
                    vitamin_c_mg=float(row.get('vitc_mg', 0) or 0)
                )
                
                # Nutrition per serving (if available)
                nutrition_serving = None
                if pd.notna(row.get('unit_serving_energy_kcal')):
                    nutrition_serving = NutritionInfo(
                        energy_kcal=float(row.get('unit_serving_energy_kcal', 0) or 0),
                        protein_g=float(row.get('unit_serving_protein_g', 0) or 0),
                        fat_g=float(row.get('unit_serving_fat_g', 0) or 0),
                        carb_g=float(row.get('unit_serving_carb_g', 0) or 0),
                        fiber_g=float(row.get('unit_serving_fibre_g', 0) or 0),
                        calcium_mg=float(row.get('unit_serving_calcium_mg', 0) or 0),
                        iron_mg=float(row.get('unit_serving_iron_mg', 0) or 0),
                        vitamin_c_mg=float(row.get('unit_serving_vitc_mg', 0) or 0)
                    )
                
                # Determine Ayurvedic properties
                nutrition_dict = {
                    'carb_g': nutrition_100g.carb_g,
                    'protein_g': nutrition_100g.protein_g,
                    'fat_g': nutrition_100g.fat_g,
                    'sodium_mg': float(row.get('sodium_mg', 0) or 0)
                }
                
                food_name = str(row.get('food_name', '')).strip()
                primary_rasa = determine_primary_rasa(food_name, nutrition_dict)
                virya = determine_virya(food_name, nutrition_dict)
                dosha_effects = analyze_dosha_effects(food_name, nutrition_dict, primary_rasa, virya)
                
                ayurvedic_props = AyurvedicProperties(
                    primary_rasa=primary_rasa,
                    virya=virya,
                    dosha_effects=dosha_effects,
                    therapeutic_properties=[]
                )
                
                # Get ingredients for this recipe
                food_code = str(row.get('food_code', '')).strip()
                recipe_ingredients = recipes_df[recipes_df['recipe_code'] == food_code]
                ingredients = []
                
                for _, ingredient_row in recipe_ingredients.iterrows():
                    ingredients.append({
                        'name': str(ingredient_row.get('ingredient_name_org', '')).strip(),
                        'amount': float(ingredient_row.get('amount', 0) or 0),
                        'unit': str(ingredient_row.get('unit', '')).strip(),
                        'food_code': str(ingredient_row.get('food_code_org', '')).strip()
                    })
                
                # Create food item
                food_item = {
                    '_id': str(uuid.uuid4()),
                    'food_code': food_code,
                    'food_name': food_name,
                    'food_name_local': None,  # Could be enhanced with local names
                    'category': 'recipe',
                    'source': food_code[:3] if food_code else 'unknown',  # ASC, BFP, OSR
                    'nutrition_per_100g': nutrition_100g.dict(),
                    'nutrition_per_serving': nutrition_serving.dict() if nutrition_serving else None,
                    'serving_size': str(row.get('servings_unit', '')).strip() if pd.notna(row.get('servings_unit')) else None,
                    'ayurvedic_properties': ayurvedic_props.dict(),
                    'ingredients': ingredients,
                    'created_at': datetime.now(timezone.utc)
                }
                
                foods_to_insert.append(food_item)
                
            except Exception as e:
                logger.warning(f"Error processing row {row.get('food_code', 'unknown')}: {e}")
                continue
        
        # Insert into MongoDB
        if foods_to_insert:
            await db.foods.insert_many(foods_to_insert)
            logger.info(f"Successfully loaded {len(foods_to_insert)} food items into database")
        
        # Create indexes for better performance
        await db.foods.create_index("food_code")
        await db.foods.create_index("food_name")
        await db.foods.create_index("category")
        await db.foods.create_index("source")
        
    except Exception as e:
        logger.error(f"Error loading INDB data: {e}")

# API Routes

@app.on_event("startup")
async def startup_event():
    """Load INDB data on startup"""
    await load_indb_data()

@app.get("/")
async def root():
    return {"message": "Ayurvedic Practice Management & Nutrition Analysis API", "status": "active"}

# Authentication Routes
@app.post("/api/auth/register")
async def register_user(user_data: UserRegistration):
    """Register a new Ayurvedic practitioner"""
    
    # Check if user exists
    existing_user = await db.users.find_one({"$or": [{"username": user_data.username}, {"email": user_data.email}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    # Hash password and create user
    hashed_password = hash_password(user_data.password)
    user_id = str(uuid.uuid4())
    
    user_doc = {
        "_id": user_id,
        "username": user_data.username,
        "email": user_data.email,
        "password": hashed_password,
        "full_name": user_data.full_name,
        "practice_name": user_data.practice_name,
        "license_number": user_data.license_number,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.users.insert_one(user_doc)
    
    # Create access token
    access_token = create_access_token(data={"sub": user_data.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": User(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            practice_name=user_data.practice_name,
            license_number=user_data.license_number,
            created_at=user_doc["created_at"]
        )
    }

@app.post("/api/auth/login")
async def login_user(user_data: UserLogin):
    """Login user and return access token"""
    
    user = await db.users.find_one({"username": user_data.username})
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token = create_access_token(data={"sub": user_data.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": User(
            id=str(user["_id"]),
            username=user["username"],
            email=user["email"],
            full_name=user["full_name"],
            practice_name=user.get("practice_name"),
            license_number=user.get("license_number"),
            created_at=user["created_at"]
        )
    }

# Food & Nutrition Routes
@app.get("/api/foods/search", response_model=List[FoodItem])
async def search_foods(
    query: str = Query(..., description="Search term for foods"),
    category: Optional[str] = Query(None, description="Filter by category"),
    source: Optional[str] = Query(None, description="Filter by source (ASC, BFP, OSR)"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    current_user: User = Depends(get_current_user)
):
    """Search for Indian foods and recipes"""
    
    search_filter = {}
    
    # Text search
    if query:
        search_filter["$or"] = [
            {"food_name": {"$regex": query, "$options": "i"}},
            {"food_code": {"$regex": query, "$options": "i"}},
            {"ingredients.name": {"$regex": query, "$options": "i"}}
        ]
    
    # Additional filters
    if category:
        search_filter["category"] = category
    if source:
        search_filter["source"] = source.upper()
    
    foods_cursor = db.foods.find(search_filter).limit(limit)
    foods = await foods_cursor.to_list(length=limit)
    
    result = []
    for food in foods:
        result.append(FoodItem(
            id=str(food["_id"]),
            food_code=food["food_code"],
            food_name=food["food_name"],
            food_name_local=food.get("food_name_local"),
            category=food["category"],
            source=food["source"],
            nutrition_per_100g=NutritionInfo(**food["nutrition_per_100g"]),
            nutrition_per_serving=NutritionInfo(**food["nutrition_per_serving"]) if food.get("nutrition_per_serving") else None,
            serving_size=food.get("serving_size"),
            ayurvedic_properties=AyurvedicProperties(**food["ayurvedic_properties"]),
            ingredients=food.get("ingredients", [])
        ))
    
    return result

@app.get("/api/foods/{food_id}", response_model=FoodItem)
async def get_food_details(
    food_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific food item"""
    
    food = await db.foods.find_one({"_id": food_id})
    if not food:
        raise HTTPException(status_code=404, detail="Food item not found")
    
    return FoodItem(
        id=str(food["_id"]),
        food_code=food["food_code"],
        food_name=food["food_name"],
        food_name_local=food.get("food_name_local"),
        category=food["category"],
        source=food["source"],
        nutrition_per_100g=NutritionInfo(**food["nutrition_per_100g"]),
        nutrition_per_serving=NutritionInfo(**food["nutrition_per_serving"]) if food.get("nutrition_per_serving") else None,
        serving_size=food.get("serving_size"),
        ayurvedic_properties=AyurvedicProperties(**food["ayurvedic_properties"]),
        ingredients=food.get("ingredients", [])
    )

@app.get("/api/foods/{food_id}/ayurvedic-analysis")
async def get_ayurvedic_analysis(
    food_id: str,
    constitution: Optional[DoshaType] = Query(None, description="Primary dosha constitution"),
    current_user: User = Depends(get_current_user)
):
    """Get detailed Ayurvedic analysis for a food item"""
    
    food = await db.foods.find_one({"_id": food_id})
    if not food:
        raise HTTPException(status_code=404, detail="Food item not found")
    
    ayurvedic_props = food["ayurvedic_properties"]
    
    # Enhanced analysis based on constitution
    recommendations = []
    if constitution:
        dosha_effect = ayurvedic_props["dosha_effects"].get(constitution.value, "neutral")
        if dosha_effect == "increases":
            recommendations.append(f"Consume in moderation if {constitution.value} constitution is dominant")
        elif dosha_effect == "decreases":
            recommendations.append(f"Beneficial for balancing {constitution.value} dosha")
        else:
            recommendations.append(f"Neutral effect on {constitution.value} dosha")
    
    # Add general recommendations based on properties
    if ayurvedic_props["virya"] == "heating":
        recommendations.append("Best consumed in cooler weather or by those with cold constitution")
    elif ayurvedic_props["virya"] == "cooling":
        recommendations.append("Ideal for hot weather or those with warm constitution")
    
    return {
        "food_name": food["food_name"],
        "ayurvedic_properties": ayurvedic_props,
        "constitution_analysis": constitution.value if constitution else None,
        "recommendations": recommendations,
        "nutrition_highlights": [
            f"Energy: {food['nutrition_per_100g']['energy_kcal']} kcal per 100g",
            f"Protein: {food['nutrition_per_100g']['protein_g']}g per 100g",
            f"Iron: {food['nutrition_per_100g']['iron_mg']}mg per 100g"
        ]
    }

@app.get("/api/foods/{food_id}/ai-analysis")
async def get_ai_ayurvedic_analysis(
    food_id: str,
    constitution: Optional[DoshaType] = Query(None, description="Primary dosha constitution"),
    season: Optional[str] = Query(None, description="Current season (winter/spring/monsoon/autumn)"),
    current_user: User = Depends(get_current_user)
):
    """Get AI-powered comprehensive Ayurvedic analysis for a food item"""
    
    food = await db.foods.find_one({"_id": food_id})
    if not food:
        raise HTTPException(status_code=404, detail="Food item not found")
    
    try:
        analyzer = get_analyzer()
        
        # Prepare user constitution context
        user_constitution = None
        if constitution:
            user_constitution = {
                "primary_dosha": constitution.value,
                "preferences": []
            }
        
        current_season = season or get_current_season()
        
        # Get AI analysis
        ai_analysis = await analyzer.analyze_single_food(
            food_item=food,
            user_constitution=user_constitution,
            current_season=current_season
        )
        
        return {
            "food_name": food["food_name"],
            "food_id": food_id,
            "ai_analysis": ai_analysis,
            "analysis_timestamp": datetime.now(timezone.utc),
            "season_context": current_season
        }
        
    except Exception as e:
        logger.error(f"AI analysis failed for food {food_id}: {e}")
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

@app.post("/api/diet-plans/{plan_id}/ai-analysis")
async def analyze_diet_plan_with_ai(
    plan_id: str,
    analysis_params: Dict[str, Any] = {},
    current_user: User = Depends(get_current_user)
):
    """Get AI-powered analysis of complete diet plan"""
    
    # Get diet plan
    diet_plan = await db.diet_plans.find_one({
        "_id": plan_id,
        "practitioner_id": current_user.id
    })
    if not diet_plan:
        raise HTTPException(status_code=404, detail="Diet plan not found")
    
    # Get client profile
    client = await db.clients.find_one({
        "_id": diet_plan["client_id"],
        "practitioner_id": current_user.id
    })
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    try:
        analyzer = get_analyzer()
        current_season = analysis_params.get("season") or get_current_season()
        
        # Get AI analysis
        ai_analysis = await analyzer.analyze_diet_plan(
            diet_plan=diet_plan,
            client_profile=client,
            current_season=current_season
        )
        
        # Store analysis in database
        analysis_doc = {
            "_id": str(uuid.uuid4()),
            "plan_id": plan_id,
            "client_id": diet_plan["client_id"],
            "practitioner_id": current_user.id,
            "ai_analysis": ai_analysis,
            "analysis_date": datetime.now(timezone.utc),
            "season_context": current_season,
            "analysis_version": "1.0"
        }
        
        await db.diet_analyses.insert_one(analysis_doc)
        
        return {
            "plan_name": diet_plan["plan_name"],
            "client_name": client["name"],
            "analysis_id": analysis_doc["_id"],
            "ai_analysis": ai_analysis,
            "analysis_timestamp": analysis_doc["analysis_date"],
            "season_context": current_season
        }
        
    except Exception as e:
        logger.error(f"AI diet plan analysis failed for plan {plan_id}: {e}")
        raise HTTPException(status_code=500, detail=f"AI diet analysis failed: {str(e)}")

@app.post("/api/foods/improvement-suggestions")
async def get_food_improvement_suggestions(
    request_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Get AI-powered suggestions for improving problematic foods in diet"""
    
    try:
        problematic_foods = request_data.get("problematic_foods", [])
        client_id = request_data.get("client_id")
        
        if not problematic_foods:
            raise HTTPException(status_code=400, detail="No problematic foods provided")
        
        # Get client constitution if client_id provided
        client_constitution = {"primary_dosha": "vata"}  # Default
        if client_id:
            client = await db.clients.find_one({
                "_id": client_id,
                "practitioner_id": current_user.id
            })
            if client:
                client_constitution = {
                    "primary_dosha": client.get("primary_dosha", "vata"),
                    "secondary_dosha": client.get("secondary_dosha"),
                    "health_goals": client.get("health_goals", []),
                    "dietary_restrictions": client.get("dietary_restrictions", [])
                }
        
        analyzer = get_analyzer()
        current_season = request_data.get("season") or get_current_season()
        
        # Get AI suggestions
        suggestions = await analyzer.get_food_improvement_suggestions(
            problematic_foods=problematic_foods,
            client_constitution=client_constitution,
            current_season=current_season
        )
        
        return {
            "improvement_suggestions": suggestions,
            "client_constitution": client_constitution,
            "season_context": current_season,
            "generated_at": datetime.now(timezone.utc)
        }
        
    except Exception as e:
        logger.error(f"Food improvement suggestions failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestions: {str(e)}")

@app.get("/api/foods/{food_id}/seasonal-recommendations")
async def get_seasonal_food_recommendations(
    food_id: str,
    target_season: str = Query(..., description="Target season for recommendations"),
    constitution: Optional[DoshaType] = Query(None, description="User constitution"),
    current_user: User = Depends(get_current_user)
):
    """Get seasonal recommendations for a specific food item"""
    
    food = await db.foods.find_one({"_id": food_id})
    if not food:
        raise HTTPException(status_code=404, detail="Food item not found")
    
    valid_seasons = ["winter", "spring", "monsoon", "autumn"]
    if target_season not in valid_seasons:
        raise HTTPException(status_code=400, detail=f"Invalid season. Must be one of: {', '.join(valid_seasons)}")
    
    try:
        analyzer = get_analyzer()
        
        user_constitution = None
        if constitution:
            user_constitution = {"primary_dosha": constitution.value}
        
        # Get AI analysis with seasonal focus
        ai_analysis = await analyzer.analyze_single_food(
            food_item=food,
            user_constitution=user_constitution,
            current_season=target_season
        )
        
        # Extract seasonal-specific recommendations
        seasonal_recommendations = {
            "food_name": food["food_name"],
            "target_season": target_season,
            "seasonal_suitability": ai_analysis.get("seasonal_guidance", {}),
            "preparation_modifications": ai_analysis.get("seasonal_guidance", {}).get("seasonal_modifications", ""),
            "constitution_specific_advice": ai_analysis.get("personalized_recommendations", {}),
            "overall_recommendation": "suitable" if ai_analysis.get("overall_score", 0) > 70 else "modify" if ai_analysis.get("overall_score", 0) > 50 else "avoid"
        }
        
        return seasonal_recommendations
        
    except Exception as e:
        logger.error(f"Seasonal recommendations failed for food {food_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate seasonal recommendations: {str(e)}")

@app.get("/api/dashboard/ai-insights")
async def get_dashboard_ai_insights(
    current_user: User = Depends(get_current_user)
):
    """Get AI-powered insights for dashboard"""
    
    try:
        # Get recent diet analyses
        recent_analyses = await db.diet_analyses.find({
            "practitioner_id": current_user.id
        }).sort("analysis_date", -1).limit(5).to_list(length=5)
        
        # Get client distribution by dosha
        clients_cursor = db.clients.find({"practitioner_id": current_user.id})
        clients = await clients_cursor.to_list(length=None)
        
        dosha_distribution = {"vata": 0, "pitta": 0, "kapha": 0}
        for client in clients:
            dosha = client.get("primary_dosha", "vata")
            dosha_distribution[dosha] = dosha_distribution.get(dosha, 0) + 1
        
        # Get current season
        current_season = get_current_season()
        
        # Prepare insights
        insights = {
            "total_ai_analyses": len(recent_analyses),
            "current_season": current_season,
            "seasonal_recommendation": f"Focus on {current_season}-appropriate foods for optimal health",
            "dosha_distribution": dosha_distribution,
            "recent_analyses": [
                {
                    "analysis_id": analysis["_id"],
                    "client_id": analysis["client_id"],
                    "analysis_date": analysis["analysis_date"],
                    "key_insights": analysis.get("ai_analysis", {}).get("overall_assessment", "Analysis available")[:100] + "..."
                }
                for analysis in recent_analyses
            ],
            "seasonal_tips": {
                "winter": "Emphasize warming foods, reduce raw foods, increase healthy fats",
                "spring": "Focus on detoxifying foods, reduce heavy foods, include bitter tastes",
                "monsoon": "Prefer warm, dry foods, avoid fermented foods, boost digestion",
                "autumn": "Balance with sweet and sour tastes, moderate portions, regular timing"
            }.get(current_season, "Follow seasonal eating principles")
        }
        
        return insights
        
    except Exception as e:
        logger.error(f"Dashboard AI insights failed: {e}")
        return {
            "error": "Failed to generate AI insights",
            "current_season": get_current_season(),
            "basic_recommendation": "Follow traditional Ayurvedic principles for optimal health"
        }

# Client Management Routes
@app.post("/api/clients")
async def create_client(
    client_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Create a new client profile"""
    
    client_id = str(uuid.uuid4())
    client_doc = {
        "_id": client_id,
        "name": client_data["name"],
        "age": client_data["age"],
        "gender": client_data["gender"],
        "height": client_data["height"],
        "weight": client_data["weight"],
        "contact_email": client_data.get("contact_email"),
        "contact_phone": client_data.get("contact_phone"),
        "primary_dosha": client_data["primary_dosha"],
        "secondary_dosha": client_data.get("secondary_dosha"),
        "health_goals": client_data.get("health_goals", []),
        "dietary_restrictions": client_data.get("dietary_restrictions", []),
        "medical_conditions": client_data.get("medical_conditions", []),
        "practitioner_id": current_user.id,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.clients.insert_one(client_doc)
    
    return {"message": "Client created successfully", "client_id": client_id}

@app.get("/api/clients")
async def get_clients(
    current_user: User = Depends(get_current_user)
):
    """Get all clients for the current practitioner"""
    
    clients_cursor = db.clients.find({"practitioner_id": current_user.id})
    clients = await clients_cursor.to_list(length=None)
    
    return [
        {
            "id": str(client["_id"]),
            "name": client["name"],
            "age": client["age"],
            "gender": client["gender"],
            "primary_dosha": client["primary_dosha"],
            "created_at": client["created_at"]
        }
        for client in clients
    ]

@app.get("/api/clients/{client_id}")
async def get_client_details(
    client_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed client information"""
    
    client = await db.clients.find_one({"_id": client_id, "practitioner_id": current_user.id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return ClientProfile(
        id=str(client["_id"]),
        name=client["name"],
        age=client["age"],
        gender=client["gender"],
        height=client["height"],
        weight=client["weight"],
        contact_email=client.get("contact_email"),
        contact_phone=client.get("contact_phone"),
        primary_dosha=DoshaType(client["primary_dosha"]),
        secondary_dosha=DoshaType(client["secondary_dosha"]) if client.get("secondary_dosha") else None,
        health_goals=client.get("health_goals", []),
        dietary_restrictions=client.get("dietary_restrictions", []),
        medical_conditions=client.get("medical_conditions", []),
        created_at=client["created_at"],
        practitioner_id=client["practitioner_id"]
    )

# Prakriti Assessment Routes
@app.post("/api/assessments/prakriti")
async def create_prakriti_assessment(
    assessment_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Create a new Prakriti (constitutional) assessment"""
    
    assessment_id = str(uuid.uuid4())
    assessment_doc = {
        "_id": assessment_id,
        "client_id": assessment_data["client_id"],
        "practitioner_id": current_user.id,
        "assessment_date": datetime.now(timezone.utc),
        "vata_score": assessment_data["vata_score"],
        "pitta_score": assessment_data["pitta_score"],
        "kapha_score": assessment_data["kapha_score"],
        "primary_dosha": assessment_data["primary_dosha"],
        "secondary_dosha": assessment_data.get("secondary_dosha"),
        "assessment_notes": assessment_data.get("assessment_notes")
    }
    
    await db.assessments.insert_one(assessment_doc)
    
    # Update client's dosha information
    await db.clients.update_one(
        {"_id": assessment_data["client_id"]},
        {
            "$set": {
                "primary_dosha": assessment_data["primary_dosha"],
                "secondary_dosha": assessment_data.get("secondary_dosha")
            }
        }
    )
    
    return {"message": "Assessment created successfully", "assessment_id": assessment_id}

# Diet Plan Routes
@app.post("/api/diet-plans")
async def create_diet_plan(
    plan_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Create a new diet plan for a client"""
    
    plan_id = str(uuid.uuid4())
    plan_doc = {
        "_id": plan_id,
        "client_id": plan_data["client_id"],
        "practitioner_id": current_user.id,
        "plan_name": plan_data["plan_name"],
        "duration_days": plan_data["duration_days"],
        "meals": plan_data["meals"],
        "ayurvedic_guidelines": plan_data.get("ayurvedic_guidelines", []),
        "created_at": datetime.now(timezone.utc),
        "status": "active"
    }
    
    await db.diet_plans.insert_one(plan_doc)
    
    return {"message": "Diet plan created successfully", "plan_id": plan_id}

@app.get("/api/diet-plans/client/{client_id}")
async def get_client_diet_plans(
    client_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all diet plans for a specific client"""
    
    plans_cursor = db.diet_plans.find({
        "client_id": client_id,
        "practitioner_id": current_user.id
    })
    plans = await plans_cursor.to_list(length=None)
    
    return [
        {
            "id": str(plan["_id"]),
            "plan_name": plan["plan_name"],
            "duration_days": plan["duration_days"],
            "status": plan["status"],
            "created_at": plan["created_at"]
        }
        for plan in plans
    ]

@app.post("/api/diet-plans/generate")
async def generate_diet_plan(
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Auto-generate a 7-day diet plan leveraging dosha and food database.

    Expected payload: {
      client_id: str,
      duration_days?: int (default 7),
      daily_kcal_target?: float (optional),
      exclude_ingredients?: [str]
    }
    """
    client_id = payload.get("client_id")
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id is required")

    client = await db.clients.find_one({"_id": client_id, "practitioner_id": current_user.id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    primary_dosha = client.get("primary_dosha", "vata")
    restrictions = set(map(str.lower, client.get("dietary_restrictions", [])))
    medical_conditions = set(map(str.lower, client.get("medical_conditions", [])))
    exclude_ingredients = set(map(str.lower, payload.get("exclude_ingredients", [])))

    duration_days = int(payload.get("duration_days", 7))
    if duration_days < 1 or duration_days > 28:
        raise HTTPException(status_code=400, detail="duration_days must be between 1 and 28")

    # Build food selection criteria based on dosha
    def dosha_filter(dosha: str) -> Dict[str, Any]:
        key = f"ayurvedic_properties.dosha_effects.{dosha}"
        return {key: {"$in": ["decreases", "neutral"]}}

    query_filter: Dict[str, Any] = {
        **dosha_filter(primary_dosha),
        # Prefer recipes category
        "category": {"$in": ["recipe", "food", "item", "Recipe", "Food"]}
    }

    foods_cursor = db.foods.find(query_filter).limit(500)
    foods = await foods_cursor.to_list(length=500)
    if not foods:
        raise HTTPException(status_code=404, detail="No suitable foods found to generate a plan")

    # Simple filters: handle vegetarian/non-veg keywords and ingredient exclusions
    def is_food_allowed(food: Dict[str, Any]) -> bool:
        name = str(food.get("food_name", "")).lower()
        if "vegetarian" in restrictions or "veg" in restrictions:
            blocked = ["chicken", "mutton", "fish", "egg", "prawn", "beef"]
            if any(b in name for b in blocked):
                return False
            for ing in food.get("ingredients", []) or []:
                if any(b in str(ing.get("name", "")).lower() for b in blocked):
                    return False
        if "gluten-free" in restrictions:
            if any(w in name for w in ["wheat", "atta", "maida", "roti", "chapati"]):
                return False
        # Ingredient-level excludes from payload
        for ing in food.get("ingredients", []) or []:
            if any(x in str(ing.get("name", "")).lower() for x in exclude_ingredients):
                return False
        return True

    allowed_foods = [f for f in foods if is_food_allowed(f)]
    if not allowed_foods:
        raise HTTPException(status_code=404, detail="No foods remain after applying restrictions")

    # Heuristic meal template per day
    # Choose items by simple macros: breakfast (carb + protein mild), lunch (balanced), dinner (light)
    def pick_meal(tags: List[str]) -> Optional[Dict[str, Any]]:
        for food in allowed_foods:
            name = str(food.get("food_name", "")).lower()
            if any(t in name for t in tags):
                return food
        return None

    meals: List[Dict[str, Any]] = []
    all_day_totals: List[NutritionInfo] = []
    day_tags = [
        ( ["idli", "poha", "upma", "dosa", "paratha", "oats"],
          ["dal", "sabzi", "rice", "roti", "khichdi", "curry"],
          ["khichdi", "soup", "dal", "veg", "rice"] ),
    ]
    # fallback if tag-based pick fails, just pick any
    def first_or_any(tags: List[str]) -> Dict[str, Any]:
        item = pick_meal(tags)
        return item or allowed_foods[0]

    for day in range(duration_days):
        breakfast = first_or_any(day_tags[0][0])
        lunch = first_or_any(day_tags[0][1])
        dinner = first_or_any(day_tags[0][2])

        def pack(food: Dict[str, Any]) -> Dict[str, Any]:
            nut = food.get("nutrition_per_serving") or food.get("nutrition_per_100g") or {}
            return {
                "food_id": str(food.get("_id")),
                "name": food.get("food_name"),
                "serving_size": food.get("serving_size") or "1 serving",
                "nutrition": nut,
                "ayurvedic": food.get("ayurvedic_properties"),
            }

        day_meals = {
            "day": day + 1,
            "breakfast": pack(breakfast),
            "lunch": pack(lunch),
            "dinner": pack(dinner),
            "snacks": [],
        }
        meals.append(day_meals)

        # Sum nutrition for the day
        n_infos = []
        for m in [breakfast, lunch, dinner]:
            src = m.get("nutrition_per_serving") or m.get("nutrition_per_100g")
            if src:
                n_infos.append(NutritionInfo(**src))
        day_total = _sum_nutrition(n_infos) if n_infos else NutritionInfo(
            energy_kcal=0, protein_g=0, fat_g=0, carb_g=0, fiber_g=0, calcium_mg=0, iron_mg=0, vitamin_c_mg=0
        )
        all_day_totals.append(day_total)

    plan_total = _sum_nutrition(all_day_totals)

    plan_id = str(uuid.uuid4())
    plan_doc = {
        "_id": plan_id,
        "client_id": client_id,
        "practitioner_id": current_user.id,
        "plan_name": f"{primary_dosha.capitalize()}-balancing Plan",
        "duration_days": duration_days,
        "meals": meals,
        "ayurvedic_guidelines": [
            f"Emphasize foods that balance {primary_dosha}",
            "Eat at regular times; avoid late-night meals",
            "Prefer freshly cooked meals over processed foods",
        ],
        "created_at": datetime.now(timezone.utc),
        "status": "active",
        "total_nutrition": plan_total.dict(),
    }

    await db.diet_plans.insert_one(plan_doc)

    return {"message": "Diet plan generated", "plan_id": plan_id, "plan": plan_doc}

# Dashboard and Analytics Routes
@app.get("/api/dashboard/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user)
):
    """Get dashboard statistics for the practitioner"""
    
    # Count clients
    total_clients = await db.clients.count_documents({"practitioner_id": current_user.id})
    
    # Count active diet plans
    active_plans = await db.diet_plans.count_documents({
        "practitioner_id": current_user.id,
        "status": "active"
    })
    
    # Count assessments this month
    start_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_assessments = await db.assessments.count_documents({
        "practitioner_id": current_user.id,
        "assessment_date": {"$gte": start_of_month}
    })
    
    # Count total foods in database
    total_foods = await db.foods.count_documents({})
    
    return {
        "total_clients": total_clients,
        "active_diet_plans": active_plans,
        "monthly_assessments": monthly_assessments,
        "available_foods": total_foods,
        "practice_name": current_user.practice_name or "Ayurvedic Practice"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)