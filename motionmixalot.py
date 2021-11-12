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

def _TransformPoseBoneLocalLocationsToWorldLocations(armatureObj:bpy.types.Armature, poseBoneObj: bpy.types.PoseBone, vectorList: list[Vector]):
    """
    Returns tuple (matrix, list[Vector])
    """
    restMatrix = _GetRestPoseMatrixFromPoseBone(poseBoneObj)
    transformMatrix = armatureObj.matrix_world @ restMatrix
    return transformMatrix, _TransformVectorList(transformMatrix, vectorList)


def _GetPoseBoneLocations(armatureObj: bpy.types.Armature, boneName: str):
    """
    Returns a tuple (localLocationsList, transformMatrix, worldLocationsList)
     This is a simplified function because it doesn't traverse the bone hierarchy
     at all. It assummes @boneName is the name of the first child bone of the
     armature @obj.
       The root bone from Mixamo is usually named "Hips".
    """
    localLocations = fcv.GetPoseBoneLocalLocationsFromFcurves(armatureObj, boneName)
    poseBoneObj = cmn.GetPoseBoneFromArmature(armatureObj, boneName)
    transformMatrix, worldLocations = _TransformPoseBoneLocalLocationsToWorldLocations(armatureObj, poseBoneObj, localLocations)
    return (localLocations, transformMatrix, worldLocations)



def _TransformQuaternionsList(transformMatrix: Matrix, quaternionsList: list[Quaternion]) -> list[Quaternion]:
    retList = []
    for q in quaternionsList:
        rotMat = q.to_matrix().to_4x4()
        newMat = transformMatrix @ rotMat
        worldQ = newMat.to_quaternion()
        retList.append(worldQ)
    return retList


def _TransformPoseBoneLocalQuaternionsToWorldQuaternions(armatureObj: bpy.types.Armature,
                                                         poseBoneObj: bpy.types.PoseBone,
                                                         localQuaternionsList: list[Quaternion]):
    restMatrix = _GetRestPoseMatrixFromPoseBone(poseBoneObj)
    print(f"restMatrix={restMatrix}")
    transformMatrix = armatureObj.matrix_world @ restMatrix
    return transformMatrix, _TransformQuaternionsList(transformMatrix, localQuaternionsList)
    


def ExtractAngleAroundUpVectorFromQuaternion(upVector: Vector, forwardVector: Vector, rightVector: Vector, q: Quaternion, qForwardIndex: int = 1):
    """
    A quaternion @q represents an arbitrary rotation around some vector.
    This function converts @q into a matrix 3x3. The forward basis vector of this matrix3x3,
    let's call it 'qmForward', is projected into the plane formed by @rightVector & @forwardVector.
    In Blender, usually the forward basis vector is Y (index 1), except for bones which
    by default the Z (index 2) is the forward vector. This is why We have an input parameter
    @qForwardIndex.
    this projected vector is normalized and we'll call it 'qmProjected'.
    Finally we calculate the angle between 'qmProjected' and @forwardVector. Which is the same
    as calculating the angle of rotation around the @upVector.
    """
    #This works under simple circumstances.
    #euler = q.to_euler('XYZ')
    #return euler.z
    mQ = q.to_matrix()
    qmForward = -mQ.col[qForwardIndex]

    # if @qmForward and @upVector are parallel to each other
    # the angle is 0.
    delta = 1.0 - abs(qmForward.dot(upVector))
    if delta < 0.01:
        print("Too Close")
        return 0
    qCrossed = qmForward.cross(upVector)
    qCrossed.normalize()
    qmProjected = upVector.cross(qCrossed)
    cosAngle = qmProjected.dot(forwardVector)
    # We are almost done, except for the fact that the cosine is a number between
    # -1 and 1, which always gets us the value of the cosine of the SHORTEST arc.
    # Example:
    # case1           case2  
    # v1                 v1  
    #   |             |      
    #   |             |      
    #   |             |      
    # a / b         b \ a    
    #  /               \     
    # /                 \    
    # v2                 v2
    # In both cases above v1.dot(v2) will return the same value,
    # even though in case2 v2 is to the right of v1.
    # In case 1 We need angle a.
    # In case 2 We need angle b.
    # In case 1 v2 is to left of the plane made by the @upVector & @forwardVector.
    # We can use the sign of the dot product against the @rightVector to figure this out.
    if qmProjected.dot(rightVector) < 0:
        return math.acos(cosAngle)
    return -math.acos(cosAngle)


