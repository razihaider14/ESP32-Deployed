import random
from constants import SOLAR_BASE_PER_HOUR

WEATHER_TYPES = ["Sunny", "Cloudy", "Rainy", "Storm"]

SEASON_TRANSITIONS = {
    "Spring": {"Sunny": 0.40, "Cloudy": 0.35, "Rainy": 0.20, "Storm": 0.05},
    "Summer": {"Sunny": 0.65, "Cloudy": 0.20, "Rainy": 0.10, "Storm": 0.05},
    "Autumn": {"Sunny": 0.25, "Cloudy": 0.40, "Rainy": 0.25, "Storm": 0.10},
    "Winter": {"Sunny": 0.20, "Cloudy": 0.35, "Rainy": 0.30, "Storm": 0.15},
}

SEASON_NAMES = ["Spring", "Summer", "Autumn", "Winter"]
SEASON_LENGTH_DAYS = 365 / 4

WEATHER_ICONS = {
    "Sunny":"[Sun]",
    "Cloudy": "[CLD]",
    "Rainy": "[RAN]",
    "Storm": "[STM]",
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
        self._start_season = random.choice(SEASON_NAMES)
        self.season = self._start_season 

    def update(self, delta_minutes: float, current_hour: float = 12, current_day: int = 1):
        self.minutes_since_change += delta_minutes
        self._current_hour = current_hour

        start_index = SEASON_NAMES.index(self.season) if current_day == 1 else (SEASON_NAMES.index(self._start_season) + int((current_day - 1) / SEASON_LENGTH_DAYS)) % 4
        self.season = SEASON_NAMES[start_index]
        
        if self.minutes_since_change >= WEATHER_CHANGE_INTERVAL:
            self.minutes_since_change = 0
            self._transition()

    def _transition(self):
        probs = SEASON_TRANSITIONS[self.season]
        roll = random.random()
        cumulative = 0.0
        for weather, prob in probs.items():
            cumulative += prob
            if roll<= cumulative:
                self.current = weather
                break
        else:
            self.current = list(probs.keys())[-1]

        hour = (self._current_hour) if hasattr(self, '_current_hour') else 12
        if self.current == "Sunny" and not (6 <= hour < 18):
            self.current = "Cloudy"

    def get_solar_base(self) -> float:
        return SOLAR_BASE_PER_HOUR.get(self.current, 0.0)
    
    def get_icon(self) -> str:
        return WEATHER_ICONS.get(self.current, "?")
    
    def get_color(self):
        return WEATHER_COLORS.get(self.current, (255, 255, 255))
    
    def force(self, weather: str):
        if weather in WEATHER_TYPES:
            self.current = weather 