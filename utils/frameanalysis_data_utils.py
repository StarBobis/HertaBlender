from ..config.main_config import GlobalConfig

import os

class FADataUtils:
    frameanalysis_foler_path__file_list:dict[str,str] = {}

    @classmethod
    def get_latest_frame_analysis_file_list(cls):
        # 这里要从当前最新的FrameAnalysis文件夹中获取所有的文件列表
        # 所以，需要和SSMT启动器进行联动，在测试阶段，我们暂时先和DBMT进行联动。
        latest_frame_analysis_folder_path = GlobalConfig.path_latest_frame_analysis_folder()

        if cls.frameanalysis_foler_path__file_list.get(latest_frame_analysis_folder_path) is not None:
            return cls.frameanalysis_foler_path__file_list[latest_frame_analysis_folder_path]

        frame_analysis_file_list = os.listdir(latest_frame_analysis_folder_path)
        cls.frameanalysis_foler_path__file_list[latest_frame_analysis_folder_path] = frame_analysis_file_list
        return frame_analysis_file_list
    
    @classmethod
    def filter_files(cls,frame_analysis_folder_path:str,search_content:str,suffix:str) ->list[str]:
        """
        在指定的FrameAnalysis文件夹中，搜索包含search_content的文件名，并且后缀为suffix的文件。
        """
        if not os.path.exists(frame_analysis_folder_path):
            return []
        
        latest_frame_analysis_file_list = cls.get_latest_frame_analysis_file_list()

        file_list = []
        for file_name in latest_frame_analysis_file_list:
            if search_content in file_name and file_name.endswith(suffix):
                file_list.append(file_name)
        
        return file_list
