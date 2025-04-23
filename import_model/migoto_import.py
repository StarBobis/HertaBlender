from .import_utils import *
from ..migoto.migoto_format import *
from ..utils.collection_utils import *
from ..config.main_config import *

from ..utils.obj_utils import ObjUtils
from ..utils.json_utils import JsonUtils

from array import array

import os.path
import itertools
import bpy
import json
import math
from mathutils import Vector

from bpy_extras.io_utils import unpack_list, ImportHelper, axis_conversion
from bpy.props import BoolProperty, StringProperty, CollectionProperty
from bpy_extras.io_utils import orientation_helper


def import_shapekeys(mesh, obj, shapekeys):
    if not shapekeys:
        return
    
    # ========== 基础形状键预处理 ==========
    basis = obj.shape_key_add(name='Basis')
    basis.interpolation = 'KEY_LINEAR'
    obj.data.shape_keys.use_relative = True

    # 批量获取基础顶点坐标（约快200倍）
    vert_count = len(obj.data.vertices)
    basis_co = numpy.empty(vert_count * 3, dtype=numpy.float32)
    basis.data.foreach_get('co', basis_co)
    basis_co = basis_co.reshape(-1, 3)  # 转换为(N,3)形状

    # ========== 批量处理所有形状键 ==========
    for sk_id, offsets in shapekeys.items():
        # 添加新形状键
        new_sk = obj.shape_key_add(name=f'Deform {sk_id}')
        new_sk.interpolation = 'KEY_LINEAR'

        # 转换为NumPy数组（假设offsets是列表的列表）
        offset_arr = numpy.array(offsets, dtype=numpy.float32).reshape(-1, 3)

        # 向量化计算新坐标（比循环快100倍）
        new_co = basis_co + offset_arr

        # 批量写入形状键数据（约快300倍）
        new_sk.data.foreach_set('co', new_co.ravel())

        # 强制解除Blender数据块的引用（重要！避免内存泄漏）
        del new_sk

    # 清理临时数组
    del basis_co, offset_arr, new_co


def import_vertex_groups(mesh, obj, blend_indices, blend_weights,component):
    assert (len(blend_indices) == len(blend_weights))
    if blend_indices:
        # We will need to make sure we re-export the same blend indices later -
        # that they haven't been renumbered. Not positive whether it is better
        # to use the vertex group index, vertex group name or attach some extra
        # data. Make sure the indices and names match:
        if component is None:
            num_vertex_groups = max(itertools.chain(*itertools.chain(*blend_indices.values()))) + 1
        else:
            num_vertex_groups = max(component.vg_map.values()) + 1
        
        for i in range(num_vertex_groups):
            obj.vertex_groups.new(name=str(i))
        for vertex in mesh.vertices:
            for semantic_index in sorted(blend_indices.keys()):
                for i, w in zip(blend_indices[semantic_index][vertex.index],
                                blend_weights[semantic_index][vertex.index]):
                    if w == 0.0:
                        continue
                    if component is None:
                        obj.vertex_groups[i].add((vertex.index,), w, 'REPLACE')
                    else:
                        # 这里由于C++生成的json文件是无序的，所以我们这里读取的时候要用原始的map而不是转换成列表的索引，避免无序问题
                        obj.vertex_groups[component.vg_map[str(i)]].add((vertex.index,), w, 'REPLACE')