def _GetTransformedBasisVectors(matrix:Matrix, up: Vector, forward: Vector, right: Vector):
    """
    Returns tuple of normalized vectors (upTransformed, forwardTransformed, rightTransformed) according to the
    armature world matrixx 
    """
    upTransformed = matrix @ up
    forwardTransformed = matrix @ forward
    rightTransformed = matrix @ right
    return (upTransformed.normalized(), forwardTransformed.normalized(), rightTransformed.normalized())


def _ExtractZaxisWorldQuaternions(armatureObj:bpy.types.Armature, worldQuaternionsList: list[Quaternion]):
    """
    The idea of this function is that We have a list of world quaternions,
    We need to calculate the influence of rotation around the Zaxis that is embedded in
    each quaternion in the input list.
    This function will be used later to split the world quaternions so that the zAxis
    influence is applied to the parent Armature, and We remove the zAxis influence and
    force it back to the root hip bone.  
    Returns a tuple (zAxisWorldQuaternionsList, retMirroredQuaternionList, zAxisAnglesList)
    """
    # REMARK: We don't call _GetTransformedBasisVectors() anymore because the starting armature rotation
    # is applied as the default rotation.
    #upBasis, forwardBasis, rightBasis = _GetTransformedBasisVectors(armatureObj.matrix_world, cmn.Axis.Z, cmn.Axis.Y, cmn.Axis.X)
    upBasis, forwardBasis, rightBasis = cmn.Axis.Z, cmn.Axis.Y, cmn.Axis.X
    retQuaternionList = []
    retMirroredQuaternionList = []
    retAnglesList = []
    for q in worldQuaternionsList:
        angleAroundZaxis = ExtractAngleAroundUpVectorFromQuaternion(upBasis, forwardBasis, rightBasis, q, 2)
        newQ = Quaternion(cmn.Axis.Z, angleAroundZaxis)
        newQMirrored = Quaternion(cmn.Axis.Z, angleAroundZaxis + math.pi)
        retQuaternionList.append(newQ)
        retMirroredQuaternionList.append(newQMirrored)
        angleDeg = math.degrees(angleAroundZaxis)
        retAnglesList.append((angleAroundZaxis, angleDeg))
    return (retQuaternionList, retMirroredQuaternionList, retAnglesList)


def _RemoveInfluenceOfQuaternionFromQuaternion(qInfluence: Quaternion, q: Quaternion):
    """
    This function removes the influence of quaternion @qInfluence from @q.
    The mathematical principal is that:
    q = qInfluence @ qX. This function returns qX.
    qInfluenceInv @ q = qInfluenceInv @ qInfluence @ qX
    qInfluenceInv @ q = qX
    """
    qInfluenceInv = qInfluence.inverted()
    qX = qInfluenceInv @ q
    return qX

#Returns a new list of quaternions where all quaternions in @qList
#have the rotations in qListDelta removed from them
def _RemoveInfluenceOfQuaternionsFromQuaternions(qListDelta, qList):
    retList = []
    for qInfluence, q in zip(qListDelta, qList):
        newQ = _RemoveInfluenceOfQuaternionFromQuaternion(qInfluence, q)
        retList.append(newQ)
    return retList


