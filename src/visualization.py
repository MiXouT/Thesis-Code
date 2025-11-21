import plotly.graph_objects as go
import numpy as np
from .environment import Building, Point
from .config import RX_SENSITIVITY_DBM, TX_POWER_DBM


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
        active_indices: list[int],
        sensors: list[Point],
        loss_matrix: np.ndarray,
        title="Router Placement",
    ):

        traces = self._get_building_traces()

        # 1. Plot Inactive Candidates (Small Grey Dots)
        cand_x = [p.x for i, p in enumerate(candidates) if i not in active_indices]
        cand_y = [p.y for i, p in enumerate(candidates) if i not in active_indices]
        cand_z = [p.z for i, p in enumerate(candidates) if i not in active_indices]

        traces.append(
            go.Scatter3d(
                x=cand_x,
                y=cand_y,
                z=cand_z,
                mode="markers",
                marker=dict(size=3, color="gray", opacity=0.5),
                name="Candidate Locations",
            )
        )

        # 2. Plot Active Routers (Large Red Stars)
        active_x = [candidates[i].x for i in active_indices]
        active_y = [candidates[i].y for i in active_indices]
        active_z = [candidates[i].z for i in active_indices]

        traces.append(
            go.Scatter3d(
                x=active_x,
                y=active_y,
                z=active_z,
                mode="markers",
                marker=dict(size=8, color="red", symbol="diamond"),
                name="Active Routers",
            )
        )

        # 3. Plot Sensors (Heatmap of Signal Strength)
        # Calculate max signal for each sensor
        if len(active_indices) > 0:
            active_losses = loss_matrix[active_indices, :]
            min_losses = np.min(active_losses, axis=0)
            signals = TX_POWER_DBM - min_losses
        else:
            signals = np.full(len(sensors), -120.0)

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
                    color=signals,
                    colorscale="Viridis",
                    cmin=RX_SENSITIVITY_DBM - 10,
                    cmax=TX_POWER_DBM - 40,
                    colorbar=dict(title="Signal (dBm)"),
                    opacity=0.8,
                ),
                text=[f"Signal: {s:.1f} dBm" for s in signals],
                name="Signal Coverage",
            )
        )

        fig = go.Figure(data=traces)
        fig.update_layout(title=title, scene=dict(aspectmode="data"))
        return fig

    def plot_pareto_front(self, res):
        """
        Plots Objective 1 (Uncovered Sensors) vs Objective 2 (Num Routers)
        """
        F = res.F

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=F[:, 1],  # Num Routers
                    y=F[:, 0],  # Uncovered Sensors
                    mode="markers",
                    marker=dict(size=10, color="blue"),
                )
            ]
        )

        fig.update_layout(
            title="Pareto Front: Coverage vs Energy",
            xaxis_title="Number of Routers (Energy)",
            yaxis_title="Uncovered Sensors (Inverse Coverage)",
        )
        return fig
