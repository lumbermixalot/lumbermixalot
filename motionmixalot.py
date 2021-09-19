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
import math
import sys
import os


if __package__ is None or __package__ == "":
    # When running as a standalone script from Blender Text View "Run Script"
    from commonmixalot import Status
    import commonmixalot as cmn
    import fcurvesmixalot as fcv
else:
    # When running as an installed AddOn, then it runs in package mode.
    from .commonmixalot import Status
    from . import commonmixalot as cmn
    from . import fcurvesmixalot as fcv

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


def _InsertBoneKeyFrames(armatureObj, actionObj, boneName, vectorName, vectorComponentIndex):
    fcurve = _GetBoneKeyFrames(actionObj, boneName, vectorName, vectorComponentIndex)
    dataPath = _BuildBoneDataPath(boneName, vectorName)
    if fcurve is not None:
        print("The fcurve {} at index {} already exists".format(dataPath, vectorComponentIndex))
        return fcurve
    if not armatureObj.keyframe_insert(dataPath, index=vectorComponentIndex, frame=1):
        print("Failed to insert new empty KeyFrames at path {} index {}".format(dataPath, vectorComponentIndex))
        return None
    return _GetBoneKeyFrames(actionObj, boneName, vectorName, vectorComponentIndex)


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

def _DumpBoundBox(bound_box):
    """
    bound_box comes from bpy.types.Object.bound_box
    """
    for idx, rawVec in enumerate(bound_box):
        v = Vector(rawVec)
        print(f"bbIdx[{idx}] = {v}")


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



def _GetBBoxWorldLocations(sceneObj: bpy.types.Scene , armatureObj: bpy.types.Armature, keyFrameNumbersList: list[int]) -> list[Vector]:
    """
    Returns an array of Vector. Each vector is the world location of the center of the bottom plane
    of the bounding box  per key frame.
    """
    vectorList = []
    for frameNumber in keyFrameNumbersList:
        sceneObj.frame_set(frameNumber)
        (vecMin, vecMax) = _GetBBOX(armatureObj.bound_box)
        #_DumpBoundBox(armatureObj.bound_box)
        # It is very important to multiply by armatureObj.matrix_world,
        # Because usually the Armature as it comes from Mixamo, it is rotate 90def around
        # the X axis, and with 0.01 uniform scale across all axis.
        vecMin = armatureObj.matrix_world @ vecMin
        vecMax = armatureObj.matrix_world @ vecMax
        v = _GetBBOXBaseCenter(vecMin, vecMax)
        vectorList.append(v)
    return vectorList


def _GetPoseBoneKeyFrameMatrices(sceneObj: bpy.types.Scene , armatureObj: bpy.types.Armature, poseBoneName: str, keyFrameNumbersList: list[int]) -> list[Matrix]:
    """
    Returns an array of Matrices. Each matrix is the Pose Bone transformation matrix per key frame.
    """
    poseBoneObj = cmn.GetPoseBoneFromArmature(armatureObj, poseBoneName)
    matrixList = []
    for frameNumber in keyFrameNumbersList:
        sceneObj.frame_set(frameNumber)
        matrixList.append(poseBoneObj.matrix)
        print(f"at frame {frameNumber}, matrix:\n{poseBoneObj.matrix}")
    return matrixList


#Returns a list of Quaternions
def _GetBoneLocalQuaternionsFromFcurves(armatureObj, boneName):
    retList = []

    fcurveW = _GetPoseBoneFCurveFromDataPath(armatureObj, boneName, FCurveDataPath.QUATERNION_W)
    fcurveX = _GetPoseBoneFCurveFromDataPath(armatureObj, boneName, FCurveDataPath.QUATERNION_X)
    fcurveY = _GetPoseBoneFCurveFromDataPath(armatureObj, boneName, FCurveDataPath.QUATERNION_Y)
    fcurveZ = _GetPoseBoneFCurveFromDataPath(armatureObj, boneName, FCurveDataPath.QUATERNION_Z)

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

