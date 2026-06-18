import pygame

# Window:
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 780
FPS = 60
TITLE = "ESP32: Deployed"

# Colors:
BG_DARK = (10,14,26)
BG_PANEL = (18, 24, 42)
BG_CARD = (24, 32, 56)
BG_CARD_HOVER = (30, 40, 68)

ACCENT_BLUE = (64, 156, 255)
ACCENT_GREEN = (52, 211, 153)
ACCENT_YELLOW = (251, 191, 36)
ACCENT_RED = (248, 81, 73)
ACCENT_PURPLE = (167, 139, 250)
ACCENT_ORANGE = (251, 146, 60)

TEXT_PRIMARY = (220, 230, 255)
TEXT_SECONDARY = (120, 140, 180)
TEXT_MUTED = (70, 90, 130)
TEXT_WHITE = (255, 255, 255)

BORDER_COLOR = (40, 55, 90)
BORDER_BRIGHT = (40, 90, 150)

BAR_BG = (30, 40, 68)

# Status colors:
STATUS_ONLINE = ACCENT_GREEN
STATUS_SLEEPING = ACCENT_PURPLE
STATUS_WARNING = ACCENT_YELLOW
STATUS_ERROR = ACCENT_RED

# Game clock:
GAME_MINUTES_PER_SECOND_BASE = 1.0   
TIME_SPEEDS = [0.5, 1, 2, 5, 10, 30]
DEFAULT_SPEED_INDEX = 1

DAYTIME_START = 6
DAYTIME_END = 18

# Node defaults:
DEFAULT_NODE_NAME = "ESP32 Node"

BATTERY_START_UNITS = 1000
BATTERY_CAPACITY_L1 = 1000
BATTERY_CAPACITY_L2 = 1500
BATTERY_CAPACITY_L3 = 2000
BATTERY_CAPACITY_L4 = 3000
BATTERY_CAPACITIES = [BATTERY_CAPACITY_L1, BATTERY_CAPACITY_L2, BATTERY_CAPACITY_L3, BATTERY_CAPACITY_L4]

STORAGE_CAPACITY_MB = 1000

DATA_QUALITY_START = 100
CREDITS_START = 100

# Power Consumption:
AWAKE_DRAIN_PER_MINUTE = 0.05
SLEEP_DRAIN_PER_MINUTE = 0.005

SAMPLE_ENERGY_COST = 0.1
SAMPLE_DATA_MB = 1

UPLOAD_BASE_COST = 1.0
UPLOAD_PER_MB_COST = 0.005

# Antenna:
ANTENNA_UPLOAD_SUCCESS = [0.90, 0.94, 0.97, 0.99]
ANTENNA_COST_MULTIPLIER = [1.0, 0.9, 0.8, 0.7]

# Solar:
SOLAR_BASE_PER_HOUR = {
    "Sunny": 6.0,
    "Cloudy": 3.0,
    "Rainy": 1.0,
    "Storm": 0.0,
}
SOLAR_MULTIPLIERS = [1.0, 1.25, 1.5, 2.0]

# Upgrade Costs:
UPGRADE_COSTS = {
    "battery": [0,200,500,1000],
    "solar": [0, 250, 600, 1200],
    "antenna": [0, 250, 600, 1200],
}

# Data Quality:
DQ_SAMPLE_BONUS = 0.02
DQ_UPLOAD_SUCCESS_BONUS = 0.2
DQ_UPLOAD_FAIL_PENALTY = 3.0
DQ_IDLE_PENALTY_PER_MIN = 0.008
DQ_STORAGE_FULL_PENALTY = 0.08
DQ_MIN = 0
DQ_MAX = 100

# Upload Reward: 
UPLOAD_REWARD_DIVISOR = 1000  # (MB * DQ) / 1000

# Win-Loss Conditions:
WIN_DAY = 365
LOSE_BATTERY = 0
LOSE_DQ = 20
LOSE_STORAGE_FULL_DAYS = 7

# Events:
MINOR_EVENT_CHANCE_WEEKLY = 0.80
MAJOR_EVENT_CHANCE_MONTHLY = 0.10

MINOR_EVENTS = [
    {
        "id": "light_dust",
        "name": "Light Dust on Panel",
        "description": "Dust accumulation is reducing solar output by 10%.",
        "solar_penalty": 0.10,
        "upload_penalty": 0.0,
        "fix_cost": 25,
        "severity": "minor",
    },
    {
        "id": "heavy_dust",
        "name": "Heavy Dust on Panel",
        "description": "Heavy dust is blocking solar generation by 30%.",
        "solar_penalty": 0.30,
        "upload_penalty": 0.0,
        "fix_cost": 100,
        "severity": "minor",
    },
    {
        "id": "wifi_minor",
        "name": "Minor WiFi Tower Issue",
        "description": "Local tower is experiencing intermittent issues. Upload success -10%.",
        "solar_penalty": 0.0,
        "upload_penalty": 0.10,
        "fix_cost": 50,
        "severity": "minor",
    },
    {
        "id": "sensor_drift",
        "name": "Sensor Drift",
        "description": "Sensor readings are drifting. Data Quality will degrade over time.",
        "solar_penalty": 0.0,
        "upload_penalty": 0.0,
        "dq_drain": 0.1,
        "fix_cost": 120,
        "severity": "minor",
    },
    {
        "id": "bird_nest",
        "name": "Bird Nest on Antenna",
        "description": "A bird has nested on the antenna. Upload success -20%.",
        "solar_penalty": 0.0,
        "upload_penalty": 0.20,
        "fix_cost": 75,
        "severity": "minor",
    },
]

MAJOR_EVENTS = [
    {
        "id": "wifi_major",
        "name": "Major WiFi Tower Failure",
        "description": "The regional tower is down. Upload success -50%",
        "solar_penalty": 0.0,
        "upload_penalty": 0.50,
        "fix_cost": 200,
        "severity": "major",
    },
    {
        "id": "battery_damage",
        "name": "Battery Damage",
        "description": "Physical damage has reduced battery capacity by 10%",
        "capacity_penalty": 0.10,
        "solar_penalty": 0.0,
        "upload_penalty": 0.0,
        "fix_cost": 300,
        "severity": "major",
    },
    {
        "id": "solar_damage",
        "name": "Solar Panel Damage",
        "description": "Storm damage has cut solar generation by 50%.",
        "solar_penalty": 0.50,
        "upload_penalty": 0.0,
        "fix_cost": 250,
        "severity": "major",
    },
]

# Default Player Settings:
DEFAULT_SAMPLE_INTERVAL_MIN = 10
DEFAULT_UPLOAD_INTERVAL_MIN = 60
DEFAULT_SLEEP_DURATION_MIN = 5

# UI Layout:
SIDEBAR_WIDTH = 260
TOPBAR_HEIGHT = 60
CARD_PADDING = 14
CARD_RADIUS = 10
LOG_MAX_LINES = 50