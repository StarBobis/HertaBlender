import os 


from .main_config import GlobalConfig
from ..utils.json_utils import JsonUtils
from ..migoto.migoto_format import D3D11GameType, Fatal



class TextureReplace:
    def  __init__(self):
        self.resource_name = ""
        self.filter_index = 0
        self.hash = ""
        self.style = ""

class ImportConfig:
    '''
    在一键导入工作空间时，Import.json会记录导入的GameType，在生成Mod时需要用到
    所以这里我们读取Import.json来确定要从哪个提取出来的数据类型文件夹中读取
    然后读取tmp.json来初始化D3D11GameType
    '''
    def __init__(self,draw_ib:str):
        self.draw_ib = draw_ib # DrawIB

        self.category_hash_dict = {}
        self.import_model_list = []
        self.match_first_index_list = []
        self.part_name_list = []

        self.vertex_limit_hash = ""
        self.work_game_type = ""

        self.TextureResource_Name_FileName_Dict:dict[str,str] = {} # 自动贴图配置项
        self.PartName_SlotTextureReplaceDict_Dict:dict[str,dict[str,TextureReplace]] = {} # 自动贴图配置项

        self.parse_attributes()

    def parse_attributes(self):
        workspace_import_json_path = os.path.join(GlobalConfig.path_workspace_folder(), "Import.json")
        draw_ib_gametypename_dict = JsonUtils.LoadFromFile(workspace_import_json_path)
        gametypename = draw_ib_gametypename_dict.get(self.draw_ib,"")

        # 新版本中，我们把数据类型的信息写到了tmp.json中，这样我们就能够读取tmp.json中的内容来决定生成Mod时的数据类型了。
        extract_gametype_folder_path = GlobalConfig.path_extract_gametype_folder(draw_ib=self.draw_ib,gametype_name=gametypename)
        tmp_json_path = os.path.join(extract_gametype_folder_path,"tmp.json")
        if os.path.exists(tmp_json_path):
            self.d3d11GameType:D3D11GameType = D3D11GameType(tmp_json_path)
        else:
            raise Fatal("Can't find your tmp.json for generate mod:" + tmp_json_path)
        
        '''
        读取tmp.json中的内容，后续会用于生成Mod的ini文件
        需要在确定了D3D11GameType之后再执行
        '''
        extract_gametype_folder_path = GlobalConfig.path_extract_gametype_folder(draw_ib=self.draw_ib,gametype_name=self.d3d11GameType.GameTypeName)
        tmp_json_path = os.path.join(extract_gametype_folder_path,"tmp.json")
        tmp_json_dict = JsonUtils.LoadFromFile(tmp_json_path)

        self.category_hash_dict = tmp_json_dict["CategoryHash"]
        self.import_model_list = tmp_json_dict["ImportModelList"]
        self.match_first_index_list = tmp_json_dict["MatchFirstIndex"]
        self.part_name_list = tmp_json_dict["PartNameList"]
        # print(self.partname_textureresourcereplace_dict)
        self.vertex_limit_hash = tmp_json_dict["VertexLimitVB"]
        self.work_game_type = tmp_json_dict["WorkGameType"]

        # 自动贴图依赖于这个字典
        partname_textureresourcereplace_dict:dict[str,str] = tmp_json_dict["PartNameTextureResourceReplaceList"]

        print(tmp_json_path)
        print(partname_textureresourcereplace_dict)
        for partname, texture_resource_replace_list in partname_textureresourcereplace_dict.items():
            slot_texture_replace_dict = {}
            for texture_resource_replace in texture_resource_replace_list:
                splits = texture_resource_replace.split("=")
                slot_name = splits[0].strip()
                texture_filename = splits[1].strip()

                resource_name = "Resource_" + os.path.splitext(texture_filename)[0]

                filename_splits = os.path.splitext(texture_filename)[0].split("_")
                texture_hash = filename_splits[2]

                texture_replace = TextureReplace()
                texture_replace.hash = texture_hash
                texture_replace.resource_name = resource_name
                texture_replace.style = filename_splits[3]

                slot_texture_replace_dict[slot_name] = texture_replace

                self.TextureResource_Name_FileName_Dict[resource_name] = texture_filename

            self.PartName_SlotTextureReplaceDict_Dict[partname] = slot_texture_replace_dict