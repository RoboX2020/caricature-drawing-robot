#!/usr/bin/env python3
"""
Caricature Drawing Robot — Terminal Interface
Dobot Magician Lite controller for drawing line-art from photos.
"""
import sys
import os
import time

from config import load_config, save_config, print_config
from dobot_controller import DobotController
from image_processor import load_and_process_image, map_paths_to_dobot, preview_paths
from gcode_generator import paths_to_gcode, save_gcode

# ── State ───────────────────────────────────────────────────

controller = DobotController()
config = {}
pixel_paths = None
dobot_paths = None
img_w = 0
img_h = 0
edge_image = None
current_image_path = None
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ── Helpers ─────────────────────────────────────────────────

def clear():
    os.system('clear' if os.name != 'nt' else 'cls')


def wait():
    input("\n  Press Enter to continue...")


def banner():
    clear()
    print()
    print("  ╔═══════════════════════════════════════════════════╗")
    print("  ║        ✏️  CARICATURE DRAWING ROBOT               ║")
    print("  ║        Dobot Magician Lite                        ║")
    print("  ╚═══════════════════════════════════════════════════╝")


def status_line():
    """One-line status bar."""
    parts = []
    parts.append("🟢 Connected" if controller.connected else "🔴 Disconnected")

    c1, c2 = config.get("corner1"), config.get("corner2")
    zd, zt = config.get("z_draw"), config.get("z_travel")
    if c1 and c2 and zd is not None and zt is not None:
        w = abs(c2["x"] - c1["x"])
        h = abs(c2["y"] - c1["y"])
        parts.append(f"📐 {w:.0f}×{h:.0f}mm")
    else:
        missing = []
        if not (c1 and c2):
            missing.append("corners")
        if zd is None or zt is None:
            missing.append("Z heights")
        parts.append(f"⚠️  Need: {', '.join(missing)}")

    if current_image_path:
        n = len(dobot_paths) if dobot_paths else len(pixel_paths) if pixel_paths else 0
        parts.append(f"📷 {os.path.basename(current_image_path)} ({n} paths)")
    print(f"\n  {' │ '.join(parts)}")


def is_calibrated():
    """Check if paper corners and Z heights are all set."""
    return (config.get("corner1") and config.get("corner2")
            and config.get("z_draw") is not None
            and config.get("z_travel") is not None)


def auto_generate_gcode():
    """Auto-generate gcode if everything is ready."""
    global dobot_paths
    if dobot_paths and is_calibrated():
        gcode = paths_to_gcode(
            dobot_paths,
            z_draw=config["z_draw"],
            z_travel=config["z_travel"],
            draw_speed=config.get("draw_speed", 30),
            travel_speed=config.get("travel_speed", 100),
            corner1=config.get("corner1"),
            corner2=config.get("corner2"),
        )
        save_gcode(gcode, os.path.join(BASE_DIR, "drawing.gcode"))


def jog_loop(prompt="jog", allow_save=False, save_label="position"):
    """
    Reusable jog loop. Returns saved position (x,y,z,r) if allow_save and user typed 'save'.
    Returns None if user quits with 'q'.
    """
    step = 5.0
    print(f"  Controls:  W/S=Y  A/D=X  R/F=Z  │  1=1mm  2=5mm  3=10mm  │  P=position  Q=done")
    if allow_save:
        print(f"  Type 'save' to record {save_label}")
    print(f"  Step: {step}mm")
    controller.print_position()

    JOG_MAP = {
        'w': (0, 1, 0), 's': (0, -1, 0),
        'a': (-1, 0, 0), 'd': (1, 0, 0),
        'r': (0, 0, 1), 'f': (0, 0, -1),
    }
    STEP_MAP = {'1': 1.0, '2': 5.0, '3': 10.0}

    while True:
        cmd = input(f"  {prompt}> ").strip().lower()
        if not cmd:
            continue
        if cmd == 'q':
            return None
        if cmd == 'save' and allow_save:
            pos = controller.get_position()
            if pos:
                print(f"  ✓ Saved: x={pos[0]:.2f}  y={pos[1]:.2f}  z={pos[2]:.2f}")
            return pos
        if cmd in JOG_MAP:
            dx, dy, dz = JOG_MAP[cmd]
            controller.jog_step(dx=dx, dy=dy, dz=dz, step=step)
            controller.print_position()
        elif cmd in STEP_MAP:
            step = STEP_MAP[cmd]
            print(f"  Step: {step}mm")
        elif cmd == 'p':
            controller.print_position()
        else:
            print("  W/A/S/D/R/F to move, 1/2/3 step, P position, Q quit" +
                  (", SAVE to record" if allow_save else ""))


# ── Actions ─────────────────────────────────────────────────

