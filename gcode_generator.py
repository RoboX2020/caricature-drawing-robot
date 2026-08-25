"""
G-code generator — converts drawing paths to G-code for saving/inspection.
Also supports loading G-code back into paths.
"""
import os
from datetime import datetime


def paths_to_gcode(paths, z_draw, z_travel, draw_speed=30, travel_speed=100,
                   corner1=None, corner2=None):
    """
    Convert Dobot-coordinate paths to G-code string.

    Args:
        paths: list of paths, each path = list of (x, y) Dobot coords
        z_draw: pen-down Z height
        z_travel: pen-up Z height
        draw_speed: feed rate for drawing (mm/min internally)
        travel_speed: feed rate for travel

    Returns:
        gcode: string of G-code
    """
    lines = []
    lines.append("; Caricature Drawing Robot G-code")
    lines.append(f"; Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"; Paths: {len(paths)}")
    lines.append(f"; Z draw: {z_draw}  Z travel: {z_travel}")
    if corner1 and corner2:
        lines.append(f"; Corner1: x={corner1['x']} y={corner1['y']}")
        lines.append(f"; Corner2: x={corner2['x']} y={corner2['y']}")
    total_points = sum(len(p) for p in paths)
    lines.append(f"; Total points: {total_points}")
    lines.append("")

    # Initial setup
    lines.append("G21 ; mm mode")
    lines.append("G90 ; absolute positioning")
    lines.append(f"G0 Z{z_travel:.2f} ; pen up")
    lines.append("")

    for i, path in enumerate(paths):
        if len(path) < 2:
            continue
        lines.append(f"; Path {i+1}/{len(paths)}")

        # Travel to start
        x0, y0 = path[0]
        lines.append(f"G0 X{x0:.2f} Y{y0:.2f} Z{z_travel:.2f} F{travel_speed}")

        # Pen down
        lines.append(f"G1 Z{z_draw:.2f} F{draw_speed}")

        # Draw through points
        for x, y in path[1:]:
            lines.append(f"G1 X{x:.2f} Y{y:.2f} F{draw_speed}")

        # Pen up
        lines.append(f"G0 Z{z_travel:.2f}")
        lines.append("")

    # End
    lines.append("; Done")
    lines.append(f"G0 Z{z_travel:.2f}")
    lines.append("M2 ; end of program")

    return "\n".join(lines)


def save_gcode(gcode_str, filepath=None):
    """Save G-code string to file."""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drawing.gcode")
    with open(filepath, "w") as f:
        f.write(gcode_str)
    print(f"  ✓ G-code saved to {filepath}")
    return filepath


def load_gcode(filepath):
    """
    Load G-code from file and convert back to paths.

    Returns:
        paths: list of paths in Dobot coords
        z_draw: pen-down height (parsed from header)
        z_travel: pen-up height (parsed from header)
    """
    if not os.path.exists(filepath):
        print(f"  ✗ File not found: {filepath}")
        return None, None, None

    with open(filepath, "r") as f:
        lines = f.readlines()

    z_draw = None
    z_travel = None
    paths = []
    current_path = []
    pen_is_down = False

    for line in lines:
        line = line.strip()

        # Parse header comments for Z values
        if line.startswith("; Z draw:"):
            parts = line.split()
            try:
                idx = parts.index("draw:")
                z_draw = float(parts[idx + 1])
                idx2 = parts.index("travel:")
                z_travel = float(parts[idx2 + 1])
            except (ValueError, IndexError):
                pass
            continue

        if line.startswith(";") or line == "" or line.startswith("M"):
            continue

        # Parse G-code
        if line.startswith("G0") or line.startswith("G1"):
            params = _parse_gcode_params(line)
            x = params.get("X")
            y = params.get("Y")
            z = params.get("Z")

            if z is not None:
                if z_draw is not None and abs(z - z_draw) < 0.1:
                    pen_is_down = True
                elif z_travel is not None and abs(z - z_travel) < 0.1:
                    if pen_is_down and current_path:
                        paths.append(current_path)
                        current_path = []
                    pen_is_down = False

            if pen_is_down and x is not None and y is not None:
                current_path.append((x, y))

    # Don't forget the last path
    if current_path:
        paths.append(current_path)

    print(f"  ✓ Loaded {len(paths)} paths from {filepath}")
    return paths, z_draw, z_travel


def _parse_gcode_params(line):
    """Parse G-code line into parameter dict. e.g. 'G1 X10 Y20 Z5 F100' → {'X':10, 'Y':20, 'Z':5, 'F':100}"""
    params = {}
    parts = line.split()
    for part in parts[1:]:  # skip G0/G1
        if part and part[0] in "XYZF":
            try:
                params[part[0]] = float(part[1:])
            except ValueError:
                pass
    return params
