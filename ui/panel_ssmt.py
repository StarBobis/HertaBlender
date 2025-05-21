import bpy

class SSMTExtractModelGI(bpy.types.Operator):
    bl_idname = "ssmt.extract_model_gi"
    bl_label = "提取模型(GI)"
    bl_description = "提取模型(GI)"

    def execute(self, context):
        
        return {'FINISHED'}
    

class PanelSSMTExtractModel(bpy.types.Panel):
    bl_label = "Extract Model" 
    bl_idname = "VIEW3D_PT_PANEL_SSMT_EXTRACT_MODEL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SSMT'
    

    def draw(self, context):
        layout = self.layout
        
        layout.operator(SSMTExtractModelGI.bl_idname)
