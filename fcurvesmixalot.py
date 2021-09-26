# Useful functions to work with fcurves (animation key frames)
import bpy
import mathutils

class FCurveDataPath:
    LOCATION_X = ('location', 0)
    LOCATION_Y = ('location', 1)
    LOCATION_Z = ('location', 2)
    QUATERNION_W = ('rotation_quaternion', 0)
    QUATERNION_X = ('rotation_quaternion', 1)
    QUATERNION_Y = ('rotation_quaternion', 2)
    QUATERNION_Z = ('rotation_quaternion', 3)
    SCALE_X = ('scale', 0)
    SCALE_Y = ('scale', 1)
    SCALE_Z = ('scale', 2)

def BuildPoseBoneFCurveDataPath(boneName, vectorName):
    return f"pose.bones[\"{boneName}\"].{vectorName}"

def GetPoseBoneFCurveFromArmature(armatureObj, poseBoneName, data_path, parameterIndex):
    """
    In Blender the FCurves are used to define the Key Frames.
    In general, for a single object, there's one FCurve for each of
    the following properties.
    data_path,           index
    'location',            0 (.x)
    'location',            1 (.y)
    'location',            2 (.z)
    'rotation_quaternion', 0 (.w) 
    'rotation_quaternion', 1 (.x)
    'rotation_quaternion', 2 (.y)
    'rotation_quaternion', 3 (.z)
    'scale',               0 (.x)             
    'scale',               1 (.y)
    'scale',               2 (.z)
    For more tips about this, see: https://docs.blender.org/api/blender_python_api_2_75_release/info_quickstart.html#animation
    Returns a bpy.types.FCurve
    """
    completePath = BuildPoseBoneFCurveDataPath(poseBoneName, data_path)
    return armatureObj.animation_data.action.fcurves.find(completePath, index=parameterIndex)

def GetPoseBoneFCurveFromDataPath(armatureObj, poseBoneName, fCurveDataPath):
    """
    A wrapper of GetPoseBoneFCurveFromArmature
    @armatureObj bpy.Types.Armature
    @poseBoneName str
    @fCurveDataPath is one of the class constants in FCurveDataPath
    """
    return GetPoseBoneFCurveFromArmature(armatureObj, poseBoneName, fCurveDataPath[0], fCurveDataPath[1])


def GetArmatureFCurveFromDataPath(armatureObj: bpy.types.Armature, fCurveDataPath: FCurveDataPath) -> bpy.types.FCurve :
    return armatureObj.animation_data.action.fcurves.find(fCurveDataPath[0], index=fCurveDataPath[1])


def GetPoseBoneLocalLocationsFromFcurves(armatureObj, poseBoneName):
    """
    Returns a list of vectors. Each vector is the raw location
    data as found in the FCurves
    """
    retList = []
    fcurveX = GetPoseBoneFCurveFromDataPath(armatureObj, poseBoneName, FCurveDataPath.LOCATION_X)
    fcurveY = GetPoseBoneFCurveFromDataPath(armatureObj, poseBoneName, FCurveDataPath.LOCATION_Y)
    fcurveZ = GetPoseBoneFCurveFromDataPath(armatureObj, poseBoneName, FCurveDataPath.LOCATION_Z)
    lenX = len(fcurveX.keyframe_points)
    lenY = len(fcurveY.keyframe_points)
    lenZ = len(fcurveZ.keyframe_points)
    if (lenX != lenY) or (lenX != lenZ):
        print(f"Was expecting fcurves of the same length. lenX={lenX}, lenY={lenY}, lenZ={lenZ}")
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
        v = mathutils.Vector( (KfpX.co[1], KfpY.co[1], KfpZ.co[1]) )
        retList.append(v)

    return retList

def GetKeyFramesRangeInfoFromFCurve(fcurve: bpy.types.FCurve) -> list[int, int, int]:
    """
    returns tuple (startFrameNumber, endFrameNumber, numKeyFrames)
    """
    keyFramePoints = fcurve.keyframe_points
    startFrameNumber = int(keyFramePoints[0].co.x)
    endFrameNumber = int(keyFramePoints[-1].co.x)
    numKeyFrames = len(keyFramePoints)
    return (startFrameNumber, endFrameNumber, numKeyFrames)


def GetKeyFramesRangeInfoFromPoseBoneDataPath(armatureObj: bpy.types.Armature, poseBoneName: str, fCurveDataPath: FCurveDataPath) -> list[int, int, int]:
    """
    returns tuple (startFrameNumber, endFrameNumber, numKeyFrames)
    """
    fcurve = GetPoseBoneFCurveFromDataPath(armatureObj, poseBoneName, fCurveDataPath)
    return GetKeyFramesRangeInfoFromFCurve(fcurve)


