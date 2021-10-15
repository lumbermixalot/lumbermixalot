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
    "name": "Root Motion Extractor Compatible With Mixamo & O3DE",
    "author": "Galib F. Arrieta",
    "version": (3, 0, 1),
    "blender": (2, 80, 0),
    "location": "3D View > UI (Right Panel) > Lumbermixalot Tab",
    "description": ("Script to extract and bake Root motion for Mixamo Animations"),
    "warning": "",  # used for warning icon and text in addons panel
    "wiki_url": "https://github.com/lumbermixalot/lumbermixalot",
    "tracker_url": "https://github.com/lumbermixalot/lumbermixalot" ,
    "category": "Animation"
}

import math

import bpy

if __package__ is None or __package__ == "":
    # When running as a standalone script from Blender Text View "Run Script"
    import commonmixalot
    import motionmixalot
    import fcurvesmixalot
    import actormixalot
else:
    # When running as an installed AddOn, then it runs in package mode.
    from . import commonmixalot
    from . import motionmixalot
    from . import fcurvesmixalot
    from . import actormixalot

if "bpy" in locals():
    from importlib import reload
    if "commonmixalot" in locals():
        reload(commonmixalot)
    if "motionmixalot" in locals():
        reload(motionmixalot)
    if "fcurvesmixalot" in locals():
        reload(fcurvesmixalot)
    if "actormixalot" in locals():
        reload(actormixalot)