#Returns a list of Matrix33
def _GetMatrix33ListFromQuaternionsList(localQuaternionsList):
    retList = []
    for q in localQuaternionsList:
        m33 = q.to_matrix()
        retList.append(m33)
    return retList


#@vectorList is a list of MathUtils.Vector
#@matrix is a MathUtils.Matrix
#returns a list of MathUtils.Vector
def _TransformVectorList(matrix, vectorList):
    retList = []
    for v in vectorList:
        transformedV = matrix @ v
        retList.append(transformedV)
    return retList



def _SubtractVectorLists(listA: list[Vector], listB: list[Vector]) -> list[Vector]:
    """
    returns listC = listA - listB, where listC[n] == listA[n] - listB[n] 
    """
    retList = []
    for vA, vB in zip(listA, listB):
        retList.append(vA - vB)
    return retList

def _InverseTransformVectorListWithMatrixList(feetWorldLocations, hipBoneMatrixList):
    retList = []
    for vector, matrix in zip(feetWorldLocations, hipBoneMatrixList):
        transformed = matrix.inverted() @ vector
        retList.append(transformed)
    return retList

def _GetRestPoseMatrixFromPoseBone(poseBoneObj):
    """
    bpy.types.PoseBone
    All animation data is recorded in the PoseBone.
    Technically by setting the current frame number
    with SetCurrentAnimationFrame() you can get the current Matrix4x4
    from the PoseBone.
    BUT, All animation data is technically relative to the
    Rest Pose, and for that We access the matrix from PoseBone.bone
    which is a bpy.types.Bone 
    """
    return poseBoneObj.bone.matrix_local

def _TransformPoseBoneLocalLocationsToWorldLocations(armatureObj, poseBoneObj, vectorList):
    """
    poseBoneObj is bpy.types.PoseBone
    vectorList is list of mathutils.Vector
    Returns tuple (matrix, list)
    """
    restMatrix = _GetRestPoseMatrixFromPoseBone(poseBoneObj)
    transformMatrix = armatureObj.matrix_world @ restMatrix
    return transformMatrix, _TransformVectorList(transformMatrix, vectorList)


#Returns a tuple (localLocationsList, transformMatrix, worldLocationsList)
# This is a simplified function because it doesn't traverse the bone hierarchy
# at all. It assummes @boneName is the name of the first child bone of the
# armature @obj.
#@obj (bpy.types.Armature). Object.type is assumed to be 'ARMATURE'
#@boneName (string). Name of the current root bone as originated by Mixamo.
#   The root bone from Mixamo is usually named "Hips".
def _GetPoseBoneLocations(armatureObj, boneName):
    localLocations = fcv.GetPoseBoneLocalLocationsFromFcurves(armatureObj, boneName)
    poseBoneObj = cmn.GetPoseBoneFromArmature(armatureObj, boneName)
    transformMatrix, worldLocations = _TransformPoseBoneLocalLocationsToWorldLocations(armatureObj, poseBoneObj, localLocations)
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
    #worldMatrix = obj.matrix_world
    #boneMatrix = _GetBlenderDefaultBoneMatrix44()
    transformMatrix = obj.matrix_world #worldMatrix @ boneMatrix
    transformedList = _TransformQuaternionsList(quaternionsList,
                                                transformMatrix)
    return transformMatrix, transformedList


def _GetAngleAroundProjectedAxisFromQuaternion(q, axisVector, axisVectorOrthogonal):
    transformedOrthogonal = q @ axisVectorOrthogonal
    projected = transformedOrthogonal - (axisVector * transformedOrthogonal.dot(axisVector))
    projected.normalize()
    cosineOfAngle = axisVectorOrthogonal.dot(projected)
    return math.acos(cosineOfAngle)


