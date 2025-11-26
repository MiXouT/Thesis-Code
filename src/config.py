# Simulation Configuration

# Environment
GRID_SIZE = 1.0  # Meters per grid unit
BUILDING_DIMENSIONS = (60, 40, 21)  # x, y, z (meters)

# Signal Propagation
FREQUENCY_HZ = 2.4e9  # 2.4 GHz
import json
import os

# Load external config if available
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

# Defaults
TX_POWER_LEVELS = {
    1: 10.0,
    2: 24.0,
    3: 32.0,
    4: 40.0,
}
ROUTER_BASE_LOAD_WATTS = 6.0
POE_ENABLED = False
POE_MAX_DISTANCE = 0.5

if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            config_data = json.load(f)
            if "TX_POWER_LEVELS" in config_data:
                # Convert keys to int since JSON keys are always strings
                TX_POWER_LEVELS = {
                    int(k): float(v) for k, v in config_data["TX_POWER_LEVELS"].items()
                }
            if "ROUTER_BASE_LOAD_WATTS" in config_data:
                ROUTER_BASE_LOAD_WATTS = float(config_data["ROUTER_BASE_LOAD_WATTS"])

            POE_ENABLED = config_data.get("POE_ENABLED", False)
            POE_MAX_DISTANCE = config_data.get("POE_MAX_DISTANCE", 0.5)

            print(f"Loaded config from {CONFIG_FILE}")
    except Exception as e:
        print(f"Error loading config.json: {e}")

# Radio Power (Watts) added to Base Load
TX_POWER_WATTS = {
    1: 0.003,
    2: 0.015,
    3: 0.040,
    4: 0.100,
}
RX_SENSITIVITY_DBM = -80.0
PATH_LOSS_EXPONENT = 2.5
REFERENCE_DISTANCE = 1.0  # Meters

# Material Attenuation (dB)
WALL_ATTENUATION = {
    "concrete": 15.0,
    "brick": 10.0,
    "drywall": 4.0,
    "glass": 3.0,
    "wood": 5.0,
}
FLOOR_ATTENUATION = 15.0  # dB per floor

# Optimization
POPULATION_SIZE = 200
GENERATIONS = 200
ROUTER_COUNT_MIN = 1
ROUTER_COUNT_MAX = 15
