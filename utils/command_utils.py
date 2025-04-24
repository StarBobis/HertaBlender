# The helper class helps us to execute outside programs.
import subprocess

from ..config.main_config import *


class CommandUtils:

    @classmethod
    def OpenGeneratedModFolder(cls):
        '''
        This will be call after generate mod, it will open explorer and shows the result mod files generated.

        不能使用subprocess.run('explorer',path)的方式打开文件夹，否则部分用户的电脑上无法识别到路径，且自动打开 文档 文件夹。
        #而且使用subprocess.run('explorer',path)的方式打开文件夹会导致每次都多打开一个新的文件夹，几百个在一起就会把电脑卡死。
        所以使用os.startfile()是最好的
        '''
        generated_mod_folder_path = GlobalConfig.path_generate_mod_folder()
        os.startfile(generated_mod_folder_path)



