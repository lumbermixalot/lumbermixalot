# -*- coding: utf-8 -*-

"""
Copyright (c) 2019 Galib F. Arrieta

Permission is hereby granted, free of charge, to any person obtaining a copy of 
this software and associated documentation files (the "Software"), to deal in 
the Software without restriction, including without limitation the rights to 
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies 
of the Software, and to permit persons to whom the Software is furnished to do 
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE 
SOFTWARE.
"""
import bpy
from mathutils import *
import numpy as np
import math
import sys
import os

#The modules of lumbermixalot
from commonmixalot import Status
import commonmixalot as cmn
import lowpass


#Directory for CSV files generated if debugging is enabled.
#Customize to your needs.
CSV_OUTPUT_DIR = sys.path[-1]

def _AddSiblingRootBone(obj, boneName):
    hasOnlyOneRootBone = cmn.HasOnlyOneRootBone(obj)
    hasRootMotionBone = cmn.HasRootMotionBone(obj, boneName)
    if hasOnlyOneRootBone and hasRootMotionBone:
        raise Exception("Most likely this asset was already processed because it contains a single 'root' bone")
        return
    if hasRootMotionBone:
        print("Armature already had root motion bone")
        return
    #Enter Edit Mode
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    ebones = obj.data.edit_bones

    #Create the new root bone
    newRootBone = ebones.new(boneName)
    boneSize = 1.0/obj.scale[0]
    newRootBone.tail = (0.0, -boneSize, 0)

    #Exit edit mode to save bones so they can be used in pose mode
    bpy.ops.object.mode_set(mode='OBJECT')

    print("Added bone '{}' as sibling of the current root bone.".format(boneName))


def _MakeParentBone(obj, parentBoneName, childBoneName):
    #Enter Edit Mode
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    ebones = obj.data.edit_bones
    rootBoneIndex = ebones.find(parentBoneName)
    childBoneIndex = ebones.find(childBoneName)
    print("root bone index = {}, child bone index = {}".format(rootBoneIndex, childBoneIndex))
    ebones[childBoneIndex].parent = ebones[rootBoneIndex]
    
    #Exit edit mode to save bones so they can be used in pose mode
    bpy.ops.object.mode_set(mode='OBJECT')


def _ValidateKeyFrameVectorName(vectorName):
    VECTOR_NAMES = ('location', 'rotation_quaternion', 'scale')
    if vectorName not in VECTOR_NAMES:
        raise Exception("'{}' is an invalid vectorName. It should be one of: {}".format(vectorName, VECTOR_NAMES))


def _BuildDataPath(boneName, vectorName):
    return "pose.bones[\"{}\"].{}".format(boneName, vectorName)


def _GetKeyFrames(actionObj, boneName, vectorName, vectorComponentIndex):
    #mainAction = bpy.data.actions[0] #Armature|mixamo.com|Layer0""
    #for curve in mainAction.fcurves:
    #    print(curve.data_path)
    #    pose.bones["Hips"].location
    #    pose.bones["Hips"].location
    #    pose.bones["Hips"].location
    #    pose.bones["Hips"].rotation_quaternion
    #    pose.bones["Hips"].rotation_quaternion
    #    pose.bones["Hips"].rotation_quaternion
    #    pose.bones["Hips"].rotation_quaternion
    #    pose.bones["Hips"].scale
    #    pose.bones["Hips"].scale
    #    pose.bones["Hips"].scale
    _ValidateKeyFrameVectorName(vectorName)
    dataPath = _BuildDataPath(boneName, vectorName)
    fcurve = actionObj.fcurves.find(dataPath, index=vectorComponentIndex)
    return fcurve


def _GetNumKeyFrames(actionObj, boneName, vectorName, vectorComponentIndex):
    fcurve = _GetKeyFrames(actionObj, boneName, vectorName, vectorComponentIndex)
    return len(fcurve.keyframe_points)


def _InsertKeyFrames(armatureObj, actionObj, boneName, vectorName, vectorComponentIndex):
    fcurve = _GetKeyFrames(actionObj, boneName, vectorName, vectorComponentIndex)
    dataPath = _BuildDataPath(boneName, vectorName)
    if fcurve is not None:
        print("The fcurve {} at index {} already exists".format(dataPath, vectorComponentIndex))
        return fcurve
    if not armatureObj.keyframe_insert(dataPath, index=vectorComponentIndex, frame=1):
        print("Failed to insert new empty KeyFrames at path {} index {}".format(dataPath, vectorComponentIndex))
        return None
    return _GetKeyFrames(actionObj, boneName, vectorName, vectorComponentIndex)


