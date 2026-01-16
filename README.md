# IoT Router Placement Optimization Framework

This project implements a multi-objective optimization framework for placing IoT routers in a 3D building environment. It uses the **NSGA-II** (Non-dominated Sorting Genetic Algorithm II) to find optimal trade-offs between:
1.  **Coverage:** Maximizing the number of connected sensors.
2.  **Power Consumption:** Minimizing total energy usage (Router Base Load + Transmit Power).
3.  **Interference:** Minimizing signal overlap between routers.

## Features

-   **3D Environment Modeling:** Simulates multi-floor buildings with different wall materials and attenuation properties.
-   **Signal Propagation Model:** Uses Log-Distance Path Loss model with wall and floor attenuation.
-   **Multi-Objective Optimization:** Uses `pymoo` to implement NSGA-II for finding Pareto-optimal solutions.
-   **Baseline Comparisons:** Includes "Random" (Monkey) and "Grid" (Human) placement algorithms for performance validation.
-   **Interactive Visualization:** Generates 3D solution maps and Pareto front plots using Plotly.
-   **Layout Editor:** A web-based tool to design and modify building layouts.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd Thesis-Code
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Dependencies include: `numpy`, `scipy`, `pandas`, `plotly`, `pymoo`.*

## Usage
### 1. Using the Layout Editor

To design or modify building layouts:

1.  Start the editor server:
    ```bash
    python tools/editor/server.py
    ```
2.  Open your browser and navigate to: `http://localhost:8000`

You can draw rooms, add walls, and save layouts directly to the `layouts/` directory.

### 2. Running the Simulation

To run the optimization and baseline comparisons:

```bash
python main.py
```

This will:
-   Load the layout from `layout.json`.
-   Run the NSGA-II optimization.
-   Run Random and Grid baseline algorithms.
-   Generate results in `pareto_front.html` and `solution_map.html`.

-   ## 3. Results

After running the simulation, open the generated HTML files in your browser:
```bash
powershell -c "Start-Process pareto_front.html; Start-Process solution_map.html; Start-Process solution_map_random.html; Start-Process solution_map_grid.html; Start-Process convergence_plot.html; Start-Process energy_boxplot.html; Start-Process interference_boxplot.html; Start-Process coverage_efficiency.html; Start-Process scenario_A_vertical.html; Start-Process scenario_B_shadow.html"
```
-   📊 Visualization & Analysis Plots
solution_map.html: Interactive 3D heatmap of the AI's optimal router placement, showing signal coverage strength (dBm) across all floors and exact router locations.
pareto_front.html: A scatter plot visualizing the multi-objective trade-offs (Coverage vs. Power vs. Interference), allowing users to hover and select the "sweet spot" solution.
convergence_plot.html: Tracks the optimization progress over generations, demonstrating how the AI improves fitness (minimizing uncovered sensors and power) over time.

📉 Baseline Comparisons
solution_map_random.html: 3D heatmap for the best Random Search solution, used as a baseline to visually demonstrate the AI's superior coverage efficiency.
solution_map_grid.html: 3D heatmap for the best Grid/Uniform deployment, highlighting the AI's advantage over naive manual placement.
energy_boxplot.html: Statistical comparison of Power Consumption (Watts) between AI, Grid, and Random methods, showing the AI's energy savings.
interference_boxplot.html: Statistical comparison of Signal Interference, validating the AI's ability to minimize channel overlap compared to baselines.
coverage_efficiency.html: Bar chart comparing Uncovered Sensors at fixed energy budgets (10W, 20W, 30W), proving the AI achieves better coverage for the same power.
🏗️ Physics Validation Scenarios

scenario_A_vertical.html: A controlled test verifying vertical signal propagation, showing how signals penetrate floors in a multi-story environment.
scenario_B_shadow.html: A controlled test verifying obstacle shadowing, visualizing how concrete walls and cores attenuate signals and create dead zones.



## Configuration

You can customize the simulation settings in two ways:

1.  **`config.json`**: A JSON file for easy parameter tuning.
    ```json
    {
      "TX_POWER_LEVELS": { "1": 10.0, "2": 24.0, "3": 32.0, "4": 40.0 },
      "ROUTER_BASE_LOAD_WATTS": 10.0,
      "POE_ENABLED": true,
      "POE_MAX_DISTANCE": 0.5
    }
    ```

2.  **`src/config.py`**: Core configuration file.
    -   `POPULATION_SIZE`: Number of candidate solutions per generation.
    -   `GENERATIONS`: Number of optimization loops.
    -   `BUILDING_DIMENSIONS`: Max size of the simulation space.
    -   `WALL_ATTENUATION`: Signal loss values for different materials.

## Project Structure

-   `src/`: Core source code (`optimization.py`, `physics.py`, `baseline.py`, etc.).
-   `tools/editor/`: Web-based layout editor.
-   `layouts/`: Saved JSON building layouts.
-   `main.py`: Entry point for the simulation.
-   `layout.json`: The currently active layout file.

