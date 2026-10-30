# PLAIN ENGLISH: turns a photo into clean line-art strokes the arm can draw.
"""
Image processor — converts a photo into drawable line-art paths.

Pipeline: Photo → Grayscale → Edge Detection → Contours → Simplified Paths
Then maps pixel coordinates to Dobot workspace coordinates.
"""
import cv2
import numpy as np
import os


# # The photo-to-strokes pipeline: shrink the photo, find edges (outlines),
# # trace them into continuous paths, then simplify - fewer points means a
# # faster, smoother drawing. detail_level sets how much outline survives.
def load_and_process_image(image_path, max_size=800, detail_level=3):
    """
    Load a photo and convert it to a list of drawable paths (in pixel coordinates).

    Args:
        image_path: path to JPEG/PNG image
        max_size: resize longest side to this many pixels
        detail_level: 1 (minimal) to 5 (maximum detail)

    Returns:
        paths: list of paths, each path = list of (x, y) pixel coords
        img_w: processed image width
        img_h: processed image height
        edge_image: the edge-detected image (for preview)
    """
    if not os.path.exists(image_path):
        print(f"  ✗ Image not found: {image_path}")
        return None, 0, 0, None

    # Load image
    img = cv2.imread(image_path)
    if img is None:
        print(f"  ✗ Could not read image: {image_path}")
        return None, 0, 0, None

    # Resize to manageable size
    h, w = img.shape[:2]
    scale = max_size / max(h, w)
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    h, w = img.shape[:2]
    print(f"  Image loaded: {w}x{h} pixels")

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Bilateral filter — smooths while keeping edges sharp
    d = [5, 7, 9, 11, 13][min(detail_level - 1, 4)]
    gray = cv2.bilateralFilter(gray, d, 75, 75)

    # Adaptive threshold for clean edges
    # Also do Canny for fine details and combine
    # Auto Canny thresholds
    median_val = np.median(gray)
    sigma = 0.33
    canny_low = int(max(0, (1.0 - sigma) * median_val))
    canny_high = int(min(255, (1.0 + sigma) * median_val))

    edges_canny = cv2.Canny(gray, canny_low, canny_high)

    # Adaptive threshold for bolder outlines
    block_size = [15, 13, 11, 9, 7][min(detail_level - 1, 4)]
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, block_size, 2
    )

    # Combine edges
    edges = cv2.bitwise_or(edges_canny, thresh)

    # Thin the edges (morphological skeleton)
    kernel = np.ones((2, 2), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    # Filter and simplify contours
    min_contour_length = max(10, max(w, h) * 0.02)  # skip tiny noise
    epsilon_factor = [0.02, 0.015, 0.01, 0.007, 0.005][min(detail_level - 1, 4)]

    paths = []
    for contour in contours:
        arc_len = cv2.arcLength(contour, closed=False)
        if arc_len < min_contour_length:
            continue

        # Simplify
        epsilon = epsilon_factor * arc_len
        approx = cv2.approxPolyDP(contour, epsilon, closed=False)

        if len(approx) >= 2:
            path = [(int(pt[0][0]), int(pt[0][1])) for pt in approx]
            paths.append(path)

    # Sort paths to minimize travel distance (nearest-neighbor greedy)
    paths = _optimize_path_order(paths)

    total_points = sum(len(p) for p in paths)
    print(f"  ✓ Extracted {len(paths)} paths ({total_points} total points)")

    return paths, w, h, edges


# # Convert pixel positions into the robot arm's real-world coordinates,
# # scaled to fit the physical drawing area (corner1 to corner2).
def map_paths_to_dobot(paths, img_w, img_h, corner1, corner2):
    """
    Map pixel-coordinate paths to Dobot workspace coordinates.

    corner1 and corner2 define the drawing rectangle in Dobot space.
    The image is scaled to fit within this rectangle while preserving aspect ratio.

    Args:
        paths: list of paths in pixel coords
        img_w, img_h: image dimensions
        corner1, corner2: dicts with x, y keys (Dobot coords)

    Returns:
        mapped_paths: list of paths in Dobot (x, y) coordinates
    """
    # Dobot canvas bounds
    dx_min = min(corner1["x"], corner2["x"])
    dx_max = max(corner1["x"], corner2["x"])
    dy_min = min(corner1["y"], corner2["y"])
    dy_max = max(corner1["y"], corner2["y"])

    canvas_w = dx_max - dx_min
    canvas_h = dy_max - dy_min

    # Scale to fit while preserving aspect ratio
    scale_x = canvas_w / img_w if img_w > 0 else 1
    scale_y = canvas_h / img_h if img_h > 0 else 1
    scale = min(scale_x, scale_y)

    # Center the drawing in the canvas
    draw_w = img_w * scale
    draw_h = img_h * scale
    offset_x = dx_min + (canvas_w - draw_w) / 2
    offset_y = dy_min + (canvas_h - draw_h) / 2

    mapped_paths = []
    for path in paths:
        mapped = []
        for px, py in path:
            # Map pixel (px, py) to Dobot (x, y)
            # px maps along the Dobot X axis
            # py maps along the Dobot Y axis (inverted — image Y goes down, Dobot Y goes up)
            dobot_x = offset_x + px * scale
            dobot_y = offset_y + (img_h - py) * scale  # flip Y
            mapped.append((dobot_x, dobot_y))
        mapped_paths.append(mapped)

    print(f"  ✓ Mapped to Dobot canvas: {draw_w:.1f} x {draw_h:.1f} mm")
    print(f"    X range: {offset_x:.1f} to {offset_x + draw_w:.1f}")
    print(f"    Y range: {offset_y:.1f} to {offset_y + draw_h:.1f}")

    return mapped_paths


# # Draw the planned strokes on screen (or to a file) so you can check the
# # drawing before the robot starts moving.
def preview_paths(paths, img_w, img_h, edge_image=None, save_path=None):
    """
    Render the paths as a matplotlib figure for visual preview.
    Saves to file (since we're in a headless terminal).
    """
    import matplotlib
    matplotlib.use('Agg')  # headless backend
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2 if edge_image is not None else 1, figsize=(14, 7))

    if edge_image is not None:
        ax1 = axes[0]
        ax2 = axes[1]
        ax1.imshow(edge_image, cmap='gray')
        ax1.set_title("Edge Detection")
        ax1.axis('off')
    else:
        ax2 = axes if not isinstance(axes, np.ndarray) else axes[0]

    # Draw paths
    ax2.set_xlim(0, img_w)
    ax2.set_ylim(img_h, 0)  # flip Y so it matches image orientation
    ax2.set_aspect('equal')
    ax2.set_title(f"Drawing Paths ({len(paths)} paths)")
    ax2.set_facecolor('white')

    for path in paths:
        if len(path) < 2:
            continue
        xs = [p[0] for p in path]
        ys = [p[1] for p in path]
        ax2.plot(xs, ys, 'k-', linewidth=0.5)

    plt.tight_layout()

    if save_path is None:
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview.png")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Preview saved to {save_path}")
    return save_path