def _RemoveAllKeyFrames(fcurve, fromFrameIndex=0):
    targetLength = fromFrameIndex
    while len(fcurve.keyframe_points) > targetLength:
        kfp = fcurve.keyframe_points[fromFrameIndex]
        fcurve.keyframe_points.remove(kfp, fast=True)


def _CopyKeyFrame(dstKfp, srcKfp):
    dstKfp.amplitude = srcKfp.amplitude
    dstKfp.back = srcKfp.back
    dstKfp.co = srcKfp.co
    dstKfp.easing = srcKfp.easing
    dstKfp.handle_left = srcKfp.handle_left
    dstKfp.handle_left_type = srcKfp.handle_left_type
    dstKfp.handle_right = srcKfp.handle_right
    dstKfp.handle_right_type = srcKfp.handle_right_type
    dstKfp.interpolation = srcKfp.interpolation
    dstKfp.period = srcKfp.period
    dstKfp.select_control_point = srcKfp.select_control_point
    dstKfp.select_left_handle = srcKfp.select_left_handle
    dstKfp.select_right_handle = srcKfp.select_right_handle


def _CopyKeyFrames(dstFcurve, srcFcurve, defaultValue=0.0, emptySrc=False):
    #Clear all existing keyframes in dstFcurve.
    keyFramesCount = len(srcFcurve.keyframe_points)
    if keyFramesCount < 1:
        print("The source fcurve was already empty")
        return
    _RemoveAllKeyFrames(dstFcurve)
    print("Removed all previous keyframes in destination Fcurve")
    dstFcurve.keyframe_points.add(keyFramesCount)
    for frameIndex in range(keyFramesCount):
        srcKfp = srcFcurve.keyframe_points[frameIndex]
        dstKfp = dstFcurve.keyframe_points[frameIndex]
        _CopyKeyFrame(dstKfp, srcKfp)
        dstKfp.co[1] = defaultValue #srcKfp.co[1] * scaleFactor
    print("Copied {} keyframes from source to destination with defaultValue {}".format(keyFramesCount, defaultValue))
    if not emptySrc:
        return
    _RemoveAllKeyFrames(srcFcurve, 1)
    print("Removed keyframes from source")


def _GetBBOX(ObjBbox):
    vecMin = Vector(ObjBbox[0])
    vecMax = Vector(ObjBbox[0])
    #print("BBOX:")
    for rawVec in ObjBbox:
        v = Vector(rawVec)
        #print(v.x, v.y, v.z)
        if v.x < vecMin.x:
            vecMin.x = v.x
        if v.y < vecMin.y:
            vecMin.y = v.y
        if v.z < vecMin.z:
            vecMin.z = v.z
        if v.x > vecMax.x:
            vecMax.x = v.x
        if v.y > vecMax.y:
            vecMax.y = v.y
        if v.z > vecMax.z:
            vecMax.z = v.z
    #print("BBOX: min=({},{},{}), max=({},{},{})".format(vecMin.x, vecMin.y, vecMin.z, vecMax.x, vecMax.y, vecMax.z))
    return (vecMin, vecMax)


def _GetBBOXBaseCenter(vecMin, vecMax):
    x = (vecMax.x + vecMin.x) * 0.5
    y = (vecMax.y + vecMin.y) * 0.5
    z = vecMin.z
    return Vector([x, y, z])


def _DumpBone(matrixWorld, bone):
    print("Head", bone.head)
    print("Tail", bone.tail)
    print("Location", bone.location)
    worldLocation = (matrixWorld @ bone.matrix).to_translation()
    print("World Location", worldLocation)


#Returns an array of Vector. Each vector is the world location of the center of the bottom plane
# of the bounding box  per key frame.
# @sceneObj (bpy.types.Scene)
# @obj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
# @keyFrameStart (int) Starting Keyframe index
# @keyFrameEnd (int) Ending keyframe index
def _GetBBoxWorldLocations(sceneObj, obj, keyFrameStart, keyFrameEnd):
    worldMatrix = obj.matrix_world
    vectorList = []
    for frameIdx in range(keyFrameStart, keyFrameEnd + 1):
        sceneObj.frame_set(frameIdx)
        (vecMin, vecMax) = _GetBBOX(obj.bound_box)
        vecMin = obj.matrix_world @ vecMin
        vecMax = obj.matrix_world @ vecMax
        v = _GetBBOXBaseCenter(vecMin, vecMax)
        vectorList.append(v)
    return vectorList


