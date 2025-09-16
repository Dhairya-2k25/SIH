import React, { useState, useEffect, createContext, useContext } from 'react';
import './App.css';

// Auth Context
const AuthContext = createContext(null);

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// API Base URL
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// API Client
class ApiClient {
  constructor() {
    this.baseURL = API_BASE_URL;
    this.token = localStorage.getItem('token');
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('token', token);
    } else {
      localStorage.removeItem('token');
    }
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    if (this.token) {
      config.headers.Authorization = `Bearer ${this.token}`;
    }

    if (config.body && typeof config.body !== 'string') {
      config.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url, config);
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'API request failed');
      }
      
      return data;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Auth methods
  async register(userData) {
    const response = await this.request('/api/auth/register', {
      method: 'POST',
      body: userData,
    });
    this.setToken(response.access_token);
    return response;
  }

  async login(credentials) {
    const response = await this.request('/api/auth/login', {
      method: 'POST',
      body: credentials,
    });
    this.setToken(response.access_token);
    return response;
  }

  async logout() {
    this.setToken(null);
  }

  // Food methods
  async searchFoods(query, filters = {}) {
    const params = new URLSearchParams({ query, ...filters });
    return this.request(`/api/foods/search?${params}`);
  }

  async getFoodDetails(foodId) {
    return this.request(`/api/foods/${foodId}`);
  }

  async getAyurvedicAnalysis(foodId, constitution = null) {
    const params = constitution ? `?constitution=${constitution}` : '';
    return this.request(`/api/foods/${foodId}/ayurvedic-analysis${params}`);
  }

  // Client methods
  async createClient(clientData) {
    return this.request('/api/clients', {
      method: 'POST',
      body: clientData,
    });
  }

  async getClients() {
    return this.request('/api/clients');
  }

  async getClientDetails(clientId) {
    return this.request(`/api/clients/${clientId}`);
  }

  // Dashboard methods
  async getDashboardStats() {
    return this.request('/api/dashboard/stats');
  }

  // Diet plan methods
  async createDietPlan(planData) {
    return this.request('/api/diet-plans', { method: 'POST', body: planData });
  }

  async generateDietPlan({ client_id, duration_days = 7, daily_kcal_target = null, exclude_ingredients = [] }) {
    const body = { client_id, duration_days };
    if (daily_kcal_target != null) body.daily_kcal_target = daily_kcal_target;
    if (exclude_ingredients && exclude_ingredients.length) body.exclude_ingredients = exclude_ingredients;
    return this.request('/api/diet-plans/generate', { method: 'POST', body });
  }

  // Enhanced API methods for AI analysis
  async getAIAnalysis(foodId, constitution = null, season = null) {
    const params = new URLSearchParams();
    if (constitution) params.append('constitution', constitution);
    if (season) params.append('season', season);
    return this.request(`/api/foods/${foodId}/ai-analysis?${params}`);
  }

  async analyzeDietPlanWithAI(planId, analysisParams = {}) {
    return this.request(`/api/diet-plans/${planId}/ai-analysis`, {
      method: 'POST',
      body: analysisParams,
    });
  }

  async getFoodImprovementSuggestions(problematicFoods, clientId = null, season = null) {
    return this.request('/api/foods/improvement-suggestions', {
      method: 'POST',
      body: {
        problematic_foods: problematicFoods,
        client_id: clientId,
        season: season
      }
    });
  }

  async getSeasonalRecommendations(foodId, targetSeason, constitution = null) {
    const params = new URLSearchParams({ target_season: targetSeason });
    if (constitution) params.append('constitution', constitution);
    return this.request(`/api/foods/${foodId}/seasonal-recommendations?${params}`);
  }

  async getDashboardAIInsights() {
    return this.request('/api/dashboard/ai-insights');
  }
}

const apiClient = new ApiClient();

// Components
const LoadingSpinner = () => (
  <div className="flex justify-center items-center p-8">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600"></div>
  </div>
);

const Logo = () => (
  <div className="flex items-center space-x-3">
    <div className="w-10 h-10 bg-gradient-to-br from-green-600 to-emerald-600 rounded-lg flex items-center justify-center">
      <span className="text-white font-bold text-xl">🌿</span>
    </div>
    <div>
      <h1 className="text-xl font-bold text-gray-900">AyurPractice</h1>
      <p className="text-xs text-gray-600">Nutrition & Practice Management</p>
    </div>
  </div>
);

