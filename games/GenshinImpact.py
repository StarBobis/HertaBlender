import bpy 

class SSMTExtractModelGI(bpy.types.Operator):
    bl_idname = "ssmt.extract_model_gi"
    bl_label = "提取模型(GI)"
    bl_description = "提取模型(GI)"

    def execute(self, context):
        
        return {'FINISHED'}