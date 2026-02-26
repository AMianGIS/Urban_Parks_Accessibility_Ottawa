# data_cleaning.py
import geopandas as gpd
import os
import logging
from datetime import datetime
from pyproj import CRS
import fiona
import argparse

# ----------------------------
# CONFIGURATION
# ----------------------------
LOG_FOLDER = "logs"
OUTPUT_FOLDER = "data/processed"
OUTPUT_FILE = "ottawa_accessibility_data.gpkg"

INPUT_FILES = {
    "parks": "data/raw/Ottawa_Parks_and_Greenspace.gpkg",
    "sidewalks": "data/raw/Ottawa_Pedestrian_Network.gpkg",
    "dissemination_areas": "data/raw/Ottawa_DAs.gpkg"
}

# Fields to keep for DA centroids
DA_FIELDS_TO_KEEP = ["fid", "dauid", "ctuid", "ctname", "pop_2016", "popdensqkm", "tot_areakm"]

# Fields to keep for park centroids
PARK_FIELDS_TO_KEEP = ["fid","park_id","name","park_type","ward", "ward_name", "accessible", "park_categ"]


# ----------------------------
# FUNCTIONS
# ----------------------------
def list_layers(path):
    try:
        layers = fiona.listlayers(path)
        logging.info(f"Available layers in {path}: {layers}")
        return layers
    except Exception as e:
        logging.error(f"Cannot list layers in {path}: {e}")
        return []


def load_gdf_smart(path, desired_name=None):
    if not os.path.exists(path):
        logging.error(f"Input file does not exist: {path}")
        return gpd.GeoDataFrame()

    layers = list_layers(path)
    layer_to_use = desired_name if desired_name in layers else (layers[0] if layers else None)
    if not layer_to_use:
        logging.error(f"No layers found in {path}")
        return gpd.GeoDataFrame()
    if desired_name and layer_to_use != desired_name:
        logging.warning(f"Desired layer '{desired_name}' not found; using '{layer_to_use}' instead")

    try:
        gdf = gpd.read_file(path, layer=layer_to_use)
        logging.info(f"Loaded {len(gdf)} records from layer '{layer_to_use}' in {path}")
        return gdf
    except Exception as e:
        logging.error(f"Failed to load {path} layer '{layer_to_use}': {e}")
        return gpd.GeoDataFrame()


def validate_crs(gdf, name, output_crs):
    if gdf.empty:
        return gdf
    if CRS(gdf.crs) != CRS(output_crs):
        logging.info(f"Reprojecting {name} from {gdf.crs} to {output_crs}")
        gdf = gdf.to_crs(output_crs)
    return gdf


def clean_columns(gdf):
    if gdf.empty:
        return gdf
    gdf.columns = [c.lower().replace(" ", "_") for c in gdf.columns]
    return gdf


def fix_geometries(gdf, name):
    if gdf.empty:
        return gdf
    invalid_count = (~gdf.is_valid).sum()
    if invalid_count > 0:
        logging.info(f"Fixing {invalid_count} invalid geometries in {name}")
        try:
            gdf["geometry"] = gdf.buffer(0)
        except Exception as e:
            logging.error(f"Failed to fix geometries in {name}: {e}")
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()]
    return gdf


def remove_duplicates(gdf, subset_cols, name):
    if gdf.empty:
        return gdf
    subset_cols_existing = [c for c in subset_cols if c in gdf.columns]
    if not subset_cols_existing:
        logging.warning(f"No valid columns found for duplicates removal in {name}")
        return gdf
    before = len(gdf)
    gdf = gdf.drop_duplicates(subset=subset_cols_existing)
    logging.info(f"Removed {before - len(gdf)} duplicate records from {name}")
    return gdf

def create_centroids(gdf, name, fields_to_keep):
    """
    Creates centroid points from polygon layers and keeps only selected fields.
    Returns a GeoDataFrame of centroid points.
    """
    if gdf.empty:
        logging.warning(f"{name} GeoDataFrame is empty.")
        return gpd.GeoDataFrame()

    try:
        # Keep only polygon geometries
        gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()

        # Create centroid geometry
        gdf["centroid"] = gdf.geometry.centroid

        # Keep only requested fields that exist
        valid_fields = [f for f in fields_to_keep if f in gdf.columns]

        gdf_centroid = gdf[valid_fields + ["centroid"]].copy()
        gdf_centroid = gdf_centroid.set_geometry("centroid")

        logging.info(f"Created centroid points for {name}")
        return gdf_centroid

    except Exception as e:
        logging.error(f"Failed to create centroids for {name}: {e}")
        return gpd.GeoDataFrame()