def _GetPoseBoneQuaternions(armatureObj: bpy.types.Armature, boneName: str):
    """
    Returns a tuple (localQuaternionsList, transformMatrix, worldQuaternionsList)
       Where:
       localQuaternionsList is a list of Quaternion with local bone data as
           extracted from FCurves.
       transformMatrix A 4x4 World transform Matrix used to transform the
           Quaternions in localQuaternionsList.
       worldQuaternionsList The transformed Quaternions, now in World coordinates.
     This is a simplified function because it doesn't traverse the bone hierarchy
     at all. It assummes @boneName is the name of the first child bone of the
     armature @obj.
    """
    localQuaternionsList = fcv.GetPoseBoneLocalQuaternionsFromFcurves(armatureObj, boneName)
    poseBoneObj = cmn.GetPoseBoneFromArmature(armatureObj, boneName)
    transformMatrix, worldQuaternionsList = _TransformPoseBoneLocalQuaternionsToWorldQuaternions(armatureObj, poseBoneObj, localQuaternionsList)
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


def _ClearDataForAxes(vectorList, clearX, clearY, clearZ):
    print("Will clear axes: ", clearX, clearY, clearZ)
    for v in vectorList:
        if clearX:
            v.x = 0.0
        if clearY:
            v.y = 0.0
        if clearZ:
            v.z = 0.0        


def AddLinearRotationToArmatureLocalRotationData(sceneObj: bpy.types.Scene, armatureObj: bpy.types.Armature, axis: Vector, angularSpeed: float, animationFps: float):
    """
    @angularSpeed: In radians per second.
    REMARK: This function works well, but the rotation is local.
    """
    fcurve = fcv.GetArmatureFCurveFromDataPath(armatureObj, fcv.FCurveDataPath.QUATERNION_W)
    if fcurve is None:
        #Need to allocate the quaternion fcurves according to the root bone.
        rootBoneName = cmn.GetRootBone(armatureObj).name
        fcv.AllocateQuaternionKeyFramesFromPoseBoneToArmature(rootBoneName, armatureObj)
        print(f"Created the same amount of quaternion key frames from bone '{rootBoneName}'' in the armature '{armatureObj.name}'")
    else:
        print(f"The armature '{armatureObj.name}' already has quaternion data.")
    # The fcurves exist, let's fetch all the quaternions for each keyframe.
    quaternionList = fcv.GetArmatureLocalQuaternionsFromFcurves(armatureObj)
    print(f"Collected the quaternion data from the armature '{armatureObj.name}'.")
    #r s   r
    #- - = -
    #s f   f
    radsPerFrame = angularSpeed * (1.0/animationFps)
    print(f"radsPerFrame={radsPerFrame}")
    radians = 0.0
    newQuaternionList = []
    for q in quaternionList:
        parentQ = Quaternion(axis, radians)
        newQ = parentQ @ q
        newQuaternionList.append(newQ)
        radians += radsPerFrame
    print(f"Transformed the quaternion data from the armature '{armatureObj.name}'.")
    fcv.SetQuaternionDataForArmatureKeyFrames(armatureObj, newQuaternionList)
    print(f"Finished injecting additional rotation animation to the armature '{armatureObj.name}'.")


