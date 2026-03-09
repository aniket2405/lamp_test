# LAMP Evaluation: Task 1 - Anisotropic Probabilistic Pathway Simulation

## Executive Summary

The standard state-of-the-art in architectural path tracing relies heavily on hydrographic "least cost path" (LCP) models. These models treat human movement like water flowing over a Digital Elevation Model (DEM), calculating routes based almost entirely on a single variable: topographic steepness. 

For the El-Bagawat Necropolis project, this approach is insufficient. It ignores ground density (compacted ancient paths vs. loose sand), architectural logic (the direction of building entrances), and the inherent variability of human choice. 

This document details the iterative development of a **Multi-Variable Anisotropic Behavioral Model**. By integrating Unsupervised Machine Learning (SAR-based soil density), Anisotropic Doorway Vectors, and Monte Carlo probability simulations, we successfully generated a probabilistic network of historical human movement that respects both the physical and architectural realities of the site.

---

## Iterative Development & Challenges

### Iteration 1: Base Geospatial Pipeline & Geometry Handling

- **Goal:** Establish a basic LCP algorithm routing paths between manually identified architectural entrances.
- **Challenge:** The initial script crashed with an `AttributeError` when attempting to read the X/Y coordinates of the doorway vectors. The GIS software had saved single points as `MultiPoint` geometries.
- **Solution:** We implemented a geometric `.centroid` extraction method to safely collapse `MultiPoint` arrays into singular, mathematically readable `Point` objects, allowing the matrix transformation from real-world CRS to pixel-grid indices.

### Iteration 2: Spatial Disconnects & The "Prison" Effect

- **Goal:** Generate the first set of visible paths between the Region of Interest (ROI) buildings.
- **Challenge 1 (Data Mismatch):** The script reported `0 valid ROI buildings`. The archaeological house numbers (e.g., 180, 208) in our manual dictionary did not match the generic sequential IDs (1, 2, 3) in the `Marks_Brief1.shp` file.
- **Challenge 2 (Cost Restrictiveness):** Even after hardcoding points, the Dijkstra routing engine returned `0 paths`. The combined penalty of steep slope ($10\times$) and rear-wall approach ($5\times$) created mathematical "prisons." The algorithm could not find a path under the maximum cost threshold.
- **Solution:** 1. We wrote a **Spatial Join script** (`gpd.sjoin`) to geometrically match points to the `BuildingFootprints.shp` polygons, dynamically looking up the correct building IDs based on location rather than attribute tables.
  1. We recalibrated the cost multipliers (lowering slope weight to $2\times$) and switched to a "Chain Topology" (routing from Node A to B, B to C) to ensure the network remained fully connected without hitting maximum cost limits.

### Iteration 3: "Invisible Paths" & Probabilistic Braiding

- **Goal:** Address the requirement to identify "pathways no longer visible today" and simulate the "possible range" of human movement.
- **Challenge:** A single yellow "Least Cost Path" represents a mathematical ideal, not human reality. Furthermore, optical imagery (`OrthoImage`) cannot reveal paths buried under sand.
- **Solution:** * **SAR ML Clustering:** We fed the 8-band `SAR-MS.tif` into an unsupervised **K-Means clustering** algorithm ($k=5$). Because Synthetic Aperture Radar detects sub-surface soil density, this identified historical "Packed Earth" anomalies (ancient compacted paths) distinct from loose sand. 
  - **Monte Carlo Braiding:** We wrapped the routing engine in an iterative loop ($n=12$), injecting Gaussian Noise ($\pm 15$) into the friction matrix on each pass. This simulated different human choices, transforming the single path into a "braided" probability field.

### Iteration 4: The "Ghosting" Problem & Anisotropic Permeability

- **Goal:** Finalize the architectural realism of the simulated paths.
- **Challenge:** Visual inspection of the braided network revealed that paths were "ghosting" (cutting directly through the solid western walls of Buildings 161 and 226) because the algorithm calculated that traversing 3 pixels of "wall" was mathematically cheaper than a 15-pixel detour around the building.
- **Solution - The "Permeable Wall" Anisotropy:** We completely rebuilt the doorway vector logic using a directional Cosine Similarity gradient.
  - **Entrance Alignment ($>0.7 \cos$):** Assigned a $0.1\times$ cost multiplier, creating a "gravitational pull" into the doorway.
  - **Opposing Walls ($<0.7 \cos$):** Assigned a **$20.0\times$ penalty**. 
  - *Crucial Context:* We purposefully avoided an "Infinite/Hard Wall" penalty. In archaeological ruins, walls are often collapsed into rubble. An infinite penalty would turn the site into an artificial maze and break the algorithm on single-pixel gaps. The $20\times$ penalty is "High but Permeable"—it successfully forces the primary route to detour to the correct East entrances, while allowing the probabilistic braids to reflect the faint possibility of traversing collapsed ruins.

---

## Final Technical Architecture

The finalized Task 1 pipeline (`lamp_task1_final.py`) operates in four distinct phases:

1. **Topographic & Spectral Initialization:** * Reads the `DEM_Subset-Original.tif` to calculate directional gradients (Slope).
  - Reads the `SAR-MS.tif` and applies Unsupervised ML to generate a Soil Density Friction layer.
2. **Anisotropic Field Generation:**
  - Reads building footprints and applies the 20x / 0.1x Cosine Similarity modifiers to the cost surface based on manually extracted doorway angles.
3. **Stochastic Pathfinding:**
  - Utilizes `skimage.graph.route_through_array` to calculate routes from a central node (Building 180) to all surrounding ROI nodes.
  - Applies Gaussian noise per iteration to generate spatial deviation.
4. **Geospatial Export:**
  - Re-projects pixel coordinates back to `EPSG:32636` and exports the simulated network as `LAMP_Final_Braided_Paths.shp`.

---

## Results & Inferences

Upon overlaying the final Probabilistic Network (Red Braids) in QGIS, several key behavioral patterns emerged:

1. **Doorway Magnetism:** The braided lines successfully converge at specific architectural openings, proving the anisotropic logic overrode the default "shortest distance" algorithm.
2. **Alleyway Priority:** Paths correctly route *around* solid structures (e.g., the western walls of 161 and 226), adhering to the physical topology of the "streets."
3. **The "South Gate" Corridor:** The Monte Carlo simulations revealed a highly dense, consistently overlapping path along the southern edge of the main enclosure. By cross-referencing this with the SAR K-Means output, we infer this was a primary historical thoroughfare due to its combination of low topographic slope and high sub-surface compaction.

---

## Tech Stack

- **Geospatial Processing:** `Rasterio`, `GeoPandas`, `Shapely`
- **Machine Learning:** `Scikit-learn` (K-Means Clustering)
- **Pathfinding Engine:** `Scikit-image` (MCP - Minimal Cost Path)
- **Visualization:** `QGIS 3.x`

