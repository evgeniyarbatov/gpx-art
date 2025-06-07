import sys

from utils import (
    get_files,
    get_df,
)

from drawutils import (
    color,
)

def main(gpx_dir, images_dir):
    for (name, path) in get_files(gpx_dir):
        df = get_df(path)
        
        color(
            df,
            images_dir,
            name,
        )

if __name__ == "__main__":
    main(*sys.argv[1:])