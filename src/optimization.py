import numpy as np
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.pntx import TwoPointCrossover
from pymoo.operators.mutation.bitflip import BitflipMutation
from pymoo.core.sampling import Sampling
from pymoo.optimize import minimize
from pymoo.termination import get_termination

from .config import (
    RX_SENSITIVITY_DBM,
    POPULATION_SIZE,
    GENERATIONS,
    ROUTER_COUNT_MAX,
    TX_POWER_DBM,
)


class SparseSampling(Sampling):
    def _do(self, problem, n_samples, **kwargs):
        # Initialize with a low probability of being active
        # Prob = ROUTER_COUNT_MAX / n_var
        n_var = problem.n_var
        prob = min(ROUTER_COUNT_MAX / n_var, 0.5)
        X = np.random.random((n_samples, n_var)) < prob
        return X


class RouterPlacementProblem(ElementwiseProblem):
    def __init__(self, loss_matrix: np.ndarray, threshold: float = RX_SENSITIVITY_DBM):
        """
        Binary optimization problem:
        x[i] = 1 if router is placed at candidate i, 0 otherwise.
        """
        self.loss_matrix = loss_matrix  # (n_candidates, n_sensors)
        self.threshold = threshold
        n_var = loss_matrix.shape[0]

        super().__init__(
            n_var=n_var,
            n_obj=2,  # Obj1: Max Coverage, Obj2: Min Energy
            n_ieq_constr=0,
            xl=0,
            xu=1,
            vtype=bool,
        )

    def _evaluate(self, x, out, *args, **kwargs):
        # x is a boolean array of shape (n_candidates,)
        active_indices = np.where(x)[0]

        if len(active_indices) == 0:
            # No routers placed -> 0 coverage, 0 energy
            # We want to maximize coverage (minimize negative)
            # We want to minimize energy
            out["F"] = [0, 0]  # Technically 0 coverage is bad, but 0 energy is good.
            # To penalize "no routers", we can set coverage to a huge positive number (minimization)
            # Total sensors
            n_sensors = self.loss_matrix.shape[1]
            out["F"] = [n_sensors, 0]
            return

        # Calculate Coverage
        # Get sub-matrix for active routers
        active_losses = self.loss_matrix[active_indices, :]  # (n_active, n_sensors)

        # For each sensor, the received signal is the MAX signal from any active router
        # Signal = TxPower - PathLoss.
        # Since TxPower is constant, Max Signal <=> Min Path Loss.
        # So we find min path loss for each sensor.
        min_path_losses = np.min(active_losses, axis=0)

        # Check if signal > threshold
        # Signal = 20 - Loss
        # 20 - Loss >= -85  =>  Loss <= 105
        # So we check if min_path_loss <= (TxPower - Threshold)
        # Let's assume TxPower is handled outside or we just use loss directly.
        # In config, TX_POWER_DBM = 20.
        max_allowable_loss = TX_POWER_DBM - self.threshold

        covered_sensors = np.sum(min_path_losses <= max_allowable_loss)
        total_sensors = self.loss_matrix.shape[1]
        uncovered_sensors = total_sensors - covered_sensors

        # Objectives (Minimize both)
        # f1: Minimize Uncovered Sensors (Maximize Coverage)
        # f2: Minimize Number of Routers (Energy)

        f1 = uncovered_sensors
        f2 = len(active_indices)

        out["F"] = [f1, f2]


class Optimizer:
    def __init__(self, loss_matrix: np.ndarray):
        self.loss_matrix = loss_matrix
        self.problem = RouterPlacementProblem(loss_matrix)

        self.algorithm = NSGA2(
            pop_size=POPULATION_SIZE,
            sampling=SparseSampling(),
            crossover=TwoPointCrossover(),
            mutation=BitflipMutation(),
            eliminate_duplicates=True,
        )

        self.termination = get_termination("n_gen", GENERATIONS)

    def run(self):
        print("Starting Optimization (NSGA-II)...")
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
