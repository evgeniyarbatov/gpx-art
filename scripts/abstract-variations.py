import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PatchCollection
from matplotlib.patches import Circle
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter
from utils import get_files

def create_abstract_variation(lons, lats, variation_type, bg_color, fg_color):
    """Create abstract artistic interpretations of GPS data"""
    
    points = np.array(list(zip(lons, lats)))
    
    if variation_type == "particle_field":
        # Scatter points along the path with varying density
        num_particles = random.randint(500, 2000)
        t = np.linspace(0, 1, len(points))
        t_new = np.linspace(0, 1, num_particles)
        
        # Interpolate positions
        f_lon = interp1d(t, lons, kind='cubic')
        f_lat = interp1d(t, lats, kind='cubic')
        
        particle_lons = f_lon(t_new)
        particle_lats = f_lat(t_new)
        
        # Add random scatter around path
        scatter_factor = 0.0005
        particle_lons += np.random.normal(0, scatter_factor, num_particles)
        particle_lats += np.random.normal(0, scatter_factor, num_particles)
        
        sizes = np.random.exponential(2, num_particles)
        alphas = np.random.beta(2, 5, num_particles)
        
        return {"type": "scatter", "x": particle_lons, "y": particle_lats, 
                "s": sizes, "alpha": alphas, "c": fg_color}
    
    elif variation_type == "velocity_field":
        # Create vector field based on movement direction
        segments = points[1:] - points[:-1]
        midpoints = (points[1:] + points[:-1]) / 2
        
        # Normalize and scale vectors
        lengths = np.linalg.norm(segments, axis=1)
        lengths[lengths == 0] = 1  # Avoid division by zero
        directions = segments / lengths[:, np.newaxis]
        
        scale = np.max(lengths) * 10000
        
        return {"type": "quiver", "x": midpoints[:, 0], "y": midpoints[:, 1],
                "u": directions[:, 0], "v": directions[:, 1], "scale": scale}
    
    elif variation_type == "density_heatmap":
        # Create density heatmap of path coverage
        lon_range = np.linspace(min(lons), max(lons), 100)
        lat_range = np.linspace(min(lats), max(lats), 100)
        lon_grid, lat_grid = np.meshgrid(lon_range, lat_range)
        
        # Calculate density
        density = np.zeros((100, 100))
        for lon, lat in zip(lons, lats):
            lon_idx = int((lon - min(lons)) / (max(lons) - min(lons)) * 99)
            lat_idx = int((lat - min(lats)) / (max(lats) - min(lats)) * 99)
            if 0 <= lon_idx < 100 and 0 <= lat_idx < 100:
                density[lat_idx, lon_idx] += 1
        
        # Smooth the density
        density = gaussian_filter(density, sigma=2)
        
        return {"type": "heatmap", "x": lon_grid, "y": lat_grid, "z": density}
    
    elif variation_type == "constellation":
        # Major points as stars with connecting constellation lines
        # Sample every nth point to create constellation nodes
        step = max(1, len(points) // 20)
        star_points = points[::step]
        
        star_sizes = np.random.uniform(10, 50, len(star_points))
        
        return {"type": "constellation", "points": star_points, "sizes": star_sizes,
                "connect": True}
    
    elif variation_type == "ripple_waves":
        # Concentric circles at key points along the path
        step = max(1, len(points) // 15)
        wave_centers = points[::step]
        
        circles = []
        for center in wave_centers:
            num_rings = random.randint(3, 8)
            for ring in range(num_rings):
                radius = (ring + 1) * 0.001
                alpha = 1.0 - (ring / num_rings) * 0.8
                circles.append((center[0], center[1], radius, alpha))
        
        return {"type": "ripples", "circles": circles}
    
    elif variation_type == "geometric_shards":
        # Angular geometric shapes along the path
        step = max(1, len(points) // 25)
        shard_centers = points[::step]
        
        shapes = []
        for i, center in enumerate(shard_centers):
            # Create random geometric shapes
            num_vertices = random.choice([3, 4, 5, 6])
            angles = np.linspace(0, 2*np.pi, num_vertices, endpoint=False)
            size = random.uniform(0.0008, 0.003)
            
            vertices = []
            for angle in angles:
                r = size * random.uniform(0.5, 1.0)
                x = center[0] + r * np.cos(angle)
                y = center[1] + r * np.sin(angle)
                vertices.append([x, y])
            
            shapes.append(np.array(vertices))
        
        return {"type": "polygons", "shapes": shapes}
    
    elif variation_type == "flowing_ribbons":
        # Parallel flowing ribbons with width variation
        num_ribbons = 5
        ribbon_offset = 0.0003
        
        ribbons = []
        for i in range(num_ribbons):
            offset = (i - num_ribbons//2) * ribbon_offset
            ribbon_lons = [lon + offset * random.uniform(0.8, 1.2) for lon in lons]
            ribbon_lats = [lat + offset * random.uniform(0.8, 1.2) for lat in lats]
            
            width = random.uniform(0.5, 2.5)
            alpha = random.uniform(0.3, 0.8)
            
            ribbons.append({"lons": ribbon_lons, "lats": ribbon_lats, 
                          "width": width, "alpha": alpha})
        
        return {"type": "ribbons", "ribbons": ribbons}
    
    elif variation_type == "shadow_trail":
        # Multiple shadow trails with offset and fade
        num_shadows = 8
        shadows = []
        
        for i in range(num_shadows):
            offset_x = random.uniform(-0.0005, 0.0005)
            offset_y = random.uniform(-0.0005, 0.0005)
            
            shadow_lons = [lon + offset_x for lon in lons]
            shadow_lats = [lat + offset_y for lat in lats]
            
            alpha = 0.8 - (i * 0.1)
            width = 2.0 - (i * 0.2)
            
            shadows.append({"lons": shadow_lons, "lats": shadow_lats,
                          "alpha": alpha, "width": width})
        
        return {"type": "shadows", "shadows": shadows}
    
    elif variation_type == "spiral_energy":
        # Spiral patterns at key points
        step = max(1, len(points) // 12)
        energy_centers = points[::step]
        
        spirals = []
        for center in energy_centers:
            # Create spiral
            theta = np.linspace(0, 4*np.pi, 100)
            radius_scale = random.uniform(0.0005, 0.002)
            spiral_r = radius_scale * theta / (4*np.pi)
            
            spiral_x = center[0] + spiral_r * np.cos(theta)
            spiral_y = center[1] + spiral_r * np.sin(theta)
            
            spirals.append({"x": spiral_x, "y": spiral_y})
        
        return {"type": "spirals", "spirals": spirals}
    
    elif variation_type == "fractal_branches":
        # Fractal-like branching from main path
        branch_points = points[::len(points)//10]
        
        branches = []
        for point in branch_points:
            # Create branching pattern
            num_branches = random.randint(3, 7)
            for _ in range(num_branches):
                angle = random.uniform(0, 2*np.pi)
                length = random.uniform(0.001, 0.004)
                
                end_x = point[0] + length * np.cos(angle)
                end_y = point[1] + length * np.sin(angle)
                
                branches.append({"start": point, "end": [end_x, end_y]})
        
        return {"type": "branches", "branches": branches}
    
    elif variation_type == "magnetic_field":
        # Field lines flowing around the path
        field_lines = []
        
        # Create perpendicular field lines
        for i in range(0, len(points)-1, len(points)//15):
            p1, p2 = points[i], points[i+1]
            direction = p2 - p1
            if np.linalg.norm(direction) > 0:
                direction = direction / np.linalg.norm(direction)
                perpendicular = np.array([-direction[1], direction[0]])
                
                # Create field lines on both sides
                for side in [-1, 1]:
                    field_start = (p1 + p2) / 2 + side * perpendicular * 0.001
                    field_end = field_start + side * perpendicular * 0.003
                    field_lines.append({"start": field_start, "end": field_end})
        
        return {"type": "field_lines", "lines": field_lines}
    
    elif variation_type == "echo_trails":
        # Multiple echo trails with decreasing opacity
        num_echoes = 12
        echoes = []
        
        for i in range(num_echoes):
            delay = i * 0.02  # Temporal offset
            scale = 1.0 - i * 0.05  # Spatial scaling
            alpha = 0.8 - i * 0.06
            
            if alpha > 0:
                center_lon, center_lat = np.mean(lons), np.mean(lats)
                echo_lons = center_lon + (np.array(lons) - center_lon) * scale
                echo_lats = center_lat + (np.array(lats) - center_lat) * scale
                
                echoes.append({"lons": echo_lons, "lats": echo_lats, "alpha": alpha})
        
        return {"type": "echoes", "echoes": echoes}
    
    elif variation_type == "node_network":
        # Network of nodes with connections
        step = max(1, len(points) // 30)
        nodes = points[::step]
        
        connections = []
        for i, node in enumerate(nodes):
            # Connect to nearby nodes
            for j, other_node in enumerate(nodes):
                if i != j:
                    distance = np.linalg.norm(node - other_node)
                    if distance < 0.01:  # Connect close nodes
                        connections.append((node, other_node))
        
        return {"type": "network", "nodes": nodes, "connections": connections}
    
    elif variation_type == "ink_blots":
        # Ink blot style with varying blob sizes
        step = max(1, len(points) // 40)
        blot_centers = points[::step]
        
        blots = []
        for center in blot_centers:
            # Create irregular blob
            num_points = random.randint(8, 16)
            angles = np.linspace(0, 2*np.pi, num_points, endpoint=False)
            base_radius = random.uniform(0.0008, 0.0025)
            
            blob_points = []
            for angle in angles:
                r = base_radius * random.uniform(0.3, 1.0)
                x = center[0] + r * np.cos(angle)
                y = center[1] + r * np.sin(angle)
                blob_points.append([x, y])
            
            blots.append(np.array(blob_points))
        
        return {"type": "blots", "blots": blots}
    
    elif variation_type == "wave_interference":
        # Interference pattern based on path
        grid_size = 150
        lon_range = np.linspace(min(lons), max(lons), grid_size)
        lat_range = np.linspace(min(lats), max(lats), grid_size)
        lon_grid, lat_grid = np.meshgrid(lon_range, lat_range)
        
        # Create wave interference pattern
        wave_field = np.zeros((grid_size, grid_size))
        
        # Sample key points as wave sources
        wave_sources = points[::len(points)//8]
        
        for source in wave_sources:
            distances = np.sqrt((lon_grid - source[0])**2 + (lat_grid - source[1])**2)
            wave_field += np.sin(distances * 100000) * np.exp(-distances * 50000)
        
        return {"type": "wave_field", "x": lon_grid, "y": lat_grid, "z": wave_field}
    
    elif variation_type == "crystalline":
        # Crystal-like angular formations
        step = max(1, len(points) // 20)
        crystal_centers = points[::step]
        
        crystals = []
        for center in crystal_centers:
            # Create angular crystal shape
            num_faces = random.choice([4, 6, 8])
            angles = np.linspace(0, 2*np.pi, num_faces, endpoint=False)
            
            # Create multi-layer crystal
            for layer in range(3):
                layer_points = []
                radius = (0.002 - layer * 0.0005) * random.uniform(0.5, 1.5)
                
                for angle in angles:
                    # Add angular variation
                    actual_angle = angle + random.uniform(-0.3, 0.3)
                    r = radius * random.uniform(0.7, 1.0)
                    x = center[0] + r * np.cos(actual_angle)
                    y = center[1] + r * np.sin(actual_angle)
                    layer_points.append([x, y])
                
                alpha = 0.8 - layer * 0.25
                crystals.append({"points": np.array(layer_points), "alpha": alpha})
        
        return {"type": "crystals", "crystals": crystals}
    
    elif variation_type == "flowing_hair":
        # Hair-like flowing strands
        num_strands = random.randint(15, 30)
        strands = []
        
        for i in range(num_strands):
            # Create strand following general path direction
            strand_points = []
            offset_scale = random.uniform(0.0002, 0.001)
            
            # Sample points along main path
            indices = np.linspace(0, len(points)-1, random.randint(20, 50), dtype=int)
            
            for idx in indices:
                base_point = points[idx]
                # Add flowing offset
                flow_offset_x = offset_scale * np.sin(idx * 0.3 + i * 0.5)
                flow_offset_y = offset_scale * np.cos(idx * 0.2 + i * 0.7)
                
                strand_x = base_point[0] + flow_offset_x
                strand_y = base_point[1] + flow_offset_y
                strand_points.append([strand_x, strand_y])
            
            width = random.uniform(0.2, 1.0)
            alpha = random.uniform(0.3, 0.7)
            strands.append({"points": np.array(strand_points), "width": width, "alpha": alpha})
        
        return {"type": "strands", "strands": strands}
    
    elif variation_type == "torn_paper":
        # Torn paper edge effect
        # Create jagged edge along path
        torn_points = []
        
        for i in range(len(points)):
            base_point = points[i]
            # Add jagged variation
            jagged_offset = random.uniform(-0.0003, 0.0003)
            
            if i % 2 == 0:  # Alternate sides for tearing effect
                torn_x = base_point[0] + jagged_offset
                torn_y = base_point[1] + jagged_offset * 0.5
            else:
                torn_x = base_point[0] - jagged_offset * 0.7
                torn_y = base_point[1] + jagged_offset
            
            torn_points.append([torn_x, torn_y])
        
        return {"type": "torn_edge", "points": np.array(torn_points)}
    
    elif variation_type == "lightning_bolts":
        # Lightning-like angular paths
        bolt_segments = []
        
        # Break path into segments and make them angular
        segment_length = max(1, len(points) // 20)
        
        for i in range(0, len(points) - segment_length, segment_length):
            start_point = points[i]
            end_point = points[min(i + segment_length, len(points)-1)]
            
            # Create zigzag between start and end
            num_zigs = random.randint(4, 8)
            zig_points = [start_point]
            
            for j in range(1, num_zigs):
                t = j / num_zigs
                base_x = start_point[0] + t * (end_point[0] - start_point[0])
                base_y = start_point[1] + t * (end_point[1] - start_point[1])
                
                # Add angular deviation
                deviation = random.uniform(-0.002, 0.002)
                zig_x = base_x + deviation
                zig_y = base_y + deviation * 0.5
                
                zig_points.append([zig_x, zig_y])
            
            zig_points.append(end_point)
            bolt_segments.append(np.array(zig_points))
        
        return {"type": "lightning", "segments": bolt_segments}
    
    elif variation_type == "smoke_wisps":
        # Smoke-like wisps emanating from path
        wisps = []
        step = max(1, len(points) // 25)
        
        for i in range(0, len(points), step):
            base_point = points[i]
            
            # Create wispy curve
            num_wisp_points = random.randint(10, 20)
            wisp_points = [base_point]
            
            current_point = base_point
            for j in range(num_wisp_points):
                # Drift upward and outward
                drift_x = random.uniform(-0.0002, 0.0002) + j * 0.00005
                drift_y = random.uniform(0.00005, 0.0003) + j * 0.00008
                
                current_point = [current_point[0] + drift_x, current_point[1] + drift_y]
                wisp_points.append(current_point)
            
            alpha = random.uniform(0.2, 0.6)
            width = random.uniform(0.3, 1.2)
            wisps.append({"points": np.array(wisp_points), "alpha": alpha, "width": width})
        
        return {"type": "wisps", "wisps": wisps}
    
    elif variation_type == "shattered_glass":
        # Shattered glass effect with angular fragments
        fragments = []
        center_lon, center_lat = np.mean(lons), np.mean(lats)
        
        # Create radiating cracks from path points
        crack_origins = points[::len(points)//15]
        
        for origin in crack_origins:
            num_cracks = random.randint(3, 8)
            for _ in range(num_cracks):
                # Create crack line
                angle = random.uniform(0, 2*np.pi)
                length = random.uniform(0.001, 0.005)
                
                end_x = origin[0] + length * np.cos(angle)
                end_y = origin[1] + length * np.sin(angle)
                
                # Add angular breaks in the crack
                mid_x = (origin[0] + end_x) / 2 + random.uniform(-length*0.3, length*0.3)
                mid_y = (origin[1] + end_y) / 2 + random.uniform(-length*0.3, length*0.3)
                
                crack_points = np.array([origin, [mid_x, mid_y], [end_x, end_y]])
                fragments.append(crack_points)
        
        return {"type": "glass_fragments", "fragments": fragments}
    
    elif variation_type == "cellular_growth":
        # Organic cellular growth pattern
        cells = []
        step = max(1, len(points) // 35)
        
        for i in range(0, len(points), step):
            center = points[i]
            
            # Create organic cell shape
            num_points = random.randint(12, 20)
            angles = np.linspace(0, 2*np.pi, num_points, endpoint=False)
            
            cell_points = []
            base_radius = random.uniform(0.0005, 0.002)
            
            for angle in angles:
                # Add organic variation
                radius = base_radius * (1 + 0.4 * np.sin(angle * 3) + 0.3 * np.cos(angle * 5))
                radius *= random.uniform(0.7, 1.3)
                
                x = center[0] + radius * np.cos(angle)
                y = center[1] + radius * np.sin(angle)
                cell_points.append([x, y])
            
            alpha = random.uniform(0.3, 0.7)
            cells.append({"points": np.array(cell_points), "alpha": alpha})
        
        return {"type": "cells", "cells": cells}
    
    else:  # Default fallback
        return {"type": "simple_line", "linewidth": 1.0, "alpha": 0.8}

def render_abstract_variation(ax, lons, lats, variation_data, fg_color):
    """Render the abstract variation on the axes"""
    
    var_type = variation_data["type"]
    
    if var_type == "scatter":
        ax.scatter(variation_data["x"], variation_data["y"], 
                  s=variation_data["s"], alpha=variation_data["alpha"], 
                  c=fg_color, edgecolors='none')
    
    elif var_type == "quiver":
        ax.quiver(variation_data["x"], variation_data["y"],
                 variation_data["u"], variation_data["v"],
                 scale=variation_data["scale"], color=fg_color, alpha=0.7, width=0.002)
    
    elif var_type == "heatmap":
        ax.contourf(variation_data["x"], variation_data["y"], variation_data["z"], 
                   levels=20, cmap='gray', alpha=0.8)
    
    elif var_type == "constellation":
        points = variation_data["points"]
        # Draw stars
        ax.scatter(points[:, 0], points[:, 1], s=variation_data["sizes"], 
                  c=fg_color, alpha=0.8, marker='*')
        # Draw connections
        if variation_data.get("connect", False):
            for i in range(len(points)-1):
                ax.plot([points[i, 0], points[i+1, 0]], 
                       [points[i, 1], points[i+1, 1]], 
                       color=fg_color, alpha=0.3, linewidth=0.5)
    
    elif var_type == "ripples":
        for lon, lat, radius, alpha in variation_data["circles"]:
            circle = Circle((lon, lat), radius, fill=False, 
                          edgecolor=fg_color, alpha=alpha, linewidth=0.8)
            ax.add_patch(circle)
    
    elif var_type == "polygons":
        patches = []
        for shape in variation_data["shapes"]:
            polygon = plt.Polygon(shape, closed=True)
            patches.append(polygon)
        
        pc = PatchCollection(patches, facecolor=fg_color, alpha=0.6, edgecolor=fg_color)
        ax.add_collection(pc)
    
    elif var_type == "ribbons":
        for ribbon in variation_data["ribbons"]:
            ax.plot(ribbon["lons"], ribbon["lats"], color=fg_color,
                   linewidth=ribbon["width"], alpha=ribbon["alpha"], 
                   solid_capstyle='round')
    
    elif var_type == "shadows":
        for shadow in variation_data["shadows"]:
            ax.plot(shadow["lons"], shadow["lats"], color=fg_color,
                   linewidth=shadow["width"], alpha=shadow["alpha"],
                   solid_capstyle='round')
    
    elif var_type == "spirals":
        for spiral in variation_data["spirals"]:
            ax.plot(spiral["x"], spiral["y"], color=fg_color, 
                   linewidth=0.8, alpha=0.6)
    
    elif var_type == "branches":
        for branch in variation_data["branches"]:
            start, end = branch["start"], branch["end"]
            ax.plot([start[0], end[0]], [start[1], end[1]], 
                   color=fg_color, linewidth=0.8, alpha=0.7)
    
    elif var_type == "field_lines":
        for line in variation_data["lines"]:
            start, end = line["start"], line["end"]
            ax.plot([start[0], end[0]], [start[1], end[1]], 
                   color=fg_color, linewidth=0.6, alpha=0.5)
    
    elif var_type == "echoes":
        for echo in variation_data["echoes"]:
            ax.plot(echo["lons"], echo["lats"], color=fg_color,
                   linewidth=1.0, alpha=echo["alpha"], solid_capstyle='round')
    
    elif var_type == "network":
        nodes = variation_data["nodes"]
        # Draw nodes
        ax.scatter(nodes[:, 0], nodes[:, 1], s=20, c=fg_color, alpha=0.8)
        # Draw connections
        for start, end in variation_data["connections"]:
            ax.plot([start[0], end[0]], [start[1], end[1]], 
                   color=fg_color, alpha=0.4, linewidth=0.5)
    
    elif var_type == "blots":
        patches = []
        for blot in variation_data["blots"]:
            polygon = plt.Polygon(blot, closed=True)
            patches.append(polygon)
        
        pc = PatchCollection(patches, facecolor=fg_color, alpha=0.7, edgecolor='none')
        ax.add_collection(pc)
    
    elif var_type == "wave_field":
        ax.contour(variation_data["x"], variation_data["y"], variation_data["z"], 
                  levels=15, colors=fg_color, alpha=0.6, linewidths=0.8)
    
    elif var_type == "glass_fragments":
        for fragment in variation_data["fragments"]:
            ax.plot(fragment[:, 0], fragment[:, 1], color=fg_color, 
                   linewidth=0.8, alpha=0.7, solid_capstyle='butt')
    
    elif var_type == "cells":
        patches = []
        alphas = []
        for cell in variation_data["cells"]:
            polygon = plt.Polygon(cell["points"], closed=True)
            patches.append(polygon)
            alphas.append(cell["alpha"])
        
        for patch, alpha in zip(patches, alphas):
            patch.set_facecolor(fg_color)
            patch.set_alpha(alpha)
            patch.set_edgecolor(fg_color)
            patch.set_linewidth(0.5)
            ax.add_patch(patch)
    
    elif var_type == "torn_edge":
        points = variation_data["points"]
        ax.plot(points[:, 0], points[:, 1], color=fg_color, 
               linewidth=2.0, alpha=0.8, solid_capstyle='butt', solid_joinstyle='miter')
    
    elif var_type == "wisps":
        for wisp in variation_data["wisps"]:
            points = wisp["points"]
            ax.plot(points[:, 0], points[:, 1], color=fg_color,
                   linewidth=wisp["width"], alpha=wisp["alpha"], 
                   solid_capstyle='round')
    
    else:  # simple_line fallback
        ax.plot(lons, lats, color=fg_color, linewidth=variation_data["linewidth"], 
               alpha=variation_data["alpha"])

def lines_variation(gpx_filename, image_filename, variation_name):
    """Create a specific abstract variation"""
    
    # Black and white color schemes
    bw_colors = [
        ('#ffffff', '#000000'),  # Classic white bg, black fg
        ('#000000', '#ffffff'),  # Inverted: black bg, white fg
        ('#fafafa', '#1a1a1a'),  # Soft white with near-black
        ('#0a0a0a', '#f5f5f5'),  # Near-black with soft white
        ('#f8f8f8', '#2c2c2c'),  # Warm white with charcoal
        ('#1c1c1c', '#e8e8e8'),  # Charcoal with light gray
        ('#ffffff', '#404040'),  # White with medium gray
        ('#202020', '#d0d0d0'),  # Dark gray with light gray
    ]
    
    bg_color, fg_color = random.choice(bw_colors)
    
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
    
    # Generate variation data
    variation_data = create_abstract_variation(lons, lats, variation_name, bg_color, fg_color)
    
    # Render the variation
    render_abstract_variation(ax, lons, lats, variation_data, fg_color)
    
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
    """Generate multiple abstract variations for each GPX file"""
    
    # Define 18 abstract artistic variations
    variations = [
        "particle_field",     # Scattered particles along path
        "velocity_field",     # Vector field showing movement
        "density_heatmap",    # Heat map of path density
        "constellation",      # Star constellation pattern
        "ripple_waves",       # Concentric ripples at key points
        "geometric_shards",   # Angular geometric shapes
        "flowing_ribbons",    # Multiple parallel flowing ribbons
        "shadow_trail",       # Multiple shadow trails
        "spiral_energy",      # Spiral energy patterns
        "fractal_branches",   # Fractal branching from path
        "magnetic_field",     # Magnetic field lines
        "echo_trails",        # Echo/ghost trails
        "node_network",       # Network of connected nodes
        "ink_blots",          # Organic ink blot shapes
        "wave_interference",  # Wave interference patterns
        "crystalline",        # Crystal-like formations
        "flowing_hair",       # Hair-like flowing strands
        "torn_paper",         # Torn paper edge effect
        "lightning_bolts",    # Angular lightning-like paths
        "smoke_wisps",        # Smoke wisps emanating from path
        "shattered_glass",    # Shattered glass crack patterns
        "cellular_growth",    # Organic cellular patterns
    ]
    
    for (name, gpx_path) in get_files(gpx_dir):
        print(f"\nProcessing {name}...")
        
        for variation in variations:
            output_filename = f"{images_dir}/abstract-{variation}-{name}.png"
            try:
                lines_variation(gpx_path, output_filename, variation)
            except Exception as e:
                print(f"Error creating {variation} for {name}: {e}")

def create_sample_sheet(gpx_dir, images_dir):
    """Create a sample sheet showing all abstract variations for the first GPX file"""
    
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
    
    # Create a grid of variations (4x6 grid for 22 variations)
    variations = [
        "particle_field", "velocity_field", "density_heatmap", "constellation",
        "ripple_waves", "geometric_shards", "flowing_ribbons", "shadow_trail", 
        "spiral_energy", "fractal_branches", "magnetic_field", "echo_trails",
        "node_network", "ink_blots", "wave_interference", "crystalline",
        "flowing_hair", "torn_paper", "lightning_bolts", "smoke_wisps",
        "shattered_glass", "cellular_growth"
    ]
    
    fig, axes = plt.subplots(6, 4, figsize=(16, 24), dpi=120)
    fig.suptitle(f'Abstract Variations for {name}', fontsize=20, y=0.98)
    
    for i, variation in enumerate(variations):
        row, col = i // 4, i % 4
        ax = axes[row, col]
        
        # Use consistent black and white
        bg_color, fg_color = '#ffffff', '#000000'
        ax.set_facecolor(bg_color)
        
        try:
            # Generate and render variation
            variation_data = create_abstract_variation(lons, lats, variation, bg_color, fg_color)
            render_abstract_variation(ax, lons, lats, variation_data, fg_color)
        
        except Exception as e:
            # Fallback to simple line if variation fails
            ax.plot(lons, lats, color=fg_color, linewidth=1.0, alpha=0.8)
            print(f"Error with {variation}: {e}")
        
        ax.set_aspect('equal', 'datalim')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(variation.replace('_', ' ').title(), fontsize=10, pad=8)
        
        # Remove spines
        for spine in ax.spines.values():
            spine.set_visible(False)
    
    # Hide unused subplots
    for i in range(len(variations), 24):
        row, col = i // 4, i % 4
        axes[row, col].set_visible(False)
    
    plt.tight_layout()
    sample_filename = f"{images_dir}/abstract-variations-sample-sheet.png"
    plt.savefig(sample_filename, dpi=120, facecolor='white', edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"\nCreated abstract sample sheet: {sample_filename}")

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
        print(f"\nGenerated 22 different abstract variations for each GPX file!")
        print(f"To see all variations in one image, run with --sample-sheet flag")