#Returns a list of Vector.
def _GetBoneLocalLocationsFromFcurves(boneName):
    retList = []

    actionObj = bpy.data.actions[0]
    fcurveX = _GetKeyFrames(actionObj, boneName, 'location', 0)
    fcurveY = _GetKeyFrames(actionObj, boneName, 'location', 1)
    fcurveZ = _GetKeyFrames(actionObj, boneName, 'location', 2)
    lenX = len(fcurveX.keyframe_points)
    lenY = len(fcurveY.keyframe_points)
    lenZ = len(fcurveZ.keyframe_points)
    if (lenX != lenY) or (lenX != lenZ):
        print("Was expecting fcurves of the same length. lenX={}, lenY={}, lenZ={}".format(lenX, lenY, lenZ))
        return retList
    keyFramesCount = lenX
    print(lenX)
    if keyFramesCount < 1:
        print("The fcurves are empty!")
        return retList

    for frameIndex in range(keyFramesCount):
        KfpX = fcurveX.keyframe_points[frameIndex]
        KfpY = fcurveY.keyframe_points[frameIndex]
        KfpZ = fcurveZ.keyframe_points[frameIndex]
        v = Vector( (KfpX.co[1], KfpY.co[1], KfpZ.co[1]) )
        retList.append(v)

    return retList


#Returns a list of Quaternions
def _GetBoneLocalQuaternionsFromFcurves(boneName):
    retList = []

    actionObj = bpy.data.actions[0]
    fcurveW = _GetKeyFrames(actionObj, boneName, 'rotation_quaternion', 0)
    fcurveX = _GetKeyFrames(actionObj, boneName, 'rotation_quaternion', 1)
    fcurveY = _GetKeyFrames(actionObj, boneName, 'rotation_quaternion', 2)
    fcurveZ = _GetKeyFrames(actionObj, boneName, 'rotation_quaternion', 3)

    lenW = len(fcurveW.keyframe_points)
    lenX = len(fcurveX.keyframe_points)
    lenY = len(fcurveY.keyframe_points)
    lenZ = len(fcurveZ.keyframe_points)
    if (lenW != lenX) or (lenW != lenY) or (lenW != lenZ):
        print("Was expecting fcurves of the same length. lenW={}, lenX={}, lenY={}, lenZ={}".format(lenW, lenX, lenY, lenZ))
        return retList
    keyFramesCount = lenW
    print("Number of Quaternion keyframes in bone {} = {}".format(boneName, lenW))
    if keyFramesCount < 1:
        print("The fcurves are empty!")
        return retList

    for frameIndex in range(keyFramesCount):
        KfpW = fcurveW.keyframe_points[frameIndex]
        KfpX = fcurveX.keyframe_points[frameIndex]
        KfpY = fcurveY.keyframe_points[frameIndex]
        KfpZ = fcurveZ.keyframe_points[frameIndex]
        q = Quaternion((KfpW.co[1], KfpX.co[1], KfpY.co[1], KfpZ.co[1]))
        retList.append(q)

    return retList


#Returns a list of Eulers
def _GetEulerListFromQuaternionsList(localQuaternionsList):
    retList = []
    for q in localQuaternionsList:
        e = q.to_euler('XYZ')
        retList.append(e)
    return retList


#@vectorList is a list of MathUtils.Vector
#@matrix is a MathUtils.Matrix
#returns a list of MathUtils.Vector
def _TransformVectorList(vectorList, matrix):
    retList = []
    for v in vectorList:
        transformedV = matrix @ v
        retList.append(transformedV)
    return retList


#Returns a list of quaternions
def _TransformEulersList(eulersList, matrix):
    retList = []
    for e in eulersList:
        mat44 = e.to_matrix().to_4x4()
        newRotMatix = matrix @ mat44
        q = newRotMatix.to_quaternion()
        retList.append(q)
    return retList


def _AddEulerToList(eulersList, eulerDelta):
    retList = []
    for e in eulersList:
        newEuler = e.copy()
        newEuler.x += eulerDelta.x
        newEuler.y += eulerDelta.y
        newEuler.z += eulerDelta.z
        retList.append(newEuler)
    return retList


#Returns a 4x4 matrix typical of the default
#Blender Bone orientation with respect to
# an armature parent object. 
def _GetBlenderDefaultBoneMatrix44():
    #X is X, Y is Z, Z is -Y.
    return Matrix(((1.0, 0.0,  0.0, 0.0),
                   (0.0, 0.0, -1.0, 0.0),
                   (0.0, 1.0,  0.0, 0.0),
                   (0.0, 0.0,  0.0, 1.0)))


