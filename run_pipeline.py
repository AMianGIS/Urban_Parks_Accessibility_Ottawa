# run_pipeline.py
import os
import logging
import argparse
import time
from datetime import datetime

# ----------------------------
# CONFIG
# ----------------------------
LOG_FOLDER = "logs"
LOG_FILE = os.path.join(LOG_FOLDER, "pipeline.log")

# Ensure output folder exists
os.makedirs(LOG_FOLDER, exist_ok=True)

# ----------------------------
# LOGGING
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# ----------------------------
# ENSURE REQUIRED DIRECTORIES EXIST
# ----------------------------

from pathlib import Path

REQUIRED_DIRS = [
    Path("data/processed"),
    Path("data/outputs"),
    Path("logs")
]

for folder in REQUIRED_DIRS:
    folder.mkdir(parents=True, exist_ok=True)

# ----------------------------
# IMPORT PIPELINE SCRIPTS
# ----------------------------

from scripts.data_cleaning import main as data_cleaning_main
from scripts.accessibility_analysis import main as analysis_main
from scripts.mapping import create_combined_map, ACCESSIBILITY_GPKG, DA_LAYER, CLEANED_DATA_GPKG, PARKS_LAYER

import geopandas as gpd

# ----------------------------
# PIPELINE FUNCTION
# ----------------------------
def run_pipeline(crs="EPSG:3857", buffer_distances=[400, 800, 1600]):
    start_time = time.time()
    logging.info("=== Ottawa Accessibility Pipeline Started ===")

    # ----------------------------
    # Step 1: Data Cleaning
    # ----------------------------
    logging.info("Step 1: Running Data Cleaning")
    data_cleaning_main(output_crs=crs)
    logging.info("Data cleaning complete.")

    # ----------------------------
    # Step 2: Accessibility Analysis
    # ----------------------------
    logging.info(f"Step 2: Running Accessibility Analysis for buffers {buffer_distances}")

    analysis_main(buffer_list=buffer_distances)
    logging.info("Accessibility analysis complete.")

    # ----------------------------
    # Step 3: Mapping
    # ----------------------------
    logging.info("Step 3: Generating Maps")
    da_gdf = gpd.read_file(ACCESSIBILITY_GPKG, layer=DA_LAYER)
    parks_gdf = gpd.read_file(CLEANED_DATA_GPKG, layer=PARKS_LAYER)

    create_combined_map(da_gdf, parks_gdf)
    logging.info("Mapping complete.")
    total_time = time.time() - start_time
    logging.info(f"=== Pipeline Finished Successfully in {total_time:.2f} seconds ===")

# ----------------------------
# CLI ENTRY
# ----------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run full Ottawa accessibility pipeline")
    parser.add_argument(
        "--crs",
        type=str,
        default="EPSG:4326",
        help="CRS for all processing steps"
    )
    parser.add_argument(
        "--buffers",
        nargs="+",
        type=int,
        default=[400, 800, 1600],
        help="Buffer distances (meters) for accessibility analysis"
    )
    args = parser.parse_args()

    run_pipeline(crs=args.crs, buffer_distances=args.buffers)