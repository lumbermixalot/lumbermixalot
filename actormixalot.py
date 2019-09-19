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

#The modules of lumbermixalot
if __package__ is None or __package__ == "":
    # When running as a standalone script from Blender Text View "Run Script"
    from commonmixalot import Status
    import commonmixalot as cmn
else:
    print(__package__)
    # When running as an installed AddOn, then it runs in package mode.
    from .commonmixalot import Status
    from . import commonmixalot as cmn

#Adds the root motion bone to the Actor. The Bone will be located at
#  world (0,0,0) pointing towards -Y.
# @obj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
# @rootBoneName (string). Name of the root motion bone that will be added to
#    the armature.
def _AddRootMotionBone(obj, rootBoneName):
    if not cmn.HasOnlyOneRootBone(obj):
        raise Exception("The Armature must have only one root bone!")
    if cmn.HasRootMotionBone(obj, rootBoneName):
        print("Armature already had root motion bone")
        return
    #Enter Edit Mode
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    ebones = obj.data.edit_bones

    #let's hold a reference to the current root bone. (The Hips)
    oldRootBone = ebones[0]

    #Create the new root bone
    newRootBone = ebones.new(rootBoneName)
    boneSize = 1.0/obj.scale[0]
    newRootBone.tail = (0.0, -boneSize, 0)
    oldRootBone.parent = newRootBone

    #Exit edit mode to save bones so they can be used in pose mode
    bpy.ops.object.mode_set(mode='OBJECT')

    #Finally make sure the new bone structure makes the default rest pose.
    bpy.ops.object.mode_set(mode='POSE', toggle=False)
    bpy.ops.pose.armature_apply()

    #Exit pose mode to save bones
    bpy.ops.object.mode_set(mode='OBJECT')
    print("Added root bone and updated resting pose.")


#Mixamo Actors appear to have empty animation data which confuses Lumberyard
#when the fbx asset is imported. To make life easier it is better to delete
#the empty animation data.
#@obj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
def _ClearAnimationData(obj):
    if obj.animation_data:
        obj.animation_data_clear()
        print('Removed animation data')
    else:
        print('NO animation data found')


def ProcessActor(armatureObj, rootBoneName):
    """
    Main function that converts an Actor/Character type of asset per 
    Lumberyard requirements.
    
    Adds the root bone to the armature and makes it the new resting pose.

    @armatureObj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
    @rootBoneName (string). Name of the root motion bone that will be added to
        the armature.
    """
    #The first goal is to apply the object rotation if it is not 0,0,0.
    #Notice that we do not apply the rotation to the meshes, only to the Armature.
    #armatureObj = bpy.data.objects['Armature']
    yield Status("Starting actor conversion")

    cmn.ApplyCurrentRotationAs000(armatureObj)
    yield Status("Applied rotation")

    _ClearAnimationData(armatureObj)
    yield Status("Cleared empty animation data")

    _AddRootMotionBone(armatureObj, rootBoneName)
    yield Status("Actor is ready for exporting.")