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


def _RemoveUnnecessaryUvMaps(obj: bpy.types.Armature, numUVMapsToKeep: int) -> list[int, int]:
    meshCount = 0
    removedUVMapsCount = 0
    for childObj in obj.children:
        if childObj.type != 'MESH':
            continue
        meshCount += 1
        uvlayers = childObj.data.uv_layers
        while len(uvlayers) > numUVMapsToKeep:
            layerToRemove = uvlayers[numUVMapsToKeep]
            uvlayers.remove(layerToRemove)
            print(f"From mesh '{childObj.name}'', Removed unnecessary UV Map '{layerToRemove.name}'")
            removedUVMapsCount += 1
    return meshCount, removedUVMapsCount


# Looks across first level children and see if at least one of them is of type
# 'MESH'
def CheckArmatureContainsMesh(obj: bpy.types.Armature):
    children = obj.children
    for childObj in children:
        if childObj.type == 'MESH':
            return True
    return False


def Convert(armatureObj: bpy.types.Armature, numUVMapsToKeep: int = -1):
    """
    Main function that converts an Actor/Character type of asset per 
    O3DE requirements.

    Applies current armature rotation as the 0,0,0 rotation.

    Optionally removes any other UVMaps in excess of @numUVMapsToKeep.
    The reason is because O3DE reserves those extra uvmaps as vertex streams
    and there's a limit of 12 streams.
    """
    yield Status(f"Will apply current rotation of '{armatureObj.name}' as 0,0,0")
    # Set the current rotation as 0,0,0
    cmn.ApplyCurrentRotationAs000(armatureObj)
    yield Status(f"Applied current rotation of '{armatureObj.name}' as 0,0,0")

    if numUVMapsToKeep < 0:
        yield Status("Actor was converted successfully")

    yield Status("Starting removal of unnecessary uvmaps")
    meshCount, removeCount = _RemoveUnnecessaryUvMaps(armatureObj, numUVMapsToKeep)
    yield Status(f"Removed {removeCount} UV Maps across {meshCount} meshes")

    yield Status("Actor was converted successfully")