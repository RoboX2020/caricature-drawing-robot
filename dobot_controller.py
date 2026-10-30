# PLAIN ENGLISH: the robot arm's remote control - connect, move, pen up/down,
# and draw a list of strokes.
"""
Dobot Magician Lite controller — connection, movement, pen control, and drawing.
"""
import time
from pydobotplus import Dobot


class DobotController:
    def __init__(self):
        self.device = None
        self.connected = False
        self.z_draw = None    # pen touching paper
        self.z_travel = None  # pen lifted for travel
        self.draw_speed = 30
        self.travel_speed = 100

    # ── Connection ──────────────────────────────────────────

    def connect(self, port):
        """Connect to the Dobot on the given serial port."""
        if self.connected:
            print("  Already connected. Disconnect first.")
            return True
        try:
            self.device = Dobot(port=port)
            self.connected = True
            print(f"  ✓ Connected to Dobot on {port}")
            return True
        except Exception as e:
            print(f"  ✗ Connection failed: {e}")
            return False

    def disconnect(self):
        """Close connection to the Dobot."""
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None
            self.connected = False
            print("  ✓ Disconnected")

    def _check_connected(self):
        if not self.connected or not self.device:
            print("  ✗ Not connected to Dobot!")
            return False
        return True

    # ── Position ────────────────────────────────────────────

    def get_position(self):
        """Return current (x, y, z, r) position."""
        if not self._check_connected():
            return None
        import struct
        for _ in range(3):
            try:
                pose = self.device.get_pose()
                p = pose.position
                return (p.x, p.y, p.z, p.r)
            except struct.error:
                # Sometimes the serial buffer is too short, retry
                time.sleep(0.05)
        return None

    def print_position(self):
        """Print current position to the terminal."""
        pos = self.get_position()
        if pos:
            x, y, z, r = pos
            print(f"  Position: x={x:.2f}  y={y:.2f}  z={z:.2f}  r={r:.2f}")
        return pos

    # ── Movement ────────────────────────────────────────────

    def move_to(self, x, y, z, r=0, speed=None):
        """Move to absolute coordinates. Uses time.sleep for reliable execution."""
        if not self._check_connected():
            return
        if speed:
            self.device.speed(velocity=speed, acceleration=speed)
        
        import os
        import sys
        # Suppress the stray print(current_pose) in pydobotplus
        old_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        try:
            self.device.move_to(x, y, z, r, wait=False)
        finally:
            sys.stdout.close()
            sys.stdout = old_stdout
        # Estimate travel time based on distance
        pos = self.get_position()
        if pos:
            dist = ((x - pos[0])**2 + (y - pos[1])**2 + (z - pos[2])**2) ** 0.5
            effective_speed = speed or self.draw_speed
            wait_time = max(0.3, dist / max(effective_speed, 1) + 0.15)
            time.sleep(wait_time)

    def move_to_fast(self, x, y, z, r=0):
        """Rapid move (pen up, travel speed)."""
        self.move_to(x, y, z, r, speed=self.travel_speed)

    def move_to_draw(self, x, y, z, r=0):
        """Drawing move (pen down, draw speed)."""
        self.move_to(x, y, z, r, speed=self.draw_speed)

    # ── Pen control ─────────────────────────────────────────

    def pen_up(self):
        """Raise pen to travel height."""
        if self.z_travel is None:
            print("  ✗ Z travel height not set!")
            return
        pos = self.get_position()
        if pos:
            self.move_to_fast(pos[0], pos[1], self.z_travel)

    def pen_down(self):
        """Lower pen to drawing height."""
        if self.z_draw is None:
            print("  ✗ Z draw height not set!")
            return
        pos = self.get_position()
        if pos:
            self.move_to_draw(pos[0], pos[1], self.z_draw)

    def set_z_heights(self, z_draw, z_travel):
        """Set pen-down and pen-up Z heights."""
        self.z_draw = z_draw
        self.z_travel = z_travel

    # ── Drawing ─────────────────────────────────────────────

    def draw_path(self, points):
        """
        Draw a single continuous path.
        points: list of (x, y) in Dobot coordinates.
        Pen down at start, move through all points, pen up at end.
        """
        if not points:
            return
        if self.z_draw is None or self.z_travel is None:
            print("  ✗ Z heights not calibrated!")
            return

        # Travel to start of path
        x0, y0 = points[0]
        self.move_to_fast(x0, y0, self.z_travel)
        # Pen down
        self.move_to_draw(x0, y0, self.z_draw)
        # Draw through all points
        for x, y in points[1:]:
            self.move_to_draw(x, y, self.z_draw)
        # Pen up
        pos = self.get_position()
        if pos:
            self.move_to_fast(pos[0], pos[1], self.z_travel)

    def draw_all_paths(self, paths, progress_callback=None):
        """
        Draw all paths.
        paths: list of paths, each path is a list of (x, y) tuples.
        progress_callback: optional function(current_index, total) for updates.
        """
        if not self._check_connected():
            return
        total = len(paths)
        print(f"\n  Starting to draw {total} paths...")
        # Ensure pen is up
        if self.z_travel is not None:
            pos = self.get_position()
            if pos:
                self.move_to_fast(pos[0], pos[1], self.z_travel)

        for i, path in enumerate(paths):
            self.draw_path(path)
            if progress_callback:
                progress_callback(i + 1, total)
            elif (i + 1) % 10 == 0 or i == total - 1:
                pct = int((i + 1) / total * 100)
                print(f"  Progress: {i+1}/{total} paths ({pct}%)")

        print("  ✓ Drawing complete!")

    # ── Jog ─────────────────────────────────────────────────

    def jog_step(self, dx=0, dy=0, dz=0, step=5.0):
        """Move relative by step in the given axis."""
        if not self._check_connected():
            return
        pos = self.get_position()
        if pos:
            x, y, z, r = pos
            self.move_to(x + dx * step, y + dy * step, z + dz * step, r,
                         speed=self.travel_speed)
