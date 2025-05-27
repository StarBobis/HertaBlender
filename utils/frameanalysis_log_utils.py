from ..config.main_config import GlobalConfig


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
        with open(log_file_path, 'r', encoding='utf-8') as file:
            for line in file:
                log_line_list.append(line.strip())
        
        cls.log_file_path__log_line_list[log_file_path] = log_line_list
        return log_line_list
    
    