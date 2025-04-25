import numpy
import struct
import re
from time import time
from ..properties.properties_wwmi import Properties_WWMI
from .m_export import get_buffer_ib_vb_fast

from ..migoto.migoto_format import *

from ..utils.collection_utils import *
from ..utils.shapekey_utils import ShapeKeyUtils
from ..utils.json_utils import *
from ..utils.timer_utils import *
from ..utils.migoto_utils import Fatal
from ..utils.obj_utils import ObjUtils

from ..config.main_config import GlobalConfig
from ..config.import_config import ImportConfig

from ..utils.obj_utils import ExtractedObject, ExtractedObjectHelper

import re
import bpy

from typing import List, Dict, Union
from dataclasses import dataclass, field
from enum import Enum
from dataclasses import dataclass

import bpy
import bmesh


class DrawIBModelWWMI:
    '''
    注意，单个IB的WWMI架构必定存在135W顶点索引的数量上限
    '''
    def __init__(self,draw_ib_collection,merge_objects:bool):
        '''
        根据3Dmigoto的架构设计，每个DrawIB都是一个独立的Mod
        '''
        # (1) 从集合名称中获取当前DrawIB和别名
        drawib_collection_name_splits = CollectionUtils.get_clean_collection_name(draw_ib_collection.name).split("_")
        self.draw_ib = drawib_collection_name_splits[0]
        self.draw_ib_alias = drawib_collection_name_splits[1]

        # (2) 读取工作空间中配置文件的配置项
        self.import_config = ImportConfig(draw_ib=self.draw_ib)
        self.d3d11GameType:D3D11GameType = self.import_config.d3d11GameType
        self.PartName_SlotTextureReplaceDict_Dict = self.import_config.PartName_SlotTextureReplaceDict_Dict
        self.TextureResource_Name_FileName_Dict = self.import_config.TextureResource_Name_FileName_Dict

        # (3) 读取WWMI专属配置
        self.extracted_object:ExtractedObject = ExtractedObjectHelper.read_metadata(GlobalConfig.path_extract_gametype_folder(draw_ib=self.draw_ib,gametype_name=self.d3d11GameType.GameTypeName)  + "Metadata.json")

        # (4) 解析集合架构，获得每个DrawIB中，每个Component对应的obj列表及其相关属性
        self.componentname_modelcollection_list_dict:dict[str,list[ModelCollection]] = CollectionUtils.parse_drawib_collection_architecture(draw_ib_collection=draw_ib_collection)

        # (5) 解析当前有多少个key
        self.key_number = CollectionUtils.parse_key_number(draw_ib_collection=draw_ib_collection)

        # (6) 对所有obj进行融合，得到一个最终的用于导出的临时obj
        self.merged_object = ObjUtils.build_merged_object(
            extracted_object=self.extracted_object,
            draw_ib_collection=draw_ib_collection
        )

        # (7) 填充每个obj的drawindexed值，给每个obj的属性统计好，后面就能直接用了。
        self.obj_name_drawindexed_dict:dict[str,M_DrawIndexed] = {} 
        for comp in self.merged_object.components:
            for comp_obj in comp.objects:
                draw_indexed_obj = M_DrawIndexed()
                draw_indexed_obj.DrawNumber = str(comp_obj.index_count)
                draw_indexed_obj.DrawOffsetIndex = str(comp_obj.index_offset)
                self.obj_name_drawindexed_dict[comp_obj.name] = draw_indexed_obj

        # (8) 归一化权重 (可选项)
        # 我们在导出具体数据之前，先对模型整体的权重进行normalize_all预处理，才能让后续的具体每一个权重的normalize_all更好的工作
        # 使用这个的前提是当前obj中没有锁定的顶点组，所以这里要先进行判断。
        # TODO 这里要确定一下WWMI-Tools是否需要NormalizeAll
        # if "Blend" in self.d3d11GameType.OrderedCategoryNameList:
        #     all_vgs_locked = ObjUtils.is_all_vertex_groups_locked(obj)
        #     if not all_vgs_locked:
        #         ObjUtils.normalize_all(obj)

        # (9) 选中当前融合的obj对象，计算得到ib和category_buffer，以及每个IndexId对应的VertexId
        obj = self.merged_object.object
        bpy.context.view_layer.objects.active = obj
        ib, category_buffer_dict, index_vertex_id_dict = get_buffer_ib_vb_fast(self.d3d11GameType)

        # (10) 构建每个Category的VertexBuffer，每个Category都生成一个CategoryBuffer文件。
        self.__categoryname_bytelist_dict = {} 
        for category_name in self.d3d11GameType.OrderedCategoryNameList:
            if category_name not in self.__categoryname_bytelist_dict:
                self.__categoryname_bytelist_dict[category_name] =  category_buffer_dict[category_name]
            else:
                existing_array = self.__categoryname_bytelist_dict[category_name]
                buffer_array = category_buffer_dict[category_name]

                # 确保两个数组都是NumPy数组
                existing_array = numpy.asarray(existing_array)
                buffer_array = numpy.asarray(buffer_array)

                # 使用 concatenate 连接两个数组，确保传递的是一个序列（如列表或元组）
                concatenated_array = numpy.concatenate((existing_array, buffer_array))

                # 更新字典中的值
                self.__categoryname_bytelist_dict[category_name] = concatenated_array

        # 顺便计算一下步长得到总顶点数
        position_stride = self.d3d11GameType.CategoryStrideDict["Position"]
        position_bytelength = len(self.__categoryname_bytelist_dict["Position"])
        self.draw_number = int(position_bytelength/position_stride)
        print(self.draw_number)
        print(self.merged_object.vertex_count)

        # 形态键数据
        self.shapekey_offsets = []
        self.shapekey_vertex_ids = []
        self.shapekey_vertex_offsets = []

        # 从模型中读取形态键部分，生成形态键数据所需的Buffer
        shapekey_index_list = []
        shapekey_data = {}

        mesh = obj.data
        mesh_shapekeys = mesh.shape_keys
        base_data = mesh_shapekeys.key_blocks['Basis'].data
        for shapekey in mesh_shapekeys.key_blocks:
            # 截取形态键名称中的形态键shapekey_id，获取不到就跳过
            shapekey_pattern = re.compile(r'.*(?:deform|custom)[_ -]*(\d+).*')
            match = shapekey_pattern.findall(shapekey.name.lower())
            if len(match) == 0:
                # print("当前形态键名称:" +shapekey.name + " 不是以Deform开头的，进行跳过")
                continue

            shapekey_index = int(match[0])

            # 因为WWMI的形态键数量只有128个，这里shapekey_id是从0开始的，所以到127结束，所以不能大于等于128
            if shapekey_index >= 128:
                break

            if shapekey_index not in shapekey_index_list:
                # print("添加形态键Index: " + str(shapekey_index))
                shapekey_index_list.append(shapekey_index)

            # 对于这个obj的每个顶点，我们都要尝试从当前shapekey中获取数据，如果获取到了，就放入缓存
            for vertex_index in range(len(mesh.vertices)):
                base_vertex_coords = base_data[vertex_index].co
                shapekey_vertex_coords = shapekey.data[vertex_index].co
                vertex_offset = shapekey_vertex_coords - base_vertex_coords
                # 到这里已经有vertex_id、shapekey_id、vertex_offset了，就不用像WWMI一样再从缓存读取了

                if vertex_index not in shapekey_data:
                    shapekey_data[vertex_index] = {}

                # 如果相差太小，说明无效或者是一样的，说明这个顶点没有ShapeKey，此时向ShapeKeyOffsets中添加空的0
                if vertex_offset.length < 0.000000001:
                    # print("相差太小，跳过处理。")
                    continue
                
                # 此时如果能获取到，说明有效，此时可以直接放入准备好的字典
                shapekey_data[vertex_index][shapekey_index] = list(vertex_offset)

        # shapekey_index_list.sort()

        # 转换格式问题
        shapekey_cache = {shapekey_id:{} for shapekey_id in shapekey_index_list}

        # 对于每一个obj的每个顶点，都从0到128获取它的形态键对应偏移值
        # 获取当前obj每个Index对应的VertexId
        mesh = obj.data
        for index_id, vertex_id in index_vertex_id_dict.items():
            # 这样VertexId加上全局偏移，就能获取到对应位置的形态键数据：
            vertex_shapekey_data = shapekey_data.get(vertex_id , None)
            if vertex_shapekey_data is not None:
                for shapekey_index,vertex_offsets in vertex_shapekey_data.items():
                    shapekey_cache[shapekey_index][index_id] = vertex_offsets

    
        LOG.newline()
        shapekey_verts_count = 0
        # 从0到128去获取ShapeKey的Index，有就直接加到
        for group_id in range(128):
            shapekey = shapekey_cache.get(group_id, None)
            if shapekey is None or len(shapekey_cache[group_id]) == 0:
                self.shapekey_offsets.extend([shapekey_verts_count if shapekey_verts_count != 0 else 0])
                continue

            self.shapekey_offsets.extend([shapekey_verts_count])

            for draw_index, vertex_offsets in shapekey.items():
                self.shapekey_vertex_ids.extend([draw_index])
                self.shapekey_vertex_offsets.extend(vertex_offsets + [0, 0, 0])
                shapekey_verts_count += 1


        # (5) 导出Buffer文件，Export Index Buffer files, Category Buffer files. (And Export ShapeKey Buffer Files.(WWMI))
        # 用于写出IB时使用
        # 拼接每个PartName对应的IB文件的Resource和filename,这样生成ini的时候以及导出Mod的时候就可以直接使用了。
        self.PartName_IBResourceName_Dict = {}
        style_part_name = "Component1"
        ib_resource_name = "Resource_" + self.draw_ib + "_" + style_part_name
        ib_buf_filename = self.draw_ib + "-" + style_part_name + ".buf"
        self.PartName_IBResourceName_Dict["1"] = ib_resource_name

        # 导出当前Mod的所有Buffer文件
        buf_output_folder = GlobalConfig.path_generatemod_buffer_folder(draw_ib=self.draw_ib)
        # print("Write Buffer Files::")
        # Export Index Buffer files.
        packed_data = struct.pack(f'<{len(ib)}I', *ib)
        with open(buf_output_folder + ib_buf_filename, 'wb') as ibf:
            ibf.write(packed_data) 
            
        # print("Export Category Buffers::")
        # Export category buffer files.
        for category_name, category_buf in self.__categoryname_bytelist_dict.items():
            buf_path = buf_output_folder + self.draw_ib + "-" + category_name + ".buf"
            # print("write: " + buf_path)
            # print(type(category_buf[0]))
             # 将 list 转换为 numpy 数组
            # category_array = numpy.array(category_buf, dtype=numpy.uint8)
            with open(buf_path, 'wb') as ibf:
                category_buf.tofile(ibf)

        # 鸣潮的ShapeKey三个Buffer的导出
        if len(self.shapekey_offsets) != 0:
            with open(buf_output_folder + self.draw_ib + "-" + "ShapeKeyOffset.buf", 'wb') as file:
                for number in self.shapekey_offsets:
                    # 假设数字是32位整数，使用'i'格式符
                    # 根据实际需要调整数字格式和相应的格式符
                    data = struct.pack('i', number)
                    file.write(data)
        
        if len(self.shapekey_vertex_ids) != 0:
            with open(buf_output_folder + self.draw_ib + "-" + "ShapeKeyVertexId.buf", 'wb') as file:
                for number in self.shapekey_vertex_ids:
                    # 假设数字是32位整数，使用'i'格式符
                    # 根据实际需要调整数字格式和相应的格式符
                    data = struct.pack('i', number)
                    file.write(data)
        
        if len(self.shapekey_vertex_offsets) != 0:
            # 将列表转换为numpy数组，并改变其数据类型为float16
            float_array = numpy.array(self.shapekey_vertex_offsets, dtype=numpy.float32).astype(numpy.float16)
            
            # 以二进制模式写入文件
            with open(buf_output_folder + self.draw_ib + "-" + "ShapeKeyVertexOffset.buf", 'wb') as file:
                float_array.tofile(file)