#Returns a tuple (zAxisWorldQuaternionsList, retMirroredQuaternionList, zAxisAnglesList)
def _ExtractZaxisWorldQuaternions(worldQuaternionsList):
    zAxis = Vector((0.0, 0.0, 1.0))
    zAxisOrthogonal = Vector((1.0, 0.0, 0.0))
    retQuaternionList = []
    retMirroredQuaternionList = []
    retAnglesList = []
    for q in worldQuaternionsList:
        angleAroundZaxis = _GetAngleAroundProjectedAxisFromQuaternion(q, zAxis, zAxisOrthogonal)
        newQ = Quaternion(zAxis, angleAroundZaxis)
        newQMirrored = Quaternion(zAxis, angleAroundZaxis + math.pi)
        retQuaternionList.append(newQ)
        retMirroredQuaternionList.append(newQMirrored)
        angleDeg = math.degrees(angleAroundZaxis)
        retAnglesList.append((angleAroundZaxis, angleDeg))
    return (retQuaternionList, retMirroredQuaternionList, retAnglesList)


#Returns a new list of quaternions where all quaternions in @qList
#have the rotations in qListDelta removed from them
def _RemoveRotationsFromQuaternions(qListDelta, qList):
    length = len(qList)
    retList = []
    for idx in range(length):
        deltaQuat = qListDelta[idx]
        w = deltaQuat.inverted() @ qList[idx]
        retList.append(w)
    return retList


#Returns a tuple (localQuaternionsList, transformMatrix, worldQuaternionsList)
#   Where:
#   localQuaternionsList is a list of Quaternion with local bone data as
#       extracted from FCurves.
#   transformMatrix A 4x4 World transform Matrix used to transform the
#       Quaternions in localQuaternionsList.
#   worldQuaternionsList The transformed Quaternions, now in World coordinates.
# This is a simplified function because it doesn't traverse the bone hierarchy
# at all. It assummes @boneName is the name of the first child bobe of the
# armature @obj.
#@obj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
#@boneName (string). Name of the current root bone as originated by Mixamo.
#   The root bone from Mixamo is usually named "Hips".
def _GetBoneRotations(obj, boneName):
    localQuaternionsList = _GetBoneLocalQuaternionsFromFcurves(boneName)
    transformMatrix, worldQuaternionsList = _TransformQuaternionListByDefaultBoneWorldMatrix(obj, localQuaternionsList)
    return (localQuaternionsList, transformMatrix, worldQuaternionsList)


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


def _SaveAxisAnglesListAsCsv(anglesList, axisVector, startFrame, fileName):
    filename = os.path.join(CSV_OUTPUT_DIR, fileName)
    try:
        fileObj = open(filename, 'w+')
    except:
        print("Failed to create ", filename)
        return
    fileObj.write("Frame,w,x,y,z\n")
    frameId = startFrame
    for rad, deg in anglesList:
        fileObj.write("{},{},{},{},{}\n".format(frameId, deg, axisVector.x, axisVector.y, axisVector.z))
        frameId += 1
    fileObj.close()
    print("{} was created".format(fileName))


def _GetVectorListAxisAsArray(vectorList, axis):
    pyArray = []
    for v in vectorList:
        pyArray.append(v[axis])
    return pyArray


def _SetRotationDataForBoneFCurves(boneName, quaternionList):
    for axis in range(4):  #o=W, 1=X, 2=Y, 3=Z
        fcurve = _GetBoneKeyFrames(bpy.data.actions[0], boneName, 'rotation_quaternion', axis)
        keyFramesCount = len(fcurve.keyframe_points)
        if keyFramesCount < 1:
            print("The source fcurve was already empty")
            continue
        for frameIndex in range(keyFramesCount):
            srcKfp = fcurve.keyframe_points[frameIndex]
            q = quaternionList[frameIndex]
            srcKfp.co[1] = q[axis]  
    

def _SetRotationDataForFCurves(quaternionList):
    for axis in range(4):  #o=W, 1=X, 2=Y, 3=Z
        fcurve = _GetKeyFrames(bpy.data.actions[0], 'rotation_quaternion', axis)
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
        value = abs(arr[idx])
        if value >= tolerance:
            continue
        arr[idx] = 0.0


