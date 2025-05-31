import math
import numpy

from ..properties.properties_generate_mod import Properties_GenerateMod
from ..utils.timer_utils import TimerUtils


class MeshFormatConverter:
    '''
    各种格式转换
    '''
    # 向量归一化
    @classmethod
    def vector_normalize(cls,v):
        """归一化向量"""
        length = math.sqrt(sum(x * x for x in v))
        if length == 0:
            return v  # 避免除以零
        return [x / length for x in v]
    
    @classmethod
    def add_and_normalize_vectors(cls,v1, v2):
        """将两个向量相加并规范化(normalize)"""
        # 相加
        result = [a + b for a, b in zip(v1, v2)]
        # 归一化
        normalized_result = cls.vector_normalize(result)
        return normalized_result
    
    # 辅助函数：计算两个向量的点积
    @classmethod
    def dot_product(cls,v1, v2):
        return sum(a * b for a, b in zip(v1, v2))

    '''
    这四个UNORM和SNORM比较特殊需要这样处理，其它float类型转换直接astype就行
    '''
    @classmethod
    def convert_4x_float32_to_r8g8b8a8_snorm(cls, input_array):
        return numpy.round(input_array * 127).astype(numpy.int8)
    
    @classmethod
    def convert_4x_float32_to_r8g8b8a8_unorm(cls,input_array):
        return numpy.round(input_array * 255).astype(numpy.uint8)
    
    @classmethod
    def convert_4x_float32_to_r16g16b16a16_snorm(cls,input_array):
        return numpy.round(input_array * 32767).astype(numpy.int16)
    
    @classmethod
    def normalize_weights(cls, weights):
        '''
        Normalizes provided list of float weights in an 8-bit friendly way.
        Returns list of 8-bit integers (0-255) with sum of 255.

        Credit To @SpectrumQT https://github.com/SpectrumQT
        '''
        total = sum(weights)

        if total == 0:
            return [0] * len(weights)

        precision_error = 255

        tickets = [0] * len(weights)
        
        normalized_weights = [0] * len(weights)

        for idx, weight in enumerate(weights):
            # Ignore zero weight
            if weight == 0:
                continue

            weight = weight / total * 255
            # Ignore weight below minimal precision (1/255)
            if weight < 1:
                normalized_weights[idx] = 0
                continue

            # Strip float part from the weight
            int_weight = 0

            int_weight = int(weight)

            normalized_weights[idx] = int_weight
            # Reduce precision_error by the integer weight value
            precision_error -= int_weight
            # Calculate weight 'significance' index to prioritize lower weights with float loss
            tickets[idx] = 255 / weight * (weight - int_weight)

        while precision_error > 0:
            ticket = max(tickets)
            if ticket > 0:
                # Route `1` from precision_error to weights with non-zero ticket value first
                i = tickets.index(ticket)
                tickets[i] = 0
            else:
                # Route remaining precision_error to highest weight to reduce its impact
                i = normalized_weights.index(max(normalized_weights))
            # Distribute `1` from precision_error
            normalized_weights[i] += 1
            precision_error -= 1

        return normalized_weights
    
    @classmethod
    def convert_4x_float32_to_r8g8b8a8_unorm_blendweights(cls, input_array):
        # print(f"Input shape: {input_array.shape}")  # 输出形状 (1896, 4)

        # TODO 速度很慢，但是numpy自带的方法无法解决权重炸毛的问题，暂时还必须这样
        # 这里每个顶点都要进行这个操作，总共执行21万次，平均执行4秒，呵呵呵

        result = numpy.zeros_like(input_array, dtype=numpy.uint8)

        for i in range(input_array.shape[0]):

            weights = input_array[i]

            # 如果权重含有NaN值，则将该行的所有值设置为0。
            # 因为权重只要是被刷过，就不会出现NaN值。
            find_nan = False
            for w in weights:
                if math.isnan(w):
                    row_normalized = [0, 0, 0, 0]
                    result[i] = numpy.array(row_normalized, dtype=numpy.uint8)
                    find_nan = True
                    break
                    # print(weights)
                    # raise Fatal("NaN found in weights")
            
            if not find_nan:
                # 对每一行调用 normalize_weights 方法
                row_normalized = cls.normalize_weights(input_array[i])
                result[i] = numpy.array(row_normalized, dtype=numpy.uint8)

        return result
    
    # @classmethod
    # def convert_4x_float32_to_r8g8b8a8_unorm_blendweights(cls, input_array:numpy.ndarray):
    #     # 核心转换流程
    #     scaled = input_array * 255.0                  # 缩放至0-255范围
    #     rounded = numpy.around(scaled)                 # 四舍五入
    #     clamped = numpy.clip(rounded, 0, 255)          # 约束数值范围
    #     result = clamped.astype(numpy.uint8)           # 转换为uint8

    #     return result
    
    @classmethod
    def convert_4x_float32_to_r16g16b16a16_unorm(cls, input_array):
        return numpy.round(input_array * 65535).astype(numpy.uint16)
    
    @classmethod
    def convert_4x_float32_to_r16g16b16a16_snorm(cls, input_array):
        return numpy.round(input_array * 32767).astype(numpy.int16)
    
    @classmethod
    def average_normal_tangent(cls,obj,indexed_vertices,d3d11GameType,dtype):
        '''
        Nico: 米游所有游戏都能用到这个，还有曾经的GPU-PreSkinning的GF2也会用到这个，崩坏三2.0新角色除外。
        尽管这个可以起到相似的效果，但是仍然无法完美获取模型本身的TANGENT数据，只能做到身体轮廓线99%近似。
        经过测试，头发轮廓线部分并不是简单的向量归一化，也不是算术平均归一化。
        '''
        # TimerUtils.Start("Recalculate TANGENT")

        if "TANGENT" not in d3d11GameType.OrderedFullElementList:
            return indexed_vertices
        allow_calc = False
        if Properties_GenerateMod.recalculate_tangent():
            allow_calc = True
        elif obj.get("3DMigoto:RecalculateTANGENT",False): 
            allow_calc = True
        
        if not allow_calc:
            return indexed_vertices
        
        # 不用担心这个转换的效率，速度非常快
        vb = bytearray()
        for vertex in indexed_vertices:
            vb += bytes(vertex)
        vb = numpy.frombuffer(vb, dtype = dtype)

        # 开始重计算TANGENT
        positions = numpy.array([val['POSITION'] for val in vb])
        normals = numpy.array([val['NORMAL'] for val in vb], dtype=float)

        # 对位置进行排序，以便相同的位置会相邻
        sort_indices = numpy.lexsort(positions.T)
        sorted_positions = positions[sort_indices]
        sorted_normals = normals[sort_indices]

        # 找出位置变化的地方，即我们需要分组的地方
        group_indices = numpy.flatnonzero(numpy.any(sorted_positions[:-1] != sorted_positions[1:], axis=1))
        group_indices = numpy.r_[0, group_indices + 1, len(sorted_positions)]

        # 累加法线和计算计数
        unique_positions = sorted_positions[group_indices[:-1]]
        accumulated_normals = numpy.add.reduceat(sorted_normals, group_indices[:-1], axis=0)
        counts = numpy.diff(group_indices)

        # 归一化累积法线向量
        normalized_normals = accumulated_normals / numpy.linalg.norm(accumulated_normals, axis=1)[:, numpy.newaxis]
        normalized_normals[numpy.isnan(normalized_normals)] = 0  # 处理任何可能出现的零向量导致的除零错误

        # 构建结果字典
        position_normal_dict = dict(zip(map(tuple, unique_positions), normalized_normals))

        # TimerUtils.End("Recalculate TANGENT")

        # 获取所有位置并转换为元组，用于查找字典
        positions = [tuple(pos) for pos in vb['POSITION']]

        # 从字典中获取对应的标准化法线
        normalized_normals = numpy.array([position_normal_dict[pos] for pos in positions])

        # 计算 w 并调整 tangent 的第四个分量
        w = numpy.where(vb['TANGENT'][:, 3] >= 0, -1.0, 1.0)

        # 更新 TANGENT 分量，注意这里的切片操作假设 TANGENT 有四个分量
        vb['TANGENT'][:, :3] = normalized_normals
        vb['TANGENT'][:, 3] = w

        # TimerUtils.End("Recalculate TANGENT")

        return vb

    @classmethod
    def average_normal_color(cls,obj,indexed_vertices,d3d11GameType,dtype):
        '''
        Nico: 算数平均归一化法线，HI3 2.0角色使用的方法
        '''
        if "COLOR" not in d3d11GameType.OrderedFullElementList:
            return indexed_vertices
        allow_calc = False
        if Properties_GenerateMod.recalculate_color():
            allow_calc = True
        elif obj.get("3DMigoto:RecalculateCOLOR",False): 
            allow_calc = True
        if not allow_calc:
            return indexed_vertices

        # 开始重计算COLOR
        TimerUtils.Start("Recalculate COLOR")

        # 不用担心这个转换的效率，速度非常快
        vb = bytearray()
        for vertex in indexed_vertices:
            vb += bytes(vertex)
        vb = numpy.frombuffer(vb, dtype = dtype)

        # 首先提取所有唯一的位置，并创建一个索引映射
        unique_positions, position_indices = numpy.unique(
            [tuple(val['POSITION']) for val in vb], 
            return_inverse=True, 
            axis=0
        )

        # 初始化累积法线和计数器为零
        accumulated_normals = numpy.zeros((len(unique_positions), 3), dtype=float)
        counts = numpy.zeros(len(unique_positions), dtype=int)

        # 累加法线并增加计数（这里假设vb是一个list）
        for i, val in enumerate(vb):
            accumulated_normals[position_indices[i]] += numpy.array(val['NORMAL'], dtype=float)
            counts[position_indices[i]] += 1

        # 对所有位置的法线进行一次性规范化处理
        mask = counts > 0
        average_normals = numpy.zeros_like(accumulated_normals)
        average_normals[mask] = (accumulated_normals[mask] / counts[mask][:, None])

        # 归一化到[0,1]，然后映射到颜色值
        normalized_normals = ((average_normals + 1) / 2 * 255).astype(numpy.uint8)

        # 更新颜色信息
        new_color = []
        for i, val in enumerate(vb):
            color = [0, 0, 0, val['COLOR'][3]]  # 保留原来的Alpha通道
            
            if mask[position_indices[i]]:
                color[:3] = normalized_normals[position_indices[i]]

            new_color.append(color)

        # 将新的颜色列表转换为NumPy数组
        new_color_array = numpy.array(new_color, dtype=numpy.uint8)

        # 更新vb中的颜色信息
        for i, val in enumerate(vb):
            val['COLOR'] = new_color_array[i]

        TimerUtils.End("Recalculate COLOR")
        return vb
