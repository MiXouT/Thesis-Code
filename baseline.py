import numpy as np
import random
from src.environment import Building, Room, Point
from src.physics import LossMatrix
from src.config import RX_SENSITIVITY_DBM, TX_POWER_DBM


def evaluate_placement(active_indices, loss_matrix, threshold=RX_SENSITIVITY_DBM):
    if len(active_indices) == 0:
        return 0, 0

    active_losses = loss_matrix[active_indices, :]
    min_losses = np.min(active_losses, axis=0)
    max_allowable_loss = TX_POWER_DBM - threshold

    covered_sensors = np.sum(min_losses <= max_allowable_loss)
    total_sensors = loss_matrix.shape[1]
    coverage_pct = (covered_sensors / total_sensors) * 100

    return coverage_pct, len(active_indices)


def run_random_baseline(loss_matrix, n_routers, n_trials=100):
    print(f"Running Random Baseline ({n_routers} routers, {n_trials} trials)...")
    n_candidates = loss_matrix.shape[0]
    best_coverage = 0
    avg_coverage = 0

    for _ in range(n_trials):
        indices = random.sample(range(n_candidates), n_routers)
        cov, _ = evaluate_placement(indices, loss_matrix)
        best_coverage = max(best_coverage, cov)
        avg_coverage += cov

    avg_coverage /= n_trials
    print(f"Random: Avg Coverage = {avg_coverage:.2f}%, Best = {best_coverage:.2f}%")
    return best_coverage


def run_grid_baseline(loss_matrix, candidates, n_routers):
    # Simple heuristic: Pick n_routers spread out as much as possible
    # This is hard to do generically for any N, so we'll just pick every Kth candidate
    print(f"Running Grid Baseline ({n_routers} routers)...")
    n_candidates = loss_matrix.shape[0]
    step = max(1, n_candidates // n_routers)
    indices = [i for i in range(0, n_candidates, step)][:n_routers]

    cov, _ = evaluate_placement(indices, loss_matrix)
    print(f"Grid: Coverage = {cov:.2f}%")
    return cov


if __name__ == "__main__":
    # Test logic
    pass
