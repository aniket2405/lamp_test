import os
import numpy as np
import rasterio
import geopandas as gpd
from skimage.draw import line
import plotly.graph_objects as go
import warnings

warnings.filterwarnings("ignore")

# --- CONFIG ---
DEM_ORIGINAL_FILE = "data/DEM_Subset-Original.tif"       # For 3D Graphics
DEM_BUILDINGS_FILE = "data/DEM_Subset-WithBuildings.tif" # For Math/Shadows
FOOTPRINTS_FILE = "data/BuildingFootprints.shp"
PATHS_FILE = "output/Task1_Global_Minimum_Path.shp" 
OBSERVER_PT_ID = 224

# Because the "WithBuildings" DEM already has the roof height baked in, 
# 1.6m simulates a person standing on the roof of Building 180.
OBSERVER_HEIGHT = 1.6 
STRIDE = 1 

# def get_observer_node(dem_meta, building_id):
#     buildings = gpd.read_file(FOOTPRINTS_FILE)
#     b_col = 'ID' 
#     building = buildings[buildings[b_col] == building_id].centroid.iloc[0]
#     transform = dem_meta.transform
#     c_px, r_px = ~transform * (building.x, building.y)
#     return int(r_px), int(c_px)

def get_observer_node(dem_meta, building_id):
    """Dynamically finds the center of ANY building by its ID."""
    buildings = gpd.read_file(FOOTPRINTS_FILE)
    
    # Safely find the ID column name
    b_col = next((c for c in buildings.columns if c.lower() in ['id', 'fid', 'objectid', 'build_id']), buildings.columns[0])
    
    # Find the specific building and get its center
    building = buildings[buildings[b_col] == building_id].centroid.iloc[0]
    
    transform = dem_meta.transform
    c_px, r_px = ~transform * (building.x, building.y)
    return int(r_px), int(c_px)

def calculate_viewshed(dem_with_buildings, start_r, start_c, cell_size):
    rows, cols = dem_with_buildings.shape
    viewshed = np.zeros((rows, cols), dtype=np.uint8)
    observer_z = dem_with_buildings[start_r, start_c] + OBSERVER_HEIGHT

    perimeter_pixels = []
    for r in range(rows): perimeter_pixels.extend([(r, 0), (r, cols - 1)])
    for c in range(1, cols - 1): perimeter_pixels.extend([(0, c), (rows - 1, c)])

    for end_r, end_c in perimeter_pixels:
        rr, cc = line(start_r, start_c, end_r, end_c)
        if len(rr) < 2: continue
        
        # Use the map WITH buildings so rays hit walls and stop
        elevations = dem_with_buildings[rr, cc]
        distances = np.sqrt((rr - start_r)**2 + (cc - start_c)**2) * cell_size
        distances[0] = 1e-6 
        slopes = (elevations - observer_z) / distances
        max_slopes = np.maximum.accumulate(slopes)
        visible = slopes >= max_slopes
        viewshed[rr[visible], cc[visible]] = 1

    viewshed[start_r, start_c] = 1 
    return viewshed

def get_building_mesh_optimized(row, dem_terrain, transform):
    pt = row.geometry.centroid
    c, r = ~transform * (pt.x, pt.y)
    ground_z = dem_terrain[int(r), int(c)]
    
    bounds = row.geometry.bounds
    min_x_px, min_y_px = ~transform * (bounds[0], bounds[3])
    max_x_px, max_y_px = ~transform * (bounds[2], bounds[1])
    
    min_x, max_y = transform * (min_x_px, min_y_px)
    max_x, min_y = transform * (max_x_px, max_y_px)
    
    height = 3.5 
    
    v_base = np.array([[min_x, min_y, ground_z], [max_x, min_y, ground_z], [max_x, max_y, ground_z], [min_x, max_y, ground_z]])
    v_top = np.array([[min_x, min_y, ground_z+height], [max_x, min_y, ground_z+height], [max_x, max_y, ground_z+height], [min_x, max_y, ground_z+height]])
    vertices = np.vstack([v_base, v_top])
    
    i_list = [0, 1, 2, 0, 2, 3, 4, 5, 6, 4, 6, 7, 0, 1, 5, 0, 5, 4, 1, 2, 6, 1, 6, 5, 2, 3, 7, 2, 7, 6, 3, 0, 4, 3, 4, 7]
    j_list = [1, 2, 3, 2, 3, 0, 5, 6, 7, 6, 7, 4, 1, 5, 4, 5, 4, 0, 2, 6, 5, 6, 5, 1, 3, 7, 6, 7, 6, 2, 0, 4, 7, 4, 7, 3]
    k_list = [2, 3, 0, 3, 0, 1, 6, 7, 4, 7, 4, 5, 5, 4, 0, 4, 0, 1, 6, 5, 1, 5, 1, 2, 7, 6, 2, 6, 2, 3, 4, 7, 3, 7, 3, 0]
    
    return vertices, i_list, j_list, k_list

