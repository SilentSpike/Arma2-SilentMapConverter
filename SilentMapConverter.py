#-------------------------------------------------------------------------------
# Name:        SilentMapConverter
# Purpose:     Converts arma mission files into sqf script files.
#
# Author:      SilentSpike
#
# Created:     17/10/2014
# Copyright:   (c) SilentSpike 2014
# Licence:     GNU GPL v3.0
#-------------------------------------------------------------------------------
versionNum = "2.0.0"

#Import needed libraries
import os, re, sys

#Define side dictionary used to translate config to code
sideDict = {
    "EAST": "east",
    "WEST": "west",
    "GUER": "independent",
    "CIV": "civilian",
    "LOGIC": "sideLogic"
}

#Compile commonly used regex objects
reTopLevel = re.compile(r"^\tclass\s(Groups|Vehicles|Markers|Sensors).+?^\t\};",re.I|re.M|re.S)
reSubLevel = re.compile(r"^\t\tclass\sItem(\d+).+?^\t\t\};",re.I|re.M|re.S)

reGroupSide = re.compile(r"^\t{3}side=\"(.+)\";",re.I|re.M)
reGroupTop = re.compile(r"^\t{3}class\s(Vehicles|Waypoints).+?^\t{3}\};",re.I|re.M|re.S)
reGroupSub = re.compile(r"^\t{4}class\sItem(\d+).+?^\t{4}\};",re.I|re.M|re.S)

reUnitID = re.compile(r"id=(\d+)",re.I)
reUnitVar = re.compile(r"name=\"(.+)\";",re.I)
reUnitType = re.compile(r"vehicle=\"(.+)\";",re.I)
reUnitPos = re.compile(r"position\[\]=\{(.+)\};",re.I)

#Define common function for reporting malformed sqm file
def malformed(reason):
    return "// Error: SQM file is malformed, {0}".format(reason)

#Define processing functions for later (they all take a list of match objects)
def procGroups(groupsList):
    returnCode = "// ---Groups---\n"
    for group in groupsList:
        #Extract index of the group
        groupIndex = group.group(1)

        #Extract and verify group side
        groupSide = reGroupSide.search(group.group(0))
        if groupSide:
            groupSide = groupSide.group(1)
            if groupSide in sideDict:
                groupSide = sideDict[groupSide]
            else:
                return malformed("group {0} uses unknown side {1}".format(groupIndex,groupSide))
        else:
            return malformed("group {0} has no assigned side".format(groupIndex,groupSide))

        #Extract the units and waypoints subclasses of the group
        groupSections = list(reGroupTop.finditer(group.group(0)))
        if groupSections:
            groupUnits = []
            groupWaypoints = []
            for section in groupSections:
                if section.group(1) == "Vehicles":
                    groupUnits = list(reGroupSub.finditer(section.group(0)))
                elif section.group(1) == "Waypoints":
                    groupWaypoints = list(reGroupSub.finditer(section.group(0)))
        else:
            return malformed("group {0} has no subclasses".format(groupIndex))

        #Process the units of the group, verify that it has any
        if groupUnits:
            returnCode += "_group{0} = createGroup {1};\n".format(groupIndex,groupSide)
            for unit in groupUnits:
                unitIndex = unit.group(1)
                unitID = reUnitID.search(unit.group(0))
                unitVariable = reUnitVar.search(unit.group(0))
                unitType = reUnitType.search(unit.group(0))
                unitPos = reUnitPos.search(unit.group(0))

                #Determine variable to be used for unit, must have an ID number
                if unitID:
                    if unitVariable:
                        unitVariable = unitVariable.group(1)
                    else:
                        unitVariable = "_unit{0}".format(unitID.group(1))
                else:
                    return malformed("unit {0} in group {1} has no id number".format(unitIndex,groupIndex))

                if unitType:
                    unitType = unitType.group(1)
                    if unitPos:
                        #Make a list of coordinates as strings
                        unitPos = unitPos.group(1).split(",")
                        #Round all coordinates to 2 DP then convert to string
                        unitPos = ",".join([str(int(round(float(i)))) for i in unitPos])
                        returnCode += "{0} = _group{1} createUnit [\"{2}\",[{3}],[],0,\"\"];\n".format(unitVariable,groupIndex,unitType,unitPos)
                    else:
                        return malformed("unit {0} in group {1} has no position".format(unitIndex,groupIndex))
                else:
                    return malformed("unit {0} in group {1} has no classname".format(unitIndex,groupIndex))
        else:
            return malformed("group {0} has no units".format(groupIndex))

        #Process the waypoints of the group
        '''if groupWaypoints:
            for unit in groupUnits:
                unitPos ='''

    return returnCode

