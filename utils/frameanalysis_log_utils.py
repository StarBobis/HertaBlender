from ..config.main_config import GlobalConfig
from ..utils.timer_utils import TimerUtils

class ShaderResource:
    def __init__(self, log_line):
        # initialize values to empty strings
        self.Index = ""
        self.Resource = ""
        self.Hash = ""
        self.View = ""

        # 假设有一个方法来去除字符串首尾空白字符，这里直接使用 strip() 方法
        trim_log_line = log_line.strip()
        split = trim_log_line.split(':')
        self.Index = split[0]

        # 获取并修剪参数部分
        arguments = split[1].strip() if len(split) > 1 else ""
        argument_split = [arg for arg in arguments.split(' ') if arg]  # 去除空字符串

        for key_value_str in argument_split:
            kv_list = key_value_str.split('=', 1)
            if len(kv_list) == 2:
                key, value = kv_list[0].strip(), kv_list[1].strip()

                if key.lower() == "resource":
                    self.Resource = value
                elif key.lower() == "hash":
                    self.Hash = value
                elif key.lower() == "view":
                    self.View = value


class FALogUtils:
    log_file_path__log_line_list:dict[str,list[str]] = {}


    @classmethod
    def get_log_line_list(cls, log_file_path:str = "") -> list[str]:
        # we need to know where .log file located.
        
        log_line_list = []

        # is no path provided, we think it use the latest frameanalysis log file.
        if log_file_path == "":
            log_file_path = GlobalConfig.path_latest_frameanalysis_log_file()
        
        # if we have cache, we use cache to save time.
        if cls.log_file_path__log_line_list.get(log_file_path) is not None:
            return cls.log_file_path__log_line_list[log_file_path]
        
        # if we don't have cache, we read the log file and cache it.
        with open(log_file_path, 'r', encoding='utf-8') as ff:
            log_line_list = ff.readlines()
        
        cls.log_file_path__log_line_list[log_file_path] = log_line_list
        return log_line_list
    
    @classmethod
    def get_drawcall_index_list_by_ib_hash(cls,ib_hash:str,only_match_first:bool,log_file_path:str="") ->list[str]:
        # TimerUtils.Start("FALogUtils.get_drawcall_index_list_by_ib_hash")
        log_line_list:list[str] = cls.get_log_line_list(log_file_path=log_file_path)
        # print("Log Line List Length: " + str(len(log_line_list)))
        index_set = set()
        
        for log_line in log_line_list:
            # print(log_line)
            if log_line.startswith("00"):
                current_index = log_line[0:6]
                # print("Current Index: " + current_index)
            
            if "hash=" + ib_hash in log_line:
                index_set.add(current_index)
                if only_match_first:
                    break
        # print("Draw Call Index Set: " + str(index_set))
        # TimerUtils.End("FALogUtils.get_drawcall_index_list_by_ib_hash")
        return list(index_set)
    
    @classmethod
    def get_line_list_by_index(cls,index:str,log_file_path:str="") ->list[str]:
        log_line_list:list[str] = cls.get_log_line_list(log_file_path=log_file_path)

        index_line_list = []

        index_number = int(index)
        find_index = False
        for line in log_line_list:

            if line.startswith("00") and not find_index:
                current_index_number = int(line[0:6])
                if current_index_number == index_number:
                    find_index = True
                    index_line_list.append(line)
                    continue
            
            if find_index:
                if line.startswith("00"):
                    current_index_number = int(line[0:6])
                    if current_index_number > index_number:
                        break
                    else:
                        index_line_list.append(line)
                else:
                    index_line_list.append(line)
        
        return index_line_list


    @classmethod
    def get_pointlist_index_by_ib_hash(cls,ib_hash:str,log_file_path:str="") ->str:
        # TimerUtils.Start("FALogUtils.get_pointlist_index_by_ib_hash")
        draw_call_index_list = cls.get_drawcall_index_list_by_ib_hash(ib_hash=ib_hash,only_match_first=True,log_file_path=log_file_path)
        # print("Draw Call Index List: " + str(draw_call_index_list))

        if len(draw_call_index_list) == 0:
            # if we can't find the draw call index, we return an empty list.
            return ""
        
        first_trianglelist_index = draw_call_index_list[0]

        trianglelist_index_line_list = cls.get_line_list_by_index(index=first_trianglelist_index, log_file_path=log_file_path)

        vb0_hash = ""
        find_ia_set_vb = False

        for call_line in trianglelist_index_line_list:
            if "IASetVertexBuffers" in call_line and not find_ia_set_vb:
                find_ia_set_vb = True
                continue

            if find_ia_set_vb:
                if not call_line.startswith("00"):
                    shader_resource = ShaderResource(call_line)

                    slot = "vb" + shader_resource.Index
                    if slot == "vb0":
                        vb0_hash = shader_resource.Hash
                else:
                    break
        
        if vb0_hash == "":
            return ""
        
        find_str = "hash=" + vb0_hash
        current_index = ""
        trianglelist_index_number = int(first_trianglelist_index)

        possible_index_list = []
        log_line_list = cls.get_log_line_list(log_file_path=log_file_path)
        for log_line in log_line_list:
            if log_line.startswith("00"):
                current_index = log_line[0:6]
               
            if find_str in log_line:
                pointlist_index_number = int(current_index)
                if pointlist_index_number < trianglelist_index_number:
                    if not current_index in possible_index_list:
                        possible_index_list.append(current_index)

        # TimerUtils.End("FALogUtils.get_pointlist_index_by_ib_hash")
        if len(possible_index_list) != 0:
            return possible_index_list[-1]
        
        return ""

