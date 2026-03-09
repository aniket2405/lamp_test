# import geopandas as gpd

# MARKS_FILE = "Marks_Brief1.shp"
# BUILDINGS_FILE = "BuildingFootprints.shp"
# OUTPUT_FILE = "Marks_Brief1_with_Vectors.shp"

# # Our ground-truth dictionary
# doorway_angles = {
#     150: "180", 151: "180", 152: "180", 153: "90", 154: "225", 155: "90", 156: "90", 157: "90",
#     158: "90,270", 159: "90", 160: "90", 161: "90", 162: "90", 163: "90", 164: "90", 165: "180",
#     170: "180", 171: "180", 172: "90", 173: "90", 174: "270", 175: "0", 176: "180", 177: "180",
#     178: "90", 179: "270", 180: "0", 181: "270", 182: "270", 183: "90", 184: "90,0", 185: "0,180",
#     186: "270", 188: "270", 189: "270", 190: "180", 191: "270", 192: "270", 193: "270", 194: "270",
#     195: "270", 196: "180", 197: "0,90,180", 198: "270,180", 208: "270", 210: "270", 209: "0",
#     212: "180", 213: "180", 214: "90", 215: "270", 216: "180", 217: "180", 218: "270",
#     219: "270,90,180", 220: "0,270,180", 221: "90,270,180", 222: "0,270", 223: "270", 224: "270",
#     225: "90", 226: "90", 227: "270", 228: "270", 229: "270"
# }

# def main():
#     print("Performing Spatial Join to identify buildings...")
#     marks = gpd.read_file(MARKS_FILE)
#     buildings = gpd.read_file(BUILDINGS_FILE)

#     # Ensure both are in the same coordinate system
#     marks = marks.to_crs(buildings.crs)

#     # Identify the correct ID column in the BUILDINGS file (likely 'id' or 'ID')
#     b_id_col = next((c for c in buildings.columns if c.lower() in ['id', 'fid', 'objectid', 'build_id']), buildings.columns[0])
#     print(f"Using building ID column: {b_id_col}")

#     # Spatial Join: Points that are 'within' building footprints
#     joined = gpd.sjoin(marks, buildings[[b_id_col, 'geometry']], how='left', predicate='within')

#     joined['Door_Angle'] = "Unknown"
#     match_count = 0
    
#     for idx, row in joined.iterrows():
#         try:
#             # Look up the building ID found at this point's location
#             real_id = int(row[b_id_col])
#             if real_id in doorway_angles:
#                 joined.at[idx, 'Door_Angle'] = doorway_angles[real_id]
#                 match_count += 1
#         except: continue
            
#     # Clean up and save
#     joined.to_file(OUTPUT_FILE)
#     print(f"SUCCESS: Geographically matched {match_count} points to buildings.")

# if __name__ == "__main__":
#     main()

# working solution for the line cutting through houses 161 and 226.


# new solution where we're including the physicality of the house.

