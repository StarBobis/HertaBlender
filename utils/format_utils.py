import re

class FormatUtils:

    def get_ib_hash_from_filename(filename:str) -> str:
        # 正则表达式：匹配 '-ib=' 后面的内容，直到遇到 '-' 为止
        match = re.search(r'-ib=([^-]+)', filename)
        if match:
            return match.group(1)  # 返回第一个捕获组，即 ib= 后面的内容
        return None  # 没有匹配到时返回 None