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
    b = Building("Research Lab")

    # 40x20x6 Building (2 Floors)
    # Floor height = 3.0m

    for floor in [0, 1]:
        suffix = f"_F{floor}"
        z_base = floor * 3.0

        # Room 1: 0,0 to 20,10 (Scaled up X)
        r1 = Room(f"Lobby{suffix}", floor_level=floor)
        r1.add_wall(Point(0, 0, z_base), Point(20, 0, z_base), "concrete")
        r1.add_wall(Point(20, 0, z_base), Point(20, 10, z_base), "drywall")
        r1.add_wall(Point(20, 10, z_base), Point(0, 10, z_base), "drywall")
        r1.add_wall(Point(0, 10, z_base), Point(0, 0, z_base), "concrete")
        b.add_room(r1)

        # Room 2: 20,0 to 40,10
        r2 = Room(f"Office A{suffix}", floor_level=floor)
        r2.add_wall(Point(20, 0, z_base), Point(40, 0, z_base), "concrete")
        r2.add_wall(Point(40, 0, z_base), Point(40, 10, z_base), "concrete")
        r2.add_wall(Point(40, 10, z_base), Point(20, 10, z_base), "drywall")
        r2.add_wall(Point(20, 10, z_base), Point(20, 0, z_base), "drywall")  # Shared
        b.add_room(r2)

        # Room 3: 0,10 to 20,20
        r3 = Room(f"Office B{suffix}", floor_level=floor)
        r3.add_wall(Point(0, 10, z_base), Point(20, 10, z_base), "drywall")  # Shared
        r3.add_wall(Point(20, 10, z_base), Point(20, 20, z_base), "drywall")
        r3.add_wall(Point(20, 20, z_base), Point(0, 20, z_base), "concrete")
        r3.add_wall(Point(0, 20, z_base), Point(0, 10, z_base), "concrete")
        b.add_room(r3)

        # Room 4: 20,10 to 40,20
        r4 = Room(f"Server Room{suffix}", floor_level=floor)
        r4.add_wall(Point(20, 10, z_base), Point(40, 10, z_base), "drywall")  # Shared
        r4.add_wall(Point(40, 10, z_base), Point(40, 20, z_base), "concrete")
        r4.add_wall(Point(40, 20, z_base), Point(20, 20, z_base), "concrete")
        r4.add_wall(Point(20, 20, z_base), Point(20, 10, z_base), "drywall")  # Shared
        b.add_room(r4)

    return b


def generate_grid_points(building, spacing=2.0, height_offset=1.5):
    points = []
    # 40x20 footprint
    x_range = np.arange(1, 39, spacing)
    y_range = np.arange(1, 19, spacing)

    # Generate for each floor
    # Floor 0: z=height_offset
    # Floor 1: z=3.0 + height_offset
    floors_z = [height_offset, 3.0 + height_offset]

    for z in floors_z:
        for x in x_range:
            for y in y_range:
                p = Point(x, y, z)
                # Simple check: is it roughly inside the 40x20 box?
                if building.is_point_inside(p):
                    points.append(p)
    return points


def main():
    print("=== IoT Router Placement Simulation ===")

    # 1. Setup Environment
    building = create_test_building()
    print(f"Building created: {len(building.rooms)} rooms.")

    # 2. Generate Points
    # Candidates: Coarse grid (e.g., every 4m)
    candidates = generate_grid_points(
        building, spacing=4.0, height_offset=2.5
    )  # Ceiling height
    print(f"Generated {len(candidates)} candidate router locations.")

    # Sensors: Fine grid (e.g., every 1m)
    sensors = generate_grid_points(
        building, spacing=1.0, height_offset=1.0
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
