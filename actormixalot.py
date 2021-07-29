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

def _RemoveUnnecessaryUvMaps(obj):
    for childObj in obj.children:
        if childObj.type != 'MESH':
            continue
        uvlayers = childObj.data.uv_layers
        while len(uvlayers) > 2:
            layerToRemove = uvlayers[2]
            print("From mesh {}, Removed unnecessary layer {}".format(childObj.name, layerToRemove.name))
            uvlayers.remove(layerToRemove)

def ProcessActor(armatureObj):
    """
    Main function that converts an Actor/Character type of asset per 
    Lumberyard requirements.

    This new version removes any other UVMaps beyond the first two.
    The reason is because O3DE reserves those extra uvmaps as vertex streams
    and there's a limit of 12 streams.

    @armatureObj (bpy.types.Object). Object.type is assumed to be 'ARMATURE'
    """
    yield Status("Starting removal of unnecessary uvmaps")
    _RemoveUnnecessaryUvMaps(armatureObj)
    yield Status("Cleared unnecessary uvmaps")

    yield Status("Actor is ready for exporting.")