def import_uv_layers(mesh, obj, texcoords):
    for (texcoord, data) in sorted(texcoords.items()):
        dim = len(data[0])
        if dim == 4:
            components_list = ('xy', 'zw')
        elif dim == 2:
            components_list = ('xy',)
        else:
            raise Fatal('Unhandled TEXCOORD dimension: %i' % dim)
        cmap = {'x': 0, 'y': 1, 'z': 2, 'w': 3}

        for components in components_list:
            uv_name = 'TEXCOORD%s.%s' % (texcoord if texcoord else '', components)
            mesh.uv_layers.new(name=uv_name)
            blender_uvs = mesh.uv_layers[uv_name]

            # 预计算每个顶点的翻转后的UV坐标
            c0 = cmap[components[0]]
            c1 = cmap[components[1]]
            uvs_vertex = [(d[c0], 1.0 - d[c1]) for d in data]

            # 获取所有循环的顶点索引
            loops = mesh.loops
            vertex_indices = [l.vertex_index for l in loops]

            # 生成扁平的UV数组
            uv_array = [0.0] * (2 * len(loops))
            for i, vi in enumerate(vertex_indices):
                u, v = uvs_vertex[vi]
                uv_array[2 * i] = u
                uv_array[2 * i + 1] = v

            # 批量设置UV数据
            blender_uvs.data.foreach_set('uv', uv_array)


def find_texture(texture_prefix, texture_suffix, directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(texture_suffix) and file.startswith(texture_prefix):
                texture_path = os.path.join(root, file)
                return texture_path
    return None


def create_material_with_texture(obj, mesh_name:str, directory:str):
    # Credit to Rayvy
    # Изменим имя текстуры, чтобы оно точно совпадало с шаблоном (Change the texture name to match the template exactly)
    material_name = f"{mesh_name}_Material"
    # texture_name = f"{mesh_name}-DiffuseMap.jpg"

    if "." in mesh_name:
        mesh_name_split = str(mesh_name).split(".")[0].split("-")
    else:
        mesh_name_split = str(mesh_name).split("-")
    
    if len(mesh_name_split) < 2:
        return
    
    texture_prefix = mesh_name_split[0] + "_" + mesh_name_split[1] # IB Hash
    
    texture_suffix = "-DiffuseMap.tga"

    # 查找是否存在满足条件的转换好的tga贴图文件
    texture_path = None

    # 查找是否存在满足条件的转换好的tga贴图文件
    texture_path = find_texture(texture_prefix, texture_suffix, directory)
    # 如果不存在，试试查找jpg文件
    if texture_path is None:
        texture_suffix = "_DiffuseMap.jpg"
        # 查找jpg文件，如果这里没找到的话后面也是正常的，但是这里如果找到了就能起到兼容旧版本jpg文件的作用
        texture_path = find_texture(texture_prefix, texture_suffix, directory)

    # 如果还不存在，试试查找png文件
    if texture_path is None:
        texture_suffix = "_DiffuseMap.png"
        # 查找jpg文件，如果这里没找到的话后面也是正常的，但是这里如果找到了就能起到兼容旧版本jpg文件的作用
        texture_path = find_texture(texture_prefix, texture_suffix, directory)


    # Nico: 这里如果没有检测到对应贴图则不创建材质，也不新建BSDF
    # 否则会造成合并模型后，UV编辑界面选择不同材质的UV会跳到不同UV贴图界面导致无法正常编辑的问题
    if texture_path is not None:
        # Создание нового материала (Create new materials)
        material = bpy.data.materials.new(name=material_name)
        material.use_nodes = True

        # Nico: Currently only support EN and ZH-CN
        # 4.2 简体中文是 "原理化 BSDF" 英文是 "Principled BSDF"
        bsdf = material.node_tree.nodes.get("原理化 BSDF")
        if not bsdf: 
            # 3.6 简体中文是原理化BSDF 没空格
            bsdf = material.node_tree.nodes.get("原理化BSDF")
        if not bsdf:
            bsdf = material.node_tree.nodes.get("Principled BSDF")

        if bsdf:
            # Поиск текстуры (Search for textures)

            if texture_path:
                tex_image = material.node_tree.nodes.new('ShaderNodeTexImage')
                tex_image.image = bpy.data.images.load(texture_path)

                # 因为tga格式贴图有alpha通道，所以必须用CHANNEL_PACKED才能显示正常颜色
                tex_image.image.alpha_mode = "CHANNEL_PACKED"

                material.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])

            # Применение материала к мешу (Materials applied to bags)
            if obj.data.materials:
                obj.data.materials[0] = material
            else:
                obj.data.materials.append(material)


