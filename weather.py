import random
from constants import SOLAR_BASE_PER_HOUR

WEATHER_TYPES = ["Sunny", "Cloudy", "Rainy", "Storm"]

WEATHER_TRANSITIONS = {
    "Sunny": {"Sunny": 0.60, "Cloudy": 0.30, "Rainy": 0.08, "Storm": 0.02},
    "Cloudy": {"Sunny": 0.25, "Cloudy": 0.40, "Rainy": 0.30, "Storm": 0.05},
    "Rainy": {"Sunny": 0.10, "Cloudy": 0.35, "Rainy": 0.40, "Storm": 0.15},
    "Storm": {"Sunny": 0.05, "Cloudy": 0.20, "Rainy": 0.40, "Storm": 0.35},
}

WEATHER_ICONS = {
    "Sunny":"☀️",
    "Cloudy": "⛅",
    "Rainy": "🌧️",
    "Storm": "⛈️",
}

WEATHER_COLORS = {
    "Sunny": (251, 191, 36),
    "Cloudy": (148, 163, 184),
    "Rainy": (96, 165, 250),
    "Storm": (167, 139, 250),
}

WEATHER_CHANGE_INTERVAL = 120 # every 2 hours

class WeatherSystem:
    def __init__(self):
        self.current = "Sunny"
        self.minutes_since_change = 0

    def update(self, delta_minutes: float):
        self.minutes_since_change += delta_minutes
        if self.minutes_since_change >= WEATHER_CHANGE_INTERVAL:
            self.minutes_since_change = 0
            self._transition()

    def _transition(self):
        probs = WEATHER_TRANSITIONS[self.current]
        roll = random.random()
        cumulative = 0.0
        for weather, prob in probs.items():
            cumulative += prob
            if roll<= cumulative:
                self.current = weather
                return
        self.current = list(probs.keys())[-1]

    def get_solar_base(self) -> float:
        return SOLAR_BASE_PER_HOUR.get(self.current, 0.0)
    
    def get_icon(self) -> str:
        return WEATHER_ICONS.get(self.current, "?")
    
    def get_color(self):
        return WEATHER_COLORS.get(self.current, (255, 255, 255))
    
    def force(self, weather: str):
        if weather in WEATHER_TYPES:
            self.current = weather 