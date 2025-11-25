import numpy as np


def precompute_wall_distances(candidate_points: np.ndarray, walls: list) -> np.ndarray:
    """
    Calculates the minimum distance from each candidate point to any wall segment.

    Args:
        candidate_points: (N, 3) array of [x, y, z] coordinates.
        walls: List of wall dictionaries, each having 'start' and 'end' [x, y] coords.
               Note: We assume walls are vertical and ignore z-distance for now,
               or we can assume 2D distance to the wall line on the floor.

    Returns:
        (N,) array of distances in meters.
    """
    if not walls:
        # No walls? Return infinity or 0?
        # If no walls, technically everything is "far" from a wall,
        # but for the sake of not breaking things, let's return a large number
        # so everything is a violation if PoE is on.
        # OR, if the user has an empty map, maybe they don't want constraints.
        # Let's return a large number (1000.0) to signify "far".
        return np.full(candidate_points.shape[0], 1000.0)

    n_points = candidate_points.shape[0]
    n_walls = len(walls)

    # Extract 2D coordinates for points and walls
    # Points: (N, 2)
    P = candidate_points[:, :2]

    # Walls: Start (M, 2) and End (M, 2)
    A = np.zeros((n_walls, 2))
    B = np.zeros((n_walls, 2))

    for i, w in enumerate(walls):
        A[i] = w["start"]
        B[i] = w["end"]

    # Vectorized Point-to-Segment Distance
    # We want dist(P[i], Segment(A[j], B[j])) for all i, j
    # This is an N x M calculation.

    # Expand dims for broadcasting
    # P: (N, 1, 2)
    # A: (1, M, 2)
    # B: (1, M, 2)
    P_exp = P[:, np.newaxis, :]
    A_exp = A[np.newaxis, :, :]
    B_exp = B[np.newaxis, :, :]

    # Vector AB
    AB = B_exp - A_exp  # (1, M, 2)

    # Vector AP
    AP = P_exp - A_exp  # (N, M, 2)

    # Project AP onto AB to find parameter t
    # t = dot(AP, AB) / dot(AB, AB)

    dot_AP_AB = np.sum(AP * AB, axis=2)  # (N, M)
    dot_AB_AB = np.sum(AB * AB, axis=2)  # (1, M)

    # Avoid division by zero for zero-length walls
    dot_AB_AB[dot_AB_AB == 0] = 1e-9

    t = dot_AP_AB / dot_AB_AB  # (N, M)

    # Clamp t to segment [0, 1]
    t = np.clip(t, 0.0, 1.0)

    # Closest point on segment: C = A + t * AB
    # We need to broadcast t to (N, M, 1) to multiply with AB (1, M, 2)
    C = A_exp + t[:, :, np.newaxis] * AB

    # Distance P to C
    diff = P_exp - C  # (N, M, 2)
    dists_sq = np.sum(diff * diff, axis=2)  # (N, M)
    dists = np.sqrt(dists_sq)

    # Min distance to ANY wall for each point
    min_dists = np.min(dists, axis=1)  # (N,)

    return min_dists