#Returns a tuple (transformMatrix, transformedList)
#   Where transformMatrix is a 4x4 world Matrix.
#   transformedList is a new list of Vector.
#@obj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
#@vectorList (list of Vector)
def _TransformVectorListByDefaultBoneWorldMatrix(obj, vectorList):
    worldMatrix = obj.matrix_world
    boneMatrix = _GetBlenderDefaultBoneMatrix44()
    transformMatrix = worldMatrix @ boneMatrix
    transformedList = _TransformVectorList(vectorList, transformMatrix)
    return transformMatrix, transformedList


#Returns a tuple (localLocationsList, transformMatrix, worldLocationsList)
# This is a simplified function because it doesn't traverse the bone hierarchy
# at all. It assummes @boneName is the name of the first child bobe of the
# armature @obj.
#@obj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
#@boneName (string). Name of the current root bone as originated by Mixamo.
#   The root bone from Mixamo is usually named "Hips".
def _GetBoneLocations(obj, boneName):
    localLocations = _GetBoneLocalLocationsFromFcurves(boneName)
    transformMatrix, worldLocations = _TransformVectorListByDefaultBoneWorldMatrix(
        obj, localLocations)
    return (localLocations, transformMatrix, worldLocations)


#@quaternionsList is a list of MathUtils.Quaternion
#@transformMatrix is a 4x4 MathUtils.Matrix
#returns a list of MathUtils.Quaternion
def _TransformQuaternionsList(quaternionsList, transformMatrix):
    retList = []
    for q in quaternionsList:
        rotMat = q.to_matrix().to_4x4()
        newMat = transformMatrix @ rotMat
        worldQ = newMat.to_quaternion()
        retList.append(worldQ)
    return retList


#Returns a tuple (transformMatrix, transformedList)
#   Where transformMatrix is a 4x4 world Matrix.
#   transformedList is a new list of Quaternion.
#@obj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
#@quaternionsList (list of Quaternion)
def _TransformQuaternionListByDefaultBoneWorldMatrix(obj, quaternionsList):
    worldMatrix = obj.matrix_world
    boneMatrix = _GetBlenderDefaultBoneMatrix44()
    transformMatrix = worldMatrix @ boneMatrix
    transformedList = _TransformQuaternionsList(quaternionsList,
                                                transformMatrix)
    return transformMatrix, transformedList


#Returns a tuple (localQuaternionsList, transformMatrix, worldQuaternionsList,
#                 worldEulersList)
#   Where:
#   localQuaternionsList is a list of Quaternion with local bone data as
#       extracted from FCurves.
#   transformMatrix A 4x4 World transform Matrix used to transform the
#       Quaternions in localQuaternionsList.
#   worldQuaternionsList The transformed Quaternions, now in World coordinates.
#   worldEulersList Euler list version of worldQuaternionsList.
# This is a simplified function because it doesn't traverse the bone hierarchy
# at all. It assummes @boneName is the name of the first child bobe of the
# armature @obj.
#@obj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
#@boneName (string). Name of the current root bone as originated by Mixamo.
#   The root bone from Mixamo is usually named "Hips".
def _GetBoneRotations(obj, boneName):
    localQuaternionsList = _GetBoneLocalQuaternionsFromFcurves(boneName)
    transformMatrix, worldQuaternionsList = _TransformQuaternionListByDefaultBoneWorldMatrix(obj, localQuaternionsList)
    #localEulerLists = _GetEulerListFromQuaternionsList(localQuaternionsList)
    worldEulersList = _GetEulerListFromQuaternionsList(worldQuaternionsList)
    return (localQuaternionsList, transformMatrix, worldQuaternionsList, worldEulersList)


#Returns a list of Vectors
def _GetEulerListAsVectorDegreeList(eulerList):
    retList = []
    for e in eulerList:
        v = Vector((math.degrees(e.x), math.degrees(e.y), math.degrees(e.z)))
        retList.append(v)
    return retList


#Returns a tuple (eulersListNoZ, eulersListOnlyZ)
def _SplitEulersListByZ(eulersList):
    eulersListNoZ = []
    eulersListOnlyZ = []
    for e in eulersList:
        eNoZ = e.copy()
        eNoZ.z = 0.0
        eulersListNoZ.append(eNoZ)
        eOnlyZ = e.copy()
        eOnlyZ.x = 0.0
        eOnlyZ.y = 0.0
        eulersListOnlyZ.append(eOnlyZ)
    return (eulersListNoZ, eulersListOnlyZ)


def _GetBoneLocalLocationsFromWorldLocations(worldLocations, bone, worldMatrix):
    worldMatrixInverse = (worldMatrix @ bone.matrix).inverted()
    retList = []
    for worldLoc in worldLocations:
        localLoc = worldMatrixInverse @ worldLoc
        retList.append(localLoc)
    return retList