#ef ProcessMotion(sceneObj, armatureObj, hipBoneName,
#                 extractTranslationX, zeroOutTranslationX,
#                 extractTranslationY, zeroOutTranslationY,
#                 extractTranslationZ, zeroOutTranslationZ,
#                 extractRotationZ, zeroOutRotationZ,
#                 dumpCSVs=False):
#   """
#   Main function that transforms a Motion type of Asset per Lumberyard 
#   requirements.
#
#   In Short: Transfers root motion
#    from the Hips bone to the "Armature" object. The motion data is transferred
#    from Hips bone FCurves to  the "Armature" FCurves.
#
#   @sceneObj (bpy.types.Scene)
#   @armatureObj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
#   @hipBoneName (string). Name of the "Hips" bone as originated by Mixamo.
#   @extractTranslationX,Y,Z (bool). Extract X,Y,Z Axis Translation.
#   @zeroOutTranslationX,Y,Z (bool). Zero Out X,Y,Z Axis Translation upon
#       extraction.
#   @extractRotationZ (bool). Extract Rotation around Z Axis.
#   @zeroOutRotationZ (bool). Zero Out Rotation around Z Axis upon extraction.
#   @dumpCSVs (bool) DEBUG Only. Dump motion vector data as CSV files
#   """
#   print(f"Armature world matrix:\n{armatureObj.matrix_world}")
#   hipLocalLocations, hipWorldMatrix, hipWorldLocations = _GetPoseBoneLocations(armatureObj, hipBoneName)
#   print(f"hipWorldMatrix = {hipWorldMatrix}")
#   yield Status("Got '{}' bone local and world locations".format(hipBoneName))
#   if dumpCSVs:
#       _SaveVectorListAsCsv(hipLocalLocations, 0,
#           "HipLocalLocations.csv")
#       _SaveVectorListAsCsv(hipWorldLocations, 0,
#           "HipWorldLocations.csv")
#
#   if extractRotationZ:
#       (localQuaternionsList, transformMatrix, worldQuaternionsList) = _GetPoseBoneQuaternions(armatureObj, hipBoneName)
#       print(f"transformMatrix = {transformMatrix}")
#       yield Status("Got '{}' bone local and world rotations".format(hipBoneName))
#       if dumpCSVs:
#           _SaveQuaternionListAsCsv(localQuaternionsList, 0, "hipLocalQuaternionsList.csv")
#           _SaveQuaternionListAsCsv(worldQuaternionsList, 0, "hipWorldQuaternionsList.csv")
#
#       #The idea is that zAxisWorldQuaternionsList will contain the world rotations of the root bone
#       #around zAxis.
#       zAxisWorldQuaternionsList, mirroredZAxisWorldQuaternionsList, zAxisAnglesList = _ExtractZaxisWorldQuaternions(armatureObj, worldQuaternionsList)
#       #noZAxisWorldQuaternionsList will be the new world rotations for the hip bone because it has
#       #rotation around zAxis removed from it.
#       noZAxisWorldQuaternionsList = _RemoveInfluenceOfQuaternionsFromQuaternions(zAxisWorldQuaternionsList, worldQuaternionsList)
#       #Now hipsLocalQuaternionsListNoZ contains the new quaternions for the hip bone but zAxis rotation has been
#       #removed from it.
#       hipsLocalQuaternionsListNoZ = _TransformQuaternionsList(hipWorldMatrix.inverted(), noZAxisWorldQuaternionsList)
#       if dumpCSVs:
#           _SaveQuaternionListAsCsv(zAxisWorldQuaternionsList, 0, "zAxisWorldQuaternionsList.csv")
#           _SaveQuaternionListAsCsv(mirroredZAxisWorldQuaternionsList, 0, "mirroredZAxisWorldQuaternionsList.csv")
#           _SaveQuaternionListAsCsv(noZAxisWorldQuaternionsList, 0, "noZAxisWorldQuaternionsList.csv")
#           _SaveQuaternionListAsCsv(hipsLocalQuaternionsListNoZ, 0, "hipsLocalQuaternionsListNoZ.csv")
#           _SaveAxisAnglesListAsCsv(zAxisAnglesList, Vector((0.0, 0.0, 1.0)), 0, "zAxisWorldAnglesList.csv")
#
#   
#   #startTimeNS = time.perf_counter_ns()
#   #Extract World Positions of all the key frames for the Hip bone.
#   keyFrameNumbersList = fcv.GetKeyFrameNumbersListPoseBoneDataPath(armatureObj, hipBoneName, fcv.FCurveDataPath.LOCATION_X)
#   keyFrameStart = keyFrameNumbersList[0]
#   keyFrameEnd = keyFrameNumbersList[-1]
#   keyFrameCount = len(keyFrameNumbersList)
#   print("Frame Count is ", keyFrameCount)
#   sceneObj.frame_start = keyFrameStart
#   sceneObj.frame_end = keyFrameEnd
#
#   #Extract World Positions of the center of the bottom plane center point
#   #of the Bound Box per key frame.
#   #This data will be used to calculate root motion in the Z(Up) axis
#   bboxBaseLocations = _GetBBoxWorldLocations(
#       sceneObj, armatureObj, keyFrameNumbersList)
#   yield Status("Got Armature bottom plane center world location per keyframe")
#   if dumpCSVs:
#       _SaveVectorListAsCsv(bboxBaseLocations, keyFrameStart, "BBoxWorldLocations.csv")
#
#   # Experimental
#   # hipBoneMatrixList = _GetPoseBoneKeyFrameMatrices(sceneObj, armatureObj, hipBoneName, keyFrameNumbersList)
#
#   rawHipWorldAxisDataX = _GetVectorListAxisAsArray(hipWorldLocations, 0)
#   rawHipWorldAxisDataY = _GetVectorListAxisAsArray(hipWorldLocations, 1)
#   rawHipWorldAxisDataZ = _GetVectorListAxisAsArray(hipWorldLocations, 2)
#   rawFeetWorldAxisDataZ = _GetVectorListAxisAsArray(bboxBaseLocations, 2)
#   yield Status("extracted world location axis arrays from '{}' bone".format(hipBoneName))
#
#   if extractTranslationX or extractTranslationY or extractTranslationZ:
#       _ClearCloseToZeroDataFromArrayInPlace(rawFeetWorldAxisDataZ)
#       yield Status("Cleared close to 0.0 feet world Z values")
#
#       feetWorldLocations = _BuildVectorListFromArrays(
#           rawHipWorldAxisDataX, rawHipWorldAxisDataY, rawFeetWorldAxisDataZ)
#       yield Status("Built feet world locations list from '{}' bone".format(hipBoneName))
#       if dumpCSVs:
#           _SaveVectorListAsCsv(feetWorldLocations, keyFrameStart,
#               "feetWorldLocations_beforeClear.csv")
#
#       #Make sure the transform of the Armature node has all the required keyframes allocated.
#       fcv.AllocateLocationKeyFramesFromPoseBoneToArmature(hipBoneName, armatureObj)
#       yield Status(f"Allocated all 'location' KeyFrames in Armature named '{armatureObj.name}' from bone '{hipBoneName}'")
#
#       #Let's clear the feet world locations data for the axis that won't require root motion extraction
#       _ClearDataForAxes(feetWorldLocations, not extractTranslationX,
#                         not extractTranslationY, not extractTranslationZ)
#       yield Status("Cleared motion data for the following axes X({}), Y({}), Z({})".format(
#           not extractTranslationX, not extractTranslationY, not extractTranslationZ))
#       if dumpCSVs:
#           _SaveVectorListAsCsv(feetWorldLocations, keyFrameStart,
#               "feetWorldLocations_afterClear.csv")
#
#       #Get the feetWorldLocations transformed in hips local space. The resulting
#       #vectors will be deltas that will be subtracted from the hip local locations.
#       hipBoneWorldLocationDeltas = _SubtractVectorLists(hipWorldLocations, feetWorldLocations)
#       newHipLocalLocations = _TransformVectorList(hipWorldMatrix.inverted(), hipBoneWorldLocationDeltas)
#
#       yield Status("Got '{}' bone local locations from feet world locations".format(hipBoneName))
#       if dumpCSVs:
#           _SaveVectorListAsCsv(hipBoneWorldLocationDeltas, keyFrameStart,
#               "hipBoneWorldLocationDeltas.csv")
#           _SaveVectorListAsCsv(newHipLocalLocations, keyFrameStart,
#               "newHipLocalLocations.csv")
#           #_SaveVectorListAsCsv(deltaHipLocalLocations, keyFrameStart,
#           #    "deltaHipLocalLocations.csv")
#
#       #Subtract from hip the motions that will be transferred to the root.
#       #fcv.SubtractLocationDataFromPoseBoneKeyFrames(armatureObj, hipBoneName, deltaHipLocalLocations)
#       fcv.SetLocationDataForPoseBoneKeyFrames(armatureObj, hipBoneName, newHipLocalLocations)
#       yield Status(f"Removed motion data from '{hipBoneName}' bone locations FCurve")
#       
#
#       if zeroOutTranslationX or zeroOutTranslationY or zeroOutTranslationZ:
#           _ClearDataForAxes(feetWorldLocations, zeroOutTranslationX,
#                             zeroOutTranslationY, zeroOutTranslationZ)
#           yield Status("zeroed Out motion data for the following axes X({}), Y({}), Z({})".format(
#           zeroOutTranslationX, zeroOutTranslationY, zeroOutTranslationZ))
#           if dumpCSVs:
#               _SaveVectorListAsCsv(feetWorldLocations, keyFrameStart,
#               "feetWorldLocations_afterZeroedOut.csv")
#
#       fcv.SetLocationDataForArmatureKeyFrames(armatureObj, feetWorldLocations)
#       yield Status("Set location root motion to '{}' locations FCurve".format(armatureObj.name))
#
#   if extractRotationZ:
#       #Apply rotation around Z axis.
#       fcv.AllocateQuaternionKeyFramesFromPoseBoneToArmature(hipBoneName, armatureObj)
#       yield Status(f"Inserted empty rotation keyframes in '{armatureObj.name}' quaternions FCurve")
#
#       #Update Hips rotations with noZ rotation.
#       fcv.SetQuaternionDataForPoseBoneFCurves(armatureObj, hipBoneName, hipsLocalQuaternionsListNoZ)
#       yield Status(f"Removed Z axis rotation from '{hipBoneName}' bone quaternions FCurve")
#
#       if not zeroOutRotationZ:
#           #Now, the worldEulerOnlyZ rotations need to be converted to the root bone local frame:
#           worldMatrix = armatureObj.matrix_world
#
#           rootLocalQuaternionsListOnlyZ = _TransformQuaternionsList(worldMatrix.inverted(), zAxisWorldQuaternionsList)
#           yield Status("Transformed '{}' world Quaternions to local Quaternions".format(armatureObj.name))
#
#           fcv.SetQuaternionDataForArmatureKeyFrames(armatureObj, rootLocalQuaternionsListOnlyZ)
#           yield Status("Applied root motion Z rotation to '{}' quaternion FCurves".format(armatureObj.name))
#   
#   #InjectRotation(sceneObj, armatureObj, cmn.Axis.Z, math.pi, 60.0)
#   RotateAnimation(armatureObj, cmn.Axis.Z, -math.pi * 0.5)
#
#   yield Status("Completed root motion extraction from '{}' bone to '{}'".format(hipBoneName, armatureObj.name))


