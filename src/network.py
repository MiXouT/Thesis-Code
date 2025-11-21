from dataclasses import dataclass
from .environment import Point
from .config import TX_POWER_DBM, RX_SENSITIVITY_DBM


@dataclass
class Router:
    id: int
    location: Point
    tx_power_dbm: float = TX_POWER_DBM
    active: bool = False
    cost: float = 100.0  # Monetary cost
    power_consumption_watts: float = 10.0  # Active power consumption


@dataclass
class Sensor:
    id: int
    location: Point
    required_signal_dbm: float = RX_SENSITIVITY_DBM
    connected: bool = False
    connected_router_id: int = -1


class NetworkManager:
    """
    Helper class to manage the state of the network.
    """

    def __init__(self, routers: list[Router], sensors: list[Sensor]):
        self.routers = routers
        self.sensors = sensors

    def get_active_routers(self) -> list[Router]:
        return [r for r in self.routers if r.active]

    def calculate_total_energy(self) -> float:
        """Returns total power consumption in Watts"""
        return sum(r.power_consumption_watts for r in self.routers if r.active)

    def calculate_total_cost(self) -> float:
        """Returns total deployment cost"""
        return sum(r.cost for r in self.routers if r.active)