#@obj is an Armature Object.
def _GetBoneWorldMatrix(obj, boneName):
    bone = obj.pose.bones["root"]
    objWorldMatrix = obj.matrix_world
    boneWorldMatrix = objWorldMatrix @ bone.matrix
    return boneWorldMatrix


#Debug function that dumps a list of Vector as a CSV file.
def _SaveVectorListAsCsv(vectorList, startFrame, fileName):
    filename = os.path.join(CSV_OUTPUT_DIR, fileName)
    try:
        fileObj = open(filename, 'w+')
    except:
        print("Failed to create ", filename)
        return
    fileObj.write("Frame,x,y,z\n")
    frameId = startFrame
    for v in vectorList:
        fileObj.write("{},{},{},{}\n".format(frameId, v.x, v.y, v.z))
        frameId += 1
    fileObj.close()
    print("{} was created".format(fileName))


#Debug function that dumps a list of Quaternion as a CSV file.
def _SaveQuaternionListAsCsv(quaternionsList, startFrame, fileName):
    filename = os.path.join(CSV_OUTPUT_DIR, fileName)
    try:
        fileObj = open(filename, 'w+')
    except:
        print("Failed to create ", filename)
        return
    fileObj.write("Frame,w,x,y,z\n")
    frameId = startFrame
    for q in quaternionsList:
        fileObj.write("{},{},{},{},{}\n".format(frameId, q.w, q.x, q.y, q.z))
        frameId += 1
    fileObj.close()
    print("{} was created".format(fileName))


def _GetVectorListAxisAsNumpyArray(vectorList, axis):
    pyArray = []
    for v in vectorList:
        pyArray.append(v[axis])
    return np.array(pyArray)


#If the last value of the array for a given axis
#is distant by at least @tolerance, then we consider
#the axis to have translation
def _AxisFinalPosHasTranslation(vectorList, axis, tolerance):
    lastVector = vectorList[-1]
    lastAxisValue = lastVector[axis]
    print(lastAxisValue)
    return math.fabs(lastAxisValue) > tolerance


#Returns tuple (cnt, aMin, aMax, aAvg, aStdev)
def _CalcNumpyArrayRunningStats(npArray):
    Svar = 0.0
    cnt = 0
    for v in npArray:
        cnt += 1
        sample = v
        if cnt == 1:
            aMin = aMax = aAvg = sample
            cnt += 1
            continue
        if sample < aMin:
            aMin = sample
        elif sample > aMax:
            aMax = sample
        prevAvg = aAvg
        aAvg = aAvg + (sample - aAvg)/cnt
        Svar = Svar + (sample - prevAvg)*(sample - aAvg)
    # For variance we are using Svar/cnt insteead of Svar/(cnt-1) because
    # we are analyzing the whole data set, not a sample of a larger set.
    variance = Svar/cnt if (cnt > 0) else 0.0
    aStdev = math.sqrt(variance)
    return (cnt, aMin, aMax, aAvg, aStdev)


#return tuple (bool, npRawAxisData, npLowPassAxisData)
#   The first item in the tuple is True if the data for a given axis of the
#   vectorList suggests that there's a change of distance large enough
#   that makes it important to extract it as part of the root motion.
#   npRawAxisData is a numpy array that contains the raw data from
#       @vectorList for a given axis.
#   npLowPassAxisData is a numpy array that contains the low frequency data
#       from @vectorList for a given axis. In other words:
#       npRawAxisData - npLowPassAxisData = High Frequency data.
#@vectorList (list of Vector)
#@axis (int) Index of axis to analyze. 0 for X, 1 for Y, 2 for Z.
#@tolerance (double)
#@sampleRate How fast 
def _ShouldExtractRootMotionForAxis(vectorList, axis, tolerance=0.01,
                                   sampleRate = 60.0,
                                   cutoffFrequency = None):
    if cutoffFrequency is None:
        cutoffFrequency = sampleRate / 10.0
    #No matter what we always calculate the low pass version of the axis data.
    npRawAxisData = _GetVectorListAxisAsNumpyArray(vectorList, axis)
    npLowPassAxisData = lowpass.butter_lowpass_filter(npRawAxisData,
                                                      cutoffFrequency,
                                                      sampleRate)

    #See if there's considerable translation across the axis.
    if _AxisFinalPosHasTranslation(vectorList, axis, tolerance):
        return True, npRawAxisData, npLowPassAxisData

    #Ok, so the final value at the given axis is close to zero.
    #But, is there considerable translation before arriving at the final value?
    #If the low pass data "max" value
    (cnt, aMin, aMax, aAvg, aStdev) = _CalcNumpyArrayRunningStats(npLowPassAxisData)
    print("low pass stats: ", cnt, aMin, aMax, aAvg, aStdev)
    if aMax > 0.2: #Define this as configurable.
        return True, npRawAxisData, npLowPassAxisData

    return False, npRawAxisData, npLowPassAxisData


