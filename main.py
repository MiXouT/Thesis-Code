import sys
import os
import numpy as np
import pandas as pd
import plotly.io as pio

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.environment import Building, Room, Point
from src.physics import LossMatrix
from src.optimization import Optimizer
from src.visualization import Visualizer
import src.geometry as geometry
import src.config as config
import src.baseline as baseline


def get_building_from_config():
    layout_file = os.path.join(os.path.dirname(__file__), "layout.json")
    if not os.path.exists(layout_file):
        raise FileNotFoundError(f"Layout file not found: {layout_file}")
    return Building.from_json(layout_file)


def generate_grid_points(building, spacing=2.0, height_offset=1.5):
    points = []
    # 60x40 footprint
    x_range = np.arange(1, 59, spacing)
    y_range = np.arange(1, 39, spacing)

    # Dynamic Z generation based on building floors
    unique_floors = {}
    for room in building.rooms:
        if not room.walls:
            continue

        # Get the base Z of the floor this room is on
        min_z = room.bounds()[2]
        if room.floor_level not in unique_floors:
            unique_floors[room.floor_level] = min_z

    floors_z = []
    for level, base_z in unique_floors.items():
        floors_z.append(base_z + height_offset)

    for z in floors_z:
        for x in x_range:
            for y in y_range:
                p = Point(x, y, z)
                # Simple check: is it roughly inside the 60x40 box?
                if building.is_point_inside(p):
                    points.append(p)
    return points


def main():
    print("=== IoT Router Placement Simulation ===")

    # 1. Setup Environment
    building = get_building_from_config()
    print(f"Building created: {len(building.rooms)} rooms.")

    # 2. Generate Points
    # Candidates: Coarse grid (e.g., every 5m for larger building)
    candidates = generate_grid_points(
        building, spacing=5.0, height_offset=2.5
    )  # Ceiling height (adjusted to be < 3.0m room height)
    print(f"Generated {len(candidates)} candidate router locations.")

    # Sensors: Fine grid (e.g., every 1.5m to keep count reasonable)
    sensors = generate_grid_points(
        building, spacing=1.5, height_offset=1.0
    )  # Desk height
    print(f"Generated {len(sensors)} sensor locations.")

    # 3. Compute Physics
    lm = LossMatrix(building, candidates, sensors)
    loss_matrix = lm.compute()

    # 3b. Precompute Wall Distances for PoE Constraint
    print("Precomputing wall distances...")
    # Extract walls from building
    walls = []
    for room in building.rooms:
        for wall in room.walls:
            # Wall is a Wall object, need start/end
            # Wall.start and Wall.end are Point objects
            walls.append(
                {"start": [wall.start.x, wall.start.y], "end": [wall.end.x, wall.end.y]}
            )

    # Convert candidates to numpy array for geometry function
    candidate_coords = np.array([[p.x, p.y, p.z] for p in candidates])
    wall_dist_cache = geometry.precompute_wall_distances(candidate_coords, walls)
    print("Wall distance cache built.")

    # 4. Run Optimization
    optimizer = Optimizer(loss_matrix, wall_dist_cache)
    res = optimizer.run()

    # 5. Analyze Results
    # Get best solution (Trade-off)
    F = res.F
    # F[:, 0] is Uncovered Sensors (Min)
    # F[:, 1] is Total Power (Min)
    # F[:, 2] is Interference (Min)

    # Find solution with max coverage (min uncovered), then min power
    # Sort by Uncovered (asc), then Power (asc)
    sorted_indices = np.lexsort((F[:, 1], F[:, 0]))
    best_idx = sorted_indices[0]

    best_solution = res.X[best_idx]
    best_objectives = res.F[best_idx]

    # Ensure best_solution is integer for visualization
    best_solution = np.round(best_solution).astype(int)

    active_routers = np.sum(best_solution > 0)
    best_uncovered = best_objectives[0]
    best_power = best_objectives[1]
    best_interference = best_objectives[2]

    print(
        f"\nBest AI Solution: {active_routers} Routers, {best_uncovered} Uncovered, {best_power:.2f} Watts, {best_interference} Interfered"
    )

    print("\n--- Baseline Comparison ---")
    # Run Baselines
    # Need to pass candidates to grid baseline for sorting
    # Convert candidates to numpy array of [x, y, z]
    candidate_coords = np.array([[p.x, p.y, p.z] for p in candidates])

    random_X, random_F, random_G = baseline.generate_random_solutions(
        optimizer.problem, n_solutions=50
    )
    grid_X, grid_F, grid_G = baseline.generate_grid_solutions(
        optimizer.problem, candidate_coords
    )

    print(f"Random Baseline: Generated {len(random_F)} solutions.")
    print(f"Grid Baseline: Generated {len(grid_F)} solutions.")

    # 7. Visualize
    viz = Visualizer(building)

    # Construct Metadata Title
    poe_status = "On" if config.POE_ENABLED else "Off"
    tx_levels = list(config.TX_POWER_LEVELS.values())
    meta_title = f"{building.name} | Base Load: {config.ROUTER_BASE_LOAD_WATTS}W | PoE: {poe_status} | Tx Levels: {tx_levels} dBm"

    # Plot Pareto Front (3D/Multi-plot)
    fig_pareto = viz.plot_pareto_front(
        res, random_F=random_F, grid_F=grid_F, title=f"Pareto Front - {meta_title}"
    )
    fig_pareto.write_html("pareto_front.html")
    print("Saved pareto_front.html")

    # Plot Best Solution
    # Pass the full integer genome
    fig_sol = viz.plot_solution(
        candidates,
        best_solution,
        sensors,
        loss_matrix,
        title=f"Best Solution ({active_routers} Routers, {best_power:.2f}W) <br> {meta_title}",
    )
    fig_sol.write_html("solution_map.html")
    print("Saved solution_map.html")


if __name__ == "__main__":
    main()
