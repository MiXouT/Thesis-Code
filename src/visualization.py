import plotly.graph_objects as go
import numpy as np
from plotly.subplots import make_subplots
from .environment import Building, Point
from .config import RX_SENSITIVITY_DBM, TX_POWER_LEVELS


class Visualizer:
    def __init__(self, building: Building):
        self.building = building

    def _get_building_traces(self):
        traces = []
        for room in self.building.rooms:
            # Draw floor
            min_x, min_y, min_z, max_x, max_y, max_z = room.bounds()

            # Floor (Rectangle)
            traces.append(
                go.Mesh3d(
                    x=[min_x, max_x, max_x, min_x],
                    y=[min_y, min_y, max_y, max_y],
                    z=[min_z, min_z, min_z, min_z],
                    color="lightgray",
                    opacity=0.2,
                    name=f"Floor {room.name}",
                )
            )

            # Walls (Lines)
            for wall in room.walls:
                x = [wall.start.x, wall.end.x, wall.end.x, wall.start.x, wall.start.x]
                y = [wall.start.y, wall.end.y, wall.end.y, wall.start.y, wall.start.y]
                z_base = wall.start.z
                z = [z_base, z_base, z_base + wall.height, z_base + wall.height, z_base]

                # Plotly lines for walls
                traces.append(
                    go.Scatter3d(
                        x=x,
                        y=y,
                        z=z,
                        mode="lines",
                        line=dict(color="black", width=2),
                        name=f"Wall ({wall.material})",
                        showlegend=False,
                    )
                )
        return traces

    def plot_solution(
        self,
        candidates: list[Point],
        solution_genome: np.ndarray,
        sensors: list[Point],
        loss_matrix: np.ndarray,
        uncovered=None,
        interfered=None,
        title="Router Placement",
    ):
        if uncovered is not None and interfered is not None:
            title += f" (Uncovered: {uncovered}, Interfered: {interfered})"
        # solution_genome is int array (0-4)
        active_indices = np.where(solution_genome > 0)[0]

        traces = self._get_building_traces()

        # 1. Plot Inactive Candidates (Small Grey Dots)
        inactive_indices = np.where(solution_genome == 0)[0]
        cand_x = [candidates[i].x for i in inactive_indices]
        cand_y = [candidates[i].y for i in inactive_indices]
        cand_z = [candidates[i].z for i in inactive_indices]

        traces.append(
            go.Scatter3d(
                x=cand_x,
                y=cand_y,
                z=cand_z,
                mode="markers",
                marker=dict(size=3, color="gray", opacity=0.3),
                name="Candidate Locations",
            )
        )

        # 2. Plot Active Routers (Colored by Power Level)
        # Map levels to colors/sizes
        # 1: Low (Blue), 2: Med (Green), 3: High (Orange), 4: Max (Red)
        colors = {1: "blue", 2: "green", 3: "orange", 4: "red"}
        sizes = {1: 6, 2: 8, 3: 10, 4: 12}
        names = {1: "Low (3mW)", 2: "Med (15mW)", 3: "High (40mW)", 4: "Max (100mW)"}

        for lvl in range(1, 5):
            indices = np.where(solution_genome == lvl)[0]
            if len(indices) == 0:
                continue

            rx = [candidates[i].x for i in indices]
            ry = [candidates[i].y for i in indices]
            rz = [candidates[i].z for i in indices]

            traces.append(
                go.Scatter3d(
                    x=rx,
                    y=ry,
                    z=rz,
                    mode="markers",
                    marker=dict(size=sizes[lvl], color=colors[lvl], symbol="diamond"),
                    name=f"Router {names[lvl]}",
                )
            )

        # 3. Plot Sensors (Heatmap of Signal Strength)
        if len(active_indices) > 0:
            active_losses = loss_matrix[active_indices, :]
            # Get Tx Power for each active router
            tx_powers = np.array(
                [TX_POWER_LEVELS[solution_genome[i]] for i in active_indices]
            )
            # Calculate signal from each router to each sensor
            # (n_active, 1) - (n_active, n_sensors)
            signals_matrix = tx_powers[:, np.newaxis] - active_losses
            # Max signal at each sensor
            max_signals = np.max(signals_matrix, axis=0)
        else:
            max_signals = np.full(len(sensors), -120.0)

        sens_x = [p.x for p in sensors]
        sens_y = [p.y for p in sensors]
        sens_z = [p.z for p in sensors]

        traces.append(
            go.Scatter3d(
                x=sens_x,
                y=sens_y,
                z=sens_z,
                mode="markers",
                marker=dict(
                    size=4,
                    color=max_signals,
                    colorscale="Viridis",
                    cmin=RX_SENSITIVITY_DBM - 10,
                    cmax=-40,  # Cap at reasonable max
                    colorbar=dict(title="Signal (dBm)", x=1.1, y=0.5, len=0.8),
                    opacity=0.8,
                ),
                text=[f"Signal: {s:.1f} dBm" for s in max_signals],
                name="Signal Coverage",
            )
        )

        fig = go.Figure(data=traces)
        fig.update_layout(
            title=title,
            scene=dict(aspectmode="data"),
            legend=dict(x=0, y=1),
            margin=dict(r=100),
            annotations=[
                dict(
                    text="Tip: Click legend items to toggle visibility",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0,
                    y=0,
                    xanchor="left",
                    yanchor="bottom",
                    font=dict(size=12, color="gray"),
                )
            ],
        )
        return fig

    def plot_pareto_front(
        self,
        res,
        random_F=None,
        grid_F=None,
        title="Multi-Objective Pareto Front Analysis",
    ):
        """
        Plots 3 2D projections of the 3-Objective Pareto Front
        Obj 1: Uncovered Sensors (Min)
        Obj 2: Total Power (Min)
        Obj 3: Interference (Min)
        """
        F = res.F

        # Create subplots
        fig = make_subplots(
            rows=1,
            cols=3,
            subplot_titles=(
                "Coverage vs Energy",
                "Energy vs Interference",
                "Coverage vs Interference",
            ),
        )

        # Helper to add baseline traces
        def add_baseline(F_data, name, color, symbol):
            if F_data is None or len(F_data) == 0:
                return
            # 1. Cov vs Energy
            fig.add_trace(
                go.Scatter(
                    x=F_data[:, 1],
                    y=F_data[:, 0],
                    mode="markers",
                    marker=dict(color=color, symbol=symbol, size=6, opacity=0.5),
                    name=name,
                    legendgroup=name,
                    text=[
                        f"Uncovered: {u}<br>Power: {p:.2f} W<br>Interference: {i}"
                        for u, p, i in zip(F_data[:, 0], F_data[:, 1], F_data[:, 2])
                    ],
                    hovertemplate="%{text}<extra></extra>",
                ),
                row=1,
                col=1,
            )
            # 2. Energy vs Int
            fig.add_trace(
                go.Scatter(
                    x=F_data[:, 1],
                    y=F_data[:, 2],
                    mode="markers",
                    marker=dict(color=color, symbol=symbol, size=6, opacity=0.5),
                    name=name,
                    legendgroup=name,
                    showlegend=False,
                ),
                row=1,
                col=2,
            )
            # 3. Cov vs Int
            fig.add_trace(
                go.Scatter(
                    x=F_data[:, 0],
                    y=F_data[:, 2],
                    mode="markers",
                    marker=dict(color=color, symbol=symbol, size=6, opacity=0.5),
                    name=name,
                    legendgroup=name,
                    showlegend=False,
                ),
                row=1,
                col=3,
            )

        # Add Baselines first (so they are behind AI?) or after?
        # Let's add them first so AI pops out
        add_baseline(random_F, "Random (Monkey)", "gray", "circle")
        add_baseline(grid_F, "Grid (Uniform)", "orange", "square")

        # 1. Coverage vs Energy (Uncovered vs Watts)
        fig.add_trace(
            go.Scatter(
                x=F[:, 1],  # Watts
                y=F[:, 0],  # Uncovered
                mode="markers",
                marker=dict(color="blue", size=8),
                text=[
                    f"Uncovered: {u}<br>Power: {p:.2f} W<br>Interference: {i}"
                    for u, p, i in zip(F[:, 0], F[:, 1], F[:, 2])
                ],
                hovertemplate="%{text}<extra></extra>",
                name="AI (NSGA-II)",
                legendgroup="AI",
            ),
            row=1,
            col=1,
        )

        # 2. Energy vs Interference (Watts vs Count)
        fig.add_trace(
            go.Scatter(
                x=F[:, 1],  # Watts
                y=F[:, 2],  # Interference
                mode="markers",
                marker=dict(color="blue", size=8),
                name="AI (NSGA-II)",
                legendgroup="AI",
                showlegend=False,
            ),
            row=1,
            col=2,
        )

        # 3. Coverage vs Interference (Uncovered vs Count)
        fig.add_trace(
            go.Scatter(
                x=F[:, 0],  # Uncovered
                y=F[:, 2],  # Interference
                mode="markers",
                marker=dict(color="blue", size=8),
                name="AI (NSGA-II)",
                legendgroup="AI",
                showlegend=False,
            ),
            row=1,
            col=3,
        )

        fig.update_layout(title=title, showlegend=True)

        # Update axes labels
        fig.update_xaxes(title_text="Total Power (Watts)", row=1, col=1)
        fig.update_yaxes(title_text="Uncovered Sensors", row=1, col=1)

        fig.update_xaxes(title_text="Total Power (Watts)", row=1, col=2)
        fig.update_yaxes(title_text="Interference Count", row=1, col=2)

        fig.update_xaxes(title_text="Uncovered Sensors", row=1, col=3)
        fig.update_yaxes(title_text="Interference Count", row=1, col=3)

        return fig