// Auth Components
const LoginForm = ({ onToggle }) => {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await login(credentials);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto bg-white rounded-xl shadow-lg p-8">
      <div className="text-center mb-8">
        <Logo />
        <h2 className="text-2xl font-bold text-gray-900 mt-4">Welcome Back</h2>
        <p className="text-gray-600">Sign in to your Ayurvedic practice</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Username
          </label>
          <input
            type="text"
            required
            value={credentials.username}
            onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Password
          </label>
          <input
            type="password"
            required
            value={credentials.password}
            onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
        >
          {loading ? 'Signing In...' : 'Sign In'}
        </button>
      </form>

      <p className="text-center text-gray-600 mt-6">
        Don't have an account?{' '}
        <button onClick={onToggle} className="text-green-600 hover:text-green-700 font-medium">
          Sign Up
        </button>
      </p>
    </div>
  );
};

const RegisterForm = ({ onToggle }) => {
  const [userData, setUserData] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
    practice_name: '',
    license_number: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await register(userData);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto bg-white rounded-xl shadow-lg p-8">
      <div className="text-center mb-8">
        <Logo />
        <h2 className="text-2xl font-bold text-gray-900 mt-4">Create Account</h2>
        <p className="text-gray-600">Join our Ayurvedic practice platform</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Full Name *
          </label>
          <input
            type="text"
            required
            value={userData.full_name}
            onChange={(e) => setUserData({ ...userData, full_name: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Username *
          </label>
          <input
            type="text"
            required
            value={userData.username}
            onChange={(e) => setUserData({ ...userData, username: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Email *
          </label>
          <input
            type="email"
            required
            value={userData.email}
            onChange={(e) => setUserData({ ...userData, email: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Password *
          </label>
          <input
            type="password"
            required
            value={userData.password}
            onChange={(e) => setUserData({ ...userData, password: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Practice Name
          </label>
          <input
            type="text"
            value={userData.practice_name}
            onChange={(e) => setUserData({ ...userData, practice_name: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            License Number
          </label>
          <input
            type="text"
            value={userData.license_number}
            onChange={(e) => setUserData({ ...userData, license_number: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
        >
          {loading ? 'Creating Account...' : 'Create Account'}
        </button>
      </form>

      <p className="text-center text-gray-600 mt-4">
        Already have an account?{' '}
        <button onClick={onToggle} className="text-green-600 hover:text-green-700 font-medium">
          Sign In
        </button>
      </p>
    </div>
  );
};

// Dashboard Components
const DashboardStats = ({ stats }) => (
  <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className="p-2 bg-blue-100 rounded-lg">
          <span className="text-2xl">👥</span>
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">Total Clients</p>
          <p className="text-2xl font-bold text-gray-900">{stats.total_clients}</p>
        </div>
      </div>
    </div>

    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className="p-2 bg-green-100 rounded-lg">
          <span className="text-2xl">📋</span>
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">Active Diet Plans</p>
          <p className="text-2xl font-bold text-gray-900">{stats.active_diet_plans}</p>
        </div>
      </div>
    </div>

    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className="p-2 bg-yellow-100 rounded-lg">
          <span className="text-2xl">📊</span>
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">Monthly Assessments</p>
          <p className="text-2xl font-bold text-gray-900">{stats.monthly_assessments}</p>
        </div>
      </div>
    </div>

    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className="p-2 bg-purple-100 rounded-lg">
          <span className="text-2xl">🥘</span>
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">Available Foods</p>
          <p className="text-2xl font-bold text-gray-900">{stats.available_foods}</p>
        </div>
      </div>
    </div>
  </div>
);

const FoodSearchCard = ({ food, onViewDetails }) => (
  <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
    <div className="flex justify-between items-start mb-4">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">{food.food_name}</h3>
        <p className="text-sm text-gray-600">Code: {food.food_code}</p>
        <p className="text-sm text-gray-600">Source: {food.source}</p>
      </div>
      <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
        {food.category}
      </span>
    </div>

    <div className="grid grid-cols-2 gap-4 mb-4">
      <div>
        <p className="text-sm text-gray-600">Energy</p>
        <p className="font-semibold">{food.nutrition_per_100g.energy_kcal} kcal</p>
      </div>
      <div>
        <p className="text-sm text-gray-600">Protein</p>
        <p className="font-semibold">{food.nutrition_per_100g.protein_g}g</p>
      </div>
    </div>

    <div className="flex flex-wrap gap-1 mb-4">
      {food.ayurvedic_properties.primary_rasa.map((rasa, index) => (
        <span key={index} className="px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded">
          {rasa}
        </span>
      ))}
      <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
        {food.ayurvedic_properties.virya}
      </span>
    </div>

    <button
      onClick={() => onViewDetails(food)}
      className="w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 transition-colors"
    >
      View Details
    </button>
  </div>
);

const AIAnalysisModal = ({ food, analysis, onClose, onGetSuggestions }) => {
  if (!analysis) return null;

  const ScoreIndicator = ({ score, label }) => (
    <div className="text-center">
      <div className={`w-16 h-16 rounded-full flex items-center justify-center text-lg font-bold mx-auto mb-2 ${
        score >= 80 ? 'bg-green-100 text-green-800' :
        score >= 60 ? 'bg-yellow-100 text-yellow-800' :
        'bg-red-100 text-red-800'
      }`}>
        {score}
      </div>
      <p className="text-sm text-gray-600">{label}</p>
    </div>
  );

  const DoshaEffect = ({ dosha, effect }) => (
    <div className="text-center p-3 rounded-lg">
      <p className="font-medium capitalize">{dosha}</p>
      <p className={`text-sm px-2 py-1 rounded mt-1 ${
        effect === 'balancing' ? 'bg-green-100 text-green-800' :
        effect === 'aggravating' ? 'bg-red-100 text-red-800' :
        'bg-gray-100 text-gray-800'
      }`}>
        {effect}
      </p>
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">🧠 AI-Powered Analysis</h2>
              <p className="text-gray-600">{food?.food_name}</p>
              <p className="text-sm text-gray-500">Season: {analysis.season_context || 'Spring'}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ×
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Overall Score */}
            <div className="lg:col-span-1">
              <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg p-6">
                <ScoreIndicator 
                  score={analysis.ai_analysis?.overall_score || 75} 
                  label="Overall Ayurvedic Score" 
                />
                <div className="mt-4 text-center">
                  <p className="text-sm text-gray-600">
                    {analysis.ai_analysis?.overall_score >= 80 ? 'Excellent choice!' :
                     analysis.ai_analysis?.overall_score >= 60 ? 'Good with modifications' :
                     'Consider alternatives'}
                  </p>
                </div>
              </div>
            </div>

            {/* Dosha Analysis */}
            <div className="lg:col-span-2">
              <h3 className="text-lg font-semibold mb-4">Dosha Effects</h3>
              <div className="grid grid-cols-3 gap-4 mb-4">
                {analysis.ai_analysis?.dosha_analysis && (
                  <>
                    <DoshaEffect dosha="Vata" effect={analysis.ai_analysis.dosha_analysis.vata_effect} />
                    <DoshaEffect dosha="Pitta" effect={analysis.ai_analysis.dosha_analysis.pitta_effect} />
                    <DoshaEffect dosha="Kapha" effect={analysis.ai_analysis.dosha_analysis.kapha_effect} />
                  </>
                )}
              </div>
              {analysis.ai_analysis?.dosha_analysis?.explanation && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-blue-800">{analysis.ai_analysis.dosha_analysis.explanation}</p>
                </div>
              )}
            </div>
          </div>

          {/* Detailed Analysis Sections */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
            {/* Nutritional Assessment */}
            {analysis.ai_analysis?.nutritional_assessment && (
              <div>
                <h3 className="text-lg font-semibold mb-4">📊 Nutritional Assessment</h3>
                <div className="space-y-4">
                  {analysis.ai_analysis.nutritional_assessment.strengths?.length > 0 && (
                    <div>
                      <h4 className="font-medium text-green-700 mb-2">Strengths</h4>
                      <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                        {analysis.ai_analysis.nutritional_assessment.strengths.map((strength, idx) => (
                          <li key={idx}>{strength}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {analysis.ai_analysis.nutritional_assessment.concerns?.length > 0 && (
                    <div>
                      <h4 className="font-medium text-red-700 mb-2">Concerns</h4>
                      <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                        {analysis.ai_analysis.nutritional_assessment.concerns.map((concern, idx) => (
                          <li key={idx}>{concern}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Seasonal Guidance */}
            {analysis.ai_analysis?.seasonal_guidance && (
              <div>
                <h3 className="text-lg font-semibold mb-4">🌸 Seasonal Guidance</h3>
                <div className="space-y-3">
                  {analysis.ai_analysis.seasonal_guidance.best_seasons && (
                    <div>
                      <h4 className="font-medium text-gray-700 mb-2">Best Seasons</h4>
                      <div className="flex flex-wrap gap-2">
                        {analysis.ai_analysis.seasonal_guidance.best_seasons.map((season, idx) => (
                          <span key={idx} className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">
                            {season}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {analysis.ai_analysis.seasonal_guidance.seasonal_modifications && (
                    <div>
                      <h4 className="font-medium text-gray-700 mb-2">Seasonal Modifications</h4>
                      <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded">
                        {analysis.ai_analysis.seasonal_guidance.seasonal_modifications}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Food Interactions */}
          {analysis.ai_analysis?.food_interactions && (
            <div className="mt-8">
              <h3 className="text-lg font-semibold mb-4">🥘 Food Interactions</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {analysis.ai_analysis.food_interactions.beneficial_combinations?.length > 0 && (
                  <div>
                    <h4 className="font-medium text-green-700 mb-2">✅ Beneficial Combinations</h4>
                    <div className="flex flex-wrap gap-2">
                      {analysis.ai_analysis.food_interactions.beneficial_combinations.map((combo, idx) => (
                        <span key={idx} className="px-2 py-1 bg-green-100 text-green-800 rounded text-sm">
                          {combo}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {analysis.ai_analysis.food_interactions.avoid_combinations?.length > 0 && (
                  <div>
                    <h4 className="font-medium text-red-700 mb-2">❌ Avoid Combinations</h4>
                    <div className="flex flex-wrap gap-2">
                      {analysis.ai_analysis.food_interactions.avoid_combinations.map((avoid, idx) => (
                        <span key={idx} className="px-2 py-1 bg-red-100 text-red-800 rounded text-sm">
                          {avoid}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              {analysis.ai_analysis.food_interactions.timing_recommendations && (
                <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <h4 className="font-medium text-blue-700 mb-2">⏰ Best Timing</h4>
                  <p className="text-sm text-blue-800">{analysis.ai_analysis.food_interactions.timing_recommendations}</p>
                </div>
              )}
            </div>
          )}

          {/* Improvement Suggestions */}
          {analysis.ai_analysis?.improvement_suggestions?.length > 0 && (
            <div className="mt-8">
              <h3 className="text-lg font-semibold mb-4">💡 Improvement Suggestions</h3>
              <div className="space-y-4">
                {analysis.ai_analysis.improvement_suggestions.map((suggestion, idx) => (
                  <div key={idx} className="border border-gray-200 rounded-lg p-4">
                    <h4 className="font-medium text-gray-800 mb-2">Issue: {suggestion.issue}</h4>
                    <p className="text-sm text-gray-600 mb-3">{suggestion.solution}</p>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                      {suggestion.foods_to_add?.length > 0 && (
                        <div>
                          <h5 className="font-medium text-green-700">Add Foods:</h5>
                          <ul className="list-disc list-inside text-gray-600">
                            {suggestion.foods_to_add.map((food, foodIdx) => (
                              <li key={foodIdx}>{food}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {suggestion.herbs_spices?.length > 0 && (
                        <div>
                          <h5 className="font-medium text-orange-700">Herbs/Spices:</h5>
                          <ul className="list-disc list-inside text-gray-600">
                            {suggestion.herbs_spices.map((herb, herbIdx) => (
                              <li key={herbIdx}>{herb}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {suggestion.preparation_method && (
                        <div>
                          <h5 className="font-medium text-purple-700">Preparation:</h5>
                          <p className="text-gray-600">{suggestion.preparation_method}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="mt-8 flex flex-wrap gap-4">
            <button
              onClick={() => onGetSuggestions && onGetSuggestions(food)}
              className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700 transition-colors"
            >
              Get Improvement Suggestions
            </button>
            <button
              onClick={onClose}
              className="bg-gray-600 text-white px-6 py-2 rounded-lg hover:bg-gray-700 transition-colors"
            >
              Close Analysis
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const FoodDetailsModal = ({ food, onClose, onAnalyze, onAIAnalyze }) => {
  if (!food) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">{food.food_name}</h2>
              <p className="text-gray-600">Code: {food.food_code} | Source: {food.source}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ×
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Nutrition Information */}
            <div>
              <h3 className="text-lg font-semibold mb-4">Nutritional Information (per 100g)</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Energy</span>
                  <span className="font-semibold">{food.nutrition_per_100g.energy_kcal} kcal</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Protein</span>
                  <span className="font-semibold">{food.nutrition_per_100g.protein_g}g</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Fat</span>
                  <span className="font-semibold">{food.nutrition_per_100g.fat_g}g</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Carbohydrates</span>
                  <span className="font-semibold">{food.nutrition_per_100g.carb_g}g</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Fiber</span>
                  <span className="font-semibold">{food.nutrition_per_100g.fiber_g}g</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Calcium</span>
                  <span className="font-semibold">{food.nutrition_per_100g.calcium_mg}mg</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Iron</span>
                  <span className="font-semibold">{food.nutrition_per_100g.iron_mg}mg</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Vitamin C</span>
                  <span className="font-semibold">{food.nutrition_per_100g.vitamin_c_mg}mg</span>
                </div>
              </div>

              {food.nutrition_per_serving && (
                <div className="mt-6">
                  <h4 className="font-semibold mb-2">Per Serving ({food.serving_size})</h4>
                  <div className="text-sm text-gray-600">
                    <p>Energy: {food.nutrition_per_serving.energy_kcal} kcal</p>
                    <p>Protein: {food.nutrition_per_serving.protein_g}g</p>
                    <p>Carbs: {food.nutrition_per_serving.carb_g}g</p>
                  </div>
                </div>
              )}
            </div>

            {/* Ayurvedic Properties */}
            <div>
              <h3 className="text-lg font-semibold mb-4">Ayurvedic Properties</h3>
              
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-gray-700">Rasa (Taste)</h4>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {food.ayurvedic_properties.primary_rasa.map((rasa, index) => (
                      <span key={index} className="px-2 py-1 bg-orange-100 text-orange-800 text-sm rounded">
                        {rasa}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-gray-700">Virya (Potency)</h4>
                  <span className="px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded">
                    {food.ayurvedic_properties.virya}
                  </span>
                </div>

                <div>
                  <h4 className="font-medium text-gray-700">Dosha Effects</h4>
                  <div className="grid grid-cols-3 gap-2 mt-2">
                    <div className="text-center">
                      <p className="text-sm font-medium">Vata</p>
                      <p className={`text-sm px-2 py-1 rounded ${
                        food.ayurvedic_properties.dosha_effects.vata === 'increases' ? 'bg-red-100 text-red-800' :
                        food.ayurvedic_properties.dosha_effects.vata === 'decreases' ? 'bg-green-100 text-green-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {food.ayurvedic_properties.dosha_effects.vata}
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-medium">Pitta</p>
                      <p className={`text-sm px-2 py-1 rounded ${
                        food.ayurvedic_properties.dosha_effects.pitta === 'increases' ? 'bg-red-100 text-red-800' :
                        food.ayurvedic_properties.dosha_effects.pitta === 'decreases' ? 'bg-green-100 text-green-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {food.ayurvedic_properties.dosha_effects.pitta}
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-medium">Kapha</p>
                      <p className={`text-sm px-2 py-1 rounded ${
                        food.ayurvedic_properties.dosha_effects.kapha === 'increases' ? 'bg-red-100 text-red-800' :
                        food.ayurvedic_properties.dosha_effects.kapha === 'decreases' ? 'bg-green-100 text-green-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {food.ayurvedic_properties.dosha_effects.kapha}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <button
                onClick={() => onAnalyze(food)}
                className="mt-4 w-full bg-purple-600 text-white py-2 px-4 rounded-lg hover:bg-purple-700 transition-colors"
              >
                Get Detailed Analysis
              </button>
            </div>
          </div>

          {/* Ingredients */}
          {food.ingredients && food.ingredients.length > 0 && (
            <div className="mt-8">
              <h3 className="text-lg font-semibold mb-4">Recipe Ingredients</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {food.ingredients.map((ingredient, index) => (
                  <div key={index} className="bg-gray-50 p-3 rounded-lg">
                    <p className="font-medium">{ingredient.name}</p>
                    <p className="text-sm text-gray-600">
                      {ingredient.amount} {ingredient.unit}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const NutritionAnalysis = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedFood, setSelectedFood] = useState(null);
  const [showModal, setShowModal] = useState(false);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    try {
      const results = await apiClient.searchFoods(searchQuery);
      setSearchResults(results);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = (food) => {
    setSelectedFood(food);
    setShowModal(true);
  };

  const handleAnalyze = async (food) => {
    try {
      const analysis = await apiClient.getAyurvedicAnalysis(food.id);
      console.log('Analysis:', analysis);
      // You could show this in a separate modal or section
    } catch (error) {
      console.error('Analysis failed:', error);
    }
  };

  return (
    <div className="p-6">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Indian Food Nutrition Analysis</h2>
        <p className="text-gray-600 mb-6">
          Search through 1,000+ traditional Indian recipes with complete nutritional and Ayurvedic analysis
        </p>

        <div className="flex gap-4 mb-6">
          <input
            type="text"
            placeholder="Search for foods (e.g., dal, rice, chai, samosa...)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </div>

      {loading && <LoadingSpinner />}

      {searchResults.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {searchResults.map((food) => (
            <FoodSearchCard
              key={food.id}
              food={food}
              onViewDetails={handleViewDetails}
            />
          ))}
        </div>
      )}

      {showModal && (
        <FoodDetailsModal
          food={selectedFood}
          onClose={() => setShowModal(false)}
          onAnalyze={handleAnalyze}
        />
      )}
    </div>
  );
};

const ClientForm = ({ onSuccess }) => {
  const [clientData, setClientData] = useState({
    name: '',
    age: '',
    gender: 'female',
    height: '',
    weight: '',
    contact_email: '',
    contact_phone: '',
    primary_dosha: 'vata',
    secondary_dosha: '',
    health_goals: '',
    dietary_restrictions: '',
    medical_conditions: '',
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const processedData = {
        ...clientData,
        age: parseInt(clientData.age),
        height: parseFloat(clientData.height),
        weight: parseFloat(clientData.weight),
        health_goals: clientData.health_goals.split(',').map(g => g.trim()).filter(g => g),
        dietary_restrictions: clientData.dietary_restrictions.split(',').map(d => d.trim()).filter(d => d),
        medical_conditions: clientData.medical_conditions.split(',').map(m => m.trim()).filter(m => m),
        secondary_dosha: clientData.secondary_dosha || null,
      };

      await apiClient.createClient(processedData);
      onSuccess();
    } catch (error) {
      console.error('Failed to create client:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Add New Client</h3>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Full Name *
            </label>
            <input
              type="text"
              required
              value={clientData.name}
              onChange={(e) => setClientData({ ...clientData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Age *
            </label>
            <input
              type="number"
              required
              value={clientData.age}
              onChange={(e) => setClientData({ ...clientData, age: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Gender *
            </label>
            <select
              value={clientData.gender}
              onChange={(e) => setClientData({ ...clientData, gender: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
            >
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Height (cm) *
            </label>
            <input
              type="number"
              step="0.1"
              required
              value={clientData.height}
              onChange={(e) => setClientData({ ...clientData, height: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Weight (kg) *
            </label>
            <input
              type="number"
              step="0.1"
              required
              value={clientData.weight}
              onChange={(e) => setClientData({ ...clientData, weight: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Primary Dosha *
            </label>
            <select
              value={clientData.primary_dosha}
              onChange={(e) => setClientData({ ...clientData, primary_dosha: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
            >
              <option value="vata">Vata</option>
              <option value="pitta">Pitta</option>
              <option value="kapha">Kapha</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Secondary Dosha
            </label>
            <select
              value={clientData.secondary_dosha}
              onChange={(e) => setClientData({ ...clientData, secondary_dosha: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
            >
              <option value="">None</option>
              <option value="vata">Vata</option>
              <option value="pitta">Pitta</option>
              <option value="kapha">Kapha</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={clientData.contact_email}
              onChange={(e) => setClientData({ ...clientData, contact_email: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Health Goals (comma-separated)
          </label>
          <input
            type="text"
            placeholder="Weight loss, better digestion, increased energy"
            value={clientData.health_goals}
            onChange={(e) => setClientData({ ...clientData, health_goals: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Dietary Restrictions (comma-separated)
          </label>
          <input
            type="text"
            placeholder="Vegetarian, gluten-free, dairy-free"
            value={clientData.dietary_restrictions}
            onChange={(e) => setClientData({ ...clientData, dietary_restrictions: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
        >
          {loading ? 'Creating Client...' : 'Create Client'}
        </button>
      </form>
    </div>
  );
};

const ClientManagement = () => {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const loadClients = async () => {
    try {
      const clientsData = await apiClient.getClients();
      setClients(clientsData);
    } catch (error) {
      console.error('Failed to load clients:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClients();
  }, []);

  const handleClientCreated = () => {
    setShowForm(false);
    loadClients();
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Client Management</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
        >
          {showForm ? 'Cancel' : 'Add New Client'}
        </button>
      </div>

      {showForm && (
        <div className="mb-8">
          <ClientForm onSuccess={handleClientCreated} />
        </div>
      )}

      {clients.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg">No clients yet</p>
          <p className="text-gray-400">Add your first client to get started</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {clients.map((client) => (
            <div key={client.id} className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900">{client.name}</h3>
              <p className="text-gray-600">Age: {client.age} | {client.gender}</p>
              <p className="text-gray-600">Primary Dosha: {client.primary_dosha}</p>
              <p className="text-sm text-gray-500">
                Added: {new Date(client.created_at).toLocaleDateString()}
              </p>
              <button className="mt-4 w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors">
                View Details
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const DietPlans = () => {
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState('');
  const [duration, setDuration] = useState(7);
  const [exclude, setExclude] = useState('');
  const [plans, setPlans] = useState([]);
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const c = await apiClient.getClients();
      setClients(c);
      if (c.length && !selectedClient) setSelectedClient(c[0].id);
      if (c.length) {
        const ps = await apiClient.getClientPlans(c[0].id);
        setPlans(ps);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleGenerate = async () => {
    if (!selectedClient) return;
    setCreating(true);
    try {
      const excludeList = exclude.split(',').map(s => s.trim()).filter(Boolean);
      await apiClient.generateDietPlan({ client_id: selectedClient, duration_days: Number(duration), exclude_ingredients: excludeList });
      const ps = await apiClient.getClientPlans(selectedClient);
      setPlans(ps);
    } catch (e) {
      console.error('Failed to generate plan', e);
    } finally {
      setCreating(false);
    }
  };

  const handleSelectClient = async (id) => {
    setSelectedClient(id);
    try {
      const ps = await apiClient.getClientPlans(id);
      setPlans(ps);
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Diet Plans</h2>

      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h3 className="text-lg font-semibold mb-4">Generate Plan</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Client</label>
            <select value={selectedClient} onChange={(e) => handleSelectClient(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500">
              <option value="">Select client</option>
              {clients.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Duration (days)</label>
            <input type="number" min="1" max="28" value={duration} onChange={(e) => setDuration(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500" />
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Exclude Ingredients (comma-separated)</label>
            <input type="text" placeholder="e.g., chili, garlic" value={exclude} onChange={(e) => setExclude(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500" />
          </div>
        </div>
        <button onClick={handleGenerate} disabled={creating || !selectedClient} className="mt-4 bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 disabled:opacity-50">{creating ? 'Generating...' : 'Generate Plan'}</button>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Existing Plans</h3>
        {plans.length === 0 ? (
          <p className="text-gray-500">No plans yet for this client.</p>
        ) : (
          <div className="space-y-3">
            {plans.map(p => (
              <div key={p.id} className="border rounded-lg p-4 flex items-center justify-between">
                <div>
                  <p className="font-semibold">{p.plan_name}</p>
                  <p className="text-sm text-gray-600">Duration: {p.duration_days} days • Created: {new Date(p.created_at).toLocaleDateString()}</p>
                </div>
                <span className={`px-2 py-1 text-xs rounded ${p.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>{p.status}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const statsData = await apiClient.getDashboardStats();
        setStats(statsData);
      } catch (error) {
        console.error('Failed to load stats:', error);
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="p-6">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900">
          Welcome to {stats?.practice_name || 'Your Practice'}
        </h2>
        <p className="text-gray-600">Your Ayurvedic practice management dashboard</p>
      </div>

      {stats && <DashboardStats stats={stats} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <button className="w-full text-left p-3 bg-green-50 rounded-lg hover:bg-green-100 transition-colors">
              <span className="font-medium text-green-800">Add New Client</span>
              <p className="text-sm text-green-600">Create a new client profile</p>
            </button>
            <button className="w-full text-left p-3 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors">
              <span className="font-medium text-blue-800">Search Foods</span>
              <p className="text-sm text-blue-600">Analyze Indian foods and recipes</p>
            </button>
            <button className="w-full text-left p-3 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors">
              <span className="font-medium text-purple-800">Create Diet Plan</span>
              <p className="text-sm text-purple-600">Design personalized meal plans</p>
            </button>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Ayurvedic Principles</h3>
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-gray-700">The Three Doshas</h4>
              <div className="grid grid-cols-3 gap-2 mt-2">
                <div className="text-center p-2 bg-red-50 rounded">
                  <span className="text-sm font-medium text-red-800">Vata</span>
                  <p className="text-xs text-red-600">Air & Space</p>
                </div>
                <div className="text-center p-2 bg-yellow-50 rounded">
                  <span className="text-sm font-medium text-yellow-800">Pitta</span>
                  <p className="text-xs text-yellow-600">Fire & Water</p>
                </div>
                <div className="text-center p-2 bg-green-50 rounded">
                  <span className="text-sm font-medium text-green-800">Kapha</span>
                  <p className="text-xs text-green-600">Earth & Water</p>
                </div>
              </div>
            </div>
            <div>
              <h4 className="font-medium text-gray-700">Six Tastes (Rasa)</h4>
              <div className="flex flex-wrap gap-1 mt-2">
                {['Sweet', 'Sour', 'Salty', 'Pungent', 'Bitter', 'Astringent'].map((rasa) => (
                  <span key={rasa} className="px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded">
                    {rasa}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Main App Component
const MainApp = () => {
  const { user, logout } = useAuth();
  const [currentView, setCurrentView] = useState('dashboard');

  const navigation = [
    { id: 'dashboard', label: 'Dashboard', icon: '🏠' },
    { id: 'nutrition', label: 'Food Analysis', icon: '🥘' },
    { id: 'clients', label: 'Clients', icon: '👥' },
    { id: 'plans', label: 'Diet Plans', icon: '📋' },
  ];

  const renderContent = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard />;
      case 'nutrition':
        return <NutritionAnalysis />;
      case 'clients':
        return <ClientManagement />;
      case 'plans':
        return <DietPlans />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-white shadow-lg">
        <div className="p-6 border-b">
          <Logo />
        </div>

        <nav className="mt-6">
          {navigation.map((item) => (
            <button
              key={item.id}
              onClick={() => setCurrentView(item.id)}
              className={`w-full text-left px-6 py-3 flex items-center space-x-3 hover:bg-gray-50 transition-colors ${
                currentView === item.id ? 'bg-green-50 border-r-2 border-green-600 text-green-700' : 'text-gray-700'
              }`}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="font-medium">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="absolute bottom-0 w-64 p-6 border-t">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center">
              <span className="text-white text-sm font-medium">
                {user?.full_name?.charAt(0)?.toUpperCase()}
              </span>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">{user?.full_name}</p>
              <p className="text-xs text-gray-600">{user?.username}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full bg-gray-100 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        {renderContent()}
      </div>
    </div>
  );
};

// Auth Provider Component
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing token on app start
    const token = localStorage.getItem('token');
    if (token) {
      apiClient.setToken(token);
      // In a real app, you'd validate the token with the server
      // For now, we'll just set loading to false
    }
    setLoading(false);
  }, []);

  const login = async (credentials) => {
    const response = await apiClient.login(credentials);
    setUser(response.user);
  };

  const register = async (userData) => {
    const response = await apiClient.register(userData);
    setUser(response.user);
  };

  const logout = async () => {
    await apiClient.logout();
    setUser(null);
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// App Component
const App = () => {
  const [isLogin, setIsLogin] = useState(true);

  return (
    <AuthProvider>
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-50">
        <AuthContext.Consumer>
          {({ user }) => (
            user ? (
              <MainApp />
            ) : (
              <div className="flex items-center justify-center min-h-screen p-4">
                {isLogin ? (
                  <LoginForm onToggle={() => setIsLogin(false)} />
                ) : (
                  <RegisterForm onToggle={() => setIsLogin(true)} />
                )}
              </div>
            )
          )}
        </AuthContext.Consumer>
      </div>
    </AuthProvider>
  );
};

export default App;