# accessibility_analysis.py
import geopandas as gpd
import os
import logging
import argparse

# ----------------------------
# CONFIGURATION
# ----------------------------
INPUT_GPKG = "data/processed/ottawa_accessibility_data.gpkg"
DA_LAYER = "dissemination_areas"
PARKS_LAYER = "parks"
LOG_FOLDER = "logs"
OUTPUT_FOLDER = "data/processed"
OUTPUT_FILE = "ottawa_accessibility_results.gpkg"
POP_FIELD = "pop_2016"

# Columns to always keep (except geometry, which will be detected automatically)
BASE_COLUMNS = ["dauid", "ctuid", "ctname", "tot_area_m", "pop_2016"]

# ----------------------------
# FUNCTIONS
# ----------------------------
def load_layer(gpkg_path, layer_name):
    try:
        gdf = gpd.read_file(gpkg_path, layer=layer_name)
        logging.info(f"Loaded {len(gdf)} records from '{layer_name}'")
        return gdf
    except Exception as e:
        logging.error(f"Failed to load layer '{layer_name}': {e}")
        return gpd.GeoDataFrame()

def validate_crs(gdf, target_crs=None):
    if gdf.empty:
        return gdf
    if target_crs and gdf.crs != target_crs:
        logging.info(f"Reprojecting to {target_crs}")
        gdf = gdf.to_crs(target_crs)
    return gdf

def calculate_accessible_population(da_gdf, parks_gdf, buffer_distance, pop_field):
    logging.info(f"Processing buffer: {buffer_distance} m")

    # Pre-calculate full DA area
    da_gdf["full_da_area"] = da_gdf.geometry.area

    # Create and dissolve park buffers
    parks_buffer = parks_gdf.geometry.buffer(buffer_distance).simplify(1)
    dissolved_buffer = parks_buffer.union_all()
    buffer_gdf = gpd.GeoDataFrame(geometry=[dissolved_buffer], crs=parks_gdf.crs)

    # Intersection
    da_intersect = gpd.overlay(da_gdf, buffer_gdf, how="intersection")

    accessible_col = f"accessible_pop_{buffer_distance}m"
    percent_col = f"percent_area_{buffer_distance}m"

    if da_intersect.empty:
        da_gdf[accessible_col] = 0
        da_gdf[percent_col] = 0
        return da_gdf

    # Area-based population calculation
    da_intersect["intersect_area"] = da_intersect.geometry.area
    da_intersect["area_ratio"] = (da_intersect["intersect_area"] / da_intersect["full_da_area"]).clip(upper=1.0)
    da_intersect["accessible_pop"] = da_intersect[pop_field] * da_intersect["area_ratio"]

    # Map back to original GDF
    pop_map = da_intersect.groupby("dauid")["accessible_pop"].sum()
    da_gdf[accessible_col] = da_gdf["dauid"].map(pop_map).fillna(0)

    area_map = da_intersect.groupby("dauid")["area_ratio"].sum() / 1  # sum ratio per DA (max 1)
    da_gdf[percent_col] = da_gdf["dauid"].map(area_map).fillna(0)

    return da_gdf

# ----------------------------
# MAIN PIPELINE
# ----------------------------
def main(buffer_list):
    logging.info("=== Ottawa Accessibility Analysis Started ===")

    # Load layers
    da_gdf = load_layer(INPUT_GPKG, DA_LAYER)
    parks_gdf = load_layer(INPUT_GPKG, PARKS_LAYER)

    # Preserve input CRS for output
    input_crs = da_gdf.crs

    # Ensure geometries are valid
    da_gdf = da_gdf[da_gdf.geometry.notna() & (da_gdf.geometry.area > 0)]
    parks_gdf = parks_gdf[parks_gdf.geometry.notna() & (parks_gdf.geometry.area > 0)]

    # Calculate accessible population and percent area for each buffer
    accessible_columns = []
    percent_columns = []
    for buffer_distance in buffer_list:
        da_gdf = calculate_accessible_population(da_gdf, parks_gdf, buffer_distance, POP_FIELD)
        accessible_columns.append(f"accessible_pop_{buffer_distance}m")
        percent_columns.append(f"percent_area_{buffer_distance}m")

    # Detect the geometry column dynamically
    geometry_col = da_gdf.geometry.name

    # Keep only selected columns + geometry
    final_columns = BASE_COLUMNS + accessible_columns + percent_columns + [geometry_col]
    final_gdf = da_gdf[final_columns].copy()
    final_gdf = final_gdf.set_geometry(geometry_col)
    final_gdf = final_gdf.set_crs(input_crs, allow_override=True)

    # Round population values to integers
    pop_columns = [POP_FIELD] + accessible_columns
    final_gdf[pop_columns] = final_gdf[pop_columns].round(0).astype(int)

    # Save results
    output_path = os.path.join(OUTPUT_FOLDER, OUTPUT_FILE)
    final_gdf.to_file(output_path, layer=DA_LAYER, driver="GPKG")
    logging.info(f"Saved results to {output_path}")

    # ----------------------------
    # LOG SUMMARY STATISTICS
    # ----------------------------
    total_pop = final_gdf[POP_FIELD].sum()
    logging.info(f"Total population: {int(total_pop)}")

    for buffer_distance in buffer_list:
        accessible_pop_sum = final_gdf[f"accessible_pop_{buffer_distance}m"].sum()
        avg_area_coverage = final_gdf[f"percent_area_{buffer_distance}m"].mean() * 100
        percent_serviced = (accessible_pop_sum / total_pop) * 100
        logging.info(f"--- Buffer {buffer_distance}m Summary ---")
        logging.info(f"Population with park access: {int(accessible_pop_sum)}")
        logging.info(f"Percentage population with access: {percent_serviced:.2f}%")
        logging.info(f"Average DA area coverage: {avg_area_coverage:.2f}%")

    logging.info("=== Accessibility Analysis Complete ===")

# ----------------------------
# RUN SCRIPT
# ----------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ottawa Accessibility Analysis using buffer distances")
    parser.add_argument(
        "--buffer",
        type=str,
        required=True,
        help="Comma-separated list of buffer distances in meters, e.g., 400,800"
    )
    args = parser.parse_args()

    # Parse buffer distances
    buffer_list = [int(b) for b in args.buffer.split(",") if b.strip().isdigit()]

    main(buffer_list)

