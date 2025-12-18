import os
import glob
import gpxpy

import pandas as pd


def get_files(input_dir):
    gpx_files = []

    for gpx_file in glob.glob(
        os.path.join(input_dir, "*.[gG][pP][xX]"),
    ):
        name, _ = os.path.splitext(
            os.path.basename(gpx_file),
        )

        gpx_files.append((name, gpx_file))

    return gpx_files


def get_df(filepath):
    with open(filepath, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    data = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                data.append(
                    {
                        "time": point.time,
                        "lat": point.latitude,
                        "lon": point.longitude,
                        "elevation": point.elevation,
                    }
                )

    df = pd.DataFrame(data)
    return df
