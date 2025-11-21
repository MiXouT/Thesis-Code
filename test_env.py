from src.environment import Building, Room, Point


def test_environment():
    print("Testing Environment Module...")

    # Create a building
    b = Building("Test Lab")

    # Create a room (10x10m)
    r1 = Room("Main Hall", floor_level=0, height=3.0)

    # Add walls (Simple square)
    p1 = Point(0, 0, 0)
    p2 = Point(10, 0, 0)
    p3 = Point(10, 10, 0)
    p4 = Point(0, 10, 0)

    r1.add_wall(p1, p2, "concrete")
    r1.add_wall(p2, p3, "glass")
    r1.add_wall(p3, p4, "drywall")
    r1.add_wall(p4, p1, "concrete")

    b.add_room(r1)

    print(f"Building '{b.name}' created with {len(b.rooms)} room(s).")
    print(f"Total walls: {len(b.get_all_walls())}")

    # Test bounds
    bounds = r1.bounds()
    print(f"Room Bounds: {bounds}")

    # Test point inside
    test_p_in = Point(5, 5, 1.5)
    test_p_out = Point(15, 5, 1.5)

    print(f"Point (5,5,1.5) inside? {b.is_point_inside(test_p_in)}")
    print(f"Point (15,5,1.5) inside? {b.is_point_inside(test_p_out)}")

    assert b.is_point_inside(test_p_in) == True
    assert b.is_point_inside(test_p_out) == False
    print("Environment tests passed!")


if __name__ == "__main__":
    test_environment()
