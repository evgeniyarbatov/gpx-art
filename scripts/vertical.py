import sys
import gpxpy

from PIL import Image, ImageDraw
import numpy as np

from utils import (
    get_files,
)

def lines(gpx_filename, image_filename, num_lines=20, img_width=1000, img_height=1000, trace_width=30):
    # Step 1: Parse GPX
    with open(gpx_filename, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append((point.longitude, point.latitude))

    if len(points) < 2:
        print("Not enough points.")
        return

    # Step 2: Normalize points to image coords
    lons, lats = zip(*points)
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    def normalize(lon, lat):
        x = (lon - min_lon) / (max_lon - min_lon) * img_width
        y = img_height - (lat - min_lat) / (max_lat - min_lat) * img_height
        return (x, y)

    norm_points = [normalize(lon, lat) for lon, lat in points]

    # Step 3: Rasterize GPX trace onto a mask image
    trace_mask = Image.new("L", (img_width, img_height), 0)
    draw = ImageDraw.Draw(trace_mask)
    draw.line(norm_points, fill=255, width=trace_width)

    mask_array = np.array(trace_mask)

    # Step 4: Create white canvas with black vertical lines except where mask is non-zero
    img = Image.new("RGB", (img_width, img_height), "white")
    pixels = img.load()

    for i in range(num_lines):
        x = int(img_width * i / num_lines)
        for y in range(img_height):
            if mask_array[y, x] == 0:  # no trace at this pixel
                pixels[x, y] = (0, 0, 0)  # draw black pixel

    # Step 5: Save
    img.save(image_filename)
    
def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):        
        lines(
            gpx_path,
            f"{images_dir}/vertical-lines-{name}.png",
        )

if __name__ == "__main__":
    main(*sys.argv[1:])