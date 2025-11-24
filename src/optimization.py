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
)


class IntegerSampling(IntegerRandomSampling):
    def _do(self, problem, n_samples, **kwargs):
        # Custom sampling to favor 0 (Off) but allow 1-4
        # We want roughly ROUTER_COUNT_MAX active routers per individual
        n_var = problem.n_var
        X = np.zeros((n_samples, n_var), dtype=int)

        prob_active = min(ROUTER_COUNT_MAX / n_var, 0.5)

        for i in range(n_samples):
            # Decide which are active
            active_mask = np.random.random(n_var) < prob_active
            # Assign random power level 1-4 to active ones
            X[i, active_mask] = np.random.randint(1, 5, size=np.sum(active_mask))

        return X


class RouterPlacementProblem(ElementwiseProblem):
    def __init__(self, loss_matrix: np.ndarray, threshold: float = RX_SENSITIVITY_DBM):
        """
        Integer optimization problem:
        x[i] = 0 (Off), 1 (Low), 2 (Med), 3 (High), 4 (Max)
        """
        self.loss_matrix = loss_matrix  # (n_candidates, n_sensors)
        self.threshold = threshold
        n_var = loss_matrix.shape[0]

        super().__init__(
            n_var=n_var,
            n_obj=3,  # Obj1: Min Uncovered, Obj2: Min Total Power, Obj3: Min Interference
            n_ieq_constr=0,
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


class Optimizer:
    def __init__(self, loss_matrix: np.ndarray):
        self.problem = RouterPlacementProblem(loss_matrix)

        self.algorithm = NSGA2(
            pop_size=POPULATION_SIZE,
            sampling=IntegerSampling(),
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
