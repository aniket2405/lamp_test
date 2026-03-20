import os
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
DEM_FILE = "data/DEM_Subset-Original.tif"
SAR_FILE = "data/SAR-MS.tif"
MARKS_FILE = "data/Marks_Brief1_with_Vectors.shp" 
OUTPUT_MINIMUM = "output/Task1_Global_Minimum_Path.shp"
OUTPUT_BRAIDED = "output/Task1_Probabilistic_Network.shp"
ITERATIONS = 12

def calculate_slope(dem_array, cell_size):
    dy, dx = np.gradient(dem_array, cell_size, cell_size)
    return np.sqrt(dx**2 + dy**2)

def get_ml_surface_friction(sar_file):
    print("Running K-Means Surface Density clustering...")
    with rasterio.open(sar_file) as src:
        ms_array = np.nan_to_num(src.read())
        bands, rows, cols = ms_array.shape
    data = ms_array.transpose(1, 2, 0).reshape(-1, bands)
    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    labels = kmeans.fit_predict(data)
    return ((labels.reshape(rows, cols) / 4.0) * 2) + 1 

def apply_permeable_funnels(cost_surface, marks_gdf, transform):
    print("Applying 20x Permeable Architectural Vectors...")
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
            
            alignment = np.cos(phi - theta)
            penalty = np.where(alignment > 0.7, 0.1, 20.0)
            mask = dist < 10 
            modified_cost[mask] *= penalty[mask]
            
    return np.clip(modified_cost, 1.0, 500.0)

def main():
    print("--- TASK 1: ANISOTROPIC PATHWAY SIMULATION ---")

    # Check if data directory exists
    if not os.path.exists("data"):
        print("ERROR: 'data' folder not found. Are you running this from the project root?")
        return
        
    # Auto-create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)

    # 1. Setup Master Grid & Calculate Base Cost
    with rasterio.open(SAR_FILE) as src:
        m_trans, crs, m_shape = src.transform, src.crs, (src.height, src.width)
    with rasterio.open(DEM_FILE) as src:
        slope = resize(calculate_slope(src.read(1), src.transform[0]), m_shape, order=1, preserve_range=True)
    
    base_cost = get_ml_surface_friction(SAR_FILE) + (slope * 2.0)
    
    marks_gdf = gpd.read_file(MARKS_FILE)
    roi_gdf = marks_gdf[marks_gdf['Door_Angle'] != "Unknown"]
    
    # Apply the 20x Permeable Wall Logic
    final_cost = apply_permeable_funnels(base_cost, roi_gdf, m_trans)
    
    nodes = []
    for _, row in roi_gdf.iterrows():
        pt = row.geometry.centroid
        c, r = ~m_trans * (pt.x, pt.y)
        nodes.append((min(max(int(r), 0), m_shape[0]-1), min(max(int(c), 0), m_shape[1]-1)))

    start_node = nodes[0]
    global_minimum_paths = []
    probabilistic_paths = []

    print(f"Routing from Building 180 to {len(nodes)-1} targets...")

    for i in range(1, len(nodes)):
        target_node = nodes[i]
        
        # --- A. GENERATE THE GLOBAL MINIMUM PATH ---
        try:
            path_idx, _ = route_through_array(final_cost, start_node, target_node)
            coords = [m_trans * (c, r) for r, c in path_idx]
            global_minimum_paths.append(LineString(coords))
        except: continue
        
        # --- B. GENERATE THE PROBABILISTIC NETWORK ---
        for _ in range(ITERATIONS):
            noise = np.random.normal(1.0, 0.15, size=m_shape) 
            dynamic_cost = final_cost * np.clip(noise, 0.7, 1.5)
            try:
                path_idx, _ = route_through_array(dynamic_cost, start_node, target_node)
                coords = [m_trans * (c, r) for r, c in path_idx]
                probabilistic_paths.append(LineString(coords))
            except: continue

    # 4. Export Both Shapefiles
    if global_minimum_paths:
        gpd.GeoDataFrame(geometry=global_minimum_paths, crs=crs).to_file(OUTPUT_MINIMUM)
        print(f"SUCCESS: Saved {OUTPUT_MINIMUM}")
        
    if probabilistic_paths:
        gpd.GeoDataFrame(geometry=probabilistic_paths, crs=crs).to_file(OUTPUT_BRAIDED)
        print(f"SUCCESS: Saved {OUTPUT_BRAIDED}")

if __name__ == "__main__":
    main()