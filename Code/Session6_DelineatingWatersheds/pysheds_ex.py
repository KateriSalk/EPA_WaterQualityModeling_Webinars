"""
Purpose of this script is to allow the automated delineation of watersheds from
a Digital Elevation Model and a lat/long point. The script tool makes use of 
several open source Python packages, namely PySheds, and was designed in Python
3.
"""

from pysheds.grid import Grid
import geopandas as gpd
import os

# User input
in_dem = r'C:\temp\EPA Delineating Watersheds\Data\elevation.tiff'
lat, long = -97.294, 32.737
output = r'C:\temp\EPA Delineating Watersheds\Example Output\pysheds'

# Set grid dimensions and read DEM
grid = Grid.from_raster(in_dem)
dem = grid.read_raster(in_dem)

# Fill pits in DEM
pit_filled_dem = grid.fill_pits(dem)

# Fill depressions in DEM
flooded_dem = grid.fill_depressions(pit_filled_dem)
    
# Resolve flats in DEM
inflated_dem = grid.resolve_flats(flooded_dem)
grid.to_raster(inflated_dem, os.path.join(output, 'FilledDEM.tif'))

# Determine D8 flow directions from DEM
## Specify directional mapping
dirmap = (64, 128, 1, 2, 4, 8, 16, 32)   
fdir = grid.flowdir(inflated_dem, dirmap=dirmap)
grid.to_raster(fdir, os.path.join(os.path.join(output, 'DEM_FlowD.tif')))

# Calculate flow accumulation
acc = grid.accumulation(fdir, dirmap=dirmap)
grid.to_raster(fdir, os.path.join(os.path.join(output, 'DEM_FlowA.tif')))

## Snap pour point to high accumulation cell
x_snap, y_snap = grid.snap_to_mask(acc > 1000, (lat, long))

# Delineate the catchment
catch = grid.catchment(x=x_snap, y=y_snap, fdir=fdir, dirmap=dirmap, xytype='coordinate')
catch = catch.astype(int)
grid.to_raster(catch, os.path.join(output, 'Delineated_watershed.tif'))

# Extract river network
grid.clip_to(catch)
clipped_catch = grid.view(catch)
branches = grid.extract_river_network(fdir, acc > 50, dirmap=dirmap)
def saveDict(dic,file):
    f = open(file,'w')
    f.write(str(dic))
    f.close()

#save geojson as separate file
streamNetwork = os.path.join(output, "streamNetwork.geojson")
saveDict(branches, streamNetwork)
gdf = gpd.read_file(streamNetwork)
gdf.to_file(streamNetwork[:-7]+'shp')
