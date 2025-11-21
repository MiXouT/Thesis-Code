# Simulation Configuration

# Environment
GRID_SIZE = 1.0  # Meters per grid unit
BUILDING_DIMENSIONS = (60, 40, 21)  # x, y, z (meters)

# Signal Propagation
FREQUENCY_HZ = 2.4e9  # 2.4 GHz
TX_POWER_DBM = 5.0  # Set to 5.0 as requested
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

# Optimization
POPULATION_SIZE = 50
GENERATIONS = 50
ROUTER_COUNT_MIN = 1
ROUTER_COUNT_MAX = 5