def do_calibrate():
    """Guided calibration: 2 corners + Z heights in one flow."""
    global config
    if not controller.connected:
        print("\n  ✗ Connect first! Run the program with Dobot plugged in.")
        wait()
        return

    print("\n  ╔═══ CALIBRATION ═════════════════════════════════╗")
    print("  ║  We'll set 4 things:                            ║")
    print("  ║    1. Pen DOWN height (Z touching paper)        ║")
    print("  ║    2. Pen UP height   (Z travel clearance)      ║")
    print("  ║    3. Paper corner 1  (bottom-left)             ║")
    print("  ║    4. Paper corner 2  (top-right)               ║")
    print("  ╚═════════════════════════════════════════════════╝")

    # ── Step 1: Z draw ──
    print("\n  ── STEP 1/4: Pen DOWN height ──")
    print("  Lower the pen until it just touches the paper.\n")
    pos = jog_loop(prompt="z-down", allow_save=True, save_label="pen-down height")
    if pos is None:
        print("  Calibration cancelled.")
        wait()
        return
    config["z_draw"] = round(pos[2], 2)
    print(f"  ✓ Pen DOWN = {config['z_draw']}mm\n")

    # ── Step 2: Z travel ──
    print("  ── STEP 2/4: Pen UP height ──")
    print("  Raise the pen to safe travel height.\n")
    pos = jog_loop(prompt="z-up", allow_save=True, save_label="pen-up height")
    if pos is None:
        print("  Calibration cancelled.")
        wait()
        return
    config["z_travel"] = round(pos[2], 2)
    print(f"  ✓ Pen UP = {config['z_travel']}mm\n")

    # ── Step 3: Corner 1 ──
    print("  ── STEP 3/4: Paper corner 1 (bottom-left) ──")
    print("  Jog the pen to the BOTTOM-LEFT corner of your paper.\n")
    pos = jog_loop(prompt="corner1", allow_save=True, save_label="corner 1")
    if pos is None:
        print("  Calibration cancelled.")
        wait()
        return
    config["corner1"] = {"x": pos[0], "y": pos[1], "z": pos[2]}

    # ── Step 4: Corner 2 ──
    print("\n  ── STEP 4/4: Paper corner 2 (top-right) ──")
    print("  Jog the pen to the TOP-RIGHT corner of your paper.\n")
    pos = jog_loop(prompt="corner2", allow_save=True, save_label="corner 2")
    if pos is None:
        print("  Calibration cancelled.")
        wait()
        return
    config["corner2"] = {"x": pos[0], "y": pos[1], "z": pos[2]}

    # Apply & save
    controller.set_z_heights(config["z_draw"], config["z_travel"])
    w = abs(config["corner2"]["x"] - config["corner1"]["x"])
    h = abs(config["corner2"]["y"] - config["corner1"]["y"])
    save_config(config)

    print(f"\n  ✅ Calibration complete!")
    print(f"     Canvas: {w:.1f} × {h:.1f} mm")
    print(f"     Pen down: {config['z_draw']}mm  │  Pen up: {config['z_travel']}mm")

    # Re-map image if one was already loaded
    if pixel_paths:
        global dobot_paths
        dobot_paths = map_paths_to_dobot(pixel_paths, img_w, img_h,
                                         config["corner1"], config["corner2"])
        auto_generate_gcode()
        print(f"     Image re-mapped to new canvas ({len(dobot_paths)} paths)")

    wait()