def procVehicles(vehiclesList):
    returnCode = "// ---Vehicles---\n"
    return returnCode

def procMarkers(markersList):
    returnCode = "// ---Markers---\n"
    return returnCode

def procTriggers(triggersList):
    returnCode = "// ---Triggers---\n"
    return returnCode
#-------------------------------------------------------------------------------
#Main

#Retrieve directory the program is ran in
if hasattr(sys, 'frozen'):
    #For use as an executable - sys.frozen only exists in the .exe
    scriptDirectory = os.path.dirname(os.path.realpath(sys.argv[0]))
else:
    #For use in script form
    scriptDirectory = os.path.dirname(os.path.realpath(__file__))

#Produce an array of sqm files in the directory
sqmFiles = []
for fileName in os.listdir(scriptDirectory):
    if fileName[len(fileName)-4:] == ".sqm":
        sqmFiles.append(fileName)

for fileName in sqmFiles:
    missionPath = scriptDirectory + "\\" + fileName
    #Make sure the file exists before opening to avoid errors
    if os.path.isfile(missionPath):
        # Initialise the output code with file header
        outputCode = "// Created by SMC v{0}\n".format(versionNum)

        #Open the file this way so that it closes automatically when done
        with open(missionPath) as missionFile:
            fileContents = missionFile.read()
            mainSections = []
            #Verify that the number of braces match
            if len(re.findall(r"{",fileContents)) == len(re.findall(r"}",fileContents)):
                # Extract the top-level sections of mission.sqm, returns an iterator of match objects so cast to list
                mainSections = list(reTopLevel.finditer(fileContents))
            else:
                outputCode += malformed("number of opening and closing braces isn't equal")
            #Clear file contents variable (unrequired from here)
            fileContents = None

        groupsCode = ""
        vehiclesCode = ""
        markersCode = ""
        triggersCode = ""
        if mainSections:
            for currentSection in mainSections:
                #All sections use the same classname system
                sectionList = list(reSubLevel.finditer(currentSection.group(0)))
                if currentSection.group(1) == "Groups":
                    groupsCode += procGroups(sectionList)
                elif currentSection.group(1) == "Vehicles":
                    vehiclesCode += procVehicles(sectionList)
                elif currentSection.group(1) == "Markers":
                    markersCode += procMarkers(sectionList)
                elif currentSection.group(1) == "Sensors":
                    triggersCode += procTriggers(sectionList)
        else:
            outputCode += malformed("doesn't contain any data to convert")

        #Verify that valid code was returned
        validCode = ""
        #If section was malformed then include error message at top
        for code in [markersCode,vehiclesCode,groupsCode,triggersCode]:
            if re.match(r"//\sError:",code,re.I):
                outputCode += code + "\n"
            else:
                validCode += code + "\n"

        #Combine valid sqf code from each section with output code
        outputCode += validCode

        #The written file should be created/overwritten in the same directory
        outputPath = scriptDirectory + "\\" + fileName[:len(fileName)-1] + "f"
        with open(outputPath, 'w') as outputFile:
            outputFile.write(outputCode)