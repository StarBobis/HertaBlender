import bpy
import numpy
import collections

from ..migoto.migoto_format import D3D11GameType
from .mesh_data import MeshData
from .mesh_format_converter import MeshFormatConverter
from ..utils.migoto_utils import MigotoUtils, Fatal

from ..config.main_config import GlobalConfig, GameCategory

class BufferModel:
    '''
    BufferModel用于抽象每一个obj的mesh对象中的数据，加快导出速度。
    '''
    
    def __init__(self,d3d11GameType:D3D11GameType) -> None:
        self.d3d11GameType:D3D11GameType = d3d11GameType

        self.dtype = None
        self.element_vertex_ndarray  = None
        
    def check_and_verify_attributes(self,obj:bpy.types.Object):
        '''
        校验并补全部分元素
        COLOR
        TEXCOORD、TEXCOORD1、TEXCOORD2、TEXCOORD3
        '''
        for d3d11_element_name in self.d3d11GameType.OrderedFullElementList:
            d3d11_element = self.d3d11GameType.ElementNameD3D11ElementDict[d3d11_element_name]
            # 校验并补全所有COLOR的存在
            if d3d11_element_name.startswith("COLOR"):
                if d3d11_element_name not in obj.data.vertex_colors:
                    obj.data.vertex_colors.new(name=d3d11_element_name)
                    print("当前obj ["+ obj.name +"] 缺少游戏渲染所需的COLOR: ["+  "COLOR" + "]，已自动补全")
            
            # 校验TEXCOORD是否存在
            if d3d11_element_name.startswith("TEXCOORD"):
                if d3d11_element_name + ".xy" not in obj.data.uv_layers:
                    # 此时如果只有一个UV，则自动改名为TEXCOORD.xy
                    if len(obj.data.uv_layers) == 1 and d3d11_element_name == "TEXCOORD":
                            obj.data.uv_layers[0].name = d3d11_element_name + ".xy"
                    else:
                        # 否则就自动补一个UV，防止后续calc_tangents失败
                        obj.data.uv_layers.new(name=d3d11_element_name + ".xy")
            
            # Check if BLENDINDICES exists
            if d3d11_element_name.startswith("BLENDINDICES"):
                if not obj.vertex_groups:
                    raise Fatal("your object [" +obj.name + "] need at leat one valid Vertex Group, Please check if your model's Vertex Group is correct.")

    def parse_elementname_ravel_ndarray_dict(self,mesh:bpy.types.Mesh) -> dict:
        '''
        - 注意这里是从mesh.loops中获取数据，而不是从mesh.vertices中获取数据
        - 所以后续使用的时候要用mesh.loop里的索引来进行获取数据

        TODO 
        目前的权重导出架构，无法处理存在多个BLENDWEIGHTS的清空
        需要重新开发权重导出代码
        '''

        mesh_loops = mesh.loops
        mesh_loops_length = len(mesh_loops)
        mesh_vertices = mesh.vertices
        mesh_vertices_length = len(mesh.vertices)

        loop_vertex_indices = numpy.empty(mesh_loops_length, dtype=int)
        mesh_loops.foreach_get("vertex_index", loop_vertex_indices)

        self.dtype = numpy.dtype([])

        blendweights_formatlen = 0
        for d3d11_element_name in self.d3d11GameType.OrderedFullElementList:
            d3d11_element = self.d3d11GameType.ElementNameD3D11ElementDict[d3d11_element_name]
            np_type = MigotoUtils.get_nptype_from_format(d3d11_element.Format)
            format_len = MigotoUtils.format_components(d3d11_element.Format)

            # 因为YYSLS出现了多个BLENDWEIGHTS的情况，所以这里只能用这个StartWith判断
            if d3d11_element_name.startswith("BLENDWEIGHT"):
                blendweights_formatlen = format_len

            # XXX 长度为1时必须手动指定为(1,)否则会变成1维数组
            if format_len == 1:
                self.dtype = numpy.dtype(self.dtype.descr + [(d3d11_element_name, (np_type, (1,)))])
            else:
                self.dtype = numpy.dtype(self.dtype.descr + [(d3d11_element_name, (np_type, format_len))])

        self.element_vertex_ndarray = numpy.zeros(mesh_loops_length,dtype=self.dtype)


        mesh_data = MeshData(mesh=mesh)
        blendweights_dict, blendindices_dict = mesh_data.get_blendweights_blendindices_v2()


        # 对每一种Element都获取对应的数据
        for d3d11_element_name in self.d3d11GameType.OrderedFullElementList:
            d3d11_element = self.d3d11GameType.ElementNameD3D11ElementDict[d3d11_element_name]

            if d3d11_element_name == 'POSITION':
                # TimerUtils.Start("Position Get")
                vertex_coords = numpy.empty(mesh_vertices_length * 3, dtype=numpy.float32)
                # Notice: 'undeformed_co' is static, don't need dynamic calculate like 'co' so it is faster.
                mesh_vertices.foreach_get('undeformed_co', vertex_coords)
                
                positions = vertex_coords.reshape(-1, 3)[loop_vertex_indices]
                if d3d11_element.Format == 'R16G16B16A16_FLOAT':
                    positions = positions.astype(numpy.float16)
                    new_array = numpy.zeros((positions.shape[0], 4))
                    new_array[:, :3] = positions
                    positions = new_array

                self.element_vertex_ndarray[d3d11_element_name] = positions
                # TimerUtils.End("Position Get") # 0:00:00.057535 

            elif d3d11_element_name == 'NORMAL':
                if d3d11_element.Format == 'R16G16B16A16_FLOAT':
                    result = numpy.ones(mesh_loops_length * 4, dtype=numpy.float32)
                    normals = numpy.empty(mesh_loops_length * 3, dtype=numpy.float32)
                    mesh_loops.foreach_get('normal', normals)
                    result[0::4] = normals[0::3]
                    result[1::4] = normals[1::3]
                    result[2::4] = normals[2::3]
                    result = result.reshape(-1, 4)

                    result = result.astype(numpy.float16)
                    self.element_vertex_ndarray[d3d11_element_name] = result

                elif d3d11_element.Format == 'R8G8B8A8_SNORM':
                    result = numpy.ones(mesh_loops_length * 4, dtype=numpy.float32)
                    normals = numpy.empty(mesh_loops_length * 3, dtype=numpy.float32)
                    mesh_loops.foreach_get('normal', normals)
                    result[0::4] = normals[0::3]
                    result[1::4] = normals[1::3]
                    result[2::4] = normals[2::3]
                    

                    if GlobalConfig.get_game_category() == GameCategory.UnrealVS or GlobalConfig.get_game_category() == GameCategory.UnrealCS:
                        bitangent_signs = numpy.empty(mesh_loops_length, dtype=numpy.float32)
                        mesh_loops.foreach_get("bitangent_sign", bitangent_signs)
                        result[3::4] = bitangent_signs

                        # XXX 3.6和3.2都需要翻转一下，原因未知
                        if bpy.app.version < (4,0,0):
                            result[0::4] *= -1
                            result[1::4] *= -1
                            result[2::4] *= -1
                        # print("Unreal: Set NORMAL.W to bitangent_sign")
                    
                    result = result.reshape(-1, 4)

                    self.element_vertex_ndarray[d3d11_element_name] = MeshFormatConverter.convert_4x_float32_to_r8g8b8a8_snorm(result)


                elif d3d11_element.Format == 'R8G8B8A8_UNORM':
                    # 因为法线数据是[-1,1]如果非要导出成UNORM，那一定是进行了归一化到[0,1]
                    
                    result = numpy.ones(mesh_loops_length * 4, dtype=numpy.float32)

                    # 燕云十六声的最后一位w固定为0
                    if GlobalConfig.gamename == "YYSLS":
                        result = numpy.zeros(mesh_loops_length * 4, dtype=numpy.float32)
                        
                    normals = numpy.empty(mesh_loops_length * 3, dtype=numpy.float32)
                    mesh_loops.foreach_get('normal', normals)
                    result[0::4] = normals[0::3]
                    result[1::4] = normals[1::3]
                    result[2::4] = normals[2::3]
                    result = result.reshape(-1, 4)
                    
                    # 归一化 (此处感谢 球球 的代码开发)
                    def DeConvert(nor):
                        return (nor + 1) * 0.5

                    for i in range(len(result)):
                        result[i][0] = DeConvert(result[i][0])
                        result[i][1] = DeConvert(result[i][1])
                        result[i][2] = DeConvert(result[i][2])

                    self.element_vertex_ndarray[d3d11_element_name] = MeshFormatConverter.convert_4x_float32_to_r8g8b8a8_unorm(result)
                
                else:
                    result = numpy.empty(mesh_loops_length * 3, dtype=numpy.float32)
                    mesh_loops.foreach_get('normal', result)
                    # 将一维数组 reshape 成 (mesh_loops_length, 3) 形状的二维数组
                    result = result.reshape(-1, 3)
                    self.element_vertex_ndarray[d3d11_element_name] = result
                


            elif d3d11_element_name == 'TANGENT':

                result = numpy.empty(mesh_loops_length * 4, dtype=numpy.float32)

                # 使用 foreach_get 批量获取切线和副切线符号数据
                tangents = numpy.empty(mesh_loops_length * 3, dtype=numpy.float32)
                mesh_loops.foreach_get("tangent", tangents)
                # 将切线分量放置到输出数组中
                result[0::4] = tangents[0::3]  # x 分量
                result[1::4] = tangents[1::3]  # y 分量
                result[2::4] = tangents[2::3]  # z 分量

                if GlobalConfig.gamename == "YYSLS":
                    # 燕云十六声的TANGENT.w固定为1
                    tangent_w = numpy.ones(mesh_loops_length, dtype=numpy.float32)
                    # TODO 这里仍然不知道是什么，可能是平滑法线？
                    # result[0::4] *= -1
                    # result[1::4] *= -1
                    # result[2::4] *= -1
                    result[3::4] = tangent_w
                elif GlobalConfig.get_game_category() == GameCategory.UnityCS or GlobalConfig.get_game_category() == GameCategory.UnityVS:
                    bitangent_signs = numpy.empty(mesh_loops_length, dtype=numpy.float32)
                    mesh_loops.foreach_get("bitangent_sign", bitangent_signs)
                    # XXX 将副切线符号乘以 -1
                    # 这里翻转（翻转指的就是 *= -1）是因为如果要确保Unity游戏中渲染正确，必须翻转TANGENT的W分量
                    bitangent_signs *= -1
                    result[3::4] = bitangent_signs  # w 分量 (副切线符号)
                elif GlobalConfig.get_game_category() == GameCategory.UnrealVS or GlobalConfig.get_game_category() == GameCategory.UnrealCS:
                    # Unreal引擎中这里要填写固定的1
                    tangent_w = numpy.ones(mesh_loops_length, dtype=numpy.float32)
                    result[3::4] = tangent_w
                
                # 重塑 output_tangents 成 (mesh_loops_length, 4) 形状的二维数组
                result = result.reshape(-1, 4)

                if d3d11_element.Format == 'R16G16B16A16_FLOAT':
                    result = result.astype(numpy.float16)

                elif d3d11_element.Format == 'R8G8B8A8_SNORM':
                    result = MeshFormatConverter.convert_4x_float32_to_r8g8b8a8_snorm(result)

                elif d3d11_element.Format == 'R8G8B8A8_UNORM':
                    result = MeshFormatConverter.convert_4x_float32_to_r8g8b8a8_unorm(result)
                
                # 第五人格格式
                elif d3d11_element.Format == "R32G32B32_FLOAT":
                    result = numpy.empty(mesh_loops_length * 3, dtype=numpy.float32)

                    result[0::3] = tangents[0::3]  # x 分量
                    result[1::3] = tangents[1::3]  # y 分量
                    result[2::3] = tangents[2::3]  # z 分量

                    result = result.reshape(-1, 3)

                # 燕云十六声格式
                elif d3d11_element.Format == 'R16G16B16A16_SNORM':
                    result = MeshFormatConverter.convert_4x_float32_to_r16g16b16a16_snorm(result)
                    

                self.element_vertex_ndarray[d3d11_element_name] = result

            #  YYSLS需要BINORMAL导出，前提是先把这些代码差分简化，因为YYSLS的TANGENT和NORMAL的.w都是固定的1
            elif d3d11_element_name.startswith('BINORMAL'):
                result = numpy.empty(mesh_loops_length * 4, dtype=numpy.float32)

                # 使用 foreach_get 批量获取切线和副切线符号数据
                binormals = numpy.empty(mesh_loops_length * 3, dtype=numpy.float32)
                mesh_loops.foreach_get("bitangent", binormals)
                # 将切线分量放置到输出数组中
                # BINORMAL全部翻转即可得到和YYSLS游戏中一样的效果。
                result[0::4] = binormals[0::3] * -1 # x 分量
                result[1::4] = binormals[1::3] * -1  # y 分量
                result[2::4] = binormals[2::3] * -1 # z 分量
                binormal_w = numpy.ones(mesh_loops_length, dtype=numpy.float32)
                result[3::4] = binormal_w
                result = result.reshape(-1, 4)

                if d3d11_element.Format == 'R16G16B16A16_SNORM':
                    #  燕云十六声格式
                    result = MeshFormatConverter.convert_4x_float32_to_r16g16b16a16_snorm(result)
                    
                self.element_vertex_ndarray[d3d11_element_name] = result
            elif d3d11_element_name.startswith('COLOR'):
                # TimerUtils.Start("Get COLOR")

                if d3d11_element_name in mesh.vertex_colors:
                    # 因为COLOR属性存储在Blender里固定是float32类型所以这里只能用numpy.float32
                    result = numpy.zeros(mesh_loops_length, dtype=(numpy.float32, 4))
                    mesh.vertex_colors[d3d11_element_name].data.foreach_get("color", result.ravel())
                    
                    if d3d11_element.Format == 'R16G16B16A16_FLOAT':
                        result = result.astype(numpy.float16)
                    elif d3d11_element.Format == "R16G16_FLOAT":
                        result = result[:, :2]
                    elif d3d11_element.Format == 'R8G8B8A8_UNORM':
                        result = MeshFormatConverter.convert_4x_float32_to_r8g8b8a8_unorm(result)

                    self.element_vertex_ndarray[d3d11_element_name] = result

                # TimerUtils.End("Get COLOR") # 0:00:00.030605 
            elif d3d11_element_name.startswith('TEXCOORD') and d3d11_element.Format.endswith('FLOAT'):
                # TimerUtils.Start("GET TEXCOORD")
                for uv_name in ('%s.xy' % d3d11_element_name, '%s.zw' % d3d11_element_name):
                    if uv_name in mesh.uv_layers:
                        uvs_array = numpy.empty(mesh_loops_length ,dtype=(numpy.float32,2))
                        mesh.uv_layers[uv_name].data.foreach_get("uv",uvs_array.ravel())
                        uvs_array[:,1] = 1.0 - uvs_array[:,1]

                        if d3d11_element.Format == 'R16G16_FLOAT':
                            uvs_array = uvs_array.astype(numpy.float16)
                        
                        # 重塑 uvs_array 成 (mesh_loops_length, 2) 形状的二维数组
                        # uvs_array = uvs_array.reshape(-1, 2)

                        self.element_vertex_ndarray[d3d11_element_name] = uvs_array 
                # TimerUtils.End("GET TEXCOORD")
            
                        
            elif d3d11_element_name.startswith('BLENDINDICES'):
                blendindices = blendindices_dict.get(d3d11_element.SemanticIndex,None)
                
                # if blendindices is None:
                #     blendindices = blendindices_dict.get(0,None)

                if d3d11_element.Format == "R32G32B32A32_SINT":
                    self.element_vertex_ndarray[d3d11_element_name] = blendindices
                elif d3d11_element.Format == "R16G16B16A16_UINT":
                    self.element_vertex_ndarray[d3d11_element_name] = blendindices
                elif d3d11_element.Format == "R32G32B32A32_UINT":
                    self.element_vertex_ndarray[d3d11_element_name] = blendindices
                elif d3d11_element.Format == "R32G32_UINT":
                    self.element_vertex_ndarray[d3d11_element_name] = blendindices[:, :2]
                elif d3d11_element.Format == "R32_UINT":
                    self.element_vertex_ndarray[d3d11_element_name] = blendindices[:, :1]
                elif d3d11_element.Format == 'R8G8B8A8_SNORM':
                    self.element_vertex_ndarray[d3d11_element_name] = MeshFormatConverter.convert_4x_float32_to_r8g8b8a8_snorm(blendindices)
                elif d3d11_element.Format == 'R8G8B8A8_UNORM':
                    self.element_vertex_ndarray[d3d11_element_name] = MeshFormatConverter.convert_4x_float32_to_r8g8b8a8_unorm(blendindices)
                elif d3d11_element.Format == 'R8G8B8A8_UINT':
                    blendindices.astype(numpy.uint8)
                    self.element_vertex_ndarray[d3d11_element_name] = blendindices
                
            elif d3d11_element_name.startswith('BLENDWEIGHT'):
                blendweights = blendweights_dict.get(d3d11_element.SemanticIndex, None)

                if d3d11_element.Format == "R32G32B32A32_FLOAT":
                    self.element_vertex_ndarray[d3d11_element_name] = blendweights
                elif d3d11_element.Format == "R32G32_FLOAT":
                    self.element_vertex_ndarray[d3d11_element_name] = blendweights[:, :2]
                elif d3d11_element.Format == 'R8G8B8A8_SNORM':
                    # print("BLENDWEIGHT R8G8B8A8_SNORM")
                    self.element_vertex_ndarray[d3d11_element_name] = MeshFormatConverter.convert_4x_float32_to_r8g8b8a8_snorm(blendweights)
                elif d3d11_element.Format == 'R8G8B8A8_UNORM':
                    # print("BLENDWEIGHT R8G8B8A8_UNORM")
                    self.element_vertex_ndarray[d3d11_element_name] = MeshFormatConverter.convert_4x_float32_to_r8g8b8a8_unorm_blendweights(blendweights)

    def calc_index_vertex_buffer_girlsfrontline2(self,obj,mesh:bpy.types.Mesh):
        '''
        计算IndexBuffer和CategoryBufferDict并返回

        这里是速度瓶颈，23万顶点情况下测试，前面的获取mesh数据只用了1.5秒
        但是这里两个步骤加起来用了6秒，占了4/5运行时间。
        不过暂时也够用了，先不管了。
        '''
        # TimerUtils.Start("Calc IB VB")
        # (1) 统计模型的索引和唯一顶点
        '''
        保持相同顶点数时，让相同顶点使用相同的TANGENT值来避免增加索引数和顶点数。
        这里我们使用每个顶点第一次出现的TANGENT值。
        效率比下面的低50%，不过能使用这个选项的场景只有导入直接导出原模型，所以总运行时间基本都在0.4秒以内，用户感觉不到差距的，没问题。
        '''
        # 创建一个空列表用于存储最终的结果
        index_vertex_id_dict = {}
        ib = []
        indexed_vertices = collections.OrderedDict()
        # 一个字典确保每个符合条件的position只出现过一次
        position_normal_sharedtangent_dict = {}
        # 遍历每个多边形（polygon）
        for poly in mesh.polygons:
            # 创建一个临时列表用于存储当前多边形的索引
            vertex_indices = []
            
            # 遍历当前多边形中的每一个环（loop），根据多边形的起始环和环总数
            for blender_lvertex in mesh.loops[poly.loop_start:poly.loop_start + poly.loop_total]:
                vertex_data_get = self.element_vertex_ndarray[blender_lvertex.index].copy()
                poskey = tuple(vertex_data_get['POSITION'] + vertex_data_get['NORMAL'])
                if poskey in position_normal_sharedtangent_dict:
                    tangent_var = position_normal_sharedtangent_dict[poskey]
                    vertex_data_get['TANGENT'] = tangent_var
                else:
                    tangent_var = vertex_data_get['TANGENT']
                    position_normal_sharedtangent_dict[poskey] = tangent_var
                
                vertex_data = vertex_data_get.tobytes()
                index = indexed_vertices.setdefault(vertex_data, len(indexed_vertices))
                vertex_indices.append(index)
                index_vertex_id_dict[index] = blender_lvertex.vertex_index
            
            # 将当前多边形的顶点索引列表添加到最终结果列表中
            ib.append(vertex_indices)

        # print("长度：")
        # print(len(position_normal_sharedtangent_dict))
            
        flattened_ib = [item for sublist in ib for item in sublist]
        # TimerUtils.End("Calc IB VB")

        # (2) 转换为CategoryBufferDict
        # TimerUtils.Start("Calc CategoryBuffer")
        category_stride_dict = self.d3d11GameType.get_real_category_stride_dict()
        category_buffer_dict:dict[str,list] = {}
        for categoryname,category_stride in self.d3d11GameType.CategoryStrideDict.items():
            category_buffer_dict[categoryname] = []

        data_matrix = numpy.array([numpy.frombuffer(byte_data,dtype=numpy.uint8) for byte_data in indexed_vertices])
        stride_offset = 0
        for categoryname,category_stride in category_stride_dict.items():
            category_buffer_dict[categoryname] = data_matrix[:,stride_offset:stride_offset + category_stride].flatten()
            stride_offset += category_stride

        return flattened_ib,category_buffer_dict

    def calc_index_vertex_buffer(self,obj,mesh:bpy.types.Mesh):
        '''
        计算IndexBuffer和CategoryBufferDict并返回

        这里是速度瓶颈，23万顶点情况下测试，前面的获取mesh数据只用了1.5秒
        但是这里两个步骤加起来用了6秒，占了4/5运行时间。
        不过暂时也够用了，先不管了。
        '''
        # TimerUtils.Start("Calc IB VB")
        # (1) 统计模型的索引和唯一顶点
        '''
        不保持相同顶点时，仍然使用经典而又快速的方法
        '''
        indexed_vertices = collections.OrderedDict()
        ib = [[indexed_vertices.setdefault(self.element_vertex_ndarray[blender_lvertex.index].tobytes(), len(indexed_vertices))
                for blender_lvertex in mesh.loops[poly.loop_start:poly.loop_start + poly.loop_total]
                    ]for poly in mesh.polygons] 
            
        flattened_ib = [item for sublist in ib for item in sublist]
        # TimerUtils.End("Calc IB VB")

        # 重计算TANGENT步骤
        indexed_vertices = MeshFormatConverter.average_normal_tangent(obj=obj, indexed_vertices=indexed_vertices, d3d11GameType=self.d3d11GameType,dtype=self.dtype)
        
        # 重计算COLOR步骤
        indexed_vertices = MeshFormatConverter.average_normal_color(obj=obj, indexed_vertices=indexed_vertices, d3d11GameType=self.d3d11GameType,dtype=self.dtype)

        # (2) 转换为CategoryBufferDict
        # TimerUtils.Start("Calc CategoryBuffer")
        category_stride_dict = self.d3d11GameType.get_real_category_stride_dict()
        category_buffer_dict:dict[str,list] = {}
        for categoryname,category_stride in self.d3d11GameType.CategoryStrideDict.items():
            category_buffer_dict[categoryname] = []

        data_matrix = numpy.array([numpy.frombuffer(byte_data,dtype=numpy.uint8) for byte_data in indexed_vertices])
        stride_offset = 0
        for categoryname,category_stride in category_stride_dict.items():
            category_buffer_dict[categoryname] = data_matrix[:,stride_offset:stride_offset + category_stride].flatten()
            stride_offset += category_stride

        return flattened_ib,category_buffer_dict