def ExtractRootMotion(sceneObj:bpy.types.Scene,
                      armatureObj: bpy.types.Armature,
                      hipBoneName: str,
                      extractTranslationX: bool,
                      extractTranslationY: bool,
                      extractTranslationZ: bool,
                      extractRotationZ: bool,
                      dumpCSVs: bool =False):
    """
    Extracts root motion animation data from the Hip Bone and assigns it
    as new animation key frames to the @armatureObj transform.

    In Short: Transfers root motion
     from the Hips bone to the "Armature" object. The motion data is transferred
     from Hips bone FCurves to  the "Armature" FCurves.

    @sceneObj (bpy.types.Scene)
    @armatureObj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
    @hipBoneName (string). Name of the "Hips" bone as originated by Mixamo.
    @extractTranslationX,Y,Z (bool). Extract X,Y,Z Axis Translation.
    @extractRotationZ (bool). Extract Rotation around Z Axis.
    @dumpCSVs (bool) DEBUG Only. Dump motion vector data as CSV files
    """
    print(f"Armature world matrix before resetting orientation:\n{armatureObj.matrix_world}")

    # We need to set the current rotation as 0,0,0
    cmn.ApplyCurrentRotationAs000(armatureObj)
    yield Status(f"Applied current rotation of '{armatureObj.name}' as 0,0,0")

    hipLocalLocations, hipWorldMatrix, hipWorldLocations = _GetPoseBoneLocations(armatureObj, hipBoneName)
    print(f"hipWorldMatrix = {hipWorldMatrix}")
    yield Status("Got '{}' bone local and world locations".format(hipBoneName))
    if dumpCSVs:
        _SaveVectorListAsCsv(hipLocalLocations, 0,
            "HipLocalLocations.csv")
        _SaveVectorListAsCsv(hipWorldLocations, 0,
            "HipWorldLocations.csv")

    if extractRotationZ:
        (localQuaternionsList, transformMatrix, worldQuaternionsList) = _GetPoseBoneQuaternions(armatureObj, hipBoneName)
        print(f"transformMatrix = {transformMatrix}")
        yield Status("Got '{}' bone local and world rotations".format(hipBoneName))
        if dumpCSVs:
            _SaveQuaternionListAsCsv(localQuaternionsList, 0, "hipLocalQuaternionsList.csv")
            _SaveQuaternionListAsCsv(worldQuaternionsList, 0, "hipWorldQuaternionsList.csv")

        #The idea is that zAxisWorldQuaternionsList will contain the world rotations of the root bone
        #around zAxis.
        zAxisWorldQuaternionsList, mirroredZAxisWorldQuaternionsList, zAxisAnglesList = _ExtractZaxisWorldQuaternions(armatureObj, worldQuaternionsList)
        #noZAxisWorldQuaternionsList will be the new world rotations for the hip bone because it has
        #rotation around zAxis removed from it.
        noZAxisWorldQuaternionsList = _RemoveInfluenceOfQuaternionsFromQuaternions(zAxisWorldQuaternionsList, worldQuaternionsList)
        #Now hipsLocalQuaternionsListNoZ contains the new quaternions for the hip bone but zAxis rotation has been
        #removed from it.
        hipsLocalQuaternionsListNoZ = _TransformQuaternionsList(hipWorldMatrix.inverted(), noZAxisWorldQuaternionsList)
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

        yield Status("Got '{}' bone local locations from feet world locations".format(hipBoneName))
        if dumpCSVs:
            _SaveVectorListAsCsv(hipBoneWorldLocationDeltas, keyFrameStart,
                "hipBoneWorldLocationDeltas.csv")
            _SaveVectorListAsCsv(newHipLocalLocations, keyFrameStart,
                "newHipLocalLocations.csv")

        #Subtract from hip the motions that will be transferred to the root.
        fcv.SetLocationDataForPoseBoneKeyFrames(armatureObj, hipBoneName, newHipLocalLocations)
        yield Status(f"Removed motion data from '{hipBoneName}' bone locations FCurve")

        fcv.SetLocationDataForArmatureKeyFrames(armatureObj, feetWorldLocations)
        yield Status("Set location root motion to '{}' locations FCurve".format(armatureObj.name))

    if extractRotationZ:
        #Allocate Key frame data for the Armature Quaternions.
        fcv.AllocateQuaternionKeyFramesFromPoseBoneToArmature(hipBoneName, armatureObj)
        yield Status(f"Inserted empty rotation keyframes in '{armatureObj.name}' quaternions FCurve")

        #Update Hips rotations with noZ rotation.
        fcv.SetQuaternionDataForPoseBoneFCurves(armatureObj, hipBoneName, hipsLocalQuaternionsListNoZ)
        yield Status(f"Removed Z axis rotation from '{hipBoneName}' bone quaternions FCurve")

        #Now, the worldEulerOnlyZ rotations need to be converted to the root bone local frame:
        worldMatrix = armatureObj.matrix_world

        rootLocalQuaternionsListOnlyZ = _TransformQuaternionsList(worldMatrix.inverted(), zAxisWorldQuaternionsList)
        yield Status(f"Transformed '{armatureObj.name}' world Quaternions to local Quaternions")

        fcv.SetQuaternionDataForArmatureKeyFrames(armatureObj, rootLocalQuaternionsListOnlyZ)
        yield Status(f"Applied root motion Z rotation to '{armatureObj.name}' quaternion FCurves")

    yield Status(f"Completed root motion extraction from '{hipBoneName}' bone to '{armatureObj.name}'")


