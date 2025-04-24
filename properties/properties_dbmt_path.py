import bpy
import os
import json


class Properties_DBMT_Path(bpy.types.PropertyGroup):
    def load_dbmt_path():
        # 获取当前脚本文件的路径
        script_path = os.path.abspath(__file__)

        # 获取当前插件的工作目录
        plugin_directory = os.path.dirname(os.path.dirname(script_path))

        # 构建配置文件的路径
        config_path = os.path.join(plugin_directory, 'config\\Config.json')

        # 读取文件
        with open(config_path, 'r') as file:
            json_data = file.read()

        # 将 JSON 格式的字符串解析为字典对象
        config = json.loads(json_data)

        # 读取保存的路径
        return config['dbmt_path']
    
    # ------------------------------------------------------------------------------------------------------------
    path: bpy.props.StringProperty(
        name="DBMT.exe Location",
        description="插件需要先选择DBMT-GUI.exe的所在路径才能正常工作",
        default= load_dbmt_path(),
        subtype='DIR_PATH'
    ) # type: ignore

    @classmethod
    def path(cls):
        '''
        bpy.context.scene.dbmt_path.path
        '''
        return bpy.context.scene.dbmt_path.path

    use_specified_dbmt :bpy.props.BoolProperty(
        name="使用指定的DBMT路径",
        description="Use specified DBMT path to work for specified DBMT instead of current opening DBMT",
        default=False
    ) # type: ignore

    @classmethod
    def use_specified_dbmt(cls):
        '''
        bpy.context.scene.dbmt_path.use_specified_dbmt
        '''
        return bpy.context.scene.dbmt_path.use_specified_dbmt
    
