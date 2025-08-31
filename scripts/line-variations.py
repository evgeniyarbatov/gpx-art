import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from utils import get_files

def create_line_variation(lons, lats, variation_type, bg_color, line_color):
    """Create different line variations based on type"""
    
    if variation_type == "thin_delicate":
        return {"linewidth": 0.3, "alpha": 0.8, "linestyle": '-'}
    
    elif variation_type == "thick_bold":
        return {"linewidth": 4.0, "alpha": 0.9, "linestyle": '-'}
    
    elif variation_type == "dashed":
        return {"linewidth": 1.5, "alpha": 0.8, "linestyle": '--', "dash_capstyle": 'round'}
    
    elif variation_type == "dotted":
        return {"linewidth": 2.0, "alpha": 0.7, "linestyle": ':', "dash_capstyle": 'round'}
    
    elif variation_type == "dash_dot":
        return {"linewidth": 1.8, "alpha": 0.8, "linestyle": '-.'}
    
    elif variation_type == "gradient_width":
        # Varying line width along the path
        points = np.array(list(zip(lons, lats)))
        segments = np.array([points[:-1], points[1:]]).transpose(1, 0, 2)
        widths = np.linspace(0.5, 3.0, len(segments))
        return {"segments": segments, "widths": widths, "colors": [line_color] * len(segments)}
    
    elif variation_type == "double_line":
        return {"linewidth": 0.8, "alpha": 0.6, "double": True}
    
    elif variation_type == "sketchy":
        # Add slight randomness to coordinates for hand-drawn effect
        noise_factor = 0.0001
        noisy_lons = [lon + random.uniform(-noise_factor, noise_factor) for lon in lons]
        noisy_lats = [lat + random.uniform(-noise_factor, noise_factor) for lat in lats]
        return {"coords": (noisy_lons, noisy_lats), "linewidth": 1.0, "alpha": 0.7}
    
    elif variation_type == "textured_rough":
        return {"linewidth": 2.5, "alpha": 0.6, "solid_capstyle": 'butt', "solid_joinstyle": 'miter'}
    
    elif variation_type == "ultra_thin":
        return {"linewidth": 0.1, "alpha": 0.9, "linestyle": '-'}
    
    elif variation_type == "medium_soft":
        return {"linewidth": 1.8, "alpha": 0.75, "solid_capstyle": 'round', "solid_joinstyle": 'round'}
    
    elif variation_type == "heavy_bold":
        return {"linewidth": 6.0, "alpha": 0.8, "solid_capstyle": 'round'}
    
    elif variation_type == "fade_gradient":
        # Gradient alpha along the line
        points = np.array(list(zip(lons, lats)))
        segments = np.array([points[:-1], points[1:]]).transpose(1, 0, 2)
        alphas = np.linspace(0.2, 1.0, len(segments))
        colors = [(line_color[1:3], line_color[3:5], line_color[5:7], alpha) for alpha in alphas]
        return {"segments": segments, "colors": colors, "linewidth": 1.5}
    
    elif variation_type == "stippled":
        return {"linewidth": 1.0, "alpha": 0.8, "linestyle": (0, (1, 2))}
    
    elif variation_type == "chunky_dashed":
        return {"linewidth": 3.0, "alpha": 0.7, "linestyle": (0, (5, 3)), "dash_capstyle": 'round'}
    
    elif variation_type == "whisper_thin":
        return {"linewidth": 0.05, "alpha": 1.0, "linestyle": '-'}
    
    elif variation_type == "marker_dots":
        return {"linewidth": 0, "marker": 'o', "markersize": 0.8, "alpha": 0.6}
    
    elif variation_type == "cross_hatch":
        # Create cross-hatching effect with multiple slightly offset lines
        return {"linewidth": 0.5, "alpha": 0.4, "multi_line": True}
    
    elif variation_type == "brush_stroke":
        return {"linewidth": 8.0, "alpha": 0.3, "solid_capstyle": 'round', "solid_joinstyle": 'round'}
    
    elif variation_type == "segmented":
        # Break line into segments with gaps
        return {"linewidth": 2.0, "alpha": 0.8, "segmented": True}
    
    else:  # default
        return {"linewidth": 1.2, "alpha": 0.8, "linestyle": '-'}

