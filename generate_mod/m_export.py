import bpy

from ..utils.obj_utils import ObjUtils

from ..migoto.migoto_format import D3D11GameType
from ..config.main_config import GlobalConfig
from .mesh_buffer_model import BufferModel


def get_buffer_ib_vb_fast(d3d11GameType:D3D11GameType):
    '''
    使用Numpy直接从当前选中的obj的mesh中转换数据到目标格式Buffer
    '''
    buffer_model = BufferModel(d3d11GameType=d3d11GameType)

    obj = ObjUtils.get_bpy_context_object()
    buffer_model.check_and_verify_attributes(obj)
    print("正在处理: " + obj.name)
    
    # Nico: 通过evaluated_get获取到的是一个新的mesh，用于导出，不影响原始Mesh
    mesh = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()

    # 三角化mesh
    ObjUtils.mesh_triangulate(mesh)

    # Calculates tangents and makes loop normals valid (still with our custom normal data from import time):
    # 前提是有UVMap，前面的步骤应该保证了模型至少有一个TEXCOORD.xy
    mesh.calc_tangents()

    # 读取并解析数据
    buffer_model.parse_elementname_ravel_ndarray_dict(mesh)

    # 因为只有存在TANGENT时，顶点数才会增加，所以如果是GF2并且存在TANGENT才使用共享TANGENT防止增加顶点数
    if "TANGENT" in buffer_model.d3d11GameType.OrderedFullElementList and GlobalConfig.gamename == "GF2":
        ib, category_buffer_dict = buffer_model.calc_index_vertex_buffer_girlsfrontline2(obj, mesh)
        return ib, category_buffer_dict
    
    else:
        # 计算IndexBuffer和CategoryBufferDict
        ib, category_buffer_dict = buffer_model.calc_index_vertex_buffer(obj, mesh)

        return ib, category_buffer_dict