def _pick_file():
    """Open a native macOS Finder file picker. Returns path or None."""
    import subprocess
    try:
        # Tell Finder to activate so the dialog pops to the front
        script = '''
        tell application "Finder" to activate
        tell application "System Events"
            activate
            return POSIX path of (choose file of type {"public.image"} with prompt "Select an image for the drawing robot")
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def do_load_image():
    """Load an image, process it, auto-map and auto-generate gcode."""
    global pixel_paths, dobot_paths, img_w, img_h, edge_image, current_image_path

    print("\n  ── LOAD IMAGE ──")
    print("  [1] 📂 Open file picker (Finder)")
    print("  [2] ⌨️  Type / paste file path")
    choice = input("\n  > ").strip()

    path = None
    if choice == '1':
        print("  Opening file picker...")
        path = _pick_file()
        if path:
            print(f"  Selected: {path}")
        else:
            print("  No file selected.")
            return
    elif choice == '2':
        print("  Drag & drop the file here, or type the path:")
        path = input("  Image: ").strip()
        path = path.strip("'\"")  # remove quotes from drag-and-drop
        # Also handle escaped spaces from drag-and-drop (e.g. /path/to/my\ file.png)
        path = path.replace('\\ ', ' ')
    else:
        print("  Cancelled.")
        return

    if not path:
        print("  Cancelled.")
        return

    if not os.path.exists(path):
        print(f"  ✗ File not found: {path}")
        wait()
        return

    # Detail level
    detail_str = input("  Detail level 1-5 [3]: ").strip()
    detail = 3
    if detail_str:
        try:
            detail = max(1, min(5, int(detail_str)))
        except ValueError:
            pass

    print(f"\n  Processing (detail={detail})...")
    pixel_paths, img_w, img_h, edge_image = load_and_process_image(path, detail_level=detail)

    if pixel_paths is None:
        wait()
        return

    current_image_path = path

    # Auto-map to Dobot if calibrated
    c1, c2 = config.get("corner1"), config.get("corner2")
    if c1 and c2:
        dobot_paths = map_paths_to_dobot(pixel_paths, img_w, img_h, c1, c2)
        # Auto-generate gcode
        if is_calibrated():
            auto_generate_gcode()
    else:
        dobot_paths = None
        print("  ⚠ Calibrate paper first to enable drawing.")

    # Auto-preview
    print("\n  Generating preview...")
    save_path = os.path.join(BASE_DIR, "preview.png")
    preview_paths(pixel_paths, img_w, img_h, edge_image, save_path=save_path)
    os.system(f'open "{save_path}" 2>/dev/null')

    wait()


def do_draw():
    """Start drawing. Checks everything is ready."""
    if not controller.connected:
        print("\n  ✗ Dobot not connected!")
        wait()
        return

    if dobot_paths is None:
        if pixel_paths is None:
            print("\n  ✗ No image loaded. Use [I] to load one.")
        else:
            print("\n  ✗ Not calibrated. Use [C] to calibrate.")
        wait()
        return

    if not is_calibrated():
        print("\n  ✗ Z heights not set. Use [C] to calibrate.")
        wait()
        return

    total_points = sum(len(p) for p in dobot_paths)
    est_min = total_points * 0.3 / 60

    print(f"\n  ┌─── READY TO DRAW ──────────────────────┐")
    print(f"  │  Image:   {os.path.basename(current_image_path)}")
    print(f"  │  Paths:   {len(dobot_paths)}")
    print(f"  │  Points:  {total_points}")
    print(f"  │  Est:     ~{est_min:.0f} min")
    print(f"  └──────────────────────────────────────────┘")

    confirm = input("\n  Start? (y/n): ").strip().lower()
    if confirm not in ('y', 'yes'):
        print("  Cancelled.")
        return

    print("\n  ⚡ Drawing! Ctrl+C = emergency stop\n")
    try:
        controller.draw_all_paths(dobot_paths)
    except KeyboardInterrupt:
        print("\n\n  🛑 EMERGENCY STOP")
        try:
            controller.pen_up()
        except Exception:
            pass
        print("  Pen lifted. Drawing aborted.")

    wait()


def do_jog():
    """Free jog mode."""
    if not controller.connected:
        print("\n  ✗ Dobot not connected!")
        wait()
        return
    print("\n  ── JOG MODE ──")
    jog_loop(prompt="jog")


# ── Auto-connect ────────────────────────────────────────────

def auto_connect():
    """Try to connect using saved port on startup."""
    port = config.get("port")
    if port:
        print(f"  Connecting to {port}...", end=" ", flush=True)
        if controller.connect(port):
            # Apply saved calibration
            if config.get("z_draw") is not None and config.get("z_travel") is not None:
                controller.set_z_heights(config["z_draw"], config["z_travel"])
            if config.get("draw_speed"):
                controller.draw_speed = config["draw_speed"]
            if config.get("travel_speed"):
                controller.travel_speed = config["travel_speed"]
            return True
    return False


# ── Main ────────────────────────────────────────────────────

def main():
    global config
    config = load_config()

    banner()
    auto_connect()

    while True:
        status_line()
        ready = is_calibrated() and dobot_paths is not None and controller.connected

        print("\n  ─────────────────────────────────────")
        print("  [C] Calibrate  (corners + Z heights)")
        print("  [I] Load Image")
        if dobot_paths:
            print("  [P] Preview")
        if ready:
            print("  [D] 🖊  DRAW!")
        print("  [J] Jog (manual control)")
        print("  [Q] Quit")
        print("  ─────────────────────────────────────")

        choice = input("\n  > ").strip().lower()

        if choice == 'c':
            do_calibrate()
        elif choice == 'i':
            do_load_image()
        elif choice == 'p' and dobot_paths:
            # Re-preview
            save_path = os.path.join(BASE_DIR, "preview.png")
            preview_paths(pixel_paths, img_w, img_h, edge_image, save_path=save_path)
            os.system(f'open "{save_path}" 2>/dev/null')
            print("  Preview opened.")
        elif choice == 'd' and ready:
            do_draw()
        elif choice == 'j':
            do_jog()
        elif choice == 'q':
            controller.disconnect()
            print("\n  Goodbye! 👋\n")
            sys.exit(0)
        else:
            print("  Invalid option.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Shutting down...")
        controller.disconnect()
        sys.exit(0)
