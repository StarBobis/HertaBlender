import bpy
import os

from ..utils.migoto_utils import *
from ..config.main_config import * 
from .generate_mod_ui import *

from ..properties.properties_dbmt_path import Properties_DBMT_Path


# 用于选择DBMT所在文件夹，主要是这里能自定义逻辑从而实现保存DBMT路径，这样下次打开就还能读取到。
class OBJECT_OT_select_dbmt_folder(bpy.types.Operator):
    bl_idname = "object.select_dbmt_folder"
    bl_label = "选择DBMT工作文件夹"

    directory: bpy.props.StringProperty(
        subtype='DIR_PATH',
        options={'HIDDEN'},
    ) # type: ignore

    def execute(self, context):
        scene = context.scene
        if self.directory:
            scene.dbmt_path.path = self.directory
            # print(f"Selected folder: {self.directory}")
            # 在这里放置你想要执行的逻辑
            # 比如验证路径是否有效、初始化某些资源等
            GlobalConfig.save_dbmt_path()
            
            self.report({'INFO'}, f"Folder selected: {self.directory}")
        else:
            self.report({'WARNING'}, "No folder selected.")
        
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    
class MigotoAttributePanel(bpy.types.Panel):
    bl_label = "特殊属性面板"
    bl_idname = "VIEW3D_PT_CATTER_MigotoAttribute_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Herta'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        # 检查是否有选中的对象
        if len(context.selected_objects) > 0:
            # 获取第一个选中的对象
            selected_obj = context.selected_objects[0]
            
            # 显示对象名称
            # layout.row().label(text=f"obj name: {selected_obj.name}")
            # layout.row().label(text=f"mesh name: {selected_obj.data.name}")
            gametypename = selected_obj.get("3DMigoto:GameTypeName",None)
            if gametypename is not None:
                row = layout.row()
                row.label(text=f"GameType: " + str(gametypename))

            # 示例：显示位置信息
            recalculate_tangent = selected_obj.get("3DMigoto:RecalculateTANGENT",None)
            if recalculate_tangent is not None:
                row = layout.row()
                row.label(text=f"Recalculate TANGENT:" + str(recalculate_tangent))

            recalculate_color = selected_obj.get("3DMigoto:RecalculateCOLOR",None)
            if recalculate_color is not None:
                row = layout.row()
                row.label(text=f"Recalculate COLOR:" + str(recalculate_color))

        else:
            # 如果没有选中的对象，则显示提示信息
            row = layout.row()
            row.label(text="当前未选中任何物体")


class PanelModelImportConfig(bpy.types.Panel):
    bl_label = "导入模型配置"
    bl_idname = "VIEW3D_PT_CATTER_WorkSpace_IO_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Herta'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene.properties_import_model,"model_scale",text="模型导入大小比例")
        layout.prop(context.scene.properties_import_model,"import_flip_scale_x",text="设置Scale的X分量为-1避免模型镜像")
        layout.prop(context.scene.properties_import_model,"import_flip_scale_y",text="设置Scale的Y分量为-1来改变模型朝向")

        if GlobalConfig.get_game_category() == GameCategory.UnrealVS or GlobalConfig.get_game_category() == GameCategory.UnrealCS:
            layout.prop(context.scene.properties_wwmi,"import_merged_vgmap",text="使用融合统一顶点组")


