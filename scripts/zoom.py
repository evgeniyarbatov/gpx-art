import sys
import gpxpy

import numpy as np
import matplotlib.pyplot as plt

from utils import (
    get_files,
)

def lines(gpx_filename, image_filename, grid_size=200, expansion=20):
   # Parse GPX
    with open(gpx_filename, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    # Extract points
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append((point.longitude, point.latitude))

    points = np.array(points)
    if len(points) < 2:
        print("Not enough points to draw lines.")
        return

    # Create line segments
    segments = np.array([points[i:i+2] for i in range(len(points) - 1)])

    # Normalize
    min_x, min_y = np.min(points, axis=0)
    max_x, max_y = np.max(points, axis=0)
    scale = max(max_x - min_x, max_y - min_y)
    norm_segments = (segments - [min_x, min_y]) / scale

    mids = np.mean(norm_segments, axis=1)

    # Create 2D histogram for density
    hist, xedges, yedges = np.histogram2d(mids[:, 0], mids[:, 1], bins=grid_size)

    # Find bin with max count
    max_idx = np.unravel_index(np.argmax(hist), hist.shape)
    i, j = max_idx

    # Expand zoom area by 'expansion' bins around densest cell
    i_min = max(i - expansion, 0)
    i_max = min(i + expansion + 1, grid_size)
    j_min = max(j - expansion, 0)
    j_max = min(j + expansion + 1, grid_size)

    # Calculate expanded bounding box coordinates
    x0 = xedges[i_min]
    x1 = xedges[i_max]
    y0 = yedges[j_min]
    y1 = yedges[j_max]

    # Mask lines within expanded bounding box
    mask = (mids[:, 0] >= x0) & (mids[:, 0] <= x1) & (mids[:, 1] >= y0) & (mids[:, 1] <= y1)
    zoom_lines = norm_segments[mask]

    # Plot with bolder lines
    fig, ax = plt.subplots(figsize=(10, 10))
    for line in zoom_lines:
        ax.plot(line[:, 0], line[:, 1], linewidth=6, color='black')

    ax.axis('off')
    ax.set_aspect('equal')
    plt.tight_layout()
    plt.savefig(image_filename, dpi=300, bbox_inches='tight', pad_inches=0)
    plt.close()
    
def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):        
        lines(
            gpx_path,
            f"{images_dir}/zoom-{name}.png",
        )

if __name__ == "__main__":
    main(*sys.argv[1:])