#locationData is a list of Vector.
def _SubtractLocationDataFromBoneFCurves(boneName, locationData):
    for axis in range(3):  #0=X, 1=Y, 2=Z
        fcurve = _GetKeyFrames(bpy.data.actions[0], boneName, 'location', axis)
        keyFramesCount = len(fcurve.keyframe_points)
        if keyFramesCount < 1:
            print("The source fcurve was already empty")
            continue
        for frameIndex in range(keyFramesCount):
            srcKfp = fcurve.keyframe_points[frameIndex]
            v = locationData[frameIndex]
            srcKfp.co[1] -= v[axis]


#locationList is a list of Vector.
def _SetLocationDataForBoneFCurves(boneName, locationList):
    for axis in range(3):  #0=X, 1=Y, 2=Z
        fcurve = _GetKeyFrames(bpy.data.actions[0], boneName, 'location', axis)
        keyFramesCount = len(fcurve.keyframe_points)
        if keyFramesCount < 1:
            print("The source fcurve was already empty")
            continue
        for frameIndex in range(keyFramesCount):
            srcKfp = fcurve.keyframe_points[frameIndex]
            v = locationList[frameIndex]
            srcKfp.co[1] = v[axis]


def _SetRotationDataForBoneFCurves(boneName, quaternionList):
    for axis in range(4):  #o=W, 1=X, 2=Y, 3=Z
        fcurve = _GetKeyFrames(bpy.data.actions[0], boneName, 'rotation_quaternion', axis)
        keyFramesCount = len(fcurve.keyframe_points)
        if keyFramesCount < 1:
            print("The source fcurve was already empty")
            continue
        for frameIndex in range(keyFramesCount):
            srcKfp = fcurve.keyframe_points[frameIndex]
            q = quaternionList[frameIndex]
            srcKfp.co[1] = q[axis]  
    

def _ClearCloseToZeroDataFromArrayInPlace(arr, tolerance = 0.1):
    cnt = len(arr)
    for idx in range(cnt):
        value = arr[idx]
        if value >= tolerance:
            continue
        arr[idx] = 0.0


def _BuildVectorListFromNumpyArrays(npLowPassAxisDataX,
                                   npLowPassAxisDataY,
                                   npLowPassAxisDataZ):
    cnt = len(npLowPassAxisDataX)
    retList = []
    for idx in range(cnt):
        v = Vector((npLowPassAxisDataX[idx], npLowPassAxisDataY[idx],
                   npLowPassAxisDataZ[idx]))
        retList.append(v)
    return retList


#Makes sure the bone named @boneName contains the exact same amount of keyframe
# 'location' data as the bone named  @templateBoneName
#@obj should the "Armature" object
def _InsertLocationKeyframes(obj, boneName, templateBoneName):
    actionObj = bpy.data.actions[0]
    for axis in range(3):
        newFcurve = _InsertKeyFrames(obj, actionObj, boneName, 'location', axis)#0=X, 1=Y, 2=Z
        templateFCurve = _GetKeyFrames(actionObj, templateBoneName, 'location', axis) 
        _CopyKeyFrames(newFcurve, templateFCurve, defaultValue=0.0)


def _InsertRotationKeyframes(obj, boneName, templateBoneName):
    actionObj = bpy.data.actions[0]
    for axis in range(4):
        newFcurve = _InsertKeyFrames(obj, actionObj, boneName, 'rotation_quaternion', axis)#0=X, 1=Y, 2=Z
        templateFCurve = _GetKeyFrames(actionObj, templateBoneName, 'rotation_quaternion', axis)
        if axis == 0: #W.
            _CopyKeyFrames(newFcurve, templateFCurve, defaultValue=1.0)
        else:
            _CopyKeyFrames(newFcurve, templateFCurve, defaultValue=0.0)


def _ClearDataForAxes(vectorList, clearX, clearY, clearZ):
    print("Will clear axes: ", clearX, clearY, clearZ)
    for v in vectorList:
        if clearX:
            v.x = 0.0
        if clearY:
            v.y = 0.0
        if clearZ:
            v.z = 0.0        