def import_3dmigoto_raw_buffers(operator, context, fmt_path:str, vb_path:str, ib_path:str):
    operator.report({'INFO'}, "Import From " + fmt_path)

    # 如果vb和ib文件不存在，则跳过导入
    vb_file_size = os.path.getsize(vb_path)
    if vb_file_size == 0 or os.path.getsize(ib_path) == 0:
        return obj
    
    # 获取导入模型的前缀，去掉.fmt就是了，因为我们导入是选择.fmt文件导入
    mesh_name = os.path.basename(fmt_path)
    if mesh_name.endswith(".fmt"):
        mesh_name = mesh_name[0:len(mesh_name) - 4]
    print("导入模型: " + mesh_name)

    # 创建mesh和obj
    mesh = bpy.data.meshes.new(mesh_name)
    obj = bpy.data.objects.new(mesh.name, mesh)
    # 虽然每个游戏导入时的坐标不一致，导致模型朝向都不同，但是不在这里修改，而是在后面根据具体的游戏进行扶正
    obj.matrix_world = axis_conversion(from_forward='-Z', from_up='Y').to_4x4()
    # Nico: 设置默认不重计算TANGNET和COLOR
    obj["3DMigoto:RecalculateTANGENT"] = False
    obj["3DMigoto:RecalculateCOLOR"] = False


    # 读取fmt文件，解析出后面要用的dtype
    fmt_file = FMTFile(fmt_path)
    fmt_dtype = fmt_file.get_dtype()
    # 设置GameTypeName，方便在Catter的Properties面板中查看
    obj['3DMigoto:GameTypeName'] = fmt_file.gametypename


    # 导入IB文件设置为mesh的三角形索引
    ib_stride = MigotoUtils.format_size(fmt_file.format)
    ib_count = int(os.path.getsize(ib_path) / ib_stride)
    ib_polygon_count = int(ib_count / 3)
    ib_data = numpy.fromfile(ib_path, dtype=MigotoUtils.get_nptype_from_format(fmt_file.format), count=ib_count)
    mesh.loops.add(ib_count)
    mesh.polygons.add(ib_polygon_count)
    mesh.loops.foreach_set('vertex_index', ib_data)
    mesh.polygons.foreach_set('loop_start', [x * 3 for x in range(ib_polygon_count)])
    mesh.polygons.foreach_set('loop_total', [3] * ib_polygon_count)


    # 导入vb文件中的数据
    vb_stride = fmt_dtype.itemsize
    vb_vertex_count = int(vb_file_size / vb_stride)
    vb_data = numpy.fromfile(vb_path, dtype=fmt_dtype, count=vb_vertex_count)
    mesh.vertices.add(vb_vertex_count)

    blend_indices = {}
    blend_weights = {}
    texcoords = {}
    shapekeys = {}
    use_normals = False
    normals = []

    for element in fmt_file.elements:
        data = vb_data[element.ElementName]
        if element.SemanticName == "POSITION":
            if len(data[0]) == 4:
                if ([x[3] for x in data] != [1.0] * len(data)):
                    # Nico: Blender暂时不支持4D索引，加了也没用，直接不行就报错，转人工处理。
                    raise Fatal('Positions are 4D')
            positions = [(x[0], x[1], x[2]) for x in data]
            mesh.vertices.foreach_set('co', unpack_list(positions))
        elif element.SemanticName.startswith("COLOR"):
            mesh.vertex_colors.new(name=element.ElementName)
            color_layer = mesh.vertex_colors[element.ElementName].data
            for l in mesh.loops:
                color_layer[l.index].color = list(data[l.vertex_index]) + [0] * (4 - len(data[l.vertex_index]))
        elif element.SemanticName.startswith("BLENDINDICES"):
            blend_indices[element.SemanticIndex] = data
        elif element.SemanticName.startswith("BLENDWEIGHT"):
            blend_weights[element.SemanticIndex] = data
        elif element.SemanticName.startswith("TEXCOORD"):
            texcoords[element.SemanticIndex] = data
        elif element.SemanticName.startswith("SHAPEKEY"):
            shapekeys[element.SemanticIndex] = data
        elif element.SemanticName.startswith("NORMAL"):
            use_normals = True
            normals = [(x[0], x[1], x[2]) for x in data]
        elif element.SemanticName == "TANGENT":
            pass
        elif element.SemanticName == "BINORMAL":
            pass
        else:
            raise Fatal("Unknown ElementName: " + element.ElementName)

    # 导入完之后，如果发现blend_weights是空的，则自动补充默认值为1,0,0,0的BLENDWEIGHTS
    if len(blend_weights) == 0 and len(blend_indices) != 0:
        print("检测到BLENDWEIGHTS为空，但是含有BLENDINDICES数据，特殊情况，默认补充1,0,0,0的BLENDWEIGHTS")
        tmpi = 0
        for blendindices_turple in blend_indices.values():
            print(blendindices_turple)
            new_dict = []
            for indices in blendindices_turple:
                new_dict.append((1.0,0,0,0))
            blend_weights[tmpi] = tuple(new_dict)
            tmpi = tmpi + 1

    import_uv_layers(mesh, obj, texcoords)

    #  metadata.json, if contains then we can import merged vgmap.
    component = None
    if ImportModelConfigUnreal.import_merged_vgmap():
        # print("尝试读取Metadata.json")
        metadatajsonpath = os.path.join(os.path.dirname(fmt_path),'Metadata.json')
        if os.path.exists(metadatajsonpath):
            # print("鸣潮读取Metadata.json")
            extracted_object = ExtractedObjectHelper.read_metadata(metadatajsonpath)
            fmt_filename = os.path.splitext(os.path.basename(fmt_path))[0]
            if "-" in fmt_filename:
                partname_count = int(fmt_filename.split("-")[1]) - 1
                print("import partname count: " + str(partname_count))
                component = extracted_object.components[partname_count]

    import_vertex_groups(mesh, obj, blend_indices, blend_weights, component)

    import_shapekeys(mesh, obj, shapekeys)

    # Validate closes the loops so they don't disappear after edit mode and probably other important things:
    mesh.validate(verbose=False, clean_customdata=False)  
    mesh.update()
    
    # XXX 这个方法还必须得在mesh.validate和mesh.update之后调用 3.6和4.2都可以用这个
    if use_normals:
        mesh.normals_split_custom_set_from_vertices(normals)

    # auto texture 
    create_material_with_texture(obj, mesh_name=mesh_name,directory= os.path.dirname(fmt_path))

    # ZZZ need reset rotation.
    if MainConfig.gamename not in ["GI","HI3","HSR","Game001"]:
        obj.rotation_euler[0] = 0.0  # X轴
        obj.rotation_euler[1] = 0.0  # Y轴
        obj.rotation_euler[2] = 0.0  # Z轴

    # 设置导入时模型大小比例，Unreal模型常用
    scalefactor = bpy.context.scene.dbmt.model_scale
    obj.scale = scalefactor,scalefactor,scalefactor

    # 导入时翻转模型
    if ImportModelConfig.import_flip_scale_x():
        obj.scale.x = obj.scale.x * -1
    if ImportModelConfig.import_flip_scale_y():
        obj.scale.y = obj.scale.y * -1

    return obj



