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

    # Calculate total AI evaluations to match fairness
    total_evals = config.POPULATION_SIZE * config.GENERATIONS
    print(
        f"Running Random Baseline with {total_evals} samples (matching AI evaluations)..."
    )

    random_X, random_F, random_G = baseline.generate_random_solutions(
        optimizer.problem, n_solutions=total_evals
    )

    # Filter Random Baseline to Top 1000 (Rank-based)
    print("Filtering Random Baseline to Top 1000 Solutions...")
    from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

    # Sort all 40k by rank
    nds = NonDominatedSorting()
    fronts = nds.do(random_F)

    best_indices = []
    for front in fronts:
        best_indices.extend(front)
        if len(best_indices) >= 1000:
            break

    # Truncate to exactly 1000
    best_indices = best_indices[:1000]

    random_X = random_X[best_indices]
    random_F = random_F[best_indices]
    if random_G is not None:
        random_G = random_G[best_indices]

    print(
        f"Random Baseline: Reduced {total_evals} samples to the {len(random_F)} best (Top 1000) solutions."
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
        uncovered=best_uncovered,
        interfered=best_interference,
        title=f"Best Solution ({active_routers} Routers, {best_power:.2f}W) <br> {meta_title}",
    )
    fig_sol.write_html("solution_map.html")
    print("Saved solution_map.html")

    # --- Plot Random Baseline Best Solution ---
    # Find best Random solution (min Uncovered, then min Power)
    rnd_indices = np.lexsort((random_F[:, 1], random_F[:, 0]))
    best_rnd_idx = rnd_indices[0]
    best_rnd_sol = random_X[best_rnd_idx]
    best_rnd_obj = random_F[best_rnd_idx]

    rnd_active = np.sum(best_rnd_sol > 0)

    fig_rnd = viz.plot_solution(
        candidates,
        best_rnd_sol,
        sensors,
        loss_matrix,
        uncovered=best_rnd_obj[0],
        interfered=best_rnd_obj[2],
        title=f"Best Random Solution ({rnd_active} Routers, {best_rnd_obj[1]:.2f}W) <br> {meta_title}",
    )
    fig_rnd.write_html("solution_map_random.html")
    print("Saved solution_map_random.html")

    # --- Plot Grid Baseline Best Solution ---
    # Find best Grid solution (min Uncovered, then min Power)
    grid_indices = np.lexsort((grid_F[:, 1], grid_F[:, 0]))
    best_grid_idx = grid_indices[0]
    best_grid_sol = grid_X[best_grid_idx]
    best_grid_obj = grid_F[best_grid_idx]

    grid_active = np.sum(best_grid_sol > 0)

    fig_grid = viz.plot_solution(
        candidates,
        best_grid_sol,
        sensors,
        loss_matrix,
        uncovered=best_grid_obj[0],
        interfered=best_grid_obj[2],
        title=f"Best Grid Solution ({grid_active} Routers, {best_grid_obj[1]:.2f}W) <br> {meta_title}",
    )
    fig_grid.write_html("solution_map_grid.html")
    print("Saved solution_map_grid.html")

    # Plot Convergence (Generations vs Fitness)
    fig_conv = viz.plot_convergence(res, title=f"Convergence Plot - {meta_title}")
    fig_conv.write_html("convergence_plot.html")
    print("Saved convergence_plot.html")

    # Save Convergence Data to CSV
    print("Saving convergence history to CSV...")
    history_data = []
    for i, algo in enumerate(res.history):
        gen = i + 1
        F_gen = algo.pop.get("F")
        min_uncovered = np.min(F_gen[:, 0])
        min_power = np.min(F_gen[:, 1])
        min_interference = np.min(F_gen[:, 2])
        history_data.append([gen, min_uncovered, min_power, min_interference])

    df_hist = pd.DataFrame(
        history_data,
        columns=["Generation", "Min_Uncovered", "Min_Power", "Min_Interference"],
    )
    df_hist.to_csv("convergence_history.csv", index=False)
    print("Saved convergence_history.csv")

    # Plot Energy Box Plot
    fig_box = viz.plot_energy_boxplot(
        res.F, random_F, grid_F, title=f"Energy Distribution - {meta_title}"
    )
    fig_box.write_html("energy_boxplot.html")
    print("Saved energy_boxplot.html")

    # 8. Print Pareto Data to Terminal
    print("\n=== Pareto Front Data (Text Output) ===")

    datasets = {"AI": res.F, "Random": random_F, "Grid": grid_F}

    # F columns: 0=Uncovered, 1=Power, 2=Interference
    charts = [
        ("Coverage vs Energy", 0, 1, "Uncovered", "Power(W)"),
        ("Energy vs Interference", 1, 2, "Power(W)", "Interference"),
        ("Coverage vs Interference", 0, 2, "Uncovered", "Interference"),
    ]

    # Save full datasets to CSV
    print("\n=== Saving Results to CSV ===")
    for method_name, data in datasets.items():
        df = pd.DataFrame(data, columns=["Uncovered", "Power", "Interference"])
        csv_filename = f"results_{method_name.lower()}.csv"
        df.to_csv(csv_filename, index=False)
        print(f"Saved {method_name} results to {csv_filename}")

    for chart_name, x_idx, y_idx, x_label, y_label in charts:
        print(f"\n--- {chart_name} ---")
        for method_name, data in datasets.items():
            print(f"\n[{method_name}]")
            print(f"{x_label}, {y_label}")

            # Sort by X for readability
            sorted_indices = np.argsort(data[:, x_idx])
            sorted_data = data[sorted_indices]

            # Truncate output if too large
            MAX_PRINT = 50
            if len(sorted_data) > MAX_PRINT:
                # Print first 25
                for row in sorted_data[:25]:
                    print(f"{row[x_idx]:.4f}, {row[y_idx]:.4f}")
                print(f"... ({len(sorted_data) - MAX_PRINT} hidden rows) ...")
                # Print last 25
                for row in sorted_data[-25:]:
                    print(f"{row[x_idx]:.4f}, {row[y_idx]:.4f}")
                print(f"Full data saved to results_{method_name.lower()}.csv")
            else:
                for row in sorted_data:
                    print(f"{row[x_idx]:.4f}, {row[y_idx]:.4f}")


if __name__ == "__main__":
    main()
