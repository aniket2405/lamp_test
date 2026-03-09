# import rasterio
# import numpy as np
# import geopandas as gpd
# from sklearn.cluster import KMeans
# from skimage.graph import route_through_array
# from skimage.transform import resize
# from shapely.geometry import LineString
# import warnings

# warnings.filterwarnings("ignore")

# DEM_FILE = "DEM_Subset-Original.tif"
# SAR_FILE = "SAR-MS.tif"
# MARKS_FILE = "Marks_Brief1_with_Vectors.shp" 
# OUTPUT_SHP = "LAMP_Predicted_Paths.shp"

# def calculate_slope(dem_array, cell_size):
#     dy, dx = np.gradient(dem_array, cell_size, cell_size)
#     return np.sqrt(dx**2 + dy**2)

# def get_surface_friction(sar_file):
#     with rasterio.open(sar_file) as src:
#         ms_array = np.nan_to_num(src.read())
#         b, r, c = ms_array.shape
#     data = ms_array.transpose(1, 2, 0).reshape(r * c, b)
#     labels = KMeans(n_clusters=4, random_state=42).fit_predict(data)
#     # Scale friction between 1 and 3
#     return ((labels.reshape(r, c) / 3.0) * 2) + 1

# def apply_doorway_funnels(cost_surface, marks_gdf, transform):
#     modified_cost = np.copy(cost_surface)
#     rows, cols = cost_surface.shape
#     y_grid, x_grid = np.mgrid[0:rows, 0:cols]
    
#     for _, row in marks_gdf.iterrows():
#         if row['Door_Angle'] == "Unknown": continue
#         pt = row.geometry.centroid
#         c_px, r_px = ~transform * (pt.x, pt.y)
#         r_px, c_px = int(r_px), int(c_px)
        
#         for angle in [int(a) for a in str(row['Door_Angle']).split(',')]:
#             theta = np.radians(angle - 90) 
#             dy, dx = y_grid - r_px, x_grid - c_px
#             phi = np.arctan2(dy, dx)
#             dist = np.sqrt(dx**2 + dy**2)
#             # Soften the penalty to 2.0 instead of 5.0
#             penalty = np.where(np.cos(phi - theta) > 0, 0.5, 2.0)
#             mask = dist < 10 # Slightly smaller radius
#             modified_cost[mask] *= penalty[mask]
            
#     return np.clip(modified_cost, 1.0, 50.0) # Cap max cost at 50

# def main():
#     print("--- LAMP TASK 1: RECALIBRATING ROUTER ---")
#     with rasterio.open(SAR_FILE) as src:
#         m_trans, crs, m_shape = src.transform, src.crs, (src.height, src.width)
#     with rasterio.open(DEM_FILE) as src:
#         slope_raw = calculate_slope(src.read(1), src.transform[0])
    
#     slope = resize(slope_raw, m_shape, order=1, preserve_range=True)
#     cost_surface = get_surface_friction(SAR_FILE) + (slope * 2) # Lowered multiplier
    
#     marks_gdf = gpd.read_file(MARKS_FILE)
#     # Filtering for the ROI buildings we actually mapped
#     roi_gdf = marks_gdf[marks_gdf['Door_Angle'] != "Unknown"]
#     anisotropic_cost = apply_doorway_funnels(cost_surface, roi_gdf, m_trans)
    
#     paths_list = []
#     nodes = []
#     for _, row in roi_gdf.iterrows():
#         pt = row.geometry.centroid
#         c, r = ~m_trans * (pt.x, pt.y)
#         nodes.append((int(r), int(c)))

#     print(f"Attempting to route between {len(nodes)} valid ROI buildings...")
    
#     # Route in a chain (1 to 2, 2 to 3, etc.) to ensure a connected network
#     for i in range(len(nodes) - 1):
#         try:
#             path_idx, _ = route_through_array(anisotropic_cost, nodes[i], nodes[i+1])
#             coords = [m_trans * (c, r) for r, c in path_idx]
#             if len(coords) > 1: paths_list.append(LineString(coords))
#         except: continue

#     if paths_list:
#         gpd.GeoDataFrame(geometry=paths_list, crs=crs).to_file(OUTPUT_SHP)
#         print(f"SUCCESS! {len(paths_list)} paths saved to {OUTPUT_SHP}")
#     else:
#         print("FAIL: Still no paths. Try decreasing the slope weight further.")

# if __name__ == "__main__":
#     main()

# # WORKING SOLUTION FOR ONE PARTICULAR PATH


# NEW MODELLING MONTE CARLO PATH FINDER for braided paths

# import rasterio
# import numpy as np
# import geopandas as gpd
# from sklearn.cluster import KMeans
# from skimage.graph import route_through_array
# from skimage.transform import resize
# from shapely.geometry import LineString
# import warnings

# warnings.filterwarnings("ignore")

# # --- FILE CONFIGURATION ---
# DEM_FILE = "DEM_Subset-Original.tif"
# SAR_FILE = "SAR-MS.tif"
# MARKS_FILE = "Marks_Brief1_with_Vectors.shp" 
# OUTPUT_SHP = "LAMP_Braided_Probable_Paths_permeable.shp"

