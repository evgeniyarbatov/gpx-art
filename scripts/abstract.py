import sys
import gpxpy
import random

import matplotlib.pyplot as plt
import numpy as np

from utils import (
    get_files,
)

def distance(p1, p2):
    return np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)

def plot(gpx_filename, image_filename):
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    # Extract points
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append((point.longitude, point.latitude))

    # Normalize coordinates
    points = np.array(points)
    points -= points.mean(axis=0)
    points /= np.abs(points).max()

    # Function to transform (rotate + offset)
    def transform(points, angle, offset):
        theta = np.radians(angle)
        rot_matrix = np.array([[np.cos(theta), -np.sin(theta)],
                            [np.sin(theta),  np.cos(theta)]])
        return np.dot(points, rot_matrix.T) + offset

    # Plot setup
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect('equal')
    ax.axis('off')

    # Draw multiple abstract layers
    for i in range(random.randint(10, 60)):  # More layers = more texture
        angle = random.uniform(0, 360)
        offset = np.random.uniform(-1.5, 1.5, size=2)
        transformed = transform(points, angle, offset)
        ax.plot(transformed[:,0], transformed[:,1],
                linewidth=0.3,
                color='black',
                alpha=random.uniform(0.4, 0.5))

    plt.savefig(image_filename, bbox_inches='tight', dpi=300)
    plt.close()

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):        
        plot(
            gpx_path,
            f"{images_dir}/abstract-{name}.png",
        )

if __name__ == "__main__":
    main(*sys.argv[1:])