def ProcessMotion(sceneObj, armatureObj, hipBoneName, rootBoneName,
                  animationSampleRate, dumpCSVs=False):
    """
    Main function that transforms a Motion type of Asset per Lumberyard 
    requirements.

    In Short: Adds the "root" bone to the armature and transfers root motion
     from the Hips bone to the "root" bone. The motion data is transferred
     from Hips bone FCurves to  the "root" bone FCurves.

    @sceneObj (bpy.types.Scene)
    @armatureObj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
    @hipBoneName (string). Name of the "Hips" bone as originated by Mixamo.
    @rootBoneName (string). Name of the root motion bone that will be added to
        the armature.
    @animationSampleRate (double) A value in Hz that represents the target
        Frames Per Second at which the animation is supposed to run. It is
        usually 60fps or 30fps. It is used to calculate the low pass motion
        data.
    @dumpCSVs (bool) DEBUG Only. Dump motion vector data as CSV files
    """
    #The first goal is to apply the object rotation if it is not 0,0,0.
    cmn.ApplyCurrentRotationAs000(armatureObj)
    yield Status("Applied rotation")

    hipLocalLocations, hipWorldMatrix, hipWorldLocations = _GetBoneLocations(armatureObj, hipBoneName)
    yield Status("Got '{}' bone local and world locations".format(hipBoneName))
    if dumpCSVs:
        _SaveVectorListAsCsv(hipLocalLocations, 0,
            "HipLocalLocations.csv")
        _SaveVectorListAsCsv(hipWorldLocations, 0,
            "HipWorldLocations.csv")

    (localQuaternionsList, transformMatrix, worldQuaternionsList,
        worldEulersList) = _GetBoneRotations(armatureObj, hipBoneName)
    yield Status("Got '{}' bone local and world rotations".format(hipBoneName))
    if dumpCSVs:
        hipWorldVectorDegreesList = _GetEulerListAsVectorDegreeList(worldEulersList)
        _SaveVectorListAsCsv(hipWorldVectorDegreesList, 0,
                "hipWorldVectorDegreesList.csv")
    
    worldEulersListNoZ, worldEulersListOnlyZ = _SplitEulersListByZ(worldEulersList)
    yield Status("Splitted '{}' bone world Euler rotations".format(hipBoneName))
    if dumpCSVs:
        hipWorldNoZVectorDegreesList = _GetEulerListAsVectorDegreeList(worldEulersListNoZ)
        _SaveVectorListAsCsv(hipWorldNoZVectorDegreesList, 0,
                "hipWorldNoZVectorDegreesList.csv")
        hipWorldOnlyZVectorDegreesList = _GetEulerListAsVectorDegreeList(worldEulersListOnlyZ)
        _SaveVectorListAsCsv(hipWorldOnlyZVectorDegreesList, 0,
                "hipWorldOnlyZVectorDegreesList.csv")

    hipsLocalQuaternionsListNoZ = _TransformEulersList(worldEulersListNoZ, transformMatrix.inverted())
    yield Status("Transformed '{}' bone world No-Z Euler rotations to local Quaternions".format(hipBoneName))
    if dumpCSVs:
        #The idea is that copyLocalQuaternionsList should be identical to hipsLocalQuaternionsListNoZ
        copyLocalQuaternionsList = _TransformEulersList(worldEulersList, transformMatrix.inverted())
        _SaveQuaternionListAsCsv(copyLocalQuaternionsList, 0, "copyLocalQuaternionsList.csv")
        _SaveQuaternionListAsCsv(hipsLocalQuaternionsListNoZ, 0, "hipsLocalQuaternionsListNoZ.csv")

    
    #startTimeNS = time.perf_counter_ns()
    #Extract World Positions of all the key frames for the Hip bone.
    keyFrameCount = _GetNumKeyFrames(bpy.data.actions[0], hipBoneName, 'location', 0)
    print("Frame Count is ", keyFrameCount)
    keyFrameStart = 1
    keyFrameEnd = keyFrameCount
    sceneObj.frame_start = keyFrameStart
    sceneObj.frame_end = keyFrameEnd

    #Extract World Positions of the center of the bottom plane center point
    #of the Bound Box per key frame.
    #This data will be used to calculate root motion in the Z(Up) axis
    bboxBaseLocations = _GetBBoxWorldLocations(
        sceneObj, armatureObj, keyFrameStart, keyFrameEnd)
    yield Status("Got Armature bottom plane center world location per keyframe")
    if dumpCSVs:
        _SaveVectorListAsCsv(bboxBaseLocations, keyFrameStart, "BBoxWorldLocations.csv")

    (extractX, npRawAxisDataX, npLowPassAxisDataX) = _ShouldExtractRootMotionForAxis(hipWorldLocations, 0)
    (extractY, npRawAxisDataY, npLowPassAxisDataY) = _ShouldExtractRootMotionForAxis(hipWorldLocations, 1)
    (extractZ, npRawAxisDataZ, npLowPassAxisDataZ) = _ShouldExtractRootMotionForAxis(bboxBaseLocations, 2)
    yield Status("extracted low pass motion from locations of '{}' bone".format(hipBoneName))

    #sceneObj.frame_set(keyFrameStart)

    _AddSiblingRootBone(armatureObj, rootBoneName)

    if extractX or extractY or extractZ:
        _ClearCloseToZeroDataFromArrayInPlace(npLowPassAxisDataZ)
        yield Status("Cleared close to 0.0 low pass Z values")
        lowPassHipWorldLocations = _BuildVectorListFromNumpyArrays(
            npLowPassAxisDataX, npLowPassAxisDataY, npLowPassAxisDataZ)
        yield Status("Built Low Pass '{}' bone world locations list".format(hipBoneName))
        if dumpCSVs:
            _SaveVectorListAsCsv(lowPassHipWorldLocations, keyFrameStart,
                "lowPassHipWorldLocations_beforeClear.csv")

        #Make sure the root bone has all the required keyframes allocated.
        _InsertLocationKeyframes(armatureObj, rootBoneName, hipBoneName)
        yield Status("Inserted empty location KeyFrames in '{}' bone".format(rootBoneName))

        #Let's clear the low pass data for the axis that won't require root motion extraction
        _ClearDataForAxes(lowPassHipWorldLocations, not extractX, not extractY, not extractZ)
        yield Status("Cleared low pass motion data for the following axes X({}), Y({}), Z({})".format(not extractX, not extractY, not extractZ))
        if dumpCSVs:
            _SaveVectorListAsCsv(lowPassHipWorldLocations, keyFrameStart,
                "lowPassHipWorldLocations_afterClear.csv")

        #Subtract low pass data from Hips Bone
        lowPassHiplocalLocations = _TransformVectorList(lowPassHipWorldLocations,
                                                       hipWorldMatrix.inverted())
        yield Status("Got low pass '{}' bone local locations from world locations".format(hipBoneName))
        _SubtractLocationDataFromBoneFCurves(hipBoneName, lowPassHiplocalLocations)
        yield Status("Removed low pass motion data '{}' bone locations FCurve".format(hipBoneName))
        if dumpCSVs:
            _SaveVectorListAsCsv(lowPassHiplocalLocations, keyFrameStart,
                "lowPassHiplocalLocations.csv")

        #Set low pass data to Root Bone
        lowPassRootlocalLocations = _GetBoneLocalLocationsFromWorldLocations(
            lowPassHipWorldLocations, armatureObj.pose.bones[rootBoneName], armatureObj.matrix_world)
        yield Status("Got lowpass local locations for '{}' bone".format(rootBoneName))
        _SetLocationDataForBoneFCurves(rootBoneName, lowPassRootlocalLocations)
        yield Status("Set location root motion to '{}' bone locations FCurve".format(rootBoneName))
        if dumpCSVs:
            _SaveVectorListAsCsv(lowPassRootlocalLocations, keyFrameStart,
                "lowPassRootlocalLocations.csv")

    #Apply rotation around Z axis.
    _InsertRotationKeyframes(armatureObj, rootBoneName, hipBoneName)
    yield Status("Inserted empty rotation keyframes in '{}' bone quaternions FCurve".format(rootBoneName))

    #Update Hips rotations with noZ rotation.
    _SetRotationDataForBoneFCurves(hipBoneName, hipsLocalQuaternionsListNoZ)
    yield Status("Remove Z axis rotation from '{}' bone quaternions FCurve".format(hipBoneName))

    #Now, the worldEulerOnlyZ rotations need to be converted to the root bone local frame:
    boneWorldMatrix = _GetBoneWorldMatrix(armatureObj, rootBoneName)
    worldEulersListOnlyZ = _AddEulerToList(worldEulersListOnlyZ, Euler((0.0, 0.0, math.radians(180.0)), 'XYZ'))
    yield Status("Applied 180 degrees offset to Z axis rotations of '{}' bone".format(rootBoneName))

    rootLocalQuaternionsListOnlyZ = _TransformEulersList(worldEulersListOnlyZ, boneWorldMatrix.inverted())
    yield Status("Transformed '{}' bone world Eulers to local Quaternion".format(rootBoneName))

    _SetRotationDataForBoneFCurves(rootBoneName, rootLocalQuaternionsListOnlyZ)
    yield Status("Applied root motion Z rotation to '{}' bone quaternion FCurves".format(rootBoneName))

    #Finally make "root" the father of "Hips".
    _MakeParentBone(armatureObj, parentBoneName=rootBoneName, childBoneName=hipBoneName)
    yield Status("Completed root motion extraction from '{}' bone to '{}' bone".format(hipBoneName, rootBoneName))
    