# # How many times we simulate "walking" the path (higher = more braided)
# ITERATIONS = 10 

# def calculate_slope(dem_array, cell_size):
#     dy, dx = np.gradient(dem_array, cell_size, cell_size)
#     return np.sqrt(dx**2 + dy**2)

# def get_ml_surface_friction(sar_file):
#     """
#     Uses 8-band SAR/Multispectral data to detect soil density 
#     anomalies (invisible paths).
#     """
#     print("Training Unsupervised ML (K-Means) on 8-band Surface Data...")
#     with rasterio.open(sar_file) as src:
#         ms_array = np.nan_to_num(src.read())
#         bands, rows, cols = ms_array.shape
        
#     # Flatten 8 bands into feature vectors for clustering
#     data = ms_array.transpose(1, 2, 0).reshape(-1, bands)
    
#     # K-Means groups pixels into 5 classes: sand, packed earth, rock, rubble, etc.
#     kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
#     labels = kmeans.fit_predict(data)
#     surface_classes = labels.reshape(rows, cols)
    
#     # We assign lower friction to "Packed Earth" (Cluster 1 usually)
#     # and higher friction to "Loose Sand" or "Rocky Debris".
#     # This identifies the 'invisible' paths people walked for centuries.
#     return ((surface_classes / 4.0) * 2) + 1 

# def apply_anisotropic_funnels(cost_surface, marks_gdf, transform):
#     """Forces paths to align with the manually extracted doorway angles."""
#     modified_cost = np.copy(cost_surface)
#     y_grid, x_grid = np.mgrid[0:cost_surface.shape[0], 0:cost_surface.shape[1]]
    
#     for _, row in marks_gdf.iterrows():
#         if row['Door_Angle'] == "Unknown": continue
#         pt = row.geometry.centroid
#         c_px, r_px = ~transform * (pt.x, pt.y)
#         r_px, c_px = int(r_px), int(c_px)
        
#         for angle in [int(a) for a in str(row['Door_Angle']).split(',')]:
#             theta = np.radians(angle - 90) # Adjust for raster coordinates
#             dy, dx = y_grid - r_px, x_grid - c_px
#             phi = np.arctan2(dy, dx)
#             dist = np.sqrt(dx**2 + dy**2)
            
#             # Use Cosine Similarity for directional pull
#             # Forward alignment = 0.5 (Easy), Backward = 3.0 (Hard Wall)
#             penalty = np.where(np.cos(phi - theta) > 0, 0.5, 3.0)
#             mask = dist < 12 
#             modified_cost[mask] *= penalty[mask]
            
#     return np.clip(modified_cost, 1.0, 50.0)

# def main():
#     print("--- LAMP TASK 1: PROBABILISTIC BRAIDED NETWORK ---")
    
#     # 1. Setup Master Grid
#     with rasterio.open(SAR_FILE) as src:
#         m_trans, crs, m_shape = src.transform, src.crs, (src.height, src.width)
    
#     # 2. Topography & SAR-ML Surface Logic
#     with rasterio.open(DEM_FILE) as src:
#         slope_raw = calculate_slope(src.read(1), src.transform[0])
#     slope = resize(slope_raw, m_shape, order=1, preserve_range=True)
    
#     # Fusing SAR Density + Topographic Slope
#     # This solves the "One Variable" limitation the mentors mentioned.
#     base_cost = get_ml_surface_friction(SAR_FILE) + (slope * 1.5)
    
#     # 3. Apply Building Entrance Vectors
#     marks_gdf = gpd.read_file(MARKS_FILE)
#     roi_gdf = marks_gdf[marks_gdf['Door_Angle'] != "Unknown"]
#     anisotropic_cost = apply_anisotropic_funnels(base_cost, roi_gdf, m_trans)
    
#     # 4. Monte Carlo Routing (The "Braided" Network)
#     print(f"Simulating {ITERATIONS} human walkers between {len(roi_gdf)} buildings...")
#     paths_list = []
#     nodes = []
#     for _, row in roi_gdf.iterrows():
#         pt = row.geometry.centroid
#         c, r = ~m_trans * (pt.x, pt.y)
#         nodes.append((min(max(int(r), 0), m_shape[0]-1), min(max(int(c), 0), m_shape[1]-1)))

#     # Route from the central enclosure (Node 0) to all other mapped tombs
#     start_node = nodes[0]
#     for i in range(1, len(nodes)):
#         target_node = nodes[i]
        
#         for _ in range(ITERATIONS):
#             # Inject "Behavioral Noise" - simulated humans make slightly different choices
#             noise = np.random.normal(1.0, 0.2, size=m_shape) 
#             # dynamic_cost = anisotropic_cost * np.clip(noise, 0.6, 1.8)
#             dynamic_cost = permeable_cost * np.clip(noise, 0.6, 1.8)
            
#             try:
#                 path_idx, _ = route_through_array(dynamic_cost, start_node, target_node)
#                 coords = [m_trans * (c, r) for r, c in path_idx]
#                 if len(coords) > 1:
#                     paths_list.append(LineString(coords))
#             except: continue

