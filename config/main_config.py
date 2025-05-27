import bpy
import os
import json


from ..properties.properties_dbmt_path import Properties_DBMT_Path

class GameCategory:
    UnityVS = "UnityVS"
    UnityCS = "UnityCS"
    UnrealCS = "UnrealCS"
    UnrealVS = "UnrealVS"
    Unknown = "Unknown"

# 全局配置类，使用字段默认为全局可访问的唯一静态变量的特性，来实现全局变量
# 可减少从Main.json中读取的IO消耗
class GlobalConfig:
    # 全局静态变量,任何地方访问到的值都是唯一的
    gamename = ""
    workspacename = ""
    dbmtlocation = ""
    current_game_migoto_folder = ""

    @classmethod
    def get_game_category(cls) -> str:
        if cls.gamename in ["GI","HI3","ZZZ","BloodySpell","GF2","IdentityV"]:
            return GameCategory.UnityVS
        
        elif cls.gamename in ["Game001","AILIMIT"]:
            return GameCategory.UnityCS
        
        elif cls.gamename in ["Game002","WWMI"]:
            return GameCategory.UnrealVS
        
        elif cls.gamename in ["Game003"]:
            return GameCategory.UnrealCS
        else:
            return GameCategory.Unknown
        
    @classmethod
    def save_dbmt_path(cls):
        # 获取当前脚本文件的路径
        script_path = os.path.abspath(__file__)

        # 获取当前插件的工作目录
        plugin_directory = os.path.dirname(script_path)

        # 构建保存文件的路径
        config_path = os.path.join(plugin_directory, 'Config.json')

        # 创建字典对象
        config = {'dbmt_path': bpy.context.scene.dbmt_path.path}

        # 将字典对象转换为 JSON 格式的字符串
        json_data = json.dumps(config)

        # 保存到文件
        with open(config_path, 'w') as file:
            file.write(json_data)



    @classmethod
    def read_from_main_json(cls) :
        main_json_path = GlobalConfig.path_main_json()

        # 先从main_json_path里读取dbmt位置，也就是dbmt总工作空间的位置
        # 在新架构中，总工作空间位置已不会再发生改变，所以用户只需要选择一次就可以了
        if os.path.exists(main_json_path):
            main_setting_file = open(main_json_path)
            main_setting_json = json.load(main_setting_file)
            main_setting_file.close()
            cls.workspacename = main_setting_json.get("CurrentWorkSpace","")
            cls.gamename = main_setting_json.get("CurrentGameName","")
            cls.dbmtlocation = main_setting_json.get("DBMTWorkFolder","") + "\\"
            cls.current_game_migoto_folder = main_setting_json.get("CurrentGameMigotoFolder","") + "\\"
        else:
            print("Can't find: " + main_json_path)

    @classmethod
    def base_path(cls):
        return cls.dbmtlocation
    
    @classmethod
    def path_configs_folder(cls):
        return os.path.join(GlobalConfig.base_path(),"Configs\\")
    
    @classmethod
    def path_3Dmigoto_folder(cls):
        return cls.current_game_migoto_folder
    
    @classmethod
    def path_mods_folder(cls):
        return os.path.join(GlobalConfig.path_3Dmigoto_folder(),"Mods\\") 

    @classmethod
    def path_total_workspace_folder(cls):
        return os.path.join(GlobalConfig.base_path(),"WorkSpace\\") 
    
    @classmethod
    def path_current_game_total_workspace_folder(cls):
        return os.path.join(GlobalConfig.path_total_workspace_folder(),GlobalConfig.gamename + "\\") 
    
    @classmethod
    def path_workspace_folder(cls):
        return os.path.join(GlobalConfig.path_current_game_total_workspace_folder(), GlobalConfig.workspacename + "\\")
    
    @classmethod
    def path_generate_mod_folder(cls):
        # 确保用的时候直接拿到的就是已经存在的目录
        generate_mod_folder_path = os.path.join(GlobalConfig.path_mods_folder(),"Mod_"+GlobalConfig.workspacename + "\\")
        if not os.path.exists(generate_mod_folder_path):
            os.makedirs(generate_mod_folder_path)
        return generate_mod_folder_path
    
    @classmethod
    def path_extract_gametype_folder(cls,draw_ib:str,gametype_name:str):
        return os.path.join(GlobalConfig.path_workspace_folder(), draw_ib + "\\TYPE_" + gametype_name + "\\")
    
    @classmethod
    def path_generatemod_buffer_folder(cls,draw_ib:str):
       
        buffer_path = os.path.join(GlobalConfig.path_generate_mod_folder(),"Buffer\\")
        if not os.path.exists(buffer_path):
            os.makedirs(buffer_path)
        return buffer_path
    
    @classmethod
    def path_generatemod_texture_folder(cls,draw_ib:str):

        texture_path = os.path.join(GlobalConfig.path_generate_mod_folder(),"Texture\\")
        if not os.path.exists(texture_path):
            os.makedirs(texture_path)
        return texture_path
    
    @classmethod
    def path_appdata_local(cls):
        return os.path.join(os.environ['LOCALAPPDATA'])
    
    # 定义基础的Json文件路径---------------------------------------------------------------------------------
    @classmethod
    def path_main_json(cls):
        if Properties_DBMT_Path.use_specified_dbmt():
            return os.path.join(Properties_DBMT_Path.path(),"Configs\\DBMT-Config.json")
        else:
            return os.path.join(GlobalConfig.path_appdata_local(), "DBMT-Config.json")
        
    # 提取模型需要读取当前的游戏的3Dmigoto下的最新的FrameAnalysis文件夹
    @classmethod
    def path_latest_frame_analysis_folder(cls):
        migoto_subs_folders = os.listdir(cls.current_game_migoto_folder)

        frame_analysis_folder_list = []

        for subs_folder_name in migoto_subs_folders:
            if subs_folder_name.startswith("FrameAnalysis"):
                # print(subs_folder_name)
                frame_analysis_folder_list.append(subs_folder_name)
        
        # 排序，确保能获取到最新的FrameAnalysis文件夹
        frame_analysis_folder_list.sort()

        latest_frame_analysis_folder_path = ""
        if len(frame_analysis_folder_list) > 0:
            latest_frame_analysis_folder_path = os.path.join(cls.current_game_migoto_folder, frame_analysis_folder_list[-1])

        return latest_frame_analysis_folder_path
    

    @classmethod
    def path_gametype_config_folder(cls):
        gametype_config_folder = os.path.join(cls.path_configs_folder(),"GameTypeConfigs\\")
        return gametype_config_folder

    @classmethod
    def path_current_gametype_folder(cls):
        current_gametype_folder = os.path.join(cls.path_gametype_config_folder(),cls.gamename + "\\")
        return current_gametype_folder
    
    @classmethod
    def path_latest_frameanalysis_log_file(cls):
        latest_frame_analysis_folder_path = cls.path_latest_frame_analysis_folder()
        latest_framenanalysis_log_file_path = os.path.join(latest_frame_analysis_folder_path, "log.txt")
        return latest_framenanalysis_log_file_path
    
