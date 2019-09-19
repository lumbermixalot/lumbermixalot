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

bl_info = {
    "name": "Mixamo Rig Converter for Lumberyard",
    "author": "Galib F. Arrieta",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "3D View > UI (Right Panel) > Lumbermixalot Tab",
    "description": ("Script to bake Root motion for Mixamo Animations"),
    "warning": "",  # used for warning icon and text in addons panel
    "wiki_url": "https://github.com/lumbermixalot/lumbermixalot",
    "tracker_url": "https://github.com/lumbermixalot/lumbermixalot" ,
    "category": "Animation"
}

import bpy

if __package__ is None or __package__ == "":
    # When running as a standalone script from Blender Text View "Run Script"
    import mainmixalot
    import commonmixalot
else:
    # When running as an installed AddOn, then it runs in package mode.
    from . import mainmixalot
    from . import commonmixalot

if "bpy" in locals():
    from importlib import reload
    if "mainmixalot" in locals():
        reload(mainmixalot)
    if "commonmixalot" in locals():
        reload(commonmixalot)


###############################################################################
# Scene Properties
###############################################################################
class LumbermixalotPropertyGroup(bpy.types.PropertyGroup):
    """Container of options for Mixamo To Lumberyard Converter"""
    rootBoneName:  bpy.props.StringProperty(
        name="Root Bone Name",
        description="Optional. Name of the root motion bone that will be added",
        maxlen = 256,
        default = "root",
        subtype='BYTE_STRING')
    animationFPS:  bpy.props.EnumProperty(items=
        [('24', '24fps', ''),
         ('30', '30fps', ''),
         ('60', '60fps', ''),],
        name="animation FPS",
        description="Should the Frames Per Second the animation was designed for.",
        default = '60')
    fbxFilename: bpy.props.StringProperty(
        name="Fbx name",
        description="Optional. Name of the output fbx (no path). Leave it"
        " empty if exporting is not desired",
        maxlen = 256,
        default = "",
        subtype='BYTE_STRING')
    fbxOutputPath: bpy.props.StringProperty(
        name="Fbx output dir",
        description="Optional. Name of the output path. Will be created if it"
        " doesn't exist.",
        maxlen = 1024,
        default = "",
        subtype='DIR_PATH')
    appendAssetTypeToPath: bpy.props.BoolProperty(
        name="Append Actor/ or Motions/?",
        description="If True, appends the asset type to the output dir before"
        " exporting.",
        default = True)
    debugDumpCSVs: bpy.props.BoolProperty(
        name="Debug Dump CSVs?",
        description="OPTIONAL. For Developers. If True, dumps motion vector "
            "data as CSVs.",
        default = False)



###############################################################################
# Operators
###############################################################################
class OBJECT_OT_convert(bpy.types.Operator):
    """Button/Operator for converting Actor or Motion"""
    bl_idname = "lumbermixalot.convert"
    bl_label = "Convert"
    description = "Bakes root motion bone for a single, already imported rig."

    def execute(self, context):
        mixalot = context.scene.mixalot
        if context.object == None:
            self.report({'ERROR_INVALID_INPUT'}, "Error: no object selected. Please select the Armature object.")
            return {'CANCELLED'}

        if context.object.type != 'ARMATURE':
            self.report({'ERROR_INVALID_INPUT'}, "Error: {} is not an Armature.".format(context.object.name))
            return {'CANCELLED'}

        hip_bone = commonmixalot.GetRootBone(context.object)
        if hip_bone is None:
            self.report({'ERROR'}, "Error: The Armature must have at least one bone.")
            return {'CANCELLED'}

        hip_bone_name = hip_bone.name
        root_bone_name = mixalot.rootBoneName.decode('UTF-8')
        if hip_bone_name == root_bone_name:
            self.report({'ERROR_INVALID_INPUT'}, "Error: {} is already the root bone name.".format(root_bone_name))
            return {'CANCELLED'}

        conversion_iterator = mainmixalot.Convert(
            sceneObj=context.scene,
            armatureObj=context.object,
            hipBoneName=hip_bone_name,
            rootBoneName=root_bone_name,
            animationSampleRate=mixalot.animationFPS,
            fbxFilename=mixalot.fbxFilename.decode('UTF-8'),
            fbxOutputPath=mixalot.fbxOutputPath,
            appendActorOrMotionPath=mixalot.appendAssetTypeToPath,
            dumpCSVs=mixalot.debugDumpCSVs)

        try:
            for status in conversion_iterator:
                self.report({'INFO'}, "Step Done: " + str(status))
        except Exception as e:
            self.report({'ERROR_INVALID_INPUT'}, 'Error: ' + str(e))
            return{'CANCELLED'}
        self.report({'INFO'}, "Rig Converted")
        return {'FINISHED'}


###############################################################################
# UI
###############################################################################
class LUMBERMIXALOT_VIEW_3D_PT_lumbermixalot(bpy.types.Panel):
    """Creates a Tab in the Toolshelve in 3D_View"""
    bl_label = "Mixamo To Lumberyard"
    bl_idname = "LUMBERMIXALOT_VIEW_3D_PT_lumbermixalot"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Lumbermixalot"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        #UI Section
        box = layout.box()
        row = box.row()
        row.prop(scene.mixalot, "rootBoneName")
        row = box.row()
        row.prop(scene.mixalot, "animationFPS")

        box = layout.box()
        box.label(text="FBX Export Options")
        row = box.row()
        row.prop(scene.mixalot, "fbxFilename")
        row = box.row()
        row.prop(scene.mixalot, "fbxOutputPath")
        row = box.row()
        row.prop(scene.mixalot, "appendAssetTypeToPath")

        box = layout.box()
        box.label(text="DEBUG Options")
        row = box.row()
        row.prop(scene.mixalot, "debugDumpCSVs")

        box = layout.box()
        row = box.row()
        row.scale_y = 2.0
        row.operator("lumbermixalot.convert")


###############################################################################
# Registration
###############################################################################
classes = (
    LumbermixalotPropertyGroup,
    OBJECT_OT_convert,
    LUMBERMIXALOT_VIEW_3D_PT_lumbermixalot
)


def register():
    for aclass in classes:
        bpy.utils.register_class(aclass)
    bpy.types.Scene.mixalot = bpy.props.PointerProperty(
        type=LumbermixalotPropertyGroup)


def unregister():
    for aclass in classes:
        bpy.utils.unregister_class(aclass)
    del bpy.types.Scene.mixalot

if __name__ == "__main__":
    register()