def lines_variation(gpx_filename, image_filename, variation_name):
    """Create a specific line variation"""
    
    # Expanded color palettes for different moods
    zen_colors = [
        ('#fefefe', '#333333'), # Soft white with dark gray
        ('#fafafa', '#888888'), # Gentle gray tones
        ('#ffffff', '#5c5c5c'), # Crisp white with medium gray
        ('#f9f9f9', '#a0a0a0'), # Subtle contrast
        ('#fcfcfc', '#666666'), # Quiet grays
    ]
    
    vibrant_colors = [
        ('#1a1a1a', '#ff6b6b'), # Dark with coral
        ('#0f0f0f', '#4ecdc4'), # Dark with teal
        ('#1e1e1e', '#45b7d1'), # Dark with sky blue
        ('#161616', '#96ceb4'), # Dark with mint
        ('#1c1c1c', '#feca57'), # Dark with golden
    ]
    
    nature_colors = [
        ('#f7f3e9', '#8b7355'), # Cream with earth
        ('#f0f8f0', '#2d5016'), # Light green with forest
        ('#fdf6e3', '#b58900'), # Sepia tones
        ('#f4f1de', '#81b29a'), # Warm white with sage
        ('#fefcfb', '#6b705c'), # Off-white with olive
    ]
    
    # Choose color palette based on variation
    if "bold" in variation_name or "vibrant" in variation_name:
        color_pairs = vibrant_colors
    elif "nature" in variation_name or "earth" in variation_name:
        color_pairs = nature_colors
    else:
        color_pairs = zen_colors
    
    bg_color, line_color = random.choice(color_pairs)
    
    # Extract coordinates
    lons, lats = [], []
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    lons.append(point.longitude)
                    lats.append(point.latitude)
    
    if not lons or not lats:
        print(f"No GPS data found in {gpx_filename}")
        return
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    # Get line properties for this variation
    line_props = create_line_variation(lons, lats, variation_name, bg_color, line_color)
    
    # Apply the variation
    if "gradient_width" in line_props:
        # Variable width line
        lc = LineCollection(line_props["segments"], linewidths=line_props["widths"], 
                          colors=line_props["colors"], capstyle='round')
        ax.add_collection(lc)
    
    elif "segments" in line_props and "colors" in line_props:
        # Gradient alpha line
        lc = LineCollection(line_props["segments"], linewidths=line_props["linewidth"], 
                          colors=line_props["colors"], capstyle='round')
        ax.add_collection(lc)
    
    elif line_props.get("double", False):
        # Double line effect
        ax.plot(lons, lats, color=line_color, linewidth=line_props["linewidth"] + 0.8, 
                alpha=line_props["alpha"] * 0.5, solid_capstyle='round')
        ax.plot(lons, lats, color=bg_color, linewidth=line_props["linewidth"], 
                alpha=1.0, solid_capstyle='round')
    
    elif line_props.get("multi_line", False):
        # Cross-hatch effect
        offsets = [0.0001, -0.0001, 0.00015, -0.00015]
        for i, offset in enumerate(offsets):
            offset_lons = [lon + offset for lon in lons]
            offset_lats = [lat + offset for lat in lats]
            ax.plot(offset_lons, offset_lats, color=line_color, 
                   linewidth=line_props["linewidth"], alpha=line_props["alpha"])
    
    elif "coords" in line_props:
        # Sketchy/noisy line
        sketch_lons, sketch_lats = line_props["coords"]
        ax.plot(sketch_lons, sketch_lats, color=line_color, 
               linewidth=line_props["linewidth"], alpha=line_props["alpha"])
    
    elif line_props.get("segmented", False):
        # Segmented line with gaps
        segment_length = len(lons) // 20  # Break into ~20 segments
        for i in range(0, len(lons) - segment_length, segment_length + 5):
            end_idx = min(i + segment_length, len(lons))
            ax.plot(lons[i:end_idx], lats[i:end_idx], color=line_color, 
                   linewidth=line_props["linewidth"], alpha=line_props["alpha"],
                   solid_capstyle='round')
    
    else:
        # Standard line with properties
        plot_props = {k: v for k, v in line_props.items() 
                     if k not in ['segments', 'widths', 'colors', 'coords', 'double', 'multi_line', 'segmented']}
        ax.plot(lons, lats, color=line_color, **plot_props)
    
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    fig.tight_layout(pad=0)
    
    plt.savefig(
        image_filename,
        dpi=300,
        facecolor=fig.get_facecolor(),
        edgecolor='none',
        bbox_inches='tight'
    )
    plt.close()
    print(f"Created {variation_name} variation: {image_filename}")

def main(gpx_dir, images_dir):
    """Generate multiple line variations for each GPX file"""
    
    # Define 20 different line variations
    variations = [
        "thin_delicate",      # Ultra-fine lines
        "thick_bold",         # Bold, heavy lines
        "dashed",            # Classic dashed lines
        "dotted",            # Dotted pattern
        "dash_dot",          # Dash-dot pattern
        "gradient_width",    # Variable width along path
        "double_line",       # Double line effect
        "sketchy",           # Hand-drawn, rough style
        "textured_rough",    # Rough, textured appearance
        "ultra_thin",        # Extremely thin lines
        "medium_soft",       # Medium weight, soft edges
        "heavy_bold",        # Very thick, bold lines
        "fade_gradient",     # Fading alpha gradient
        "stippled",          # Stippled/dotted texture
        "chunky_dashed",     # Thick dashed lines
        "whisper_thin",      # Barely visible thin lines
        "marker_dots",       # Dot markers instead of lines
        "cross_hatch",       # Cross-hatched effect
        "brush_stroke",      # Paint brush effect
        "segmented",         # Broken into segments
    ]
    
    for (name, gpx_path) in get_files(gpx_dir):
        print(f"\nProcessing {name}...")
        
        for variation in variations:
            output_filename = f"{images_dir}/lines-{variation}-{name}.png"
            try:
                lines_variation(gpx_path, output_filename, variation)
            except Exception as e:
                print(f"Error creating {variation} for {name}: {e}")

