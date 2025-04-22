import json
import io

from ..utils.migoto_utils import *

from ..utils.migoto_utils import *
from ..config.main_config import *
from ..utils.timer_utils import *

from typing import List, Dict, Union
from pathlib import Path
from dataclasses import dataclass, field, asdict
from ..utils.migoto_utils import *

import io


@dataclass
class ExtractedObjectComponent:
    vertex_offset: int
    vertex_count: int
    index_offset: int
    index_count: int
    vg_offset: int
    vg_count: int
    vg_map: Dict[int, int]


@dataclass
class ExtractedObjectShapeKeys:
    offsets_hash: str = ''
    scale_hash: str = ''
    vertex_count: int = 0
    dispatch_y: int = 0
    checksum: int = 0


@dataclass
class ExtractedObject:
    vb0_hash: str
    cb4_hash: str
    vertex_count: int
    index_count: int
    components: List[ExtractedObjectComponent]
    shapekeys: ExtractedObjectShapeKeys

    def __post_init__(self):
        if isinstance(self.shapekeys, dict):
            self.components = [ExtractedObjectComponent(**component) for component in self.components]
            self.shapekeys = ExtractedObjectShapeKeys(**self.shapekeys)

    def as_json(self):
        return json.dumps(asdict(self), indent=4)

class ExtractedObjectHelper:
    '''
    不用类包起来难受，还是做成工具类好一点。。
    '''
    @classmethod
    def read_metadata(cls,metadata_path: str) -> ExtractedObject:
        with open(metadata_path) as f:
            return ExtractedObject(**json.load(f))
    
    
class Element:
    def __init__(self, semantic_name, semantic_index, format_str, input_slot, aligned_byte_offset, input_slot_class, instance_data_step_rate):
        self.SemanticName:str = semantic_name
        self.SemanticIndex:int = semantic_index
        self.Format:str = format_str
        self.InputSlot:int = input_slot
        self.AlignedByteOffset:int = aligned_byte_offset
        self.InputSlotClass:str = input_slot_class
        self.InstanceDataStepRate:int = instance_data_step_rate

        self.ElementName = ""
        if self.SemanticIndex == 0:
            self.ElementName = self.SemanticName
        else:
            self.ElementName = self.SemanticName + str(self.SemanticIndex)

    def __repr__(self):
        return (f"Element(SemanticName='{self.SemanticName}', SemanticIndex={self.SemanticIndex}, "
                f"Format='{self.Format}', InputSlot={self.InputSlot}, AlignedByteOffset={self.AlignedByteOffset}, "
                f"InputSlotClass='{self.InputSlotClass}', InstanceDataStepRate={self.InstanceDataStepRate})")


class FMTFile:
    def __init__(self, filename):
        self.stride = 0
        self.topology = ""
        self.format = ""
        self.gametypename = ""
        self.prefix = ""
        self.elements:list[Element] = []

        with open(filename, 'r') as file:
            lines = file.readlines()

        element_info = {}
        for line in lines:
            parts = line.strip().split(":")
            if len(parts) < 2:
                continue  # 跳过格式不正确的行

            key, value = parts[0].strip(), ":".join(parts[1:]).strip()
            if key == "stride":
                self.stride = int(value)
            elif key == "topology":
                self.topology = value
            elif key == "format":
                self.format = value
            elif key == "gametypename":
                self.gametypename = value
            elif key == "prefix":
                self.prefix = value
            elif key.startswith("element"):
                # 处理element块
                if "SemanticName" in element_info:
                    # 如果已经有一个element信息，则先添加到列表中
                    self.elements.append(Element(
                        element_info["SemanticName"], int(element_info["SemanticIndex"]), element_info["Format"],
                        int(element_info["InputSlot"]), int(element_info["AlignedByteOffset"]),
                        element_info["InputSlotClass"], int(element_info["InstanceDataStepRate"])
                    ))
                    element_info.clear()  # 清空当前element信息

                # 将新的element属性添加到element_info字典中
                element_info[key.split()[0]] = value
            elif key in ["SemanticName", "SemanticIndex", "Format", "InputSlot", "AlignedByteOffset", "InputSlotClass", "InstanceDataStepRate"]:
                element_info[key] = value

        # 添加最后一个element
        if "SemanticName" in element_info:
            self.elements.append(Element(
                element_info["SemanticName"], int(element_info["SemanticIndex"]), element_info["Format"],
                int(element_info["InputSlot"]), int(element_info["AlignedByteOffset"]),
                element_info["InputSlotClass"], int(element_info["InstanceDataStepRate"])
            ))

    def __repr__(self):
        return (f"FMTFile(stride={self.stride}, topology='{self.topology}', format='{self.format}', "
                f"gametypename='{self.gametypename}', prefix='{self.prefix}', elements={self.elements})")
    
    def get_dtype(self):
        fields = []
        for elemnt in self.elements:
            fields.append((elemnt.ElementName, MigotoUtils.get_nptype_from_format(elemnt.Format), MigotoUtils.format_components(elemnt.Format)))
        dtype = numpy.dtype(fields)
        return dtype
