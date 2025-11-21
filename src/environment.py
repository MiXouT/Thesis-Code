import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from .config import WALL_ATTENUATION


@dataclass
class Point:
    x: float
    y: float
    z: float

    def to_numpy(self):
        return np.array([self.x, self.y, self.z])


@dataclass
class Wall:
    start: Point
    end: Point
    height: float
    material: str = "concrete"
    thickness: float = 0.15  # meters

    def __post_init__(self):
        if self.material not in WALL_ATTENUATION:
            raise ValueError(
                f"Unknown material: {self.material}. Available: {list(WALL_ATTENUATION.keys())}"
            )
        self.attenuation = WALL_ATTENUATION[self.material]

    def get_bounds(self) -> Tuple[float, float, float, float, float, float]:
        """Returns (min_x, min_y, min_z, max_x, max_y, max_z)"""
        min_x = min(self.start.x, self.end.x)
        max_x = max(self.start.x, self.end.x)
        min_y = min(self.start.y, self.end.y)
        max_y = max(self.start.y, self.end.y)
        return (min_x, min_y, 0, max_x, max_y, self.height)


@dataclass
class Room:
    name: str
    walls: List[Wall] = field(default_factory=list)
    floor_level: int = 0
    height: float = 3.0

    def add_wall(self, start: Point, end: Point, material: str = "concrete"):
        wall = Wall(start, end, self.height, material)
        self.walls.append(wall)

    def bounds(self):
        if not self.walls:
            return (0, 0, 0, 0, 0, 0)

        all_x = []
        all_y = []
        for w in self.walls:
            all_x.extend([w.start.x, w.end.x])
            all_y.extend([w.start.y, w.end.y])

        return (
            min(all_x),
            min(all_y),
            self.floor_level * self.height,
            max(all_x),
            max(all_y),
            (self.floor_level + 1) * self.height,
        )


class Building:
    def __init__(self, name: str):
        self.name = name
        self.rooms: List[Room] = []
        self.floors: int = 1

    def add_room(self, room: Room):
        self.rooms.append(room)
        self.floors = max(self.floors, room.floor_level + 1)

    def get_all_walls(self) -> List[Wall]:
        walls = []
        for room in self.rooms:
            walls.extend(room.walls)
        return walls

    def is_point_inside(self, point: Point) -> bool:
        # Simple bounding box check for now
        # In a real implementation, we'd do ray casting polygon check
        # For this thesis, we assume the building is the union of room bounding boxes
        for room in self.rooms:
            min_x, min_y, min_z, max_x, max_y, max_z = room.bounds()
            if (
                min_x <= point.x <= max_x
                and min_y <= point.y <= max_y
                and min_z <= point.z <= max_z
            ):
                return True
        return False
