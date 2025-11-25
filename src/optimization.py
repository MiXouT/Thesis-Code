import numpy as np
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.optimize import minimize
from pymoo.termination import get_termination

from .config import (
    RX_SENSITIVITY_DBM,
    POPULATION_SIZE,
    GENERATIONS,
    ROUTER_COUNT_MAX,
    TX_POWER_LEVELS,
    TX_POWER_WATTS,
    ROUTER_BASE_LOAD_WATTS,
    POE_ENABLED,
    POE_MAX_DISTANCE,
)


class IntegerSampling(IntegerRandomSampling):
    def __init__(self, wall_dist_cache=None):
        super().__init__()
        self.wall_dist_cache = wall_dist_cache

    def _do(self, problem, n_samples, **kwargs):
        # Custom sampling to favor 0 (Off) but allow 1-4
        # We want roughly ROUTER_COUNT_MAX active routers per individual
        n_var = problem.n_var
        X = np.zeros((n_samples, n_var), dtype=int)

        prob_active = min(ROUTER_COUNT_MAX / n_var, 0.5)

        # Pre-calculate valid indices if PoE is enabled
        valid_indices = None
        if POE_ENABLED and self.wall_dist_cache is not None:
            valid_indices = np.where(self.wall_dist_cache <= POE_MAX_DISTANCE)[0]
            if len(valid_indices) == 0:
                print(
                    "WARNING: No valid wall locations found for PoE. Ignoring constraint for initialization."
                )
                valid_indices = None

        for i in range(n_samples):
            # Decide how many to activate (binomial distribution centered on ROUTER_COUNT_MAX)
            # Or just simple probability mask

            if valid_indices is not None:
                # PoE Mode: Pick from valid indices only
                # How many?
                n_active = np.random.binomial(n_var, prob_active)
                n_active = max(
                    1, min(n_active, len(valid_indices))
                )  # Ensure at least 1 if possible

                chosen_indices = np.random.choice(
                    valid_indices, size=n_active, replace=False
                )
                X[i, chosen_indices] = np.random.randint(1, 5, size=n_active)
            else:
                # Standard Mode
                active_mask = np.random.random(n_var) < prob_active
                X[i, active_mask] = np.random.randint(1, 5, size=np.sum(active_mask))

        return X


class RouterPlacementProblem(ElementwiseProblem):
    def __init__(
        self,
        loss_matrix: np.ndarray,
        wall_dist_cache: np.ndarray = None,
        threshold: float = RX_SENSITIVITY_DBM,
    ):
        """
        Integer optimization problem:
        x[i] = 0 (Off), 1 (Low), 2 (Med), 3 (High), 4 (Max)
        """
        self.loss_matrix = loss_matrix  # (n_candidates, n_sensors)
        self.wall_dist_cache = wall_dist_cache  # (n_candidates,)
        self.threshold = threshold
        n_var = loss_matrix.shape[0]

        super().__init__(
            n_var=n_var,
            n_obj=3,  # Obj1: Min Uncovered, Obj2: Min Total Power, Obj3: Min Interference
            n_ieq_constr=1 if POE_ENABLED else 0,  # 1 Constraint if PoE is on
            xl=0,
            xu=4,
            vtype=int,
        )

    def _evaluate(self, x, out, *args, **kwargs):
        # x is an integer array of shape (n_candidates,)
        # 0 = Off, 1-4 = Power Levels
        # Ensure x is integer (SBX might produce floats)
        x = np.round(x).astype(int)

        active_indices = np.where(x > 0)[0]

        if len(active_indices) == 0:
            # No routers placed
            n_sensors = self.loss_matrix.shape[1]
            # Penalize heavily
            out["F"] = [n_sensors, 0.0, 0.0]
            if self.n_ieq_constr > 0:
                out["G"] = [0.0]  # No violation if no routers (technically)
            return

        # 1. Calculate Signal Strength at each sensor from each active router
        # Signal = TxPower - PathLoss

        # Get losses for active routers only
        active_losses = self.loss_matrix[active_indices, :]  # (n_active, n_sensors)

        # Get Tx Power (dBm) for each active router
        # x[active_indices] gives levels 1-4
        # Map levels to dBm values
        tx_powers_dbm = np.array([TX_POWER_LEVELS[lvl] for lvl in x[active_indices]])

        # Broadcast Tx Power to shape (n_active, n_sensors)
        # (n_active, 1) - (n_active, n_sensors)
        signals = tx_powers_dbm[:, np.newaxis] - active_losses

        # 2. Coverage (Obj 1)
        # Sensor is covered if MAX signal >= threshold
        max_signals = np.max(signals, axis=0)
        covered_mask = max_signals >= self.threshold
        uncovered_sensors = np.sum(~covered_mask)

        # 3. Total Power Consumption (Obj 2)
        # Power = Base Load + Radio Power for each active router
        # Map levels to Watts
        radio_watts = np.array([TX_POWER_WATTS[lvl] for lvl in x[active_indices]])
        total_watts = np.sum(ROUTER_BASE_LOAD_WATTS + radio_watts)

        # 4. Interference (Obj 3)
        # Count sensors that hear > 1 router above threshold
        # We already have 'signals' matrix
        strong_signals_count = np.sum(signals >= self.threshold, axis=0)
        # Interference = number of sensors with count > 1
        interfered_sensors = np.sum(strong_signals_count > 1)

        out["F"] = [uncovered_sensors, total_watts, interfered_sensors]

        # 5. PoE Constraint (G)
        if POE_ENABLED and self.wall_dist_cache is not None:
            # Get distances for active routers
            dists = self.wall_dist_cache[active_indices]
            # Violation = dist - max_dist
            # We want G <= 0. So if dist > max, G > 0 (violation)
            # We can sum the violations or take the max.
            # Pymoo handles array of constraints, but we defined n_ieq_constr=1
            # So we need to aggregate. Let's take the MAX violation.
            # If any router is too far, it's a violation.

            violations = dists - POE_MAX_DISTANCE
            # We only care about positive violations
            # But pymoo expects G <= 0.
            # If we return max(violations), and it's 0.1, that's a violation.
            # If it's -0.5, that's satisfied.
            out["G"] = [np.max(violations)]


class Optimizer:
    def __init__(self, loss_matrix: np.ndarray, wall_dist_cache: np.ndarray = None):
        self.problem = RouterPlacementProblem(loss_matrix, wall_dist_cache)

        self.algorithm = NSGA2(
            pop_size=POPULATION_SIZE,
            sampling=IntegerSampling(wall_dist_cache),
            crossover=SBX(prob=0.9, eta=15, vtype=float, repair=None),
            mutation=PM(
                prob=1.0 / loss_matrix.shape[0], eta=20, vtype=float, repair=None
            ),
            eliminate_duplicates=True,
        )

        self.termination = get_termination("n_gen", GENERATIONS)

    def run(self):
        print("Starting Optimization (NSGA-II) with Variable Power...")
        print("Objectives: [Min Uncovered, Min Watts, Min Interference]")
        if POE_ENABLED:
            print(f"Constraint: PoE Enabled (Max Dist: {POE_MAX_DISTANCE}m)")

        res = minimize(
            self.problem,
            self.algorithm,
            self.termination,
            seed=1,
            save_history=True,
            verbose=True,
        )

        print(f"Optimization Complete. Found {len(res.X)} Pareto-optimal solutions.")
        return res
