"""
Purpose of this script is to allow the automated delineation of watersheds from
a Digital Elevation Model and a lat/long point. The script tool makes use of 
several tools from the Spatial Analyst Hydrology toolset and was designed for
arcpy utilizing Python 3.
"""

#import necessary modules
from arcpy import sa
from arcpy import env
from arcpy.sa import *
import os, arcpy

# User input
in_dem = r'C:\temp\EPA Delineating Watersheds\Data\elevation.tiff'
lat, long = -97.294, 32.737
output = r'C:\temp\EPA Delineating Watersheds\Example Output'

# Fill pits in DEM
outFill = sa.Fill(in_dem)
outFill.save(os.path.join(output, 'FilledDEM.tif'))

# Run flow direction tool and save raster
outFlowD = sa.FlowDirection(outFill, 'NORMAL', '', 'D8')
outFlowD.save(os.path.join(output, 'DEM_FlowD.tif'))

# Run flow accumulation tool and save raster
outFlowA = sa.FlowAccumulation(outFlowD,'', 'FLOAT', 'D8')
outFlowA.save(os.path.join(output, 'DEM_FlowA.tif'))

# Ceate shapefile of pour point
pt = arcpy.Point()
ptGeoms = []
pt.X = lat
pt.Y = long
ptGeoms.append(arcpy.PointGeometry(pt))
pourPoints = os.path.join(output, 'pourPoints.shp')
arcpy.CopyFeatures_management(ptGeoms, pourPoints)           

# Run Snap Pour Point tool and save raster
## set env settings so union of inputs are used
env.extent = "MAXOF" 
snapPts = sa.SnapPourPoint(pourPoints, outFlowA, 0, "FID")
snapPts.save(os.path.join(output, 'SnapPourPts.tif'))

# Run watershed tool and save raster
watershed = sa.Watershed(outFlowD,snapPts)
watershed.save(os.path.join(output, 'Delineated_watershed.tif'))

# Convert delineated raster to polygon
watershed_poly = os.path.join(output, 'Delineated_watershed.shp')
arcpy.RasterToPolygon_conversion("zone", watershed, "NO_SIMPLIFY", "FID")

# Clip flow accumulation/distance by delineated polygon 
# to reduce processing time
outFlowA_clip = ExtractByMask(outFlowA, watershed_poly, "INSIDE")
outFlowA_clip.save(os.path.join(output, 'DEM_FlowA_clipped.tif'))

outFlowD_clip = ExtractByMask(outFlowD, watershed_poly, "INSIDE")
outFlowD_clip.save(os.path.join(output, 'DEM_FlowD_clipped.tif'))

# Build a stream network and save raster
# Run Con Tool to build stream network
con_threshold = "50"
streamNetwork =sa.Con(outFlowA_clip, 1, "", "Value > "+con_threshold,)
streamNetwork.save(os.path.join(output, "streamNetwork.tif"))

# Use stream link tool and save raster
streamLink = sa.StreamLink(streamNetwork,outFlowD_clip)
streamLink.save(os.path.join(output, "streamLink.tif"))

# Use stream order tool and save raster
orderMethod = "STRAHLER"
streamOrder = sa.StreamOrder(streamNetwork, outFlowD_clip, orderMethod)
streamOrder.save(os.path.join(output, "streamOrder"))

# Convert Stream to Feature
streams = os.path.join(output, 'streams.shp')
sa.StreamToFeature(streamNetwork, outFlowD_clip, streams, 'SIMPLIFY')

# Run Basin tool and save raster
basin = sa.Basin(outFlowD_clip)
basin.save(os.path.join(output, 'basin.tif'))