#Returns a list of Vector
def _BuildVectorListFromArrays(arrayDataX, arrayDataY, arrayDataZ):
    cnt = len(arrayDataX)
    retList = []
    for idx in range(cnt):
        v = Vector((arrayDataX[idx], arrayDataY[idx],
                   arrayDataZ[idx]))
        retList.append(v)
    return retList


def _InsertBoneRotationKeyframes(obj, boneName, templateBoneName):
    actionObj = bpy.data.actions[0]
    for axis in range(4):
        newFcurve = _InsertBoneKeyFrames(obj, actionObj, boneName, 'rotation_quaternion', axis)#0=X, 1=Y, 2=Z
        templateFCurve = _GetBoneKeyFrames(actionObj, templateBoneName, 'rotation_quaternion', axis)
        if axis == 0: #W.
            _CopyKeyFrames(newFcurve, templateFCurve, defaultValue=1.0)
        else:
            _CopyKeyFrames(newFcurve, templateFCurve, defaultValue=0.0)

def _InsertRotationKeyframes(obj, templateBoneName):
    actionObj = bpy.data.actions[0]
    for axis in range(4):
        newFcurve = _InsertKeyFrames(obj, actionObj, 'rotation_quaternion', axis)#0=X, 1=Y, 2=Z
        templateFCurve = _GetBoneKeyFrames(actionObj, templateBoneName, 'rotation_quaternion', axis)
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


