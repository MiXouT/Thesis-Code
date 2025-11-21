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
import baseline


def create_test_building():
    b = Building("Research Lab Complex")

    # 60x40x21 Building (3 Floors)
    # Floor height = 7.0m (21m / 3)
    floor_height = 7.0

    for floor in range(3):
        suffix = f"_F{floor}"
        z_base = floor * floor_height

        # Room 1: 0,0 to 30,20 (Lobby/Common)
        r1 = Room(f"Zone A{suffix}", floor_level=floor, height=floor_height)
        r1.add_wall(Point(0, 0, z_base), Point(30, 0, z_base), "concrete")
        r1.add_wall(Point(30, 0, z_base), Point(30, 20, z_base), "concrete")
        r1.add_wall(Point(30, 20, z_base), Point(0, 20, z_base), "concrete")
        r1.add_wall(Point(0, 20, z_base), Point(0, 0, z_base), "concrete")
        b.add_room(r1)

        # Room 2: 30,0 to 60,20
        r2 = Room(f"Zone B{suffix}", floor_level=floor, height=floor_height)
        r2.add_wall(Point(30, 0, z_base), Point(60, 0, z_base), "concrete")
        r2.add_wall(Point(60, 0, z_base), Point(60, 20, z_base), "concrete")
        r2.add_wall(Point(60, 20, z_base), Point(30, 20, z_base), "concrete")
        r2.add_wall(Point(30, 20, z_base), Point(30, 0, z_base), "concrete")  # Shared
        b.add_room(r2)

        # Room 3: 0,20 to 30,40
        r3 = Room(f"Zone C{suffix}", floor_level=floor, height=floor_height)
        r3.add_wall(Point(0, 20, z_base), Point(30, 20, z_base), "concrete")  # Shared
        r3.add_wall(Point(30, 20, z_base), Point(30, 40, z_base), "concrete")
        r3.add_wall(Point(30, 40, z_base), Point(0, 40, z_base), "concrete")
        r3.add_wall(Point(0, 40, z_base), Point(0, 20, z_base), "concrete")
        b.add_room(r3)

        # Room 4: 30,20 to 60,40
        r4 = Room(f"Zone D{suffix}", floor_level=floor, height=floor_height)
        r4.add_wall(Point(30, 20, z_base), Point(60, 20, z_base), "concrete")  # Shared
        r4.add_wall(Point(60, 20, z_base), Point(60, 40, z_base), "concrete")
        r4.add_wall(Point(60, 40, z_base), Point(30, 40, z_base), "concrete")
        r4.add_wall(Point(30, 40, z_base), Point(30, 20, z_base), "concrete")  # Shared
        b.add_room(r4)

    return b


def generate_grid_points(building, spacing=2.0, height_offset=1.5):
    points = []
    # 60x40 footprint
    x_range = np.arange(1, 59, spacing)
    y_range = np.arange(1, 39, spacing)

    # Generate for each floor (3 floors, 7m each)
    # Offsets: 2.5, 9.5, 16.5 (assuming 2.5m working height relative to floor base)
    floors_z = [2.5, 9.5, 16.5]

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
    building = create_test_building()
    print(f"Building created: {len(building.rooms)} rooms.")

    # 2. Generate Points
    # Candidates: Coarse grid (e.g., every 5m for larger building)
    candidates = generate_grid_points(
        building, spacing=5.0, height_offset=3.5
    )  # Ceiling height
    print(f"Generated {len(candidates)} candidate router locations.")

    # Sensors: Fine grid (e.g., every 1.5m to keep count reasonable)
    sensors = generate_grid_points(
        building, spacing=1.5, height_offset=1.0
    )  # Desk height
    print(f"Generated {len(sensors)} sensor locations.")

    # 3. Compute Physics
    lm = LossMatrix(building, candidates, sensors)
    loss_matrix = lm.compute()

    # 4. Run Optimization
    optimizer = Optimizer(loss_matrix)
    res = optimizer.run()

    # 5. Analyze Results
    # Get best solution (Trade-off)
    # Let's pick the solution with max coverage
    F = res.F
    # F[:, 0] is Uncovered Sensors (Min), F[:, 1] is Num Routers (Min)

    # Find solution with max coverage (min uncovered)
    best_idx = np.argmin(F[:, 0])
    best_solution = res.X[best_idx]
    best_uncovered = F[best_idx, 0]
    best_routers = F[best_idx, 1]

    print(
        f"\nBest AI Solution: {int(best_routers)} Routers, {best_uncovered} Uncovered Sensors"
    )

    # 6. Run Baselines
    print("\n--- Baseline Comparison ---")
    baseline.run_random_baseline(loss_matrix, int(best_routers))
    baseline.run_grid_baseline(loss_matrix, candidates, int(best_routers))

    # 7. Visualize
    viz = Visualizer(building)

    # Plot Pareto Front
    fig_pareto = viz.plot_pareto_front(res)
    fig_pareto.write_html("pareto_front.html")
    print("Saved pareto_front.html")

    # Plot Best Solution
    active_indices = np.where(best_solution)[0]
    fig_sol = viz.plot_solution(
        candidates,
        active_indices,
        sensors,
        loss_matrix,
        title=f"Best AI Solution ({int(best_routers)} Routers)",
    )
    fig_sol.write_html("solution_map.html")
    print("Saved solution_map.html")


if __name__ == "__main__":
    main()
