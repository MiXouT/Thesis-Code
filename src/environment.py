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
    label_pos: Optional[Tuple[float, float]] = None  # (x, y) coordinates

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
                return True
        return False

    def get_floor_level(self, z: float) -> int:
        """Returns the floor level for a given Z coordinate."""
        for room in self.rooms:
            _, _, min_z, _, _, max_z = room.bounds()
            # Use a small epsilon for float comparison or strict inequality
            if min_z <= z < max_z + 0.1:
                return room.floor_level
        return 0  # Default to ground floor if undefined

    @staticmethod
    def from_json(file_path: str):
        import json

        with open(file_path, "r") as f:
            data = json.load(f)

        building = Building(data["name"])

        for floor_data in data["floors"]:
            floor_level = floor_data["level"]
            floor_height = floor_data["height"]
            z_base = floor_level * floor_height

            for room_data in floor_data["rooms"]:
                room = Room(
                    room_data["name"],
                    floor_level=floor_level,
                    height=floor_height,
                    label_pos=(
                        tuple(room_data["label_pos"])
                        if "label_pos" in room_data
                        else None
                    ),
                )

                for wall_data in room_data["walls"]:
                    start = wall_data["start"]
                    end = wall_data["end"]
                    material = wall_data.get("material", "concrete")

                    p1 = Point(start[0], start[1], z_base)
                    p2 = Point(end[0], end[1], z_base)

                    room.add_wall(p1, p2, material)

                building.add_room(room)

        return building
