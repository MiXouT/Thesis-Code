import numpy as np
from .optimization import RouterPlacementProblem
from .config import ROUTER_COUNT_MAX


def generate_random_solutions(problem: RouterPlacementProblem, n_solutions=50):
    """
    Generates random solutions (Monkey).
    Randomly selects locations and power levels.
    """
    X = []
    F = []
    G = []

    n_var = problem.n_var

    for _ in range(n_solutions):
        # Randomly decide how many routers (1 to ROUTER_COUNT_MAX)
        # We favor a spread, but let's just pick uniformly
        n_active = np.random.randint(1, ROUTER_COUNT_MAX + 1)

        # Randomly select indices
        indices = np.random.choice(n_var, n_active, replace=False)

        # Randomly assign power levels (1-4)
        x = np.zeros(n_var, dtype=int)
        x[indices] = np.random.randint(1, 5, size=n_active)

        # Evaluate
        out = {}
        problem._evaluate(x, out)

        X.append(x)
        F.append(out["F"])
        if "G" in out:
            G.append(out["G"])

    return np.array(X), np.array(F), np.array(G) if G else None


def generate_grid_solutions(problem: RouterPlacementProblem, candidates: np.ndarray):
    """
    Generates grid/uniform solutions (Lazy Human).
    Tries different counts of routers (1 to ROUTER_COUNT_MAX), spread uniformly.
    Uses MAX Power (Level 4) as is standard for manual deployment.
    """
    X = []
    F = []
    G = []

    n_var = problem.n_var

    # Sort candidates by X then Y to make striding effective for "grid-like" selection
    # candidates is (N, 3) [x, y, z]
    # We want to sort by spatial position to ensure striding picks distributed points
    # Lexicographical sort
    sorted_indices = np.lexsort(
        (candidates[:, 1], candidates[:, 0])
    )  # Sort by Y then X

    for n_routers in range(1, ROUTER_COUNT_MAX + 1):
        # Simple heuristic: Select n_routers indices evenly spaced from the sorted list
        step = max(1, n_var // n_routers)

        # Pick indices from the sorted list
        selected_sorted_indices = [i for i in range(0, n_var, step)][:n_routers]
        indices = sorted_indices[selected_sorted_indices]

        # Assign Max Power (Level 4)
        x = np.zeros(n_var, dtype=int)
        x[indices] = 4

        # Evaluate
        out = {}
        problem._evaluate(x, out)

        X.append(x)
        F.append(out["F"])
        if "G" in out:
            G.append(out["G"])

    return np.array(X), np.array(F), np.array(G) if G else None