def ClearRootMotionTranslation(armatureObj: bpy.types.Armature,
                  zeroOutTranslationX: bool,
                  zeroOutTranslationY: bool,
                  zeroOutTranslationZ: bool):
    """
    Clears (Forces to 0.0) Translation data from the root motion key frames
    for the selected Axis.

    @zeroOutTranslationX,Y,Z  Switches for Axis to clear.
    """
    feetWorldLocations = fcv.GetArmatureLocalLocationsFromFcurves(armatureObj)
    yield Status(f"Extracted local location data from armature '{armatureObj.name}'")

    _ClearDataForAxes(feetWorldLocations,
        zeroOutTranslationX, zeroOutTranslationY, zeroOutTranslationZ)
    yield Status(f"Cleated motion data for the following axes X({zeroOutTranslationX}), Y({zeroOutTranslationY}), Z({zeroOutTranslationZ})")

    fcv.SetLocationDataForArmatureKeyFrames(armatureObj, feetWorldLocations)
    yield Status(f"New root motion translation has been applied to '{armatureObj.name}' locations FCurve")


# REMARK: This function breaks for cases where the hip bone contains
# weird rotation in between frames.
#def ClearRootMotionRotationAroundZAxis(armatureObj: bpy.types.Armature):
#    """
#    Clears (Forces to 0.0) Rotation data from the root motion key frames
#    around Z Axis (World Up).
#    """
#    quaternionsList = fcv.GetArmatureLocalQuaternionsFromFcurves(armatureObj)
#    yield Status(f"Extracted local quaternion data from armature '{armatureObj.name}'")
#
#    newQuaternionList = []
#    for q in quaternionsList:
#        euler = q.to_euler('XYZ')
#        print(f"Euler x({euler.x}), y({euler.y}), z({math.degrees(euler.z)})")
#        euler.z = 0.0 + math.pi
#        newQuaternionList.append(euler.to_quaternion())
#    yield Status(f"Cleared rotation around Z axis in local quaternions")
#
#    fcv.SetQuaternionDataForArmatureKeyFrames(armatureObj, newQuaternionList)
#    yield Status(f"New root motion quaternions have been applied to '{armatureObj.name}' FCurves")


