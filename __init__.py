
# 自动更新功能
from . import addon_updater_ops

# UI界面
from .ui.panel_ui import * 
from .ui.panel_model_ui import *
from .ui.collection_rightclick_ui import *

# 全局配置
from .properties.properties_dbmt_path import Properties_DBMT_Path
from .properties.properties_import_model import Properties_ImportModel
from .properties.properties_generate_mod import Properties_GenerateMod
from .properties.properties_wwmi import Properties_WWMI
from .properties.properties_extract_model import Properties_ExtractModel

from .migoto.migoto_import import *

# SSMT开发
from .ui.panel_ssmt import *


'''
Compatible with all version start from Blender 3.6 LTS To 4.2LTS To Latest version.
To do this, we need keep track Blender's changelog:

4.1 to 4.2
https://docs.blender.org/api/4.2/change_log.html#to-4-2
4.0 to 4.1
https://docs.blender.org/api/4.1/change_log.html
3.6 to 4.0 
https://docs.blender.org/api/4.0/change_log.html#change-log

https://www.blender.org/support/
https://docs.blender.org/api/3.6/
https://docs.blender.org/api/4.2/

Dev:
https://github.com/JacquesLucke/blender_vscode
https://github.com/BlackStartx/PyCharm-Blender-Plugin


'''

# XXX Blender插件开发中的缓存问题：
# 在使用VSCode进行Blender插件开发中，会创建一个指向项目的软连接，路径大概如下：
# C:\Users\Administrator\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons
# 在插件架构发生大幅度变更时可能导致无法启动Blender，此时需要手动删掉插件缓存的这个软链接。
# XXX 所有的文件夹都必须小写，因为git无法追踪文件夹名称大小写改变的记录

bl_info = {
    "name": "Herta",
    "description": "A blender plugin for generate 3Dmigoto mod.",
    "blender": (4, 2, 0),
    "version": (1, 3, 0),
    "location": "View3D",
    "category": "Generic",
    "tracker_url":"https://github.com/StarBobis/HertaBlender"
}

class UpdaterPanel(bpy.types.Panel):
    """Update Panel"""
    bl_label = "检查版本更新"
    bl_idname = "Herta_PT_UpdaterPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = "objectmode"
    bl_category = "Herta"
    bl_order = 99
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Call to check for update in background.
        # Note: built-in checks ensure it runs at most once, and will run in
        # the background thread, not blocking or hanging blender.
        # Internally also checks to see if auto-check enabled and if the time
        # interval has passed.
        # addon_updater_ops.check_for_update_background()
        col = layout.column()
        col.scale_y = 0.7
        # Could also use your own custom drawing based on shared variables.
        if addon_updater_ops.updater.update_ready:
            layout.label(text="There's a new update available!", icon="INFO")

        # Call built-in function with draw code/checks.
        # addon_updater_ops.update_notice_box_ui(self, context)
        addon_updater_ops.update_settings_ui(self, context)




class HertaUpdatePreference(bpy.types.AddonPreferences):
    # Addon updater preferences.
    bl_idname = __package__


    auto_check_update: bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=True) # type: ignore

    updater_interval_months: bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0) # type: ignore

    updater_interval_days: bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=1,
        min=0,
        max=31) # type: ignore

    updater_interval_hours: bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23) # type: ignore

    updater_interval_minutes: bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59) # type: ignore
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "auto_check_update")
        addon_updater_ops.update_settings_ui(self, context)


register_classes = (
    # 全局配置
    Properties_ImportModel,
    Properties_WWMI,
    Properties_DBMT_Path,
    Properties_GenerateMod,
    Properties_ExtractModel,

    # DBMT所在位置
    OBJECT_OT_select_dbmt_folder,

    # 导入3Dmigoto模型功能
    Import3DMigotoRaw,
    DBMTImportAllFromCurrentWorkSpace,
    # 生成Mod功能
    ExportModHonkaiStarRail32,
    DBMTExportUnityVSModToWorkSpaceSeperated,
    DBMTExportUnityCSModToWorkSpaceSeperated,
    GenerateModWWMI,
    GenerateModYYSLS,

    # 模型处理面板
    RemoveAllVertexGroupOperator,
    RemoveUnusedVertexGroupOperator,
    MergeVertexGroupsWithSameNumber,
    FillVertexGroupGaps,
    AddBoneFromVertexGroupV2,
    RemoveNotNumberVertexGroup,
    MMTResetRotation,
    CatterRightClickMenu,
    SplitMeshByCommonVertexGroup,
    RecalculateTANGENTWithVectorNormalizedNormal,
    RecalculateCOLORWithVectorNormalizedNormal,
    WWMI_ApplyModifierForObjectWithShapeKeysOperator,
    SmoothNormalSaveToUV,
    RenameAmatureFromGame,
    ModelSplitByLoosePart,
    ModelSplitByVertexGroup,
    ModelDeleteLoosePoint,
    ModelRenameVertexGroupNameWithTheirSuffix,
    ModelResetLocation,
    ModelSortVertexGroupByName,
    ModelVertexGroupRenameByLocation,

    # 集合的右键菜单栏
    Catter_MarkCollection_Switch,
    Catter_MarkCollection_Toggle,

    # UI
    MigotoAttributePanel,
    PanelModelImportConfig,
    PanelGenerateModConfig,
    PanelButtons,
    UpdaterPanel,
    PanelModelProcess,


    HertaUpdatePreference,


    ExtractSubmeshOperator,
    PanelModelSplit,


    # SSMT预备代码
    PanelSSMTBasicConfig,

    PanelSSMTExtractModel,
    SSMTExtractModelGI,
    SSMTExtractModelZZZ,
)


def register():
    for cls in register_classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.dbmt_path = bpy.props.PointerProperty(type=Properties_DBMT_Path)
    bpy.types.Scene.properties_wwmi = bpy.props.PointerProperty(type=Properties_WWMI)
    bpy.types.Scene.properties_import_model = bpy.props.PointerProperty(type=Properties_ImportModel)
    bpy.types.Scene.properties_generate_mod = bpy.props.PointerProperty(type=Properties_GenerateMod)
    bpy.types.Scene.properties_extract_model = bpy.props.PointerProperty(type=Properties_ExtractModel)

    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func_migoto_right_click)
    bpy.types.OUTLINER_MT_collection.append(menu_dbmt_mark_collection_switch)

    addon_updater_ops.register(bl_info)

    bpy.types.Scene.submesh_start = bpy.props.IntProperty(
        name="Start Index",
        default=0,
        min=0
    )
    bpy.types.Scene.submesh_count = bpy.props.IntProperty(
        name="Index Count",
        default=3,
        min=3
    )



def unregister():
    for cls in reversed(register_classes):
        bpy.utils.unregister_class(cls)

    # 卸载右键菜单
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func_migoto_right_click)
    bpy.types.OUTLINER_MT_collection.remove(menu_dbmt_mark_collection_switch)

    del bpy.types.Scene.submesh_start
    del bpy.types.Scene.submesh_count

if __name__ == "__main__":
    register()