# # Reorder strokes so the pen travels less between them (nearest first),
# # which makes the whole drawing faster.
def _optimize_path_order(paths):
    """
    Reorder paths using nearest-neighbor heuristic to minimize pen-up travel.
    """
    if len(paths) <= 1:
        return paths

    remaining = list(range(len(paths)))
    ordered = [remaining.pop(0)]
    current_end = paths[ordered[0]][-1]

    while remaining:
        # Find nearest path start to current end
        best_idx = None
        best_dist = float('inf')
        best_reversed = False

        for i in remaining:
            # Check distance to start
            start = paths[i][0]
            d_start = (current_end[0] - start[0])**2 + (current_end[1] - start[1])**2

            # Also check distance to end (we can reverse the path)
            end = paths[i][-1]
            d_end = (current_end[0] - end[0])**2 + (current_end[1] - end[1])**2

            if d_start < best_dist:
                best_dist = d_start
                best_idx = i
                best_reversed = False
            if d_end < best_dist:
                best_dist = d_end
                best_idx = i
                best_reversed = True

        remaining.remove(best_idx)
        if best_reversed:
            paths[best_idx] = list(reversed(paths[best_idx]))
        ordered.append(best_idx)
        current_end = paths[best_idx][-1]

    return [paths[i] for i in ordered]
