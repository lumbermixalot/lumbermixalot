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

class Axis:
    X = Vector([1, 0, 0])
    Y = Vector([0, 1, 0])
    Z = Vector([0, 0, 1])

#For debugging.
def Dump(obj):
    print(type(obj))
    print(dir(obj))

class Status:
    """ Used for yield statements """
    def __init__(self, msg, status_type='default'):
        print(msg)
        self.msg = msg
        self.status_type = status_type
    def __str__(self):
        return str(self.msg)


def ApplyCurrentRotationAs000(obj):
    """
    Whatever is the default rotation of the armature we need to apply as
    its default rotation. This way the rotation becomes (0,0,0) if seen
    as an Euler.
    @obj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
    """
    #Set 'OBJECT' mode
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    print("Applied current rotation")


def GetRootBone(obj):
    """
    This method assumes the root bone has no siblings.
    returns the first non parented bone. 
    """
    bones = obj.data.bones
    for bone in bones:
        if bone.parent == None:
            return bone
    return None


def HasOnlyOneRootBone(obj):
    """
    Returns True if @obj only has a single root bone without siblings.
    @obj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
    """
    bones = obj.data.bones
    rootBoneCount = 0
    for bone in bones:
        if bone.parent == None:
            rootBoneCount += 1
    return rootBoneCount == 1


def HasRootMotionBone(obj, rootBoneName):
    """
    Returns True if the root bone is named @rootBoneName
    @obj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
    @rootBoneName (string). Name of the root motion bone to compare with
    """
    bones = obj.data.bones
    for bone in bones:
        #print(bone.name, len(bone.children), bone.parent)
        if (bone.parent is None) and (bone.name==rootBoneName):
            return True
    return False


def GetRestPoseMatrixFromPoseBone(poseBoneObj):
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


def GetPoseBoneFromArmature(armatureObj, boneName):
    """
    @armatureObj is a bpy.types.Armature
    @boneName str
    returns a bpy.types.PoseBone
    """
    bpy.ops.object.mode_set(mode='POSE')
    for bone in armatureObj.pose.bones:
        if bone.name == boneName:
            return bone
    return None

def AddSiblingRootBone(obj, boneName):
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


def MakeParentBone(obj, parentBoneName, childBoneName):
    #Enter Edit Mode
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    ebones = obj.data.edit_bones
    rootBoneIndex = ebones.find(parentBoneName)
    childBoneIndex = ebones.find(childBoneName)
    print("root bone index = {}, child bone index = {}".format(rootBoneIndex, childBoneIndex))
    ebones[childBoneIndex].parent = ebones[rootBoneIndex]
    
    #Exit edit mode to save bones so they can be used in pose mode
    bpy.ops.object.mode_set(mode='OBJECT')