def create_sample_sheet(gpx_dir, images_dir):
    """Create a sample sheet showing all variations for the first GPX file"""
    
    files = list(get_files(gpx_dir))
    if not files:
        print("No GPX files found")
        return
    
    # Use first file for sample sheet
    name, gpx_path = files[0]
    
    # Extract coordinates
    lons, lats = [], []
    with open(gpx_path, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    lons.append(point.longitude)
                    lats.append(point.latitude)
    
    if not lons or not lats:
        print(f"No GPS data found in {gpx_path}")
        return
    
    # Create a grid of variations
    variations = [
        "thin_delicate", "thick_bold", "dashed", "dotted",
        "ultra_thin", "medium_soft", "heavy_bold", "sketchy",
        "gradient_width", "fade_gradient", "stippled", "chunky_dashed",
        "whisper_thin", "marker_dots", "cross_hatch", "brush_stroke",
        "dash_dot", "double_line", "textured_rough", "segmented"
    ]
    
    fig, axes = plt.subplots(4, 5, figsize=(20, 16), dpi=150)
    fig.suptitle(f'Line Variations for {name}', fontsize=16, y=0.95)
    
    for i, variation in enumerate(variations):
        row, col = i // 5, i % 5
        ax = axes[row, col]
        
        # Simple color scheme for sample sheet
        bg_color, line_color = '#fefefe', '#333333'
        ax.set_facecolor(bg_color)
        
        # Apply variation
        line_props = create_line_variation(lons, lats, variation, bg_color, line_color)
        
        try:
            if "gradient_width" in line_props:
                lc = LineCollection(line_props["segments"], linewidths=line_props["widths"], 
                                  colors=line_props["colors"], capstyle='round')
                ax.add_collection(lc)
            elif "segments" in line_props and "colors" in line_props:
                lc = LineCollection(line_props["segments"], linewidths=line_props["linewidth"], 
                                  colors=line_props["colors"], capstyle='round')
                ax.add_collection(lc)
            elif line_props.get("double", False):
                ax.plot(lons, lats, color=line_color, linewidth=line_props["linewidth"] + 0.8, 
                       alpha=line_props["alpha"] * 0.5, solid_capstyle='round')
                ax.plot(lons, lats, color=bg_color, linewidth=line_props["linewidth"], 
                       alpha=1.0, solid_capstyle='round')
            elif line_props.get("multi_line", False):
                offsets = [0.0001, -0.0001, 0.00015, -0.00015]
                for offset in offsets:
                    offset_lons = [lon + offset for lon in lons]
                    offset_lats = [lat + offset for lat in lats]
                    ax.plot(offset_lons, offset_lats, color=line_color, 
                           linewidth=line_props["linewidth"], alpha=line_props["alpha"])
            elif "coords" in line_props:
                sketch_lons, sketch_lats = line_props["coords"]
                ax.plot(sketch_lons, sketch_lats, color=line_color, 
                       linewidth=line_props["linewidth"], alpha=line_props["alpha"])
            elif line_props.get("segmented", False):
                segment_length = len(lons) // 10
                for j in range(0, len(lons) - segment_length, segment_length + 3):
                    end_idx = min(j + segment_length, len(lons))
                    ax.plot(lons[j:end_idx], lats[j:end_idx], color=line_color, 
                           linewidth=line_props["linewidth"], alpha=line_props["alpha"])
            else:
                plot_props = {k: v for k, v in line_props.items() 
                             if k not in ['segments', 'widths', 'colors', 'coords', 'double', 'multi_line', 'segmented']}
                ax.plot(lons, lats, color=line_color, **plot_props)
        
        except Exception as e:
            # Fallback to simple line if variation fails
            ax.plot(lons, lats, color=line_color, linewidth=1.0, alpha=0.8)
        
        ax.set_aspect('equal', 'datalim')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(variation.replace('_', ' ').title(), fontsize=8, pad=5)
        
        # Remove spines
        for spine in ax.spines.values():
            spine.set_visible(False)
    
    plt.tight_layout()
    sample_filename = f"{images_dir}/line-variations-sample-sheet.png"
    plt.savefig(sample_filename, dpi=150, facecolor='white', edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"\nCreated sample sheet: {sample_filename}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script.py <gpx_dir> <images_dir> [--sample-sheet]")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    
    # Check if user wants sample sheet
    if len(sys.argv) > 3 and sys.argv[3] == "--sample-sheet":
        create_sample_sheet(gpx_dir, images_dir)
    else:
        main(gpx_dir, images_dir)
        print(f"\nGenerated 20 different line variations for each GPX file!")
        print(f"To see all variations in one image, run with --sample-sheet flag")