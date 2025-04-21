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
import textwrap
import collections
import math


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
    

class IndexBuffer(object):
    def __init__(self, *args):
        self.faces = []
        self.first = 0
        self.index_count = 0
        self.format = 'DXGI_FORMAT_UNKNOWN'
        self.gametypename = ""
        self.offset = 0
        self.topology = 'trianglelist'

        # 如果是IOBase类型，说明是以文件名称初始化的，此时fmt要从文件中解析
        if len(args) == 0:
            # 如果不填写参数，则默认为DXGI_FORMAT_R32_UINT类型
            self.format = "DXGI_FORMAT_R32_UINT"
        elif isinstance(args[0], io.IOBase):
            assert (len(args) == 1)
            self.parse_fmt(args[0])
        else:
            self.format, = args

        self.encoder, self.decoder = MigotoUtils.EncoderDecoder(self.format)

    def append(self, face):
        self.faces.append(face)
        self.index_count += len(face)

    def parse_fmt(self, f):
        for line in map(str.strip, f):
            if line.startswith('byte offset:'):
                self.offset = int(line[13:])
            if line.startswith('first index:'):
                self.first = int(line[13:])
            elif line.startswith('index count:'):
                self.index_count = int(line[13:])
            elif line.startswith('topology:'):
                self.topology = line[10:]
                if line != 'topology: trianglelist':
                    raise Fatal('"%s" is not yet supported' % line)
            elif line.startswith('format:'):
                self.format = line[8:]
            elif line.startswith('gametypename:'):
                self.gametypename = line[14:]
            elif line == '':
                    return
        assert (len(self.faces) * 3 == self.index_count)

    def parse_ib_bin(self, f):
        f.seek(self.offset)
        stride = MigotoUtils.format_size(self.format)
        # XXX: Should we respect the first index?
        # f.seek(self.first * stride, whence=1)
        self.first = 0

        face = []
        while True:
            index = f.read(stride)
            if not index:
                break
            face.append(*self.decoder(index))
            if len(face) == 3:
                self.faces.append(tuple(face))
                face = []
        assert (len(face) == 0)

        # We intentionally disregard the index count when loading from a
        # binary file, as we assume frame analysis might have only dumped a
        # partial buffer to the .txt files (e.g. if this was from a dump where
        # the draw call index count was overridden it may be cut short, or
        # where the .txt files contain only sub-meshes from each draw call and
        # we are loading the .buf file because it contains the entire mesh):
        self.index_count = len(self.faces) * 3


    def write(self, output, operator=None):
        for face in self.faces:
            output.write(self.encoder(face))

        msg = 'Wrote %i indices to %s' % (len(self), output.name)
        if operator:
            operator.report({'INFO'}, msg)
        else:
            print(msg)
    
    def __len__(self):
        return len(self.faces) * 3

    
class Element:
    def __init__(self, semantic_name, semantic_index, format_str, input_slot, aligned_byte_offset, input_slot_class, instance_data_step_rate):
        self.SemanticName:str = semantic_name
        self.SemanticIndex:int = semantic_index
        self.Format:str = format_str
        self.InputSlot = input_slot
        self.AlignedByteOffset = aligned_byte_offset
        self.InputSlotClass = input_slot_class
        self.InstanceDataStepRate = instance_data_step_rate

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
            if elemnt.SemanticName == "POSITION":
                if elemnt.Format == "R32G32B32_FLOAT":
                    fields.append((elemnt.ElementName, numpy.float32, 3))
                else:
                    raise Fatal("Unknown POSITION format: " + elemnt.Format)
            elif elemnt.SemanticName == "NORMAL":
                if elemnt.Format == "R32G32B32_FLOAT":
                    fields.append((elemnt.ElementName, numpy.float32, 3))
                elif elemnt.Format == "R8G8B8A8_SNORM":
                    fields.append((elemnt.ElementName, numpy.int8, 4))
                else:
                    raise Fatal("Unknown NORMAL format: " + elemnt.Format)
            elif elemnt.SemanticName == "TANGENT":
                if elemnt.Format == "R32G32B32A32_FLOAT":
                    fields.append((elemnt.ElementName, numpy.float32, 4))
                elif elemnt.Format == "R8G8B8A8_SNORM":
                    fields.append((elemnt.ElementName, numpy.int8, 4))
                else:
                    raise Fatal("Unknown TANGENT format: " + elemnt.Format)
            elif elemnt.SemanticName == "TEXCOORD":
                if elemnt.Format == "R32G32_FLOAT":
                    fields.append((elemnt.ElementName, numpy.float32, 2))
                elif elemnt.Format == "R16G16_FLOAT":
                    fields.append((elemnt.ElementName, numpy.float16, 2))
                else:
                    raise Fatal("Unknown TEXCOORD format: " + elemnt.Format)
            elif elemnt.SemanticName == "COLOR":
                if elemnt.Format == "R8G8B8A8_UNORM":
                    fields.append((elemnt.ElementName, numpy.uint8, 4))
                elif elemnt.Format == "R32G32_FLOAT":
                    fields.append((elemnt.ElementName, numpy.float32, 2))
                else:
                    raise Fatal("Unknown COLOR format: " + elemnt.Format)
            elif elemnt.SemanticName == "BLENDINDICES":
                if elemnt.Format == "R8G8B8A8_UINT":
                    fields.append((elemnt.ElementName, numpy.uint8, 4))
                elif elemnt.Format == "R32G32B32A32_UINT":
                    fields.append((elemnt.ElementName, numpy.uint32, 4))
                elif elemnt.Format == "R16G16B16A16_UINT":
                    fields.append((elemnt.ElementName, numpy.uint16, 4))
                elif elemnt.Format == "R32G32_UINT":
                    fields.append((elemnt.ElementName, numpy.uint32, 2))
                elif elemnt.Format == "R32_UINT":
                    fields.append((elemnt.ElementName, numpy.uint32, 1))
                else:
                    raise Fatal("Unknown BLENDINDICES format: " + elemnt.Format)
            elif elemnt.SemanticName.startswith("BLENDWEIGHT"):
                if elemnt.Format == "R8G8B8A8_UNORM":
                    fields.append((elemnt.ElementName, numpy.uint8, 4))
                elif elemnt.Format == "R32G32B32A32_FLOAT":
                    fields.append((elemnt.ElementName, numpy.float32, 4))
                elif elemnt.Format == "R16G16B16A16_FLOAT":
                    fields.append((elemnt.ElementName, numpy.float16, 4))
                elif elemnt.Format == "R32G32_FLOAT":
                    fields.append((elemnt.ElementName, numpy.float32, 2))
                elif elemnt.Format == "R32_FLOAT":
                    fields.append((elemnt.ElementName, numpy.float32, 1))
                else:
                    raise Fatal("Unknown BLENDWEIGHT format: " + elemnt.Format)
            elif elemnt.SemanticName.startswith("SHAPEKEY"):
                if elemnt.Format == "R16G16B16_FLOAT":
                    fields.append((elemnt.ElementName, numpy.float16, 3))
                else:
                    raise Fatal("Unknown SHAPEKEY format: " + elemnt.Format)
                
        # 这里的dtype是numpy的dtype,使用numpy的复杂数据类型实现快速导入
        dtype = numpy.dtype(fields)

        return dtype
