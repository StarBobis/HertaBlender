import bpy

from ..config.main_config import GlobalConfig
from ..utils.frameanalysis_data_utils import FADataUtils
from ..utils.frameanalysis_log_utils import FALogUtils
from ..utils.format_utils import FormatUtils
from ..utils.log_utils import LOG

from ..properties.properties_extract_model import Properties_ExtractModel


class ZZZModel:

    @classmethod
    def extract_model(cls):
        LOG.newline()
        print("CurrentGame: " + GlobalConfig.gamename)

        print(GlobalConfig.current_game_migoto_folder)
        latest_frameanalysis_folder_path = GlobalConfig.path_latest_frame_analysis_folder()
        
        print("Latest Frame Analysis Folder Path: " + latest_frameanalysis_folder_path)

        ib_buf_file_list:list = FADataUtils.filter_files(latest_frameanalysis_folder_path,"-ib=",".buf")

        ib_hash_set = set()
        for ib_buf_file_name in ib_buf_file_list:
            # print("IB Buffer File Name: " + ib_buf_file_name)
            ib_hash = FormatUtils.get_ib_hash_from_filename(ib_buf_file_name)
            # print("IB Hash: " + ib_hash)
            ib_hash_set.add(ib_hash)

        print("Unique IB Hashes: " + str(ib_hash_set))

        extract_ib_hash_list = list(ib_hash_set)
        # If only extract gpu-preskinning type, we need to filter the ib hash.
        if Properties_ExtractModel.only_match_gpu():
            print("Only extracting GPU pre-skinning models.")
            
            pointlist_ib_hash_list = []
            for ib_hash in ib_hash_set:
                pointlist_index = FALogUtils.get_pointlist_index_by_ib_hash(ib_hash=ib_hash)
                if pointlist_index != "":
                    pointlist_ib_hash_list.append(ib_hash)

            extract_ib_hash_list = pointlist_ib_hash_list
            print("Point List IB: " + str(pointlist_ib_hash_list))
        
        LOG.info("Extract IB Hash List: " + str(extract_ib_hash_list))
        LOG.newline()


class SSMTExtractModelZZZ(bpy.types.Operator):
    bl_idname = "ssmt.extract_model_zzz"
    bl_label = "Extract Model(ZZZ)"
    bl_description = "Extract Model(ZZZ)"

    def execute(self, context):
        ZZZModel.extract_model()
        return {'FINISHED'}
    