class PanelGenerateModConfig(bpy.types.Panel):
    bl_label = "生成Mod配置"
    bl_idname = "VIEW3D_PT_CATTER_GenerateMod_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Herta'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        # 根据当前游戏类型判断哪些应该显示哪些不显示。
        # 因为UnrealVS显然无法支持这里所有的特性，每个游戏只能支持一部分特性。
        if GlobalConfig.gamename == "HSR":
            layout.prop(context.scene.properties_generate_mod, "only_use_marked_texture",text="只使用标记过的贴图")
            layout.prop(context.scene.properties_generate_mod, "forbid_auto_texture_ini",text="禁止自动贴图流程")
            layout.prop(context.scene.properties_generate_mod, "recalculate_tangent",text="向量归一化法线存入TANGENT(全局)")
        
        if GlobalConfig.get_game_category() == GameCategory.UnityVS or GlobalConfig.get_game_category() == GameCategory.UnityCS:
            
            layout.prop(context.scene.properties_generate_mod, "only_use_marked_texture",text="只使用标记过的贴图")
            layout.prop(context.scene.properties_generate_mod, "forbid_auto_texture_ini",text="禁止自动贴图流程")
            layout.prop(context.scene.properties_generate_mod, "recalculate_tangent",text="向量归一化法线存入TANGENT(全局)")
            
            # 只有崩坏三2.0可能会用到重计算COLOR值
            if GlobalConfig.gamename == "HI3":
                layout.prop(context.scene.properties_generate_mod, "recalculate_color",text="算术平均归一化法线存入COLOR(全局)")
            layout.prop(context.scene.properties_generate_mod, "position_override_filter_draw_type",text="Position替换添加DRAW_TYPE=1判断")
            layout.prop(context.scene.properties_generate_mod, "vertex_limit_raise_add_filter_index",text="VertexLimitRaise添加filter_index过滤器")
            layout.prop(context.scene.properties_generate_mod, "slot_style_texture_add_filter_index",text="槽位风格贴图添加filter_index过滤器")
        elif GlobalConfig.get_game_category() == GameCategory.UnrealVS or GlobalConfig.get_game_category() == GameCategory.UnrealCS:
            layout.prop(context.scene.properties_generate_mod, "only_use_marked_texture",text="只使用标记过的贴图")
            layout.prop(context.scene.properties_generate_mod, "forbid_auto_texture_ini",text="禁止自动贴图流程")
            layout.prop(context.scene.properties_wwmi, "ignore_muted_shape_keys")
            layout.prop(context.scene.properties_wwmi, "apply_all_modifiers")


    

class PanelButtons(bpy.types.Panel):
    bl_label = "Herta基础面板" 
    bl_idname = "VIEW3D_PT_CATTER_Buttons_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Herta'
    

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

        operator_import_ib_vb = layout.operator("import_mesh.migoto_raw_buffers_mmt",icon='IMPORT')
        operator_import_ib_vb.filepath = GlobalConfig.path_workspace_folder()

        layout.operator("dbmt.import_all_from_workspace",icon='IMPORT')

        if GlobalConfig.gamename == "HSR" :
            layout.operator("dbmt.export_mod_hsr_32",text="生成XXMI格式Mod",icon='EXPORT')
        elif GlobalConfig.gamename == "AILIMIT":
            layout.operator("dbmt.export_mod_hsr_32",text="生成HSR加载器格式Mod",icon='EXPORT')
            layout.operator("dbmt.export_unity_cs_mod_to_workspace_seperated",text="生成DBMT自带加载器格式Mod",icon='EXPORT')
        elif GlobalConfig.gamename == "YYSLS" or GlobalConfig.gamename == "IdentityV":
            layout.operator("dbmt.generate_mod_yysls",text="生成Mod",icon='EXPORT')
            
        elif GlobalConfig.gamename == "WWMI":
            layout.operator("herta.export_mod_wwmi",text="生成Mod",icon='EXPORT')
        else:
            if GlobalConfig.get_game_category() == GameCategory.UnityVS:
                layout.operator("dbmt.export_unity_vs_mod_to_workspace_seperated")
            elif GlobalConfig.get_game_category() == GameCategory.UnityCS:
                layout.operator("dbmt.export_unity_cs_mod_to_workspace_seperated")
            elif GlobalConfig.get_game_category() == GameCategory.UnrealVS:
                layout.operator("dbmt.export_unreal_vs_mod_to_workspace")
            elif GlobalConfig.get_game_category() == GameCategory.UnrealCS:
                layout.operator("dbmt.export_unreal_cs_mod_to_workspace")
            else:
                layout.label(text= "Generate Mod for " + GlobalConfig.gamename + " Not Supported Yet.")

