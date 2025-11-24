# Simulation Configuration

# Environment
GRID_SIZE = 1.0  # Meters per grid unit
BUILDING_DIMENSIONS = (60, 40, 21)  # x, y, z (meters)

# Signal Propagation
FREQUENCY_HZ = 2.4e9  # 2.4 GHz
# TX_POWER_DBM is removed in favor of variable levels
# Power Levels: 0=Off, 1=Low, 2=Med, 3=High, 4=Max
TX_POWER_LEVELS = {
    1: 10.0,  # 3mW  ~ 10dBm
    2: 24.0,  # 15mW ~ 24dBm
    3: 32.0,  # 40mW ~ 32dBm
    4: 40.0,  # 100mW ~ 40dBm
}

# Power Consumption (Watts)
# Base Load: Hardware overhead (CPU, WiFi chip idle/active baseline)
ROUTER_BASE_LOAD_WATTS = 10.0

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
POPULATION_SIZE = 50
GENERATIONS = 50
ROUTER_COUNT_MIN = 1
ROUTER_COUNT_MAX = 5
