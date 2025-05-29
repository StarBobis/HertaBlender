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
                draw_indexed_obj.AliasName = comp_obj.name
                self.obj_name_drawindexed_dict[comp_obj.name] = draw_indexed_obj

        # (98) 选中当前融合的obj对象，计算得到ib和category_buffer，以及每个IndexId对应的VertexId
        obj = self.merged_object.object
        bpy.context.view_layer.objects.active = obj
        
        ib, category_buffer_dict = get_buffer_ib_vb_fast(self.d3d11GameType)
        

        # (9) 构建每个Category的VertexBuffer，每个Category都生成一个CategoryBuffer文件。
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

        # (10) 顺便计算一下步长得到总顶点数
        position_stride = self.d3d11GameType.CategoryStrideDict["Position"]
        position_bytelength = len(self.__categoryname_bytelist_dict["Position"])
        self.draw_number = int(position_bytelength/position_stride)

        # (11) 拼接ShapeKey数据
        if obj.data.shape_keys is None or len(getattr(obj.data.shape_keys, 'key_blocks', [])) == 0:
            print(f'No shapekeys found to process!')
            return {}

        shapekey_offsets, shapekey_vertex_ids, shapekey_vertex_offsets = [], [], []
        shapekey_pattern = re.compile(r'.*(?:deform|custom)[_ -]*(\d+).*')
        shapekey_ids = {}
        
        for shapekey in obj.data.shape_keys.key_blocks:
            match = shapekey_pattern.findall(shapekey.name.lower())
            if len(match) == 0:
                continue
            shapekey_id = int(match[0])
            shapekey_ids[shapekey_id] = shapekey.name

        shapekeys = ShapeKeyUtils.get_shapekey_data(obj, names_filter=list(shapekey_ids.values()), deduct_basis=True)

        shapekey_verts_count = 0

        vertex_ids = numpy.arange(len(obj.data.vertices))
        for group_id in range(128):

            shapekey = shapekeys.get(shapekey_ids.get(group_id, -1), None)

            # print(shapekey)
            if shapekey is None or not (-0.00000001 > numpy.min(shapekey) or numpy.max(shapekey) > 0.00000001):
                shapekey_offsets.extend([shapekey_verts_count if shapekey_verts_count != 0 else 0])
                continue

            shapekey_offsets.extend([shapekey_verts_count])

            shapekey = shapekey[vertex_ids]

            shapekey_vert_ids = numpy.where(numpy.any(shapekey != 0, axis=1))[0]

            shapekey_vertex_ids.extend(shapekey_vert_ids)
            shapekey_vertex_offsets.extend(shapekey[shapekey_vert_ids])
            shapekey_verts_count += len(shapekey_vert_ids)
            
        if len(shapekey_vertex_ids) == 0:
            return {}

        shapekey_offsets = numpy.array(shapekey_offsets)
        
        shapekey_vertex_offsets_np = numpy.zeros(len(shapekey_vertex_offsets), dtype=(numpy.float16, 6))
        # shapekey_vertex_offsets = numpy.zeros(len(shapekey_vertex_offsets), dtype=numpy.float16)
        shapekey_vertex_offsets_np[:, 0:3] = shapekey_vertex_offsets

        shapekey_vertex_ids = numpy.array(shapekey_vertex_ids, dtype=numpy.uint32)

        self.shapekey_offsets = shapekey_offsets
        self.shapekey_vertex_ids = shapekey_vertex_ids
        self.shapekey_vertex_offsets = shapekey_vertex_offsets_np

        bpy.data.objects.remove(obj, do_unlink=True)

        # (12) 导出Buffer文件，Export Index Buffer files, Category Buffer files. (And Export ShapeKey Buffer Files.(WWMI))
        # 用于写出IB时使用
        # 拼接每个PartName对应的IB文件的Resource和filename,这样生成ini的时候以及导出Mod的时候就可以直接使用了。
        style_part_name = "Component1"
        ib_resource_name = "Resource_" + self.draw_ib + "_" + style_part_name
        ib_buf_filename = self.draw_ib + "-" + style_part_name + ".buf"

        # 导出当前Mod的所有Buffer文件
        buf_output_folder = GlobalConfig.path_generatemod_buffer_folder(draw_ib=self.draw_ib)
        packed_data = struct.pack(f'<{len(ib)}I', *ib)
        with open(buf_output_folder + ib_buf_filename, 'wb') as ibf:
            ibf.write(packed_data) 
            
        for category_name, category_buf in self.__categoryname_bytelist_dict.items():
            buf_path = buf_output_folder + self.draw_ib + "-" + category_name + ".buf"
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
            with open(buf_output_folder + self.draw_ib + "-" + "ShapeKeyVertexOffset.buf", 'wb') as file:
                float_array.tofile(file)

