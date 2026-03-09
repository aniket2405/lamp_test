import rasterio
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans

SAR_FILE_PATH = "SAR-MS.tif"

def main():
    print("Loading 8-band multispectral data...")
    with rasterio.open(SAR_FILE_PATH) as src:
        ms_array = src.read() 
        # ms_array shape is currently (8, 58, 70)
        bands, rows, cols = ms_array.shape
        
    # --- 1. DATA PREPARATION ---
    # Scikit-learn cannot read 3D image arrays. 
    # It needs a 2D table: (Number of Pixels, Number of Features).
    # We flatten our (58x70) grid into 4,060 individual pixels.
    # Each pixel has 8 features (the spectral bands).
    print("Flattening matrix for machine learning...")
    
    # Transpose moves bands to the end: (58, 70, 8), then reshape makes it (4060, 8)
    reshaped_data = ms_array.transpose(1, 2, 0).reshape(rows * cols, bands)
    
    # Replace any potential missing data (NaNs) with 0 to prevent ML crashes
    reshaped_data = np.nan_to_num(reshaped_data)

    # --- 2. TRAIN THE COMPUTER VISION MODEL ---
    # We ask the algorithm to find K=4 distinct surface types in the dirt.
    n_clusters = 4 
    print(f"Training K-Means clustering model to identify {n_clusters} surface types...")
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    
    # The model analyzes all 8 bands and assigns a Class ID (0, 1, 2, or 3) to every pixel
    labels = kmeans.fit_predict(reshaped_data)
    
    # --- 3. RECONSTRUCT THE MAP ---
    # Fold the 4,060 labels back into the original 58x70 grid shape
    clustered_image = labels.reshape(rows, cols)
    
    # --- 4. VISUALIZATION ---
    print("Rendering Classified Surface Map...")
    plt.figure(figsize=(10, 8))
    
    # We use a discrete colormap to clearly show the boundaries of the classes
    plt.imshow(clustered_image, cmap='viridis')
    plt.colorbar(ticks=range(n_clusters), label="Surface Class ID")
    plt.title("ML Classification: Terrain Surface Types")
    plt.xlabel("Columns (X)")
    plt.ylabel("Rows (Y)")
    plt.show()

if __name__ == "__main__":
    main()