# ----------------------------
# MAIN PIPELINE
# ----------------------------
def main(output_crs):
    logging.info("=== Ottawa Accessibility Preprocessing Started ===")

    # Load datasets
    parks_gdf = load_gdf_smart(INPUT_FILES["parks"], desired_name="Parks")
    sidewalks_gdf = load_gdf_smart(INPUT_FILES["sidewalks"], desired_name="Sidewalks/Roads")
    da_gdf = load_gdf_smart(INPUT_FILES["dissemination_areas"], desired_name="Dissemination Areas")

    # Validate CRS
    parks_gdf = validate_crs(parks_gdf, "Parks", output_crs)
    sidewalks_gdf = validate_crs(sidewalks_gdf, "Sidewalks/Roads", output_crs)
    da_gdf = validate_crs(da_gdf, "Dissemination Areas", output_crs)

    # Clean column names
    parks_gdf = clean_columns(parks_gdf)
    sidewalks_gdf = clean_columns(sidewalks_gdf)
    da_gdf = clean_columns(da_gdf)

    # Fix invalid geometries
    parks_gdf = fix_geometries(parks_gdf, "Parks")
    sidewalks_gdf = fix_geometries(sidewalks_gdf, "Sidewalks/Roads")
    da_gdf = fix_geometries(da_gdf, "Dissemination Areas")

    # Remove duplicates
    parks_gdf = remove_duplicates(parks_gdf, ["park_id"], "Parks")
    sidewalks_gdf = remove_duplicates(sidewalks_gdf, ["fid"], "Sidewalks/Roads")
    da_gdf = remove_duplicates(da_gdf, ["dauid"], "Dissemination Areas")

    # Create DA centroids
    da_centroids = create_centroids(da_gdf,"Dissemination Areas",DA_FIELDS_TO_KEEP)

    # Create Park centroids
    parks_centroids = create_centroids(parks_gdf,"Parks",PARK_FIELDS_TO_KEEP)

    # ----------------------------
    # SAVE TO GEOPACKAGE
    # ----------------------------
    gpkg_path = os.path.join(OUTPUT_FOLDER, OUTPUT_FILE)
    logging.info(f"Saving all datasets to GeoPackage: {gpkg_path}")

    # Parks
    if not parks_gdf.empty:
        parks_gdf = parks_gdf.set_geometry("geometry")
        parks_gdf.to_file(gpkg_path, layer="parks", driver="GPKG", mode="w")
        logging.info(f"Saved layer 'parks' with {len(parks_gdf)} records")

    # Sidewalks
    if not sidewalks_gdf.empty:
        sidewalks_gdf = sidewalks_gdf.set_geometry("geometry")
        sidewalks_gdf.to_file(gpkg_path, layer="sidewalks", driver="GPKG", mode="a")
        logging.info(f"Saved layer 'sidewalks' with {len(sidewalks_gdf)} records")

    # DA polygons
    if not da_gdf.empty:
        # Drop centroid if present
        if "centroid" in da_gdf.columns:
            da_gdf = da_gdf.drop(columns=["centroid"])
        da_gdf = da_gdf.set_geometry("geometry")
        da_gdf.to_file(gpkg_path, layer="dissemination_areas", driver="GPKG", mode="a")
        logging.info(f"Saved layer 'dissemination_areas' with {len(da_gdf)} records")

    # Save DA centroids
    if not da_centroids.empty:
        if "geometry" in da_centroids.columns:
            da_centroids = da_centroids.drop(columns=["geometry"])
        da_centroids = da_centroids.set_geometry("centroid")
        da_centroids.to_file(
            gpkg_path,
            layer="dissemination_areas_centroids",
            driver="GPKG",
            mode="a"
        )
        logging.info(f"Saved DA centroids ({len(da_centroids)})")

    # Save Park centroids
    if not parks_centroids.empty:
        if "geometry" in parks_centroids.columns:
            parks_centroids = parks_centroids.drop(columns=["geometry"])
        parks_centroids = parks_centroids.set_geometry("centroid")
        parks_centroids.to_file(
            gpkg_path,
            layer="parks_centroids",
            driver="GPKG",
            mode="a"
        )
        logging.info(f"Saved park centroids ({len(parks_centroids)})")

    logging.info("=== Preprocessing Complete ===")


# ----------------------------
# RUN SCRIPT
# ----------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess Ottawa GIS data (clean centroids)")
    parser.add_argument(
        "--crs",
        type=str,
        default="EPSG:4326",
        help="Output coordinate system (e.g., EPSG:4326)"
    )
    args = parser.parse_args()
    main(args.crs)