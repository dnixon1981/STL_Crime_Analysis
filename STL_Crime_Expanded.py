#  Name:   STL_Crime_Expanded.py
#
#  Created: 03/18/2017
#
#  Purpose: Provide an interface to convert the STL police crime xls file to a table in a geodatabase and convert that table
#               to a spatial feature class that can then be added to the map to see where the crime events happened.
#               Then corilate mulitple crime classifications into similar symbology and do Kriging analysis modules.
#
#  Author:  Dave Nixon
##################################################

import arcpy
from arcpy import env
import os

arcpy.env.overwriteOutput = True

##env.workspace = r'H:\crime_data'
##outputGDB = r'H:\crime_data\output.gdb\Jan_Crime'

infile = arcpy.GetParameterAsText(0) #as CSV
outfile = arcpy.GetParameterAsText(1) #as GDB
csvPath = os.path.dirname(infile)
csvFile = os.path.basename(infile)
outName = os.path.splitext(csvFile)[0] + "_Points"
spRef = arcpy.SpatialReference("NAD 1983 StatePlane Missouri East FIPS 2401 (US Feet)")
NullCount = 0

if arcpy.Exists(outfile) == False:
     arcpy.AddMessage("Creating GDB...")
     arcpy.CreateFileGDB_management(os.path.dirname(outfile), os.path.basename(outfile))

arcpy.AddMessage("Copying Rows...")
arcpy.CopyRows_management(csvFile, outfile + '/' + os.path.splitext(csvFile)[0])

arcpy.AddMessage("Making Point Features...")
arcpy.MakeXYEventLayer_management( outfile + '/' + os.path.splitext(csvFile)[0], "XCoord", "YCoord", "Temp_Points", spRef, "")
arcpy.FeatureClassToFeatureClass_conversion("Temp_Points", outfile, outName)
pointsVar = outfile + '\\' + outName

arcpy.AddField_management(pointsVar, "Short_Desc", "TEXT", "", "", 20 , "Short Crime Description", "NULLABLE", "REQUIRED")
arcpy.AddField_management(pointsVar, "Cri_Weight", "LONG", "", "", 20, "Crime Weighting", "NULLABLE", "REQUIRED")
fields = ['Description','Short_Desc', 'Cri_Weight', 'XCoord', 'YCoord']

#updateCursor to combine multiple/various crime types into categories
with arcpy.da.UpdateCursor(pointsVar, fields) as cursor:
    for row in cursor:
        if "ASSAULT" in row[0] or "ASSLT" in row[0] or "ASLT" in row[0]:
            row[1] = 'ASSAULT'
            row[2] = 15
        elif "ARSON" in row[0]:
            row[1] = 'ARSON'
            row[2] = 13
        elif "THEFT" in row[0] or "LARCENY" in row[0] or "BURGLARY" in row[0] or "STOLEN" in row[0] or "STLG" in row[0] \
            or "ROBBERY" in row[0] or "LARC" in row[0] or "FRAUD" in row[0] or "FAILURE TO RETURN" in row[0] or "EMBEZZLEMENT" in row[0] or "FORGERY" in row[0]:
            row[1] = 'THEFT'
            row[2] = 9
        elif "DESTRUCTION" in row[0]:
            row[1] = 'DESTRUCTION'
            row[2] = 12
        elif "DISORDERLY" in row[0]:
            row[1] = 'DISORDERLY'
            row[2] = 7
        elif "DRUGS" in row[0] or "LIQUOR" in row[0]:
            row[1] = 'DRUGS-LIQUOR'
            row[2] = 8
        elif "DUI" in row[0]:
            row[1] = 'DUI'
            row[2] = 14
        elif "WEAPONS" in row[0]:
            row[1] = 'WEAPONS'
            row[2] = 11
        elif "RAPE" in row[0] or "SEX" in row[0] or "PROSTITUTION" in row[0] or "PORNAGRAPHY" in row[0]:
            row[1] = 'SEX OFFENSE'
            row[2] = 16
        elif "TRESPASSING" in row[0]:
            row[1] = 'TRESPASSING'
            row[2] = 6
        elif "LOITERING" in row[0]:
            row[1] = 'LOITERING'
            row[2] = 4
        elif "OBSTRUCT" in row[0]:
            row[1] = 'OBSTRUCTION'
            row[2] = 5
        elif "LEAVING" in row[0]:
            row[1] = 'LEAVING ACCIDENT'
            row[2] = 3
        elif "FAMILY" in row[0]:
            row[1] = 'CHILD ENDANGERMENT'
            row[2] = 10
        elif "HOMICIDE" in row[0]:
            row[1] = 'HOMICIDE'
            row[2] = 17
        else:
            row[1] = 'OTHER'
            row[2] = 2
        #need to remove weights from 0,0
        if row[3] == 0 or row[4] == 0:
             row[2] = None
             NullCount = NullCount + 1
        cursor.updateRow(row)

#Symbology voodoo magic, this was rough
SymbologyPath = os.path.dirname(os.path.realpath(__file__))
arcpy.AddMessage("Applying Symbology...")
mxd = arcpy.mapping.MapDocument("CURRENT")
df = arcpy.mapping.ListDataFrames(mxd,"*")[0]
newlayer = arcpy.mapping.Layer(pointsVar)
arcpy.mapping.AddLayer(df, newlayer,"TOP")
if arcpy.Exists(SymbologyPath + r"\Symbology_Template.lyr"):
    symbolLyr = SymbologyPath + r"\Symbology_Template.lyr" #Layer file with desired symbology
    lyr = arcpy.mapping.ListLayers(mxd, outName, df)[0]
    arcpy.ApplySymbologyFromLayer_management(lyr, symbolLyr) #Apply symbology
else:
    arcpy.AddMessage("Symbology cannot be applied, Missing Symbology_Template.lyr")

#and now we Kriging
# Set environment settings
env.workspace = csvPath

# Set local variables as Inputs
cellSize = arcpy.GetParameterAsText(3)
kModel = arcpy.GetParameterAsText(4)
kRadius = arcpy.GetParameterAsText(5)
KrigVar = outfile + '\\Krigout'
arcpy.AddMessage("Applying Kriging Model..." + str(NullCount) + " features excluded due to no location information")
if arcpy.CheckExtension("Spatial") == "Available":
     arcpy.CheckOutExtension("Spatial")
     # Execute Kriging
     #arcpy.Kriging_3d(inFeatures, field, outRaster, kModel, cellSize, kRadius, outVarRaster)
     arcpy.Kriging_3d(pointsVar, "Cri_Weight", KrigVar, kModel, cellSize, kRadius, outfile + '\\' + "outVar")
     arcpy.CheckInExtension("Spatial")
     KrigingLayer = arcpy.mapping.Layer(KrigVar)
     arcpy.mapping.AddLayer(df, KrigingLayer,"AUTO_ARRANGE")
else:
     arcpy.AddMessage("KRIGING NOT RUN: Spatial Analyst Extension unavailable, please confirm your license availability and retry")    
