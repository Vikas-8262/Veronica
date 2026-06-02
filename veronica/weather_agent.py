"""Live Weather Integration agent for Veronica."""

import importlib
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_weather_request(message: str) -> bool:
    """Matcher for Weather requests."""
    lowered = message.lower().strip()
    return "weather in" in lowered or "weather for" in lowered

def handle_weather_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to fetch real-time weather data for a city."""
    requests = _optional_module("requests")
    if requests is None:
        return SkillResult(True, "Weather Agent requires 'requests'. Run: pip install requests")

    lowered = message.lower().strip()
    
    # Extract city name (e.g., "what is the weather in tokyo" -> "tokyo")
    city = ""
    if "weather in" in lowered:
        city = lowered.split("weather in")[-1].strip()
    elif "weather for" in lowered:
        city = lowered.split("weather for")[-1].strip()
        
    # Strip trailing punctuation
    city = city.strip("?.!")
    
    if not city:
        return SkillResult(True, "Please specify a city (e.g., 'What is the weather in London?').")
        
    try:
        # Step 1: Geocoding (Resolve City to Lat/Lon)
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        geocode_res = requests.get(geocode_url, timeout=10)
        geocode_data = geocode_res.json()
        
        if "results" not in geocode_data or len(geocode_data["results"]) == 0:
            return SkillResult(True, f"Could not find coordinates for the city: {city.title()}")
            
        location = geocode_data["results"][0]
        lat = location["latitude"]
        lon = location["longitude"]
        resolved_name = f"{location.get('name')}, {location.get('country', '')}"
        
        # Step 2: Fetch Weather Data
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_res = requests.get(weather_url, timeout=10)
        weather_data = weather_res.json()
        
        if "current_weather" not in weather_data:
            return SkillResult(True, f"Could not fetch weather data for {resolved_name}.")
            
        current = weather_data["current_weather"]
        temp = current.get("temperature", "Unknown")
        windspeed = current.get("windspeed", "Unknown")
        
        # WMO Weather interpretation codes mapping
        wmo_codes = {
            0: "Clear sky ☀️",
            1: "Mainly clear 🌤️",
            2: "Partly cloudy ⛅",
            3: "Overcast ☁️",
            45: "Fog 🌫️",
            48: "Depositing rime fog 🌫️",
            51: "Light drizzle 🌧️",
            53: "Moderate drizzle 🌧️",
            55: "Dense drizzle 🌧️",
            61: "Slight rain ☔",
            63: "Moderate rain ☔",
            65: "Heavy rain ☔",
            71: "Slight snow fall ❄️",
            73: "Moderate snow fall ❄️",
            75: "Heavy snow fall ❄️",
            95: "Thunderstorm 🌩️"
        }
        
        weathercode = current.get("weathercode", 0)
        condition = wmo_codes.get(weathercode, "Unknown")
        
        output = (
            f"🌤️ Weather in {resolved_name}:\n"
            f"- Temperature: {temp}°C\n"
            f"- Condition: {condition}\n"
            f"- Wind Speed: {windspeed} km/h"
        )
        
        return SkillResult(True, output)
        
    except requests.RequestException as e:
        return SkillResult(True, f"Network error while fetching weather data: {e}")
    except Exception as e:
        return SkillResult(True, f"An error occurred: {e}")