def ProcessMotion(sceneObj, armatureObj, hipBoneName,
                  extractTranslationX, zeroOutTranslationX,
                  extractTranslationY, zeroOutTranslationY,
                  extractTranslationZ, zeroOutTranslationZ,
                  extractRotationZ, zeroOutRotationZ,
                  dumpCSVs=False):
    """
    Main function that transforms a Motion type of Asset per Lumberyard 
    requirements.

    In Short: Transfers root motion
     from the Hips bone to the "Armature" object. The motion data is transferred
     from Hips bone FCurves to  the "Armature" FCurves.

    @sceneObj (bpy.types.Scene)
    @armatureObj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
    @hipBoneName (string). Name of the "Hips" bone as originated by Mixamo.
    @extractTranslationX,Y,Z (bool). Extract X,Y,Z Axis Translation.
    @zeroOutTranslationX,Y,Z (bool). Zero Out X,Y,Z Axis Translation upon
        extraction.
    @extractRotationZ (bool). Extract Rotation around Z Axis.
    @zeroOutRotationZ (bool). Zero Out Rotation around Z Axis upon extraction.
    @dumpCSVs (bool) DEBUG Only. Dump motion vector data as CSV files
    """
    hipLocalLocations, hipWorldMatrix, hipWorldLocations = _GetPoseBoneLocations(armatureObj, hipBoneName)
    yield Status("Got '{}' bone local and world locations".format(hipBoneName))
    if dumpCSVs:
        _SaveVectorListAsCsv(hipLocalLocations, 0,
            "HipLocalLocations.csv")
        _SaveVectorListAsCsv(hipWorldLocations, 0,
            "HipWorldLocations.csv")

    if extractRotationZ:
        (localQuaternionsList, transformMatrix, worldQuaternionsList) = _GetBoneRotations(armatureObj, hipBoneName)
        yield Status("Got '{}' bone local and world rotations".format(hipBoneName))
        if dumpCSVs:
            _SaveQuaternionListAsCsv(localQuaternionsList, 0, "hipLocalQuaternionsList.csv")
            _SaveQuaternionListAsCsv(worldQuaternionsList, 0, "hipWorldQuaternionsList.csv")

        #The idea is that zAxisWorldQuaternionsList will contain the world rotations of the root bone
        #around zAxis.
        zAxisWorldQuaternionsList, mirroredZAxisWorldQuaternionsList, zAxisAnglesList = _ExtractZaxisWorldQuaternions(worldQuaternionsList)
        #noZAxisWorldQuaternionsList will be the new world rotations for the hip bone because it has
        #rotation around zAxis removed from it.
        noZAxisWorldQuaternionsList = _RemoveRotationsFromQuaternions(zAxisWorldQuaternionsList, worldQuaternionsList)
        #Now hipsLocalQuaternionsListNoZ contains the new quaternions for the hip bone but zAxis rotation has been
        #removed from it.
        hipsLocalQuaternionsListNoZ = _TransformQuaternionsList(noZAxisWorldQuaternionsList, hipWorldMatrix.inverted())
        if dumpCSVs:
            _SaveQuaternionListAsCsv(zAxisWorldQuaternionsList, 0, "zAxisWorldQuaternionsList.csv")
            _SaveQuaternionListAsCsv(mirroredZAxisWorldQuaternionsList, 0, "mirroredZAxisWorldQuaternionsList.csv")
            _SaveQuaternionListAsCsv(noZAxisWorldQuaternionsList, 0, "noZAxisWorldQuaternionsList.csv")
            _SaveQuaternionListAsCsv(hipsLocalQuaternionsListNoZ, 0, "hipsLocalQuaternionsListNoZ.csv")
            _SaveAxisAnglesListAsCsv(zAxisAnglesList, Vector((0.0, 0.0, 1.0)), 0, "zAxisWorldAnglesList.csv")

    
    #startTimeNS = time.perf_counter_ns()
    #Extract World Positions of all the key frames for the Hip bone.
    keyFrameNumbersList = fcv.GetKeyFrameNumbersListPoseBoneDataPath(armatureObj, hipBoneName, fcv.FCurveDataPath.LOCATION_X)
    keyFrameStart = keyFrameNumbersList[0]
    keyFrameEnd = keyFrameNumbersList[-1]
    keyFrameCount = len(keyFrameNumbersList)
    print("Frame Count is ", keyFrameCount)
    sceneObj.frame_start = keyFrameStart
    sceneObj.frame_end = keyFrameEnd

    #Extract World Positions of the center of the bottom plane center point
    #of the Bound Box per key frame.
    #This data will be used to calculate root motion in the Z(Up) axis
    bboxBaseLocations = _GetBBoxWorldLocations(
        sceneObj, armatureObj, keyFrameNumbersList)
    yield Status("Got Armature bottom plane center world location per keyframe")
    if dumpCSVs:
        _SaveVectorListAsCsv(bboxBaseLocations, keyFrameStart, "BBoxWorldLocations.csv")

    # Experimental
    # hipBoneMatrixList = _GetPoseBoneKeyFrameMatrices(sceneObj, armatureObj, hipBoneName, keyFrameNumbersList)

    rawHipWorldAxisDataX = _GetVectorListAxisAsArray(hipWorldLocations, 0)
    rawHipWorldAxisDataY = _GetVectorListAxisAsArray(hipWorldLocations, 1)
    rawHipWorldAxisDataZ = _GetVectorListAxisAsArray(hipWorldLocations, 2)
    rawFeetWorldAxisDataZ = _GetVectorListAxisAsArray(bboxBaseLocations, 2)
    yield Status("extracted world location axis arrays from '{}' bone".format(hipBoneName))

    if extractTranslationX or extractTranslationY or extractTranslationZ:
        _ClearCloseToZeroDataFromArrayInPlace(rawFeetWorldAxisDataZ)
        yield Status("Cleared close to 0.0 feet world Z values")

        feetWorldLocations = _BuildVectorListFromArrays(
            rawHipWorldAxisDataX, rawHipWorldAxisDataY, rawFeetWorldAxisDataZ)
        yield Status("Built feet world locations list from '{}' bone".format(hipBoneName))
        if dumpCSVs:
            _SaveVectorListAsCsv(feetWorldLocations, keyFrameStart,
                "feetWorldLocations_beforeClear.csv")

        #Make sure the transform of the Armature node has all the required keyframes allocated.
        fcv.AllocateLocationKeyFramesFromPoseBoneToArmature(hipBoneName, armatureObj)
        yield Status(f"Allocated all 'location' KeyFrames in Armature named '{armatureObj.name}' from bone '{hipBoneName}'")

        #Let's clear the feet world locations data for the axis that won't require root motion extraction
        _ClearDataForAxes(feetWorldLocations, not extractTranslationX,
                          not extractTranslationY, not extractTranslationZ)
        yield Status("Cleared motion data for the following axes X({}), Y({}), Z({})".format(
            not extractTranslationX, not extractTranslationY, not extractTranslationZ))
        if dumpCSVs:
            _SaveVectorListAsCsv(feetWorldLocations, keyFrameStart,
                "feetWorldLocations_afterClear.csv")

        #Get the feetWorldLocations transformed in hips local space. The resulting
        #vectors will be deltas that will be subtracted from the hip local locations.
        
        hipBoneWorldLocationDeltas = _SubtractVectorLists(hipWorldLocations, feetWorldLocations)
        newHipLocalLocations = _TransformVectorList(hipWorldMatrix.inverted(), hipBoneWorldLocationDeltas)
        #deltaHipLocalLocations = _TransformVectorList(hipWorldMatrix.inverted(), feetWorldLocations)
        #deltaHipLocalLocations = _InverseTransformVectorListWithMatrixList(feetWorldLocations, hipBoneMatrixList)

        yield Status("Got '{}' bone local locations from feet world locations".format(hipBoneName))
        if dumpCSVs:
            _SaveVectorListAsCsv(hipBoneWorldLocationDeltas, keyFrameStart,
                "hipBoneWorldLocationDeltas.csv")
            _SaveVectorListAsCsv(newHipLocalLocations, keyFrameStart,
                "newHipLocalLocations.csv")
            #_SaveVectorListAsCsv(deltaHipLocalLocations, keyFrameStart,
            #    "deltaHipLocalLocations.csv")

        #Subtract from hip the motions that will be transferred to the root.
        #fcv.SubtractLocationDataFromPoseBoneKeyFrames(armatureObj, hipBoneName, deltaHipLocalLocations)
        fcv.SetLocationDataForPoseBoneKeyFrames(armatureObj, hipBoneName, newHipLocalLocations)
        yield Status(f"Removed motion data from '{hipBoneName}' bone locations FCurve")
        

        if zeroOutTranslationX or zeroOutTranslationY or zeroOutTranslationZ:
            _ClearDataForAxes(feetWorldLocations, zeroOutTranslationX,
                              zeroOutTranslationY, zeroOutTranslationZ)
            yield Status("zeroed Out motion data for the following axes X({}), Y({}), Z({})".format(
            zeroOutTranslationX, zeroOutTranslationY, zeroOutTranslationZ))
            if dumpCSVs:
                _SaveVectorListAsCsv(feetWorldLocations, keyFrameStart,
                "feetWorldLocations_afterZeroedOut.csv")

        fcv.SetLocationDataForArmatureKeyFrames(armatureObj, feetWorldLocations)
        yield Status("Set location root motion to '{}' locations FCurve".format(armatureObj.name))

    if extractRotationZ:
        #Apply rotation around Z axis.
        _InsertRotationKeyframes(armatureObj, hipBoneName)
        yield Status("Inserted empty rotation keyframes in '{}' quaternions FCurve".format(armatureObj.name))

        #Update Hips rotations with noZ rotation.
        _SetRotationDataForBoneFCurves(hipBoneName, hipsLocalQuaternionsListNoZ)
        yield Status("Remove Z axis rotation from '{}' bone quaternions FCurve".format(hipBoneName))

        if not zeroOutRotationZ:
            #Now, the worldEulerOnlyZ rotations need to be converted to the root bone local frame:
            worldMatrix = armatureObj.matrix_world

            rootLocalQuaternionsListOnlyZ = _TransformQuaternionsList(mirroredZAxisWorldQuaternionsList, worldMatrix.inverted())
            yield Status("Transformed '{}' world Quaternions to local Quaternions".format(armatureObj.name))

            _SetRotationDataForFCurves(rootLocalQuaternionsListOnlyZ)
            yield Status("Applied root motion Z rotation to '{}' quaternion FCurves".format(armatureObj.name))

    yield Status("Completed root motion extraction from '{}' bone to '{}'".format(hipBoneName, armatureObj.name))
    