def GetKeyFrameNumbersListPoseBoneDataPath(armatureObj: bpy.types.Armature, poseBoneName: str, fCurveDataPath: FCurveDataPath) -> list[int]:
    """
    returns list of integers where each integer is the number of a key frame
    """
    retList = []
    fcurve = GetPoseBoneFCurveFromDataPath(armatureObj, poseBoneName, fCurveDataPath)
    if fcurve is None:
        return retList
    keyFramePoints = fcurve.keyframe_points
    for kfp in keyFramePoints:
        frameNumber = int(kfp.co.x)
        retList.append(frameNumber)
    return retList


def CreateFCurveForArmatureObj(armatureObj: bpy.types.Armature, fCurveDataPath: FCurveDataPath) -> bpy.types.FCurve:
    """
    If the FCurve, with the given data path @fCurveDataPath, already exists it returns the existing fcurve object.
    If the FCurve doesn't exist creates it and returns it.
    The created FCurve will have one dummy key frame at frame number 1.
    """
    fcurve = GetArmatureFCurveFromDataPath(armatureObj, fCurveDataPath)
    if fcurve is not None:
        print(f"The fcurve {fCurveDataPath[0]} at index {fCurveDataPath[1]} already exists")
        return fcurve
    if not armatureObj.keyframe_insert(fCurveDataPath[0], index=fCurveDataPath[1], frame=1):
        print(f"Failed to insert new empty KeyFrame at path {fCurveDataPath[0]} index {fCurveDataPath[1]}")
        return None
    return GetArmatureFCurveFromDataPath(armatureObj, fCurveDataPath)


def _RemoveKeyFrames(fcurve: bpy.types.FCurve, fromFrameIndex: int = 0):
    """
    Removes key frames from @fcurve, starting at array location @fromFrameIndex.
    Remark:  @fromFrameIndex is a regular array index, it is not a Frame Number.
        FYI, the Frame Number is fcurve.keyframe_points[@fromFrameIndex].co.x
    """
    targetLength = fromFrameIndex
    while len(fcurve.keyframe_points) > targetLength:
        kfp = fcurve.keyframe_points[fromFrameIndex]
        fcurve.keyframe_points.remove(kfp, fast=True)


def _CopyKeyFrame(dstKfp: bpy.types.Keyframe, srcKfp: bpy.types.Keyframe):
    """
    Using copy.deepcopy() throws this exception:
    Error: cannot pickle 'Keyframe' object
    """
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


def _CopyKeyFrames(dstFcurve, srcFcurve, setDefaultValue=False, defaultValue=0.0, emptySrcStartingAtFrameIndex = -1):
    keyFramesCount = len(srcFcurve.keyframe_points)
    if keyFramesCount < 1:
        print("The source fcurve was already empty")
        return
    #Clear all existing keyframes in dstFcurve.
    _RemoveKeyFrames(dstFcurve)
    print("Removed all previous keyframes in destination Fcurve")
    dstFcurve.keyframe_points.add(keyFramesCount)
    for frameIndex in range(keyFramesCount):
        srcKfp = srcFcurve.keyframe_points[frameIndex]
        dstKfp = dstFcurve.keyframe_points[frameIndex]
        _CopyKeyFrame(dstKfp, srcKfp)
        if setDefaultValue:
            dstKfp.co[1] = defaultValue
    if setDefaultValue:
        print(f"Copied {keyFramesCount} keyframes from source to destination with defaultValue {defaultValue}")
    else:
        print(f"Copied {keyFramesCount} keyframes from source to destination.")
    if emptySrcStartingAtFrameIndex < 0:
        return
    _RemoveKeyFrames(srcFcurve, emptySrcStartingAtFrameIndex)
    print(f"Removed keyframes from source starting at frame index {emptySrcStartingAtFrameIndex}")



def AllocateLocationKeyFramesFromPoseBoneToArmature(poseBoneName: str, armatureObj: bpy.types.Armature):
    """
    The 'location' (x, y, z) fcurves of the armatureObj will be created if they don't exist.
    Forces the new fcurves to have the exact same key frames as the @poseBoneName, the only
    difference is that the value (KeyFrame.co.y) will set to 0 in all ther key frames of all the 3 fcurves
    created for armatureObj.
    """
    dataPaths = (
        FCurveDataPath.LOCATION_X,
        FCurveDataPath.LOCATION_Y,
        FCurveDataPath.LOCATION_Z,
    )
    for axis, dataPath in enumerate(dataPaths):
        newFcurve = CreateFCurveForArmatureObj(armatureObj, dataPath)
        srcFCurve = GetPoseBoneFCurveFromDataPath(armatureObj, poseBoneName, dataPath)
        _CopyKeyFrames(newFcurve, srcFCurve, setDefaultValue=True, defaultValue=0.0)