def RotateArmatureAnimationData(armatureObj: bpy.types.Armature, axis: Vector, angle: float):
    """
    Rotates both the translation and orientation of the armature by the axis+angle
    @angle is in radians
    """
    originalLocations = fcv.GetArmatureLocationsFromFcurves(armatureObj)
    yield Status("Got current locations from animation data")
    rotMatrix4x4 = Matrix.Rotation(angle, 4, axis)
    transformedLocations = _TransformVectorList(rotMatrix4x4, originalLocations)
    yield Status("Transformed current locations in list")
    fcv.SetLocationDataForArmatureKeyFrames(armatureObj, transformedLocations)
    yield Status("Applied transformed locations into the Armature fcurves")

    #Now let's change the orientation of the armature.
    fcurve = fcv.GetArmatureFCurveFromDataPath(armatureObj, fcv.FCurveDataPath.QUATERNION_W)
    if fcurve is None:
        #Need to allocate the quaternion fcurves according to the root bone.
        rootBoneName = cmn.GetRootBone(armatureObj).name
        fcv.AllocateQuaternionKeyFramesFromPoseBoneToArmature(rootBoneName, armatureObj)
        yield Status(f"Created the same amount of quaternion key frames from bone '{rootBoneName}'' in the armature '{armatureObj.name}'")
    else:
        yield Status(f"The armature '{armatureObj.name}' already has quaternion data.")
    # The fcurves exist, let's fetch all the quaternions for each keyframe.
    quaternionList = fcv.GetArmatureLocalQuaternionsFromFcurves(armatureObj)
    yield Status(f"Collected the quaternion data from the armature '{armatureObj.name}'.")
    newQuaternionList = _TransformQuaternionsList(rotMatrix4x4, quaternionList)
    yield Status(f"Transformed the quaternion data from the armature '{armatureObj.name}'.")
    fcv.SetQuaternionDataForArmatureKeyFrames(armatureObj, newQuaternionList)
    yield Status("Applied transformed quaternions into the Armature fcurves")