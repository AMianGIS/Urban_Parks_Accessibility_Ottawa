# mapping.py

import geopandas as gpd
import folium
import branca.colormap as cm
from folium.features import GeoJsonTooltip
import os

# ----------------------------
# CONFIG
# ----------------------------
ACCESSIBILITY_GPKG = "data/processed/ottawa_accessibility_results.gpkg"
DA_LAYER = "dissemination_areas"

CLEANED_DATA_GPKG = "data/processed/ottawa_accessibility_data.gpkg"
PARKS_LAYER = "parks"

OUTPUT_FOLDER = "data/outputs"
POP_FIELD = "pop_2016"


# ----------------------------
# FUNCTION
# ----------------------------
def create_combined_map(da_gdf, parks_gdf):
    # ----------------------------
    # Detect buffer distances
    # ----------------------------
    buffer_distances = sorted(
        int(col.replace("percent_area_", "").replace("m", ""))
        for col in da_gdf.columns
        if col.startswith("percent_area_") and col.endswith("m") and col.replace("percent_area_", "").replace("m", "").isdigit()
    )

    if not buffer_distances:
        raise ValueError("No buffer columns found in dataset.")

    print(f"Detected buffers: {buffer_distances}")

    # ----------------------------
    # Compute map center (WGS84)
    # ----------------------------
    centroid_projected = da_gdf.geometry.centroid
    centroid_web = gpd.GeoSeries(centroid_projected, crs=da_gdf.crs).to_crs(epsg=4326)

    center_lat = centroid_web.y.mean()
    center_lon = centroid_web.x.mean()

    # Convert to WGS84
    da_web = da_gdf.to_crs(epsg=4326)
    parks_web = parks_gdf.to_crs(epsg=4326)

    # ----------------------------
    # Create base map
    # ----------------------------
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles="OpenStreetMap"
    )

    # ----------------------------
    # Add buffer layers with tooltips
    # ----------------------------
    for i, buffer_distance in enumerate(buffer_distances):
        percent_col = f"percent_area_{buffer_distance}m"
        accessible_col = f"accessible_pop_{buffer_distance}m"

        # Convert to percent
        da_web[percent_col] = da_web[percent_col] * 100

        # Create feature group
        layer = folium.FeatureGroup(
            name=f"{buffer_distance}m Access",
            show=(i == 0)
        )

        # Colour scale for choropleth
        min_val = da_web[percent_col].min()
        max_val = da_web[percent_col].max()
        colormap = cm.linear.YlGn_09.scale(min_val, max_val)
        colormap.caption = f"% Area within Distance m of Parks"

        def style_function(feature, col=percent_col):
            value = feature["properties"][col]
            return {
                "fillColor": colormap(value),
                "color": "black",
                "weight": 0.3,
                "fillOpacity": 0.7
            }

        tooltip = GeoJsonTooltip(
            fields=["ctname", POP_FIELD, accessible_col, percent_col],
            aliases=[
                "Census Tract:",
                "Total Population:",
                f"Accessible Population ({buffer_distance}m):",
                "% Area Covered:"
            ],
            localize=True
        )

        folium.GeoJson(
            da_web,
            style_function=style_function,
            tooltip=tooltip
        ).add_to(layer)

        layer.add_to(m)

        # Add legend only for the first (default) buffer
        if i == 0:
            colormap.add_to(m)

    # ----------------------------
    # Add Parks overlay
    # ----------------------------
    parks_clean = parks_web[[parks_web.geometry.name]].copy()

    parks_layer = folium.FeatureGroup(name="Parks", show=False)

    folium.GeoJson(
        parks_clean,
        style_function=lambda x: {
            "fillColor": "#2b8cbe",
            "color": "#08519c",
            "weight": 1,
            "fillOpacity": 0.6
        }
    ).add_to(parks_layer)

    parks_layer.add_to(m)

    # ----------------------------
    # Add Layer Control
    # ----------------------------
    folium.LayerControl(collapsed=False).add_to(m)

    # ----------------------------
    # Save Map
    # ----------------------------
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    output_path = os.path.join(OUTPUT_FOLDER, "park_accessibility_interactive.html")
    m.save(output_path)
    print(f"Saved combined interactive map: {output_path}")


# ----------------------------
# MAIN
# ----------------------------
if __name__ == "__main__":
    da_gdf = gpd.read_file(ACCESSIBILITY_GPKG, layer=DA_LAYER)
    parks_gdf = gpd.read_file(CLEANED_DATA_GPKG, layer=PARKS_LAYER)

    create_combined_map(da_gdf, parks_gdf)