class Import3DMigotoRaw(bpy.types.Operator, ImportHelper):
    """Import raw 3DMigoto vertex and index buffers"""
    bl_idname = "import_mesh.migoto_raw_buffers_mmt"
    bl_label = "导入.ib .vb .fmt格式模型"
    bl_description = "导入3Dmigoto格式的 .ib .vb .fmt文件，只需选择.fmt文件即可"

    # new architecture only need .fmt file to locate.
    filename_ext = '.fmt'

    filter_glob: StringProperty(
        default='*.fmt',
        options={'HIDDEN'},
    ) # type: ignore

    files: CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement,
    ) # type: ignore

    def get_vb_ib_paths_from_fmt_prefix(self, filename):
        model_prefix = ImportUtils.get_model_prefix_from_fmt_file(filename).strip()
        # print("model_prefix:" + model_prefix)

        fmt_dir_name = os.path.dirname(filename)

        vb_bin_path = ""
        ib_bin_path = ""
        fmt_path = ""

        if model_prefix == "":
            vb_bin_path = os.path.splitext(filename)[0] + '.vb'
            ib_bin_path = os.path.splitext(filename)[0] + '.ib'
            fmt_path = os.path.splitext(filename)[0] + '.fmt'
        else:
            vb_bin_path = os.path.join(fmt_dir_name, model_prefix + '.vb')
            ib_bin_path = os.path.join(fmt_dir_name, model_prefix + '.ib')
            fmt_path = filename
        
        if not os.path.exists(vb_bin_path):
            raise Fatal('Unable to find matching .vb file for %s' % filename)
        if not os.path.exists(ib_bin_path):
            raise Fatal('Unable to find matching .ib file for %s' % filename)
        if not os.path.exists(fmt_path):
            fmt_path = None
        return (vb_bin_path, ib_bin_path, fmt_path)


    def execute(self, context):
        # 我们需要添加到一个新建的集合里，方便后续操作
        # 这里集合的名称需要为当前文件夹的名称
        dirname = os.path.dirname(self.filepath)

        collection_name = os.path.basename(dirname)
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

        # 这里如果用户不选择任何fmt文件，则默认返回读取所有的fmt文件。
        import_filename_list = []
        if len(self.files) == 1:
            if str(self.filepath).endswith(".fmt"):
                import_filename_list.append(self.filepath)
            else:
                for filename in os.listdir(self.filepath):
                    if filename.endswith(".fmt"):
                        import_filename_list.append(filename)
        else:
            for fmtfile in self.files:
                import_filename_list.append(fmtfile.name)


        done = set()
        for fmt_file_name in import_filename_list:
            
            try:
                fmt_file_path = os.path.join(dirname, fmt_file_name)
                (vb_path, ib_path, fmt_path) = self.get_vb_ib_paths_from_fmt_prefix(fmt_file_path)
                if os.path.normcase(vb_path) in done:
                    continue
                done.add(os.path.normcase(fmt_path))

                if fmt_path is not None:
                    # 导入的调用链就从这里开始
                    obj_result = import_3dmigoto_raw_buffers(self, context, fmt_path=fmt_path, vb_path=vb_path, ib_path=ib_path)
                    collection.objects.link(obj_result)
                        
                else:
                    self.report({'ERROR'}, "未找到.fmt文件，无法导入")
            except Fatal as e:
                self.report({'ERROR'}, str(e))

        # Select all objects under collection (因为用户习惯了导入后就是全部选中的状态). 
        CollectionUtils.select_collection_objects(collection)

        return {'FINISHED'}