def main():
    print("--- TASK 2: 3D ARCHITECTURAL RENDERING ---")
    
    # 1. Load BOTH DEMs
    with rasterio.open(DEM_ORIGINAL_FILE) as src_terr:
        dem_terrain = src_terr.read(1)
        transform = src_terr.transform
        meta = src_terr
        cell_size = transform[0]
        rows, cols = dem_terrain.shape

    with rasterio.open(DEM_BUILDINGS_FILE) as src_bldg:
        dem_buildings = src_bldg.read(1)

    # 2. Calculate Viewshed (Using the Math Map WITH Buildings)
    start_r, start_c = get_observer_node(meta, OBSERVER_PT_ID)
    print("Casting true 3D rays (Shadows enabled)...")
    viewshed = calculate_viewshed(dem_buildings, start_r, start_c, cell_size)

    # 3. Create 3D Scene (Using the Graphics Map)
    fig = go.Figure()
    x = np.arange(0, cols, STRIDE)
    y = np.arange(0, rows, STRIDE)
    X, Y = np.meshgrid(x, y)
    Z = dem_terrain[Y, X]
    X_geo, Y_geo = transform * (X, Y)
    
    # Explicit custom colors: 0 (Hidden) = Dark Grey, 1 (Visible) = Bright Cyan
    custom_colorscale = [[0, 'rgb(50, 50, 50)'], [1, 'rgb(0, 255, 255)']]

    fig.add_trace(go.Surface(
        x=X_geo, y=Y_geo, z=Z,
        surfacecolor=viewshed[Y, X],
        colorscale=custom_colorscale,
        cmin=0, cmax=1,
        showscale=False,
        opacity=0.9, 
        name='Terrain Viewshed'
    ))

    # 4. EXPLICITLY RENDER 3D BUILDINGS
    buildings_gdf = gpd.read_file(FOOTPRINTS_FILE).to_crs(meta.crs)
    b_color = '#C19A6B' 

    all_b_verts, all_b_i, all_b_j, all_b_k = [], [], [], []
    current_v_idx = 0
    for _, row in buildings_gdf.iterrows():
        try:
            vertices, i_idx, j_idx, k_idx = get_building_mesh_optimized(row, dem_terrain, transform)
            all_b_verts.append(vertices)
            all_b_i.extend([idx + current_v_idx for idx in i_idx])
            all_b_j.extend([idx + current_v_idx for idx in j_idx])
            all_b_k.extend([idx + current_v_idx for idx in k_idx])
            current_v_idx += 8
        except: continue
        
    b_verts_matrix = np.vstack(all_b_verts)
    fig.add_trace(go.Mesh3d(
        x=b_verts_matrix[:, 0], y=b_verts_matrix[:, 1], z=b_verts_matrix[:, 2],
        i=all_b_i, j=all_b_j, k=all_b_k,
        color=b_color, opacity=1.0, flatshading=True, name='Tombs'
    ))

    # 5. Drape Final PATH for Context
    paths_gdf = gpd.read_file(PATHS_FILE).to_crs(meta.crs)
    for _, row in paths_gdf.iterrows():
        line_xyz = list(row.geometry.coords)
        xs, ys, zs = [], [], []
        for p in line_xyz:
            c, r = ~transform * (p[0], p[1])
            zs.append(dem_terrain[int(r), int(c)] + 0.5) # Raise slightly to be seen
            xs.append(p[0])
            ys.append(p[1])
        fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode='lines', line=dict(color='blue', width=6), name='Pathway'))

    # 6. Observer Node
    obs_x, obs_y = transform * (start_c, start_r)
    obs_z = dem_buildings[start_r, start_c] + OBSERVER_HEIGHT
    fig.add_trace(go.Scatter3d(
        x=[obs_x], y=[obs_y], z=[obs_z],
        mode='markers', marker=dict(size=8, color='red'), name='Observer'
    ))

    # --- Final Layout Settings ---
    fig.update_layout(
        scene=dict(
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            zaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            aspectratio=dict(x=1, y=1, z=0.3) 
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        title=f"3D Necropolis Volume: True Shadows from Building {OBSERVER_PT_ID}"
    )

    fig.show()

if __name__ == "__main__":
    main()