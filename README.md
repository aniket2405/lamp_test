# LAMP Evaluation: Task 1 - Anisotropic Path Analysis

## Executive Summary
Existing architectural pathfinding tools often rely on "hydrographic" models (Least Cost Path) that treat human movement like water flowing over a digital elevation model (DEM). This approach is limited as it only accounts for topographic steepness, ignoring ground density, architectural logic, and the inherent variability of human choice. 

Our solution implements a **Multi-Variable Anisotropic Behavioral Model** that integrates Machine Learning (ML), architectural vectors, and probabilistic simulation to identify both visible and "hidden" ancient pathways.

---

## 1. Sub-Surface Path Detection (ML-Driven Surface Friction)
To identify pathways no longer visible in optical imagery, we utilized the **8-band SAR-MS.tif** (Synthetic Aperture Radar & Multispectral) dataset.

* **Methodology:** Unsupervised **K-Means Clustering**.
* **The Science:** Radar backscatter can penetrate thin layers of shifting sand to detect differences in soil compaction. Centuries of human foot traffic result in higher soil density. 
* **Implementation:** By clustering the 8-band data into 5 distinct surface classes, the model identifies "Packed Earth" vs. "Loose Sand." 
* **Impact:** The pathfinding engine is programmed to "prefer" these high-density clusters, effectively uncovering ancient corridors that are currently buried or invisible to the naked eye.



---

## 2. Anisotropic Doorway Vectors
Standard GIS tools treat buildings as generic solid obstacles. Our model treats them as **architectural entities** with defined points of entry and exit.

* **Methodology:** Directional Cost Funnels via **Cosine Similarity**.
* **The Logic:** We manually extracted doorway orientations for the ROI (e.g., East-facing for Building 161). The algorithm applies a mathematical "funnel" to the cost surface centered on these vectors:
    * **Entrance Alignment:** Movement aligned with the door angle receives a cost multiplier of **0.1** (creating a "gravitational pull").
    * **Opposing Walls:** Movement against the architectural grain receives a cost multiplier of **20.0** (creating a "Permeable Wall").
* **Impact:** Paths now logically approach buildings at their designated entrances. The **20.0x "Permeable" penalty** ensures that while the primary path respects walls, the model acknowledges the ruined state of the site where rubble might be traversed if detours are excessive.



---

## 3. Probabilistic "Braided" Network (Monte Carlo Simulation)
A single "Least Cost Path" represents a mathematical ideal, not the reality of human behavior. To identify the "possible range of paths" requested by the mentors, we implemented a probabilistic approach.

* **Methodology:** Iterative Monte Carlo Simulation ($n=12$).
* **The Logic:** We injected **Gaussian Noise** (stochastic variation) into the terrain's friction coefficient for each iteration to simulate different human choices and environmental uncertainty.
* **Impact:** This produces the **"Red Braids"** visualized in the final output. 
    * **High-Probability Arteries:** Areas where lines converge into thick "cables."
    * **Possible Ranges:** Areas where lines branch into a "mesh," identifying secondary routes through complex architectural neighborhoods.



---
