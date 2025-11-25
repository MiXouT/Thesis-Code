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

### 1. Running the Simulation

To run the optimization and baseline comparisons:

```bash
python main.py
```

This will:
-   Load the layout from `layout.json`.
-   Run the NSGA-II optimization.
-   Run Random and Grid baseline algorithms.
-   Generate results in `pareto_front.html` and `solution_map.html`.

### 2. Using the Layout Editor

To design or modify building layouts:

1.  Start the editor server:
    ```bash
    python tools/editor/server.py
    ```
2.  Open your browser and navigate to: `http://localhost:8000`

You can draw rooms, add walls, and save layouts directly to the `layouts/` directory.

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

## Results

After running the simulation, open the generated HTML files in your browser:
```bash
Start-Process pareto_front.html; Start-Process solution_map.html
```
-   **`pareto_front.html`**: Interactive scatter plot showing the trade-offs between objectives.
-   **`solution_map.html`**: 3D visualization of the best found router placements.