def AllocateQuaternionKeyFramesFromPoseBoneToArmature(poseBoneName: str, armatureObj: bpy.types.Armature):
    """
    The 'quaternion' (w, x, y, z) fcurves of the armatureObj will be created if they don't exist.
    Forces the new fcurves to have the exact same key frames as the @poseBoneName, the only
    difference is that the value (KeyFrame.co.y) will set to 0 in all ther key frames of all the 4 fcurves
    created for armatureObj.
    """
    dataPaths = (
        FCurveDataPath.QUATERNION_W,
        FCurveDataPath.QUATERNION_X,
        FCurveDataPath.QUATERNION_Y,
        FCurveDataPath.QUATERNION_Z,
    )
    for axis, dataPath in enumerate(dataPaths):
        newFcurve = CreateFCurveForArmatureObj(armatureObj, dataPath)
        srcFCurve = GetPoseBoneFCurveFromDataPath(armatureObj, poseBoneName, dataPath)
        if axis == 0: #W.
            _CopyKeyFrames(newFcurve, srcFCurve, setDefaultValue=True, defaultValue=1.0)
        else:
            _CopyKeyFrames(newFcurve, srcFCurve, setDefaultValue=True, defaultValue=0.0)    

def CopyLocationKeyFramesFromPoseBoneToArmature(poseBoneName: str, armatureObj: bpy.types.Armature):
    """
    Straight copy of the 'location' data (x, y, z) fcurves from a bone to the armature.
    Usually not very useful because animation data inside a bone are numbers local to the bone
    and the armature is usually world referenced.
    """
    dataPaths = (
        FCurveDataPath.LOCATION_X,
        FCurveDataPath.LOCATION_Y,
        FCurveDataPath.LOCATION_Z,
    )
    for axis, dataPath in enumerate(dataPaths):
        newFcurve = CreateFCurveForArmatureObj(armatureObj, dataPath)
        srcFCurve = GetPoseBoneFCurveFromDataPath(armatureObj, poseBoneName, dataPath)
        _CopyKeyFrames(newFcurve, srcFCurve)


def SubtractLocationDataFromPoseBoneKeyFrames(armatureObj: bpy.types.Armature , boneName: str, locationsList: list[mathutils.Vector]):
    dataPaths = (
        FCurveDataPath.LOCATION_X,
        FCurveDataPath.LOCATION_Y,
        FCurveDataPath.LOCATION_Z,
    )
    for axis, dataPath in enumerate(dataPaths):
        fcurve = GetPoseBoneFCurveFromDataPath(armatureObj, boneName, dataPath)
        keyFramesCount = len(fcurve.keyframe_points)
        if keyFramesCount < 1:
            print(f"The fcurve from bone '{boneName}' and datapath '{dataPath}' was already empty")
            continue
        vectorCount = len(locationsList)
        if  vectorCount < keyFramesCount:
            print(f"The fcurve from bone '{boneName}' and datapath '{dataPath}' has {keyFramesCount} key frames, but the input list only has {vectorCount} vectors")
        count = min(vectorCount, keyFramesCount)
        for frameIndex in range(count):
            srcKfp = fcurve.keyframe_points[frameIndex]
            v = locationsList[frameIndex]
            srcKfp.co[1] -= v[axis]


def SetLocationDataForPoseBoneKeyFrames(armatureObj: bpy.types.Armature , boneName: str, locationsList: list[mathutils.Vector]):
    dataPaths = (
        FCurveDataPath.LOCATION_X,
        FCurveDataPath.LOCATION_Y,
        FCurveDataPath.LOCATION_Z,
    )
    for axis, dataPath in enumerate(dataPaths):
        fcurve = GetPoseBoneFCurveFromDataPath(armatureObj, boneName, dataPath)
        keyFramesCount = len(fcurve.keyframe_points)
        if keyFramesCount < 1:
            print(f"The fcurve from bone '{boneName}' and datapath '{dataPath}' was already empty")
            continue
        vectorCount = len(locationsList)
        if  vectorCount < keyFramesCount:
            print(f"The fcurve from bone '{boneName}' and datapath '{dataPath}' has {keyFramesCount} key frames, but the input list only has {vectorCount} vectors")
        count = min(vectorCount, keyFramesCount)
        for frameIndex in range(count):
            srcKfp = fcurve.keyframe_points[frameIndex]
            v = locationsList[frameIndex]
            srcKfp.co[1] = v[axis]

