import os

class TextureUtils:
    @classmethod
    def find_texture(cls,texture_prefix, texture_suffix, directory):
        '''
        查找目标目录下，满足指定后缀和前缀的贴图文件
        '''
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(texture_suffix) and file.startswith(texture_prefix):
                    texture_path = os.path.join(root, file)
                    return texture_path
        return None
    


    