def ImprotFromWorkSpace(self, context):
    import_drawib_aliasname_folder_path_dict = ImportUtils.get_import_drawib_aliasname_folder_path_dict_with_first_match_type()
    print(import_drawib_aliasname_folder_path_dict)

    workspace_collection = CollectionUtils.new_workspace_collection()

    # 读取时保存每个DrawIB对应的GameType名称到工作空间文件夹下面的Import.json，在导出时使用
    draw_ib_gametypename_dict = {}
    for draw_ib_aliasname,import_folder_path in import_drawib_aliasname_folder_path_dict.items():
        tmp_json = ImportUtils.read_tmp_json(import_folder_path)
        work_game_type = tmp_json.get("WorkGameType","")
        draw_ib = draw_ib_aliasname.split("_")[0]
        draw_ib_gametypename_dict[draw_ib] = work_game_type

    save_import_json_path = os.path.join(MainConfig.path_workspace_folder(),"Import.json")

    JsonUtils.SaveToFile(json_dict=draw_ib_gametypename_dict,filepath=save_import_json_path)
    

    # 开始读取模型数据
    for draw_ib_aliasname,import_folder_path in import_drawib_aliasname_folder_path_dict.items():
        import_prefix_list = ImportUtils.get_prefix_list_from_tmp_json(import_folder_path)
        if len(import_prefix_list) == 0:
            self.report({'ERROR'},"当前output文件夹"+draw_ib_aliasname+"中的内容暂不支持一键导入分支模型")
            continue

        draw_ib_collection = CollectionUtils.new_draw_ib_collection(collection_name=draw_ib_aliasname)
        workspace_collection.children.link(draw_ib_collection)

        part_count = 1
        for prefix in import_prefix_list:
            component_name = "Component " + str(part_count)
            component_collection = CollectionUtils.new_component_collection(component_name=component_name)
            defualt_switch_collection = CollectionUtils.new_switch_collection(collection_name="default")

            # combine and verify if path exists.
            vb_bin_path = import_folder_path + "\\" + prefix + '.vb'
            ib_bin_path = import_folder_path + "\\" + prefix + '.ib'
            fmt_path = import_folder_path + "\\" + prefix + '.fmt'

            if not os.path.exists(vb_bin_path):
                raise Fatal('Unable to find matching .vb file for %s' % import_folder_path + "\\" + prefix)
            if not os.path.exists(ib_bin_path):
                raise Fatal('Unable to find matching .ib file for %s' % import_folder_path + "\\" + prefix)
            if not os.path.exists(fmt_path):
                fmt_path = None

            done = set()
            try:
                if os.path.normcase(vb_bin_path) in done:
                    continue
                done.add(os.path.normcase(vb_bin_path))
                if fmt_path is not None:
                    obj_result = import_3dmigoto_raw_buffers(self, context, fmt_path=fmt_path, vb_path=vb_bin_path,
                                                                ib_path=ib_bin_path)
                    defualt_switch_collection.objects.link(obj_result)
                        
                else:
                    self.report({'ERROR'}, "Can't find .fmt file!")
                
                component_collection.children.link(defualt_switch_collection)
                draw_ib_collection.children.link(component_collection)
            except Fatal as e:
                self.report({'ERROR'}, str(e))

            part_count = part_count + 1

    bpy.context.scene.collection.children.link(workspace_collection)

    # Select all objects under collection (因为用户习惯了导入后就是全部选中的状态). 
    CollectionUtils.select_collection_objects(workspace_collection)



class DBMTImportAllFromCurrentWorkSpace(bpy.types.Operator):
    bl_idname = "dbmt.import_all_from_workspace"
    bl_label = "一键导入当前工作空间内容"
    bl_description = "一键导入当前工作空间文件夹下所有的DrawIB对应的模型为分支集合架构"

    def execute(self, context):
        if MainConfig.workspacename == "":
            self.report({"ERROR"},"Please select your WorkSpace in DBMT before import.")
        elif not os.path.exists(MainConfig.path_workspace_folder()):
            self.report({"ERROR"},"Please select a correct WorkSpace in DBMT before import " + MainConfig.path_workspace_folder())
        else:
            TimerUtils.Start("ImportFromWorkSpace")
            # TODO 导入实在是太慢了，WWMI的模型导入要13秒，还好导入模型这个操作并不是很频繁，有空再来优化吧。
            ImprotFromWorkSpace(self,context)
            TimerUtils.End("ImportFromWorkSpace")
        return {'FINISHED'}