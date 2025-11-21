import numpy as np
from typing import List, Tuple
from .environment import Building, Point, Wall
from .config import (
    FREQUENCY_HZ,
    TX_POWER_DBM,
    PATH_LOSS_EXPONENT,
    REFERENCE_DISTANCE,
    GRID_SIZE,
    FLOOR_ATTENUATION,
)
from scipy.spatial.distance import cdist


class PathLossModel:
    def __init__(self, frequency=FREQUENCY_HZ, n=PATH_LOSS_EXPONENT):
        self.frequency = frequency
        self.n = n
        # Free space path loss at reference distance (1m)
        # FSPL(dB) = 20log10(d) + 20log10(f) + 20log10(4pi/c)
        c = 3e8
        self.pl_ref = (
            20 * np.log10(REFERENCE_DISTANCE) + 20 * np.log10(frequency) - 147.55
        )

    def calculate_loss(self, distance: float) -> float:
        if distance <= 0:
            return 0.0
        # Log-distance path loss model
        # PL(d) = PL(d0) + 10n log10(d/d0)
        pl = self.pl_ref + 10 * self.n * np.log10(distance / REFERENCE_DISTANCE)
        return pl


class RayTracing:
    @staticmethod
    def intersect(p1: Point, p2: Point, wall: Wall) -> bool:
        # Simplified 2D intersection check (ignoring Z for wall bounds for now, assuming infinite Z or handled by room check)
        # Line segment p1-p2 vs Line segment wall.start-wall.end

        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        x3, y3 = wall.start.x, wall.start.y
        x4, y4 = wall.end.x, wall.end.y

        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        if denom == 0:
            return False  # Parallel

        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom

        # Check if intersection is within both segments
        if 0 <= ua <= 1 and 0 <= ub <= 1:
            # Check Z height (simple check)
            z_interp = p1.z + ua * (p2.z - p1.z)
            z_base = wall.start.z
            if z_base <= z_interp <= z_base + wall.height:
                return True

        return False

    @staticmethod
    def calculate_wall_loss(p1: Point, p2: Point, building: Building) -> float:
        total_attenuation = 0.0
        walls = building.get_all_walls()
        for wall in walls:
            if RayTracing.intersect(p1, p2, wall):
                total_attenuation += wall.attenuation
        return total_attenuation


class LossMatrix:
    """
    Pre-calculates the path loss between a set of candidate router locations
    and a set of sensor/grid locations.
    """

    def __init__(
        self,
        building: Building,
        candidate_points: List[Point],
        sensor_points: List[Point],
    ):
        self.building = building
        self.candidates = candidate_points
        self.sensors = sensor_points
        self.matrix = np.zeros((len(candidate_points), len(sensor_points)))
        self.pl_model = PathLossModel()

    def compute(self):
        print(
            f"Computing Loss Matrix: {len(self.candidates)} candidates x {len(self.sensors)} sensors..."
        )

        # 1. Calculate Distances (Vectorized)
        c_coords = np.array([[p.x, p.y, p.z] for p in self.candidates])
        s_coords = np.array([[p.x, p.y, p.z] for p in self.sensors])
        dists = cdist(c_coords, s_coords)

        # 2. Calculate Free Space Path Loss
        # Avoid log(0)
        dists[dists == 0] = 0.1
        # Vectorized path loss calculation
        # PL = A + 10n log10(d)
        path_losses = self.pl_model.pl_ref + 10 * self.pl_model.n * np.log10(
            dists / REFERENCE_DISTANCE
        )

        # 3. Calculate Wall Attenuation (Iterative - Slow part, but done once)
        # Optimization: Only check walls if distance is large enough to matter?
        # For now, brute force ray trace for accuracy
        wall_losses = np.zeros_like(path_losses)

        # Iterate through all pairs (This is O(N*M*W))
        # Can be slow for large grids.
        # TODO: Optimize with spatial indexing if needed.
        for i, c_pt in enumerate(self.candidates):
            for j, s_pt in enumerate(self.sensors):
                w_loss = RayTracing.calculate_wall_loss(c_pt, s_pt, self.building)

                # Floor Attenuation
                c_floor = self.building.get_floor_level(c_pt.z)
                s_floor = self.building.get_floor_level(s_pt.z)
                f_loss = abs(c_floor - s_floor) * FLOOR_ATTENUATION

                wall_losses[i, j] = w_loss + f_loss

        self.matrix = path_losses + wall_losses
        print("Loss Matrix Computation Complete.")
        return self.matrix
