import bpy
import os


from ..games.GenshinImpact import SSMTExtractModelGI
from ..games.ZenlessZoneZero import SSMTExtractModelZZZ

from ..config.main_config import GlobalConfig
from ..properties.properties_dbmt_path import Properties_DBMT_Path  

class PanelSSMTBasicConfig(bpy.types.Panel):
    bl_label = "Basic Config" 
    bl_idname = "VIEW3D_PT_PANEL_SSMT_Basic_Config"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SSMT'

    def draw(self, context):
        layout = self.layout

        # use_sepecified_dbmt
        layout.prop(context.scene.dbmt_path, "use_specified_dbmt",text="使用指定的DBMT工作路径")

        if Properties_DBMT_Path.use_specified_dbmt():
            # Path button to choose DBMT-GUI.exe location folder.
            row = layout.row()
            row.operator("object.select_dbmt_folder")

            # 获取DBMT.exe的路径
            dbmt_gui_exe_path = os.path.join(Properties_DBMT_Path.path(), "DBMT.exe")
            if not os.path.exists(dbmt_gui_exe_path):
                layout.label(text="Error:Please select DBMT.exe location ", icon='ERROR')
        
        GlobalConfig.read_from_main_json()

        layout.label(text="DBMT工作路径: " + GlobalConfig.dbmtlocation)
        # print(MainConfig.dbmtlocation)

        layout.label(text="当前游戏: " + GlobalConfig.gamename)
        layout.label(text="当前工作空间: " + GlobalConfig.workspacename)


class PanelSSMTExtractModel(bpy.types.Panel):
    bl_label = "Extract Model" 
    bl_idname = "VIEW3D_PT_PANEL_SSMT_EXTRACT_MODEL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SSMT'
    

    def draw(self, context):
        layout = self.layout

        layout.label(text="SSMT still under development, do not use!", icon='ERROR')

        layout.prop(context.scene.properties_extract_model,"only_match_gpu")

        # layout.operator(SSMTExtractModelGI.bl_idname)
        if GlobalConfig.gamename == "GI":
            layout.operator(SSMTExtractModelGI.bl_idname)
        elif GlobalConfig.gamename == "ZZZ":
            layout.operator(SSMTExtractModelZZZ.bl_idname)