# A MessageBox utility:
def _ShowMessageBox(message: str, title: str = "Lumbermixalot Info", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

###############################################################################
# Scene Properties
###############################################################################
class LumbermixalotPropertyGroup(bpy.types.PropertyGroup):
    """Container of options for Mixamo To O3DE Converter"""
    importedFbxFilename: bpy.props.StringProperty(
        name="Imported Fbx name",
        description="Read Only. Displays the name of the last imported FBX file.",
        maxlen = 256,
        default = "",
        subtype='BYTE_STRING')
    importedFbxDirectoryPath: bpy.props.StringProperty(
        name="Imported Fbx Directory",
        description="Read Only. Displays the directory of the last imported FBX file.",
        maxlen = 1024,
        default = "",
        subtype='BYTE_STRING')

    removeUVMaps: bpy.props.BoolProperty(
        name="Remove UV Maps",
        description="Remove unnecessary UV Maps. O3DE fails to import an actor with too many UV Maps.",
        default = True)
    countOfUVMapsToKeep: bpy.props.IntProperty(
        name="",
        description="The amount of UV Maps that should remain after removal",
        min=1,
        subtype='UNSIGNED',
        default=2
    )

    extractTranslationX: bpy.props.BoolProperty(
        name="X axis (X Right)",
        description="Extract X Axis Translation from Hip bone to the Armature tranform.",
        default = True)
    extractTranslationY: bpy.props.BoolProperty(
        name="Y axis (-Y Forward)",
        description="Extract Y Axis Translation from Hip bone to the Armature tranform.",
        default = True)
    extractTranslationZ: bpy.props.BoolProperty(
        name="Z axis (Z Up",
        description="Extract Z Axis Translation from Hip bone to the Armature tranform.",
        default = True)

    extractRotationZ: bpy.props.BoolProperty(
        name="Z Axis (Z Up)",
        description="Extract Rotation around Z Axis from Hip bone to the Armature tranform.",
        default = False)

    debugDumpCSVs: bpy.props.BoolProperty(
        name="Generate CSV files?",
        description="OPTIONAL. For Developers. If True, dumps motion vector "
            "data as Comma Separated Values .csv files.",
        default = False)

    zeroOutTranslationX: bpy.props.BoolProperty(
        name="Force X Axis Translation to 0.0",
        description="Sets Translation.X to 0.0 across all animation frames for the Armature transform.",
        default = False)
    zeroOutTranslationY: bpy.props.BoolProperty(
        name="Force Y Axis Translation to 0.0",
        description="Sets Translation.Y to 0.0 across all animation frames for the Armature transform.",
        default = False)
    zeroOutTranslationZ: bpy.props.BoolProperty(
        name="Force Z Axis Translation to 0.0",
        description="Sets Translation.Z to 0.0 across all animation frames for the Armature transform.",
        default = False)
    
    degreesAroundZAxis: bpy.props.FloatProperty(
        name="",
        description="Angle in Degrees around Z Axis to rotate the whole Root Motion animation.",
        default = -90.0)

    cacheFbxExportOptions: bpy.props.BoolProperty(
        name="Cache FBX Export Options",
        description="If enabled, a json file will be created in the directory where the current scene was imported from.",
        default = True)
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



###############################################################################
# Operators
###############################################################################
class ImportFbxOperator(bpy.types.Operator):
    """
    Button/Operator for importing an FBX file.
    """
    bl_idname = "lumbermixalot.importfbx"
    bl_label = "Import FBX"
    bl_description = "Imports an FBX file."
    #Properties that are known to fileselect_add
    filter_glob: bpy.props.StringProperty(default="*.fbx", options={'HIDDEN'})
    filepath: bpy.props.StringProperty()
    filename: bpy.props.StringProperty()
    directory: bpy.props.StringProperty()

    def execute(self, context):
        mixalot = context.scene.mixalot
        mixalot.importedFbxFilename = self.filename.encode('utf-8')
        mixalot.importedFbxDirectoryPath = self.directory.encode('utf-8')
        try:
            commonmixalot.ImportFBX(self.filepath)
        except Exception as e:
            self.report({'ERROR'}, f"Error: Failed to import FBX: '{self.filepath}': {e}")
            return{'CANCELLED'}
        mixalot.fbxFilename = self.filename.encode('utf-8')
        if mixalot.cacheFbxExportOptions:
            outPath = commonmixalot.GetFbxExportProperty(self.directory, "fbxOutputPath")
            if outPath != "":
                mixalot.fbxOutputPath = outPath
        self.report({'OPERATOR'}, f"Imported FBX file: '{self.filepath}'")
        _ShowMessageBox(f"Imported FBX file: '{self.filepath}'")
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        armatureObj = commonmixalot.GetFirstAmature(context.scene)
        if not (armatureObj is None):
            self.report({'ERROR_INVALID_INPUT'}, "Can not import if the scene already has Armature.")
            return {'CANCELLED'}
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class ActorConvertOperator(bpy.types.Operator):
    """Applies Rotation to Armature object, removes leftover UV Maps (if enabled), etc"""
    bl_idname = "lumbermixalot.actor_convert"
    bl_label = "Convert"
    bl_description = "Applies Rotation to Armature object, removes leftover UV Maps (if enabled), etc"
    #Custom properties
    armatureObj: bpy.types.Armature

    def execute(self, context):
        mixalot = context.scene.mixalot
        conversion_iterator = actormixalot.Convert(self.armatureObj, mixalot.countOfUVMapsToKeep)
        try:
            for status in conversion_iterator:
                self.report({'INFO'}, "Step Done: " + str(status))
        except Exception as e:
            self.report({'ERROR_INVALID_INPUT'}, 'Error: ' + str(e))
            return{'CANCELLED'}
        self.report({'INFO'}, "Actor Converted Successfully")
        _ShowMessageBox("Actor Converted Successfully")
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        armatureObj = context.object
        hipBoneObj = commonmixalot.GetRootBone(armatureObj)
        if hipBoneObj is None:
            self.report({'ERROR'}, f"Error: The Armature '{armatureObj.name}' must have at least one bone.")
            return {'CANCELLED'}
        self.armatureObj = armatureObj
        return self.execute(context)


class RootMotionExtractionOperator(bpy.types.Operator):
    """This operator runs the main root motion extraction algorithm."""
    bl_idname = "lumbermixalot.extract_root_motion"
    bl_label = "Extract Root Motion"
    bl_description = "Extract root motion animation data from the Hip bone to the Armature transform."
    #Custom properties
    armatureObj: bpy.types.Armature
    hipBoneName: str

    def execute(self, context):
        mixalot = context.scene.mixalot

        conversion_iterator = motionmixalot.ExtractRootMotion(
            sceneObj=context.scene,
            armatureObj=self.armatureObj,
            hipBoneName=self.hipBoneName,
            extractTranslationX=mixalot.extractTranslationX,
            extractTranslationY=mixalot.extractTranslationY,
            extractTranslationZ=mixalot.extractTranslationZ,
            extractRotationZ=mixalot.extractRotationZ,
            dumpCSVs=mixalot.debugDumpCSVs)

        try:
            for status in conversion_iterator:
                self.report({'INFO'}, "Step Done: " + str(status))
        except Exception as e:
            self.report({'ERROR_INVALID_INPUT'}, 'Error: ' + str(e))
            return{'CANCELLED'}
        self.report({'INFO'}, "Root Motion Extraction Completed")
        _ShowMessageBox("Root Motion Extraction Completed")
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        if context.object == None:
            self.report({'ERROR_INVALID_INPUT'}, "Error: no object selected. Please select the Armature object.")
            return {'CANCELLED'}

        if context.object.type != 'ARMATURE':
            self.report({'ERROR_INVALID_INPUT'}, f"Error: '{context.object.name}' is not an Armature.")
            return {'CANCELLED'}

        hip_bone = commonmixalot.GetRootBone(context.object)
        if hip_bone is None:
            self.report({'ERROR'}, "Error: The Armature must have at least one bone.")
            return {'CANCELLED'}
        
        self.armatureObj = context.object
        self.hipBoneName = hip_bone.name
        return self.execute(context)
        


class RootMotionClearAnimationDataOperator(bpy.types.Operator):
    """This operator is used to clear the desired vector components from the root motion."""
    bl_idname = "lumbermixalot.clear_root_motion_translation"
    bl_label = "Clear Translation Data From Root Motion"
    bl_description = "Clears (Forces to 0.0) the selected axis translation data from the Root Motion."
    #Custom properties
    armatureObj: bpy.types.Armature

    def execute(self, context):
        mixalot = context.scene.mixalot

        if mixalot.zeroOutTranslationX or mixalot.zeroOutTranslationY or mixalot.zeroOutTranslationZ:
            conversion_iterator = motionmixalot.ClearRootMotionTranslation(
                armatureObj=self.armatureObj,
                zeroOutTranslationX=mixalot.zeroOutTranslationX,
                zeroOutTranslationY=mixalot.zeroOutTranslationY,
                zeroOutTranslationZ=mixalot.zeroOutTranslationZ)

            try:
                for status in conversion_iterator:
                    self.report({'INFO'}, "Step Done: " + str(status))
            except Exception as e:
                self.report({'ERROR_INVALID_INPUT'}, 'Error: ' + str(e))
                return{'CANCELLED'}
            self.report({'INFO'}, "Selected translation data has been cleared from Root Motion")

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        if context.object == None:
            self.report({'ERROR_INVALID_INPUT'}, "Error: no object selected. Please select the Armature object.")
            return {'CANCELLED'}

        if context.object.type != 'ARMATURE':
            self.report({'ERROR_INVALID_INPUT'}, f"Error: '{context.object.name}' is not an Armature.")
            return {'CANCELLED'}
        
        mixalot = context.scene.mixalot
        if (not mixalot.zeroOutTranslationX) and (not mixalot.zeroOutTranslationY) and (not mixalot.zeroOutTranslationZ):
            self.report({'ERROR_INVALID_INPUT'}, "No axis data has been selected to be cleared.")
            return {'CANCELLED'}

        self.armatureObj = context.object
        return self.execute(context)


class RootMotionRotateAnimationOperator(bpy.types.Operator):
    """This operator applies a rotation around Z Axis (Z Up) to the whole animation."""
    bl_idname = "lumbermixalot.rotate_root_motion_animation"
    bl_label = "Rotate Root Motion Animation"
    bl_description = "Rotates all the Root Motion key frames N degrees around Z Axis (Z Up)."
    #Custom properties
    armatureObj: bpy.types.Armature
    degreesAroundZAxis: float

    def execute(self, context):
        conversion_iterator = motionmixalot.RotateArmatureAnimationData(self.armatureObj,
            commonmixalot.Axis.Z, math.radians(self.degreesAroundZAxis))
        try:
            for status in conversion_iterator:
                self.report({'INFO'}, "Step Done: " + str(status))
        except Exception as e:
            self.report({'ERROR_INVALID_INPUT'}, 'Error: ' + str(e))
            return{'CANCELLED'}
        self.report({'INFO'}, f"Successfully rotated Root Motion animation {self.degreesAroundZAxis} degress around Z Up")
        _ShowMessageBox(f"Successfully rotated Root Motion animation {self.degreesAroundZAxis} degress around Z Up")
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        if context.object == None:
            self.report({'ERROR_INVALID_INPUT'}, "Error: no object selected. Please select the Armature object.")
            return {'CANCELLED'}

        if context.object.type != 'ARMATURE':
            self.report({'ERROR_INVALID_INPUT'}, f"Error: '{context.object.name}' is not an Armature.")
            return {'CANCELLED'}
        
        mixalot = context.scene.mixalot
        frac, _ = math.modf(mixalot.degreesAroundZAxis / 360.0)
        degreesAroundZAxis = 360.0 * frac
        if math.isclose(degreesAroundZAxis, 0.0, abs_tol=0.01):
            self.report({'ERROR_INVALID_INPUT'}, "Requested rotation angle is zero or nearly zero.")
            return {'CANCELLED'}

        self.armatureObj = context.object
        self.degreesAroundZAxis = degreesAroundZAxis
        return self.execute(context)


class ExportFbxOperator(bpy.types.Operator):
    """
    Button/Operator for export the current scene as FBX.
    It configures the FBX presets that make it all compatible
    with O3DE.
    """
    bl_idname = "lumbermixalot.exportfbx"
    bl_label = "Export FBX"
    bl_description = "Export current scene as FBX."
    #Custom properties
    fbxFilename: str
    fbxOutputPath: str

    def execute(self, context):
        try:
            out_filename = commonmixalot.ExportFBX(self.fbxFilename, self.fbxOutputPath)
        except Exception as e:
            self.report({'ERROR'}, 'Error: ' + str(e))
            return{'CANCELLED'}
        mixalot = context.scene.mixalot
        if mixalot.cacheFbxExportOptions:
            commonmixalot.StoreFbxExportProperty(mixalot.importedFbxDirectoryPath.decode('UTF-8'), "fbxOutputPath", mixalot.fbxOutputPath)
        self.report({'OPERATOR'}, f"Scene exported as FBX file: '{out_filename}'")
        _ShowMessageBox(f"Scene exported as FBX file: '{out_filename}'")
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        mixalot = context.scene.mixalot
        if context.object == None:
            self.report({'ERROR_INVALID_INPUT'}, "Error: no object selected. Please select the Armature object.")
            return {'CANCELLED'}

        if context.object.type != 'ARMATURE':
            self.report({'ERROR_INVALID_INPUT'}, f"Error: active object '{context.object.name}' is not an Armature.")
            return {'CANCELLED'}
        
        fbxFilename = mixalot.fbxFilename.decode('UTF-8')
        fbxFilename = "" if (fbxFilename is None) else fbxFilename.strip()
        if fbxFilename == "":
            self.report({'ERROR'}, f"Error: Fbx name is empty.")
            return {'CANCELLED'}

        fbxOutputPath = mixalot.fbxOutputPath
        fbxOutputPath = "" if (fbxOutputPath is None) else fbxOutputPath.strip()
        if fbxOutputPath == "":
            self.report({'ERROR'}, f"Error: An output directory is necessary")
            return {'CANCELLED'}

        self.fbxFilename = fbxFilename
        self.fbxOutputPath = fbxOutputPath
        return self.execute(context)


###############################################################################
# UI
###############################################################################
class LUMBERMIXALOT_VIEW_3D_PT_fbx_import(bpy.types.Panel):
    """Imports an FBX file that may contain Armature or Motions"""
    bl_label = "FBX Import options"
    bl_idname = "LUMBERMIXALOT_VIEW_3D_PT_fbx_import"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Lumbermixalot"
    bl_order = 1 # Make sure this is always the bottom most panel.

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row()
        row.operator("lumbermixalot.importfbx")
        row = layout.row()
        row.prop(scene.mixalot, "importedFbxFilename")
        row.enabled = False
        row = layout.row()
        row.prop(scene.mixalot, "importedFbxDirectoryPath")
        row.enabled = False


class LUMBERMIXALOT_VIEW_3D_PT_actor_processing(bpy.types.Panel):
    """Actor processing panel 3D_View"""
    bl_label = "Actor Processing"
    bl_idname = "LUMBERMIXALOT_VIEW_3D_PT_actor_processing"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Lumbermixalot"
    bl_order = 2

    @classmethod
    def poll(cls, context):
        if context.object == None:
            return None
        if context.object.type != 'ARMATURE':
            return None
        return actormixalot.CheckArmatureContainsMesh(context.object)


    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        row = layout.row()

        box = row.box()
        box.label(text="UV Maps")
        
        row = box.row()
        row.prop(scene.mixalot, "removeUVMaps")
        
        row = box.row()
        col_label1 = row.column()
        col_label1.label(text="Keep the first ")
        col_property = row.column()
        col_property.prop(scene.mixalot, "countOfUVMapsToKeep")
        col_label2 = row.column()
        col_label2.label(text=" UV Maps")

        row = layout.row()
        row.operator("lumbermixalot.actor_convert")


class LUMBERMIXALOT_VIEW_3D_PT_root_motion_extraction(bpy.types.Panel):
    """Root motion extraction from the hip node to the actor's feet."""
    bl_label = "Root Motion Extraction"
    bl_idname = "LUMBERMIXALOT_VIEW_3D_PT_root_motion_extraction"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Lumbermixalot"
    bl_order = 3

    @classmethod
    def poll(cls, context):
        armatureObj = context.object
        if armatureObj == None:
            return None
        if armatureObj.type != 'ARMATURE':
            return None
        hipBone = commonmixalot.GetRootBone(armatureObj)
        if hipBone is None:
            return None
        startFrameNumber, endFrameNumber, numKeyFrames =  fcurvesmixalot.GetKeyFramesRangeInfoFromPoseBoneDataPath(
            armatureObj, hipBone.name, fcurvesmixalot.FCurveDataPath.LOCATION_X)
        return (numKeyFrames > 1) and  (endFrameNumber > (startFrameNumber + 1))

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        translationBox = layout.box()
        translationBox.label(text="Translation Extraction Options")
        row = translationBox.row()
        row.prop(scene.mixalot, "extractTranslationX")
        
        row = translationBox.row()
        row.prop(scene.mixalot, "extractTranslationY")

        row = translationBox.row()
        row.prop(scene.mixalot, "extractTranslationZ")


        rotationBox = layout.box()
        rotationBox.label(text="Rotation Extraction Options")
        row = rotationBox.row()
        row.prop(scene.mixalot, "extractRotationZ")

        box = layout.box()
        box.label(text="DEBUG Options")
        row = box.row()
        row.prop(scene.mixalot, "debugDumpCSVs")

        box = layout.box()
        row = box.row()
        row.scale_y = 2.0
        row.operator("lumbermixalot.extract_root_motion")


class LUMBERMIXALOT_VIEW_3D_PT_root_motion_post_processing(bpy.types.Panel):
    """This panel shows options for further processing/customization of the extracted root motion."""
    bl_label = "Root Motion Post Processing"
    bl_idname = "LUMBERMIXALOT_VIEW_3D_PT_root_motion_post_processing"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Lumbermixalot"
    bl_order = 4

    @classmethod
    def poll(cls, context):
        armatureObj = context.object
        if armatureObj == None:
            return None
        if armatureObj.type != 'ARMATURE':
            return None
        fcurve = fcurvesmixalot.GetArmatureFCurveFromDataPath(armatureObj, fcurvesmixalot.FCurveDataPath.LOCATION_Y)
        if fcurve is None:
            return None
        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.label(text="Translation Removal Options")
        row = box.row()
        row.prop(scene.mixalot, "zeroOutTranslationX")
        row = box.row()
        row.prop(scene.mixalot, "zeroOutTranslationY")
        row = box.row()
        row.prop(scene.mixalot, "zeroOutTranslationZ")

        row = box.row()
        row.operator("lumbermixalot.clear_root_motion_translation")

        row = layout.row()
        row.label(text="")

        box = layout.box()
        box.label(text="Rotate Root Motion animation")

        row = box.row()
        col = row.column()
        col.prop(scene.mixalot, "degreesAroundZAxis")
        col = row.column()
        col.label(text=" Degrees around Z Axis (Z Up)")
        row = box.row()
        row.operator("lumbermixalot.rotate_root_motion_animation")


class LUMBERMIXALOT_VIEW_3D_PT_fbx_export(bpy.types.Panel):
    """Exports the current Armature, Mesh & Motions to an fbx file"""
    bl_label = "FBX Export options"
    bl_idname = "LUMBERMIXALOT_VIEW_3D_PT_fbx_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Lumbermixalot"
    bl_order = 100 # Make sure this is always the bottom most panel.

    @classmethod
    def poll(cls, context):
        if context.object == None:
            return None
        if context.object.type != 'ARMATURE':
            return None
        x, y, z = context.object.rotation_euler
        # If the object world transform is 0, 0, 0 then the armature has been converted
        # already and fbx export through lumbermixalot should be available
        return (x == 0.0) and (y == 0.0) and (z == 0.0)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row()
        row.prop(scene.mixalot, "cacheFbxExportOptions")
        row = layout.row()
        row.prop(scene.mixalot, "fbxFilename")
        row = layout.row()
        row.prop(scene.mixalot, "fbxOutputPath")
        row = layout.row()
        row.operator("lumbermixalot.exportfbx")


###############################################################################
# Registration
###############################################################################
classes = (
    LumbermixalotPropertyGroup,
    ImportFbxOperator,
    ActorConvertOperator,
    RootMotionExtractionOperator,
    RootMotionClearAnimationDataOperator,
    RootMotionRotateAnimationOperator,
    ExportFbxOperator,
    LUMBERMIXALOT_VIEW_3D_PT_fbx_import,
    LUMBERMIXALOT_VIEW_3D_PT_actor_processing,
    LUMBERMIXALOT_VIEW_3D_PT_root_motion_extraction,
    LUMBERMIXALOT_VIEW_3D_PT_root_motion_post_processing,
    LUMBERMIXALOT_VIEW_3D_PT_fbx_export
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
    """
    Used for debugging purposes, when it is not convenient to register the UI
    of this plugin.
    """
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

    conversion_iterator = motionmixalot.ExtractRootMotion(
        sceneObj=context.scene,
        armatureObj=context.object,
        hipBoneName=hip_bone_name,
        extractTranslationX=True,
        extractTranslationY=True,
        extractTranslationZ=True,
        extractRotationZ=False, 
        dumpCSVs=True)
    try:
        for status in conversion_iterator:
            print({'INFO'}, "Step Done: " + str(status))
    except Exception as e:
        print({'ERROR_INVALID_INPUT'}, 'Error: ' + str(e))
        return
    print({'INFO'}, "Extracted Root Motion")

if __name__ == "__main__":
    register()
    # Hackery, Remove after debugging
    #_myHack()
