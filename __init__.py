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
    "version": (2, 0, 2),
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
    import motionmixalot
    import fcurvesmixalot
else:
    # When running as an installed AddOn, then it runs in package mode.
    from . import mainmixalot
    from . import commonmixalot
    from . import motionmixalot
    from . import fcurvesmixalot

if "bpy" in locals():
    from importlib import reload
    if "mainmixalot" in locals():
        reload(mainmixalot)
    if "commonmixalot" in locals():
        reload(commonmixalot)
    if "motionmixalot" in locals():
        reload(motionmixalot)
    if "fcurvesmixalot" in locals():
        reload(fcurvesmixalot)

###############################################################################
# Scene Properties
###############################################################################
class LumbermixalotPropertyGroup(bpy.types.PropertyGroup):
    """Container of options for Mixamo To Lumberyard Converter"""
    extractTranslationX: bpy.props.BoolProperty(
        name="X",
        description="Extract X Axis Translation.",
        default = True)
    zeroOutTranslationX: bpy.props.BoolProperty(
        name="Zero Out",
        description="Zero Out X Axis Translation upon extraction.",
        default = False)

    extractTranslationY: bpy.props.BoolProperty(
        name="Y",
        description="Extract Y Axis Translation.",
        default = True)
    zeroOutTranslationY: bpy.props.BoolProperty(
        name="Zero Out",
        description="Zero Out Y Axis Translation upon extraction.",
        default = False)

    extractTranslationZ: bpy.props.BoolProperty(
        name="Z",
        description="Extract Z Axis Translation.",
        default = True)
    zeroOutTranslationZ: bpy.props.BoolProperty(
        name="Zero Out",
        description="Zero Out Z Axis Translation upon extraction.",
        default = False)

    extractRotationZ: bpy.props.BoolProperty(
        name="Z Axis",
        description="Extract Rotation around Z Axis.",
        default = False)
    zeroOutRotationZ: bpy.props.BoolProperty(
        name="Zero Out",
        description="Zero Out Rotation around Z Axis upon extraction.",
        default = False)

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
    bl_description = "Bakes root motion bone for a single, already imported rig."

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

        conversion_iterator = mainmixalot.Convert(
            sceneObj=context.scene,
            armatureObj=context.object,
            hipBoneName=hip_bone_name,
            extractTranslationX=mixalot.extractTranslationX, zeroOutTranslationX=mixalot.zeroOutTranslationX,
            extractTranslationY=mixalot.extractTranslationY, zeroOutTranslationY=mixalot.zeroOutTranslationY,
            extractTranslationZ=mixalot.extractTranslationZ, zeroOutTranslationZ=mixalot.zeroOutTranslationZ,
            extractRotationZ=mixalot.extractRotationZ, zeroOutRotationZ=mixalot.zeroOutRotationZ,
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


class OBJECT_OT_exportfbx(bpy.types.Operator):
    """
    Button/Operator for export the current scene as FBX.
    This button is useful if the user had already converted the
    current Actor/Motion but forgot to specify a path for exporting
    before clicking 'Convert".
    """
    bl_idname = "lumbermixalot.exportfbx"
    bl_label = "Export FBX"
    bl_description = "Export current scene as FBX."

    def execute(self, context):
        mixalot = context.scene.mixalot
        if context.object == None:
            self.report({'ERROR_INVALID_INPUT'}, "Error: no object selected. Please select the Armature object.")
            return {'CANCELLED'}

        if context.object.type != 'ARMATURE':
            self.report({'ERROR_INVALID_INPUT'}, "Error: {} is not an Armature.".format(context.object.name))
            return {'CANCELLED'}

        root_bone = commonmixalot.GetRootBone(context.object)
        if root_bone is None:
            self.report({'ERROR'}, "Error: The Armature must have at least one bone.")
            return {'CANCELLED'}

        try:
            out_filename = mainmixalot.ExportFBX(
                armatureObj=context.object,
                fbxFilename=mixalot.fbxFilename.decode('UTF-8'),
                fbxOutputPath=mixalot.fbxOutputPath,
                appendActorOrMotionPath=mixalot.appendAssetTypeToPath)
        except Exception as e:
            self.report({'ERROR'}, 'Error: ' + str(e))
            return{'CANCELLED'}
        self.report({'INFO'}, "Asset exported as '{}'".format(out_filename))
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
        box.label(text="Motion Extraction Options")
        
        transBox = box.box()
        transBox.label(text="Translation")
        row = transBox.row()
        row.prop(scene.mixalot, "extractTranslationX")
        if scene.mixalot.extractTranslationX:
            row.prop(scene.mixalot, "zeroOutTranslationX")
        row = transBox.row()
        row.prop(scene.mixalot, "extractTranslationY")
        if scene.mixalot.extractTranslationY:
            row.prop(scene.mixalot, "zeroOutTranslationY")
        row = transBox.row()
        row.prop(scene.mixalot, "extractTranslationZ")
        if scene.mixalot.extractTranslationZ:
            row.prop(scene.mixalot, "zeroOutTranslationZ")

        transBox = box.box()
        transBox.label(text="Rotation Around")
        row = transBox.row()
        row.prop(scene.mixalot, "extractRotationZ")
        if scene.mixalot.extractRotationZ:
            row.prop(scene.mixalot, "zeroOutRotationZ")

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
        
        box = layout.box()
        row = box.row()
        row.operator("lumbermixalot.exportfbx")


###############################################################################
# Registration
###############################################################################
classes = (
    LumbermixalotPropertyGroup,
    OBJECT_OT_convert,
    OBJECT_OT_exportfbx,
    LUMBERMIXALOT_VIEW_3D_PT_lumbermixalot
)


def register():
    for class_ in classes:
        bpy.utils.register_class(class_)
    bpy.types.Scene.mixalot = bpy.props.PointerProperty(
        type=LumbermixalotPropertyGroup)


def unregister():
    for class_ in classes:
        bpy.utils.unregister_class(class_)
    del bpy.types.Scene.mixalot

def _myHack():
    print("\n\n\n\nWelcome To _myHack\n")
    context = bpy.context
    if context.object.type != 'ARMATURE':
        print({'ERROR_INVALID_INPUT'}, "Error: {} is not an Armature.".format(context.object.name))
        return

    hip_bone = commonmixalot.GetRootBone(context.object)
    if hip_bone is None:
        print({'ERROR'}, "Error: The Armature must have at least one bone.")
        return

    hip_bone_name = hip_bone.name

    conversion_iterator = mainmixalot.Convert(
        sceneObj=context.scene,
        armatureObj=context.object,
        hipBoneName=hip_bone_name,
        extractTranslationX=True, zeroOutTranslationX=False,
        extractTranslationY=True, zeroOutTranslationY=False,
        extractTranslationZ=True, zeroOutTranslationZ=False,
        extractRotationZ=False, zeroOutRotationZ=False,
        fbxFilename="",
        fbxOutputPath="",
        appendActorOrMotionPath=True,
        dumpCSVs=True)

    try:
        for status in conversion_iterator:
            print({'INFO'}, "Step Done: " + str(status))
    except Exception as e:
        print({'ERROR_INVALID_INPUT'}, 'Error: ' + str(e))
        return
    print({'INFO'}, "Rig Converted")

if __name__ == "__main__":
    register()
    # Hackery, Remove after debugging
    #_myHack()
