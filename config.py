"""
Calibration configuration — save/load paper corners, Z heights, and port settings.
"""
import json
import os

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration.json")

DEFAULT_CONFIG = {
    "port": "/dev/cu.usbmodem389438CC04312",
    "corner1": None,       # {"x": ..., "y": ..., "z": ...}
    "corner2": None,       # {"x": ..., "y": ..., "z": ...}
    "z_draw": None,        # pen-down Z height (touching paper)
    "z_travel": None,      # pen-up Z height (clearance for travel)
    "draw_speed": 30,      # mm/s for drawing moves
    "travel_speed": 100,   # mm/s for rapid travel moves
}


def load_config(path=None):
    """Load calibration from JSON file. Returns defaults if file doesn't exist."""
    path = path or DEFAULT_CONFIG_PATH
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(path):
        with open(path, "r") as f:
            saved = json.load(f)
        config.update(saved)
    return config


def save_config(config, path=None):
    """Save calibration to JSON file."""
    path = path or DEFAULT_CONFIG_PATH
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  ✓ Calibration saved to {path}")


def print_config(config):
    """Pretty-print the current calibration."""
    print("\n  ┌─── Current Calibration ───────────────────┐")
    print(f"  │ Port:         {config['port'] or 'Not set'}")
    c1 = config.get("corner1")
    c2 = config.get("corner2")
    if c1:
        print(f"  │ Corner 1:     x={c1['x']:.1f}  y={c1['y']:.1f}  z={c1['z']:.1f}")
    else:
        print(f"  │ Corner 1:     Not set")
    if c2:
        print(f"  │ Corner 2:     x={c2['x']:.1f}  y={c2['y']:.1f}  z={c2['z']:.1f}")
    else:
        print(f"  │ Corner 2:     Not set")
    print(f"  │ Z draw:       {config['z_draw'] if config['z_draw'] is not None else 'Not set'}")
    print(f"  │ Z travel:     {config['z_travel'] if config['z_travel'] is not None else 'Not set'}")
    print(f"  │ Draw speed:   {config['draw_speed']} mm/s")
    print(f"  │ Travel speed: {config['travel_speed']} mm/s")
    if c1 and c2:
        w = abs(c2["x"] - c1["x"])
        h = abs(c2["y"] - c1["y"])
        print(f"  │ Canvas size:  {w:.1f} x {h:.1f} mm")
    print(f"  └─────────────────────────────────────────────┘\n")
