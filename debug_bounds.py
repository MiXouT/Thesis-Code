import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.environment import Building, Point


def debug():
    layout_file = "layout.json"
    building = Building.from_json(layout_file)

    print(f"Building has {len(building.rooms)} rooms")

    for room in building.rooms:
        bounds = room.bounds()
        print(f"Room {room.name} (Floor {room.floor_level}): Bounds {bounds}")

        # Test a point that SHOULD be inside
        # Use the center of the bounding box for X/Y
        center_x = (bounds[0] + bounds[3]) / 2
        center_y = (bounds[1] + bounds[4]) / 2

        # Test Z at base + 1.0
        test_z = bounds[2] + 1.0

        p = Point(center_x, center_y, test_z)
        is_inside = building.is_point_inside(p)
        print(
            f"  Testing Point({p.x:.1f}, {p.y:.1f}, {p.z:.1f}) -> Inside? {is_inside}"
        )

        # Check specific room check
        min_x, min_y, min_z, max_x, max_y, max_z = bounds
        in_box = (
            min_x <= p.x <= max_x and min_y <= p.y <= max_y and min_z <= p.z <= max_z
        )
        print(f"  Direct Box Check: {in_box}")


if __name__ == "__main__":
    debug()