#     # 5. Export to Shapefile
#     if paths_list:
#         gpd.GeoDataFrame(geometry=paths_list, crs=crs).to_file(OUTPUT_SHP)
#         print(f"SUCCESS! {len(paths_list)} paths generated.")
#         print(f"File saved: {OUTPUT_SHP}")
#     else:
#         print("FAIL: No paths generated.")

# if __name__ == "__main__":
#     main()

# end of probable lines


# begin code for permeable lines:

import rasterio
import numpy as np
import geopandas as gpd
from sklearn.cluster import KMeans
from skimage.graph import route_through_array
from skimage.transform import resize
from shapely.geometry import LineString
import warnings

warnings.filterwarnings("ignore")

# --- CONFIG ---
DEM_FILE = "DEM_Subset-Original.tif"
SAR_FILE = "SAR-MS.tif"
MARKS_FILE = "Marks_Brief1_with_Vectors.shp" 
OUTPUT_SHP = "LAMP_Final_Braided_Paths.shp"
ITERATIONS = 12 # Balanced number of simulations

def calculate_slope(dem_array, cell_size):
    dy, dx = np.gradient(dem_array, cell_size, cell_size)
    return np.sqrt(dx**2 + dy**2)

def get_ml_surface_friction(sar_file):
    with rasterio.open(sar_file) as src:
        ms_array = np.nan_to_num(src.read())
        bands, rows, cols = ms_array.shape
    data = ms_array.transpose(1, 2, 0).reshape(-1, bands)
    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    labels = kmeans.fit_predict(data)
    return ((labels.reshape(rows, cols) / 4.0) * 2) + 1 

def apply_permeable_funnels(cost_surface, marks_gdf, transform):
    """
    Forces paths to avoid building interiors and respect doorway directions
    using a 'Permeable Wall' (20x) penalty.
    """
    modified_cost = np.copy(cost_surface)
    rows, cols = cost_surface.shape
    y_grid, x_grid = np.mgrid[0:rows, 0:cols]
    
    for _, row in marks_gdf.iterrows():
        if row['Door_Angle'] == "Unknown": continue
        pt = row.geometry.centroid
        c_px, r_px = ~transform * (pt.x, pt.y)
        r_px, c_px = int(r_px), int(c_px)
        
        for angle in [int(a) for a in str(row['Door_Angle']).split(',')]:
            theta = np.radians(angle - 90) 
            dy, dx = y_grid - r_px, x_grid - c_px
            phi = np.arctan2(dy, dx)
            dist = np.sqrt(dx**2 + dy**2)
            
            # THE FIX: 20x penalty for 'Back Walls' ensures the primary path
            # won't cut through 161 or 226 West-to-East.
            alignment = np.cos(phi - theta)
            penalty = np.where(alignment > 0.7, 0.1, 20.0)
            
            mask = dist < 10 
            modified_cost[mask] *= penalty[mask]
            
    return np.clip(modified_cost, 1.0, 500.0)

def main():
    print("--- RUNNING PERMEABLE WALL SIMULATION ---")
    with rasterio.open(SAR_FILE) as src:
        m_trans, crs, m_shape = src.transform, src.crs, (src.height, src.width)
    with rasterio.open(DEM_FILE) as src:
        slope = resize(calculate_slope(src.read(1), src.transform[0]), m_shape)
    
    # ML Density + Slope + Anisotropic Doors
    base_cost = get_ml_surface_friction(SAR_FILE) + (slope * 2.0)
    marks_gdf = gpd.read_file(MARKS_FILE)
    roi_gdf = marks_gdf[marks_gdf['Door_Angle'] != "Unknown"]
    final_cost = apply_permeable_funnels(base_cost, roi_gdf, m_trans)
    
    paths_list = []
    nodes = []
    for _, row in roi_gdf.iterrows():
        pt = row.geometry.centroid
        c, r = ~m_trans * (pt.x, pt.y)
        nodes.append((min(max(int(r), 0), m_shape[0]-1), min(max(int(c), 0), m_shape[1]-1)))

    # Start Node (Building 180 Area)
    start_node = nodes[0]
    for i in range(1, len(nodes)):
        target_node = nodes[i]
        for _ in range(ITERATIONS):
            # Monte Carlo 'Behavioral Noise'
            noise = np.random.normal(1.0, 0.15, size=m_shape) 
            dynamic_cost = final_cost * np.clip(noise, 0.7, 1.5)
            try:
                path_idx, _ = route_through_array(dynamic_cost, start_node, target_node)
                coords = [m_trans * (c, r) for r, c in path_idx]
                paths_list.append(LineString(coords))
            except: continue

    if paths_list:
        gpd.GeoDataFrame(geometry=paths_list, crs=crs).to_file(OUTPUT_SHP)
        print(f"SUCCESS! Check QGIS: {OUTPUT_SHP}")
    else:
        print("FAIL: Check ROI building matches.")

if __name__ == "__main__":
    main()