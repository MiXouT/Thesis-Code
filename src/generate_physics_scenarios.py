import sys
import os
import numpy as np
import plotly.graph_objects as go

# Add src to path if running from root
current_dir = os.path.dirname(os.path.abspath(__file__))  # This is src/
parent_dir = os.path.dirname(current_dir)  # This is root/
sys.path.append(current_dir)

# Now imports should work directly
try:
    from environment import Building, Room, Point
    from physics import LossMatrix
    from visualization import Visualizer
except ImportError:
    # Fallback if running from root with src.prefix
    sys.path.append(parent_dir)
    from src.environment import Building, Room, Point
    from src.physics import LossMatrix
    from src.visualization import Visualizer


def create_multi_floor_scenario():
    """
    Scenario A: Vertical Propagation Test
    - 2 Floors directly on top of each other.
    - Router on Floor 1.
    - Sensors on Floor 2.
    - Goal: Show signal attenuation through the ceiling/floor.
    """
    print("Generating Scenario A: Vertical Propagation...")
    b = Building("Scenario A")

    # Floor 1 Room (0-3m)
    r1 = Room("Floor 1 Room", floor_level=1, height=3.0)
    # 20x20 room
    r1.add_wall(Point(0, 0, 0), Point(20, 0, 0))
    r1.add_wall(Point(20, 0, 0), Point(20, 20, 0))
    r1.add_wall(Point(20, 20, 0), Point(0, 20, 0))
    r1.add_wall(Point(0, 20, 0), Point(0, 0, 0))
    b.add_room(r1)

    # Floor 2 Room (3-6m)
    # Directly above
    r2 = Room("Floor 2 Room", floor_level=2, height=3.0)
    # Note: Walls are added relative to the room's Z-base handling in Building.from_json
    # But here we are manually adding walls.
    # The Physics engine uses wall coordinates directly.
    # Room.add_wall inputs are (x,y) projected on Z=0 usually, but let's see implementation.
    # checking environment.py:
    # p1 = Point(start[0], start[1], z_base)
    # The usage in from_json suggests we manually set Z for walls.

    z_floor2 = 3.0
    r2.add_wall(Point(0, 0, z_floor2), Point(20, 0, z_floor2))
    r2.add_wall(Point(20, 0, z_floor2), Point(20, 20, z_floor2))
    r2.add_wall(Point(20, 20, z_floor2), Point(0, 20, z_floor2))
    r2.add_wall(Point(0, 20, z_floor2), Point(0, 0, z_floor2))
    b.add_room(r2)

    # 1 Router in center of Floor 1
    # Z = 1.5m (Ceiling of floor 1 is 3m, usually router is near ceiling, say 2.5m)
    candidates = [Point(10, 10, 2.5)]

    # Sensors grid on BOTH floors to show contrast
    sensors = []
    # Floor 1 Sensors
    for x in range(2, 19, 2):
        for y in range(2, 19, 2):
            sensors.append(Point(x, y, 1.0))  # Desk height
    # Floor 2 Sensors
    for x in range(2, 19, 2):
        for y in range(2, 19, 2):
            sensors.append(Point(x, y, 4.0))  # Desk height (3.0 + 1.0)

    # Compute Physics
    lm = LossMatrix(b, candidates, sensors)
    loss_grid = lm.compute()

    # Visualize
    # We fake a genome: 1 candidate, set to Power Level 4 (Max)
    # Genome size = num_candidates = 1
    genome = np.array([4])

    viz = Visualizer(b)
    fig = viz.plot_solution(
        candidates,
        genome,
        sensors,
        loss_grid,
        title="Scenario A: Vertical Propagation (Through-Floor Loss)",
    )

    # Force Camera View to Side
    fig.update_layout(scene_camera=dict(eye=dict(x=2.0, y=0.1, z=0.5)))

    fig.write_html("scenario_A_vertical.html")
    print("Saved scenario_A_vertical.html")


def create_shadow_scenario():
    """
    Scenario B: Obstacle Shadowing
    - Layout with a thick concrete core in the middle.
    - Router on left side.
    - Sensors on right side (in the shadow).
    """
    print("Generating Scenario B: Obstacle Shadowing...")
    b = Building("Scenario B")

    # Large Hall 30x20
    r1 = Room("Hall", floor_level=1, height=3.0)
    # Outer walls
    r1.add_wall(Point(0, 0, 0), Point(30, 0, 0))
    r1.add_wall(Point(30, 0, 0), Point(30, 20, 0))
    r1.add_wall(Point(30, 20, 0), Point(0, 20, 0))
    r1.add_wall(Point(0, 20, 0), Point(0, 0, 0))

    # CONCRETE CORE (Obstacle) in middle
    # x=14 to x=16 (2m thick concrete)
    # y=5 to y=15 (10m long)
    # We model this as a box of walls
    core_mat = "concrete"  # Heavy attenuation
    # Left face
    r1.add_wall(Point(14, 5, 0), Point(14, 15, 0), material=core_mat)
    # Right face
    r1.add_wall(Point(16, 5, 0), Point(16, 15, 0), material=core_mat)
    # Top face
    r1.add_wall(Point(14, 15, 0), Point(16, 15, 0), material=core_mat)
    # Bottom face
    r1.add_wall(Point(14, 5, 0), Point(16, 5, 0), material=core_mat)

    b.add_room(r1)

    # Router on LEFT side (x=5)
    candidates = [Point(5, 10, 2.5)]

    # Sensors everywhere
    sensors = []
    for x in range(1, 29, 1):
        for y in range(1, 19, 1):
            # Skip inside the core
            if 14 <= x <= 16 and 5 <= y <= 15:
                continue
            sensors.append(Point(x, y, 1.0))

    # Compute Physics
    lm = LossMatrix(b, candidates, sensors)
    loss_grid = lm.compute()

    # Visualize
    genome = np.array([4])  # Max Power

    viz = Visualizer(b)
    fig = viz.plot_solution(
        candidates,
        genome,
        sensors,
        loss_grid,
        title="Scenario B: Obstacle Shadowing (Concrete Core)",
    )

    # Force Top-Down View
    fig.update_layout(scene_camera=dict(eye=dict(x=0.1, y=0.1, z=2.5)))

    fig.write_html("scenario_B_shadow.html")
    print("Saved scenario_B_shadow.html")


if __name__ == "__main__":
    create_multi_floor_scenario()
    create_shadow_scenario()
