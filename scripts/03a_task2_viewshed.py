import os
import numpy as np
import rasterio
import geopandas as gpd
from skimage.draw import line
from rasterio.features import shapes
from shapely.geometry import shape
import warnings

warnings.filterwarnings("ignore")

# --- CONFIG ---
DEM_FILE = "data/DEM_Subset-WithBuildings.tif"
MARKS_FILE = "data/Marks_Brief1_with_Vectors.shp"
OUTPUT_VIEWSHED = "output/Task2_Viewshed.shp"
OBSERVER_HEIGHT = 1.6 # Average human eye level in meters

def calculate_viewshed(dem, start_r, start_c, cell_size):
    """
    Casts 3D rays from the observer to the edges of the map.
    Calculates visibility based on the Z-elevation viewing angle.
    """
    rows, cols = dem.shape
    viewshed = np.zeros((rows, cols), dtype=np.uint8)
    observer_z = dem[start_r, start_c] + OBSERVER_HEIGHT

    # Find all perimeter pixels to cast rays toward
    perimeter_pixels = []
    for r in range(rows):
        perimeter_pixels.extend([(r, 0), (r, cols - 1)])
    for c in range(1, cols - 1):
        perimeter_pixels.extend([(0, c), (rows - 1, c)])

    print(f"Casting {len(perimeter_pixels)} 3D rays...")

    for end_r, end_c in perimeter_pixels:
        # Get pixel coordinates along the line of sight
        rr, cc = line(start_r, start_c, end_r, end_c)
        
        if len(rr) < 2:
            continue
            
        # Extract elevations along the ray
        elevations = dem[rr, cc]
        
        # Calculate 2D distance from observer for each pixel on the ray
        distances = np.sqrt((rr - start_r)**2 + (cc - start_c)**2) * cell_size
        distances[0] = 1e-6 # Prevent division by zero at the observer's exact spot
        
        # Calculate the viewing angle (slope) to each pixel
        # Slope = (Target Elevation - Observer Eye Level) / Distance
        slopes = (elevations - observer_z) / distances
        
        # A pixel is only visible if its viewing angle is HIGHER than the highest angle seen so far
        max_slopes = np.maximum.accumulate(slopes)
        
        # If the slope is >= the max_slope, it isn't blocked by anything in front of it!
        visible = slopes >= max_slopes
        
        # Mark visible pixels (1) on our master grid
        viewshed[rr[visible], cc[visible]] = 1

    # Ensure observer's exact location is always visible
    viewshed[start_r, start_c] = 1 
    return viewshed

def main():
    print("--- TASK 2: 3D VIEWSHED RAY-TRACING ---")
    
    if not os.path.exists("data/DEM_Subset-WithBuildings.tif"):
        print("ERROR: DEM_Subset-WithBuildings.tif not found in data/ folder.")
        return

    # 1. Load the 3D DEM (With Buildings)
    with rasterio.open(DEM_FILE) as src:
        dem_array = src.read(1)
        transform = src.transform
        crs = src.crs
        cell_size = transform[0]
        
    # 2. Get Observer Location (Building 180)
    marks = gpd.read_file(MARKS_FILE)
    # Filter for Building 180 (assuming Door_Angle "0" or known main building)
    # We will use the first mark as our observer for this simulation
    observer_pt = marks.geometry.iloc[0].centroid 
    
    c_px, r_px = ~transform * (observer_pt.x, observer_pt.y)
    start_r, start_c = int(r_px), int(c_px)

    print(f"Observer placed at Pixel(Row={start_r}, Col={start_c}) with {OBSERVER_HEIGHT}m eye-level.")

    # 3. Calculate the Viewshed Matrix
    viewshed_matrix = calculate_viewshed(dem_array, start_r, start_c, cell_size)

    # 4. Vectorize the Matrix (Mentor Requirement: "Render as GIS vector layer")
    print("Converting visible raster pixels into vector polygons...")
    shapes_generator = shapes(viewshed_matrix, mask=(viewshed_matrix == 1), transform=transform)
    
    polygons = []
    for geom, value in shapes_generator:
        polygons.append(shape(geom))

    # 5. Export to Shapefile
    viewshed_gdf = gpd.GeoDataFrame(geometry=polygons, crs=crs)
    viewshed_gdf.to_file(OUTPUT_VIEWSHED)
    print(f"SUCCESS! Viewshed vector saved to: {OUTPUT_VIEWSHED}")

if __name__ == "__main__":
    main()