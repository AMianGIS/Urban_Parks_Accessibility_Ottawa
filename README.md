# Urban Parks Accessibility Analysis – Ottawa 🌳
 
## Project Summary

This project evaluates urban park accessibility across Ottawa using GIS spatial analysis.

The analysis estimates how much of the population lives within x walking distances (400m, 800m, 1600m) of public parks using area-weighted spatial overlays.

The workflow is fully automated through a modular Python GIS pipeline to ensure reproducibility.

## Objective

To quantify and visualize:

- The percentage of Ottawa’s population with access to parks
- The proportion of each Dissemination Area (DA: Canada’s smallest standard geographic unit for census data) covered by park buffers
- Spatial variation in accessibility across the city

## Preview 
![Ottawa Park Accessibility Map](data/outputs/map_preview.png)
Interactive choropleth showing the percentage of DA area within 400m of a public park.
## Spatial Methodology
### 1. Data Preparation

- Loaded multi-layer GeoPackage datasets
- Validated and reprojected all layers to EPSG:26918 (NAD83 / UTM Zone 18N)
- Cleaned invalid geometries
- Removed duplicate records

### 2️. Buffer-Based Accessibility Analysis

For each distance threshold (400m, 800m, 1600m):

- Generated park buffers
- Dissolved overlapping buffers
- Performed spatial intersection with DA polygons
- Calculated:
  - Area-weighted accessible population
  - Percent DA area covered by park buffers

Area-weighted population formula:

$$Accessible\ Population = Total\ DA\ Population \times \left( \frac{Intersect\ Area}{Total\ DA\ Area} \right)$$

### 3. Interactive GIS Mapping

- Generated choropleth maps using buffer-specific fields
- Dynamic buffer visualization
- Clean legend scaling
- Park layer overlay
- Exported as interactive HTML map

## Results (2016 Census Population ≈ 991,726)
| Buffer Distance | Population with Access | % Population with Access |
|-----------------|------------------------|--------------------------|
| 400 m           | 808,551                | 81.53%                   |
| 800 m           | 873,021                | 88.03%                   |
| 1600 m          | 901,172                | 90.87%                   |

Note: Findings indicate strong overall access, but spatial disparities exist. Access drops significantly in newer suburban developments in Kanata and Orleans compared to established neighborhoods like the Glebe.

## Requirements

- python 3.9+
- geopandas
- shapely
- fiona
- pandas
- folium

Install dependancies with:

```pip install -r requirements.txt```

## Project Structure

```
Urban_Parks_Accessibility/
│
├── data/
|   ├── outputs/    # Output Maps and Visuals
│   ├── raw/        # Original Census and Park files
│   └── processed/  # Cleaned layers & output Geopackage
│
├── logs/
│
├── scripts/
│   ├── data_cleaning.py               # Data validation & projection
│   ├── accessibility_analysis.py      # Buffer generation & area-weighting
│   └── mapping.py                     # Folium/Choropleth generation
│
├── run_pipeline.py                    # Main entry point
└── README.md

``` 
## Running the Full Pipeline

From the project root:

```python run_pipeline.py --crs 26918```

Optional custom buffers:

```python run_pipeline.py --crs 26918 --buffers 400, 800, 1600```

The pipeline will:
- Clean and standardize spatial data
- Run buffer-based overlay analysis
- Generate output GeoPackage layers
- Produce interactive maps
- Log all processing steps

## Notes
### Limitations & Future Considerations
While this model provides a robust baseline for park accessibility, several geographic factors influence real-world access:

- Euclidean vs. Network Distance: This analysis uses circular buffers however in reality, physical barriers such as the Queensway (Hwy 417), the Rideau River, or specialized transit corridors can significantly increase actual walking times.

- Park Quality & Amenities: The model treats all park polygons equally. It does not account for the type of recreation available (e.g. a small decorative green space vs. a large park with splash pads and sports fields).

- Homogeneous Population Distribution: Area-weighted interpolation assumes population is spread evenly across a Dissemination Area. In reality, population density may be concentrated in one corner of a DA, potentially over or under estimating access near park boundaries.

- Pedestrian Infrastructure: The analysis does not currently account for sidewalk availability, crosswalk safety, or terrain slope which impact accessibility for seniors and persons with disabilities.

### Future Enhancements
- Network Analysis: Integrate OpenStreetMap (OSM) road networks to calculate service areas based on actual walking paths.

- Gravity Modeling: Implement a spatial interaction model that weights parks by size or amenity count.

- Temporal Analysis: Compare 2016 Census data with more recent 2021/2026 releases to track how park development has kept pace with Ottawa’s rapid suburban growth.