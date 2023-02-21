"""
Purpose of this script is to allow the automated delineation of a watershed
utilizing pre-built catchments within the NHDPlus existing structure and a 
lat/long point. The script makes use of several open source geospatial Python 
packages, namely geopandas, fiona, and shapely and was designed for use in 
Python 3.
"""

import pandas as pd
import geopandas as gpd
import fiona, os
from shapely.geometry import Point
from dbfread import DBF
import numpy as np
from collections import deque, defaultdict


# User input
lat, long = -97.294, 32.737

VPU_zones = r'C:\temp\EPA Delineating Watersheds\Data\VPU_zones.shp'
nhdDir = r'C:\temp\EPA Delineating Watersheds\Data\NHDPlus'
interVPUtbl = pd.read_csv(r'C:\temp\EPA Delineating Watersheds\Data\interVPU.csv')
out_shape = r'C:\temp\EPA Delineating Watersheds\Example Output.shp'

# Convert lat/long to geodataframe
d = {'geometry': [Point(lat, long)]}
gdf = gpd.GeoDataFrame(d, crs="EPSG:4326")

# Read in VPU zones shapefile
in_VPU = gpd.read_file(VPU_zones)
gdf = gdf.to_crs(4269)

identify_VPU = gpd.sjoin(gdf, in_VPU, how="inner", op='intersects')
zone = identify_VPU[['VPU']].iloc[0]['VPU']

# select catchment file based on VPU zone of site
catchment_path = "NHDPlus%s/NHDPlus%s/NHDPlusCatchment/Catchment.shp" % (str(zone), str(zone))
catchment_shape = os.path.join(nhdDir, catchment_path)

# identify ComID of specific site
in_CATCHMENT = gpd.read_file(catchment_shape)
identify_FEATUREID = gpd.sjoin(gdf, in_CATCHMENT, how="inner", op='intersects')
comid_key = identify_FEATUREID[['FEATUREID']].iloc[0]['FEATUREID']

# create routing paths based on site
path = "NHDPlus%s/NHDPlus%s/NHDPlusAttributes/PlusFlow.dbf" % (str(zone), str(zone))
path = os.path.join(nhdDir, path)
db = DBF(path)
flow = pd.DataFrame(iter(db))[["TOCOMID", "FROMCOMID"]]
flow = flow[(flow.TOCOMID != 0) & (flow.FROMCOMID != 0)]

# check to see if out of zone values have FTYPE = 'Coastline'
path = "NHDPlus%s/NHDPlus%s/NHDSnapshot/Hydrography/NHDFlowline.csv" % (str(zone), str(zone))
path = os.path.join(nhdDir, path)
fls = pd.read_csv(path)
coastfl = fls.COMID[fls.FTYPE == "Coastline"]
flow = flow[~flow.FROMCOMID.isin(coastfl.values)]

# remove these FROMCOMIDs from the 'flow' table, there are three COMIDs here that won't get filtered out
remove = interVPUtbl.removeCOMs.values[interVPUtbl.removeCOMs.values != 0]
flow = flow[~flow.FROMCOMID.isin(remove)]

# find values that are coming from other zones and remove the ones that aren't in the interVPU table
out = np.setdiff1d(flow.FROMCOMID.values, fls.COMID.values)
out = out[np.nonzero(out)]
flow = flow[~flow.FROMCOMID.isin(np.setdiff1d(out, interVPUtbl.thruCOMIDs.values))]

# Now table is ready for processing and the UpCOMs dict can be created
fcom, tcom = flow.FROMCOMID.values, flow.TOCOMID.values
UpCOMs = defaultdict(list)
for i in range(0, len(flow), 1):
    from_comid = fcom[i]
    if from_comid == 0:
        continue
    else:
        UpCOMs[tcom[i]].append(from_comid)

# add IDs from UpCOMadd column if working in ToZone, forces the flowtable connection though not there
for interLine in interVPUtbl.values:
    if interLine[6] > 0 and interLine[2] == zone:
        UpCOMs[int(interLine[6])].append(int(interLine[0]))

# identify upstream ComIDs by walking through routing database
visited = set()
to_crawl = deque([comid_key])
while to_crawl:
    current = to_crawl.popleft()
    if current in visited:
        continue
    visited.add(current)
    node_children = set(UpCOMs[current])
    to_crawl.extendleft(node_children - visited)

# create output shapefile of upstream ComIDs
with fiona.open(catchment_shape) as input:
    meta = input.meta
    with fiona.open(out_shape, 'w', **meta) as output:
        for feature in input:
            if feature['properties']['FEATUREID'] in visited:
                output.write(feature)