def SetLocationDataForArmatureKeyFrames(armatureObj: bpy.types.Armature, locationsList: list[mathutils.Vector]):
    dataPaths = (
        FCurveDataPath.LOCATION_X,
        FCurveDataPath.LOCATION_Y,
        FCurveDataPath.LOCATION_Z,
    )
    for axis, dataPath in enumerate(dataPaths):
        fcurve = GetArmatureFCurveFromDataPath(armatureObj, dataPath)
        keyFramesCount = len(fcurve.keyframe_points)
        if keyFramesCount < 1:
            print(f"The fcurve from armature '{armatureObj.name}' and datapath '{dataPath}' was already empty")
            continue
        vectorCount = len(locationsList)
        if  vectorCount < keyFramesCount:
            print(f"The fcurve from armature '{armatureObj.name}' and datapath '{dataPath}' has {keyFramesCount} key frames, but the input list only has {vectorCount} vectors")
        count = min(vectorCount, keyFramesCount)
        for frameIndex in range(count):
            srcKfp = fcurve.keyframe_points[frameIndex]
            v = locationsList[frameIndex]
            srcKfp.co[1] = v[axis]


#Returns a list of Quaternions
def GetPoseBoneLocalQuaternionsFromFcurves(armatureObj, boneName):
    retList = []

    fcurveW = GetPoseBoneFCurveFromDataPath(armatureObj, boneName, FCurveDataPath.QUATERNION_W)
    fcurveX = GetPoseBoneFCurveFromDataPath(armatureObj, boneName, FCurveDataPath.QUATERNION_X)
    fcurveY = GetPoseBoneFCurveFromDataPath(armatureObj, boneName, FCurveDataPath.QUATERNION_Y)
    fcurveZ = GetPoseBoneFCurveFromDataPath(armatureObj, boneName, FCurveDataPath.QUATERNION_Z)

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
        q = mathutils.Quaternion((KfpW.co[1], KfpX.co[1], KfpY.co[1], KfpZ.co[1]))
        retList.append(q)

    return retList


def SetQuaternionDataForPoseBoneFCurves(armatureObj: bpy.types.Armature , boneName: str, quaternionList: list[mathutils.Quaternion]):
    dataPaths = (
        FCurveDataPath.QUATERNION_W,
        FCurveDataPath.QUATERNION_X,
        FCurveDataPath.QUATERNION_Y,
        FCurveDataPath.QUATERNION_Z,
    )
    for axis, dataPath in enumerate(dataPaths):
        fcurve = GetPoseBoneFCurveFromDataPath(armatureObj, boneName, dataPath)
        keyFramesCount = len(fcurve.keyframe_points)
        if keyFramesCount < 1:
            print(f"The fcurve from bone '{boneName}' and datapath '{dataPath}' was already empty")
            continue
        quaternionCount = len(quaternionList)
        if  quaternionCount < keyFramesCount:
            print(f"The fcurve from bone '{boneName}' and datapath '{dataPath}' has {keyFramesCount} key frames, but the input list only has {quaternionCount} quaternions")
        count = min(quaternionCount, keyFramesCount)
        for frameIndex in range(count):
            srcKfp = fcurve.keyframe_points[frameIndex]
            q = quaternionList[frameIndex]
            srcKfp.co[1] = q[axis]


def SetQuaternionDataForArmatureKeyFrames(armatureObj: bpy.types.Armature, quaternionList: list[mathutils.Quaternion]):
    dataPaths = (
        FCurveDataPath.QUATERNION_W,
        FCurveDataPath.QUATERNION_X,
        FCurveDataPath.QUATERNION_Y,
        FCurveDataPath.QUATERNION_Z,
    )
    for axis, dataPath in enumerate(dataPaths):
        fcurve = GetArmatureFCurveFromDataPath(armatureObj, dataPath)
        keyFramesCount = len(fcurve.keyframe_points)
        if keyFramesCount < 1:
            print(f"The fcurve from armature '{armatureObj.name}' and datapath '{dataPath}' was already empty")
            continue
        quaternionCount = len(quaternionList)
        if  quaternionCount < keyFramesCount:
            print(f"The fcurve from armature '{armatureObj.name}' and datapath '{dataPath}' has {keyFramesCount} key frames, but the input list only has {quaternionCount} quaternions")
        count = min(quaternionCount, keyFramesCount)
        for frameIndex in range(count):
            srcKfp = fcurve.keyframe_points[frameIndex]
            q = quaternionList[frameIndex]
            srcKfp.co[1] = q[axis]