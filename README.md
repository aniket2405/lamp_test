# LAMP: Spatial Analytics Pipeline for the Necropolis of El Bagawat

## 1. GitHub Repository Link
* **Link:** https://github.com/aniket2405/lamp_test

## 2. Description
**Overview:** This repository contains a spatial data science and machine learning pipeline developed for the Late Antiquity Modeling Project (LAMP). Set in the necropolis of El Bagawat (Egypt’s Kharga Oasis), this project reconstructs the embodied experiences of ancient communities. By developing predictive models for human transit and calculating true 3D visual occlusion, this pipeline moves beyond traditional hydrographic GIS analysis to craft accurate historical reconstructions.

**Requirements Achieved:**
* **Task 1:** ML-driven predictive pathfinding model accounting for topography, walking surface types, and the directional influence of specific building entrances. Rendered as a GIS vector layer.
* **Task 2:** 3D ray-traced viewshed model projecting gradients of visibility from a complex 3D scene (accounting for Z-heights of mud-brick tombs). Rendered as a GIS vector layer.
* **Bonus:** Interactive 3D volume rendering of the landscape and viewsheds.
* **Developer UX:** Interactive `demo.ipynb` wrapper for rapid testing.
* **Roadmap Note (Audibility):** The 3D ray-casting architecture developed here for visual occlusion serves as the mathematical foundation for modeling acoustic propagation (audibility) during the proposed GSoC timeline.

## 3. Condition Logic (The Architecture)

### Task 1: Predictive Path Tracing & Spatial Networks
* **Logic:** Current architectural state-of-the-art relies on flawed "least-cost paths" (water-flow models based solely on steepness). This pipeline introduces a predictive spatial network that ingests multiple variables. It generates a complex friction surface model that applies severe penalties for intersecting solid structures while creating zero-friction attractors at verified architectural entrances (doorways) and favorable walking surfaces.
* **Result:** Rather than a single hydrographic line, the model generates a braided network of likely transit corridors (agential possibilities), successfully predicting the primary southern thoroughfare as the path of least resistance between any given buildings.

### Task 2: 3D Viewshed Ray-Tracing from Complex Scenes
* **Logic:** Standard Space Syntax and GIS planimetric tools fail to account for building heights and hilly topography. This pipeline utilizes a 2.5D Digital Elevation Model (`DEM_Subset-WithBuildings.tif`) to train a mathematical line-of-sight ray-tracer. The condition evaluates the slope angle of the ray across the full 3D volume: if an intervening building's Z-height exceeds the maximum slope seen so far, the ray terminates, creating a true architectural shadow (roof-edge occlusion).
* **Dynamic Targeting:** The observer logic is highly modular, engineered to project visual occlusion from *any given point* or building ID on the site, accurately simulating what a person could see at a biologically accurate human eye level (1.6m).

## 4. Logging Implementation
**Pipeline Execution Logs:** The scripts utilize a dual-handler logging architecture via Python's `logging` module.

Outputs are synchronously printed to `stdout` for real-time monitoring and permanently saved to timestamped text files (e.g., `logs/lamp_pipeline_20260321.log`). Log milestones include:
* Data ingestion status and missing file flags.
* Coordinate transformations (Pixel to Geocoordinate translation).
* Ray-casting counts (e.g., `[INFO] Casting true 3D rays (Shadows enabled)...`).
* Mesh generation and explicit 3D geometry extrusion stages.

## 5. How to Run Locally

**1. Clone the Repository:**
```bash
git clone https://github.com/aniket2405/lamp_test
cd lamp_test
```

**2. Set Up Virtual Environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

**3. Install Dependencies:**
```bash
pip install -r requirements.txt
```

**4. Data Acquisition:**
The spatial datasets (DEMs and Shapefiles) are not stored in this repository due to file size constraints.
* **Download Link:** [El Bagawat Test Dataset (Box)](https://app.box.com/s/6c5tv2nvbm9d1a7bpmryvmc00sdo79op)
* **Crucial Step:** Please ensure all `.tif` and `.shp` files (and their sidecars) are moved from their subfolders directly into the root of the `/data` folder.
* **Final Structure should be:**
    - `lamp_test/data/DEM_Subset-WithBuildings.tif`
    - `lamp_test/data/Marks_Brief1_with_Vectors.shp`
    - (and so on...)

**5. Execution Order:**

You can execute the pipeline in two ways:

#### Option A: Interactive Demo (Recommended for Quick Review)
If you prefer a guided walkthrough, open the `demo.ipynb` Jupyter Notebook in the root directory. This notebook serves as a wrapper for the entire pipeline, providing cell-by-cell execution and immediate visual previews of the generated maps.

#### Option B: Command Line Interface (CLI)
For a production-style execution, run the scripts in order from your terminal:

```bash
# 1. Prepare doorway vectors
python scripts/01_preprocess_doorways.py

# 2. Generate spatial network
python scripts/02_task1_pipeline.py

# --- NOTE ON TASK 2 ---
# You can open the Task 2 scripts and modify OBSERVER_PT_ID to 
# dynamically calculate visibility from any building (e.g., 154, 180, 224).

# 3. Generate the 2D GIS vector layer (dynamically named by ID)
python scripts/03a_task2_viewshed.py

# 4. Generate the interactive browser-based 3D volume
python scripts/03b_task2_3d_render.py
```

**6. Viewing in QGIS:**
To verify the vector outputs, open QGIS and import `DEM_Subset-Original.tif` as a Hillshade base layer. Set the Hillshade blending mode to **Multiply** over a satellite base map for true 3D depth. Drag and drop the generated `Task1_Global_Minimum_Path.shp` and `Task2_Viewshed.shp` files over the terrain. Apply a 60% opacity to the viewshed layer to visualize the precise gradient of visibility.

## 7. Test Results & Visual Proof

**Generated Artifacts:**
* `output/Marks_Brief1_with_Vectors.shp`
* `output/Task1_Global_Minimum_Path.shp`
* `output/Task1_Probabilistic_Network.shp`
* `output/Task2_Viewshed_[ID].shp` (Dynamically generated based on observer point)

**Developer Note:** While the static previews below demonstrate results for Buildings 154, 180, and 224, the pipeline is fully dynamic. Running the `demo.ipynb` or the CLI scripts allows for real-time recalculation of these viewsheds from any building ID on the site.

### Task 1: Anisotropic Pathfinding Simulation
This rendering demonstrates the probabilistic spatial network. While the pipeline is **fully dynamic**—allowing users to input any combination of building IDs to generate custom transit routes—this specific simulation anchors the network to the three critical observer points provided in the test data (Buildings 154, 180, and 224). 

These specific points were chosen because they represent distinct topological zones (a boundary structure, a central complex, and an eastern tomb), providing a rigorous test of the algorithm. By injecting high friction penalties for solid mud-brick structures and low friction for verified doorways, the algorithm successfully traces the global minimum path (red) connecting these anchor points across the landscape.

<img src="images/path.png" width="100%" alt="Task 1 Pathway">
Figure 1: The predicted transit pathway navigating the necropolis topology, highlighting the avoidance of 3D structures and utilization of mapped doorways.

### Task 2: Vector Viewsheds & 3D Interactive Volumes
The pipeline dynamically calculates viewsheds from any given point. Below are the results from three critical observer points: a western boundary structure (154), the central complex (180), and an eastern tomb (224).
* **Top Row:** Mathematically ray-traced 2D GIS vector layers (Cyan) draped over satellite imagery and 3D hillshades.
* **Bottom Row:** Interactive 3D browser renders showcasing roof-edge occlusion and true Z-axis shadows.

| Observer Point | Building 154 | Building 180 | Building 224 |
| :--- | :--- | :--- | :--- |
| **2D GIS Vector** | <img src="images/2d_154.png" width="100%"> | <img src="images/2d_180.png" width="100%"> | <img src="images/2d_224.png" width="100%"> |
| **3D Volume** | <img src="images/3d_154.png" width="100%"> | <img src="images/3d_180.png" width="100%"> | <img src="images/3d_224.png" width="100%"> |