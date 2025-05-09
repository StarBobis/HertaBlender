import bpy
import json
import math
import bmesh
import os


from mathutils import Matrix 
from mathutils import Vector
from mathutils import *
from math import * 

from typing import List, Dict, Union
from dataclasses import dataclass, field, asdict

from .migoto_utils import Fatal
from .collection_utils import ModelCollection, CollectionUtils
from .shapekey_utils import ShapeKeyUtils
from ..properties.properties_wwmi import Properties_WWMI
from operator import attrgetter, itemgetter



def assert_object(obj):
    if isinstance(obj, str):
        obj = get_object(obj)
    elif obj not in bpy.data.objects.values():
        raise ValueError('Not of object type: %s' % str(obj))
    return obj


def get_mode(context):
    if context.active_object:
        return context.active_object.mode


def set_mode(context, mode):
    active_object = get_active_object(context)
    if active_object is not None and mode is not None:
        if not object_is_hidden(active_object):
            bpy.ops.object.mode_set(mode=mode)


@dataclass
class UserContext:
    active_object: bpy.types.Object
    selected_objects: bpy.types.Object
    mode: str


def get_user_context(context):
    return UserContext(
        active_object = get_active_object(context),
        selected_objects = get_selected_objects(context),
        mode = get_mode(context),
    )


def set_user_context(context, user_context):
    deselect_all_objects()
    for object in user_context.selected_objects:
        try:
            select_object(object)
        except ReferenceError as e:
            pass
    if user_context.active_object:
        set_active_object(context, user_context.active_object)
        set_mode(context, user_context.mode)


def get_object(obj_name):
    return bpy.data.objects[obj_name]
        

def get_active_object(context):
    return context.view_layer.objects.active


def get_selected_objects(context):
    return context.selected_objects


def link_object_to_scene(context, obj):
    context.scene.collection.objects.link(obj)


def unlink_object_from_scene(context, obj):
    context.scene.collection.objects.unlink(obj)


def object_exists(obj_name):
    return obj_name in bpy.data.objects.keys()


def link_object_to_collection(obj, col):
    obj = assert_object(obj)
    col = assert_collection(col)
    col.objects.link(obj)


def unlink_object_from_collection(obj, col):
    obj = assert_object(obj)
    col = assert_collection(col)
    col.objects.unlink(obj) 


def rename_object(obj, obj_name):
    obj = assert_object(obj)
    obj.name = obj_name
    

def select_object(obj):
    obj = assert_object(obj)
    obj.select_set(True)


def deselect_object(obj):
    obj = assert_object(obj)
    obj.select_set(False)


def deselect_all_objects():
    for obj in bpy.context.selected_objects:
        deselect_object(obj)
    bpy.context.view_layer.objects.active = None


def object_is_selected(obj):
    return obj.select_get()


def set_active_object(context, obj):
    obj = assert_object(obj)
    context.view_layer.objects.active = obj


def object_is_hidden(obj):
    return obj.hide_get()


def hide_object(obj):
    obj = assert_object(obj)
    obj.hide_set(True)


def unhide_object(obj):
    obj = assert_object(obj)
    obj.hide_set(False)


def set_custom_property(obj, property, value):
    obj = assert_object(obj)
    obj[property] = value


def remove_object(obj):
    obj = assert_object(obj)
    bpy.data.objects.remove(obj, do_unlink=True)


def get_modifiers(obj):
    obj = assert_object(obj)
    return obj.modifiers





def copy_object(context, obj, name=None, collection=None):
    with OpenObject(context, obj, mode='OBJECT') as obj:
        new_obj = obj.copy()
        new_obj.data = obj.data.copy()
        if name:
            rename_object(new_obj, name)
        if collection:
            link_object_to_collection(new_obj, collection)
        return new_obj


def assert_vertex_group(obj, vertex_group):
    obj = assert_object(obj)
    if isinstance(vertex_group, bpy.types.VertexGroup):
        vertex_group = vertex_group.name
    return obj.vertex_groups[vertex_group]


def get_vertex_groups(obj):
    obj = assert_object(obj)
    return obj.vertex_groups


def remove_vertex_groups(obj, vertex_groups):
    obj = assert_object(obj)
    for vertex_group in vertex_groups:
        obj.vertex_groups.remove(assert_vertex_group(obj, vertex_group))


def normalize_all_weights(context, obj):
    with OpenObject(context, obj, mode='WEIGHT_PAINT') as obj:
        bpy.ops.object.vertex_group_normalize_all()


def triangulate_object(context, obj):
    with OpenObject(context, obj, mode='OBJECT') as obj:
        me = obj.data
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(me)
        bm.free()


class OpenObjects:
    def __init__(self, context, objects, mode='OBJECT'):
        self.mode = mode
        self.objects = [assert_object(obj) for obj in objects]
        self.context = context
        self.user_context = get_user_context(context)

    def __enter__(self):

        deselect_all_objects()
        
        for obj in self.objects:
            unhide_object(obj)
            select_object(obj)
            if obj.mode == 'EDIT':
                obj.update_from_editmode()
            
        set_active_object(bpy.context, self.objects[0])

        set_mode(self.context, mode=self.mode)

        return self.objects

    def __exit__(self, *args):
        set_user_context(self.context, self.user_context)


def assert_mesh(mesh):
    if isinstance(mesh, str):
        mesh = get_mesh(mesh)
    elif mesh not in bpy.data.meshes.values():
        raise ValueError('Not of mesh type: %s' % str(mesh))
    return mesh


def get_mesh(mesh_name):
    return bpy.data.meshes[mesh_name]


def remove_mesh(mesh):
    mesh = assert_mesh(mesh)
    bpy.data.meshes.remove(mesh, do_unlink=True)


def mesh_triangulate(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()


def get_vertex_groups_from_bmesh(bm: bmesh.types.BMesh):
    layer_deform = bm.verts.layers.deform.active
    return [sorted(vert[layer_deform].items(), key=itemgetter(1), reverse=True) for vert in bm.verts]

def join_objects(context, objects):
    if len(objects) == 1:
        return
    unused_meshes = []
    with OpenObject(context, objects[0], mode='OBJECT'):
        for obj in objects[1:]:
            unused_meshes.append(obj.data)
            select_object(obj)  
            bpy.ops.object.join()
    for mesh in unused_meshes:
        remove_mesh(mesh)


def get_collection(col_name):
    return bpy.data.collections[col_name]


def get_layer_collection(col, layer_col=None):
    col_name = assert_collection(col).name
    if layer_col is None:
        #        layer_col = bpy.context.scene.collection
        layer_col = bpy.context.view_layer.layer_collection
    if layer_col.name == col_name:
        return layer_col
    for sublayer_col in layer_col.children:
        col = get_layer_collection(col_name, layer_col=sublayer_col)
        if col:
            return col


def collection_exists(col_name):
    return col_name in bpy.data.collections.keys()


def assert_collection(col):
    if isinstance(col, str):
        col = get_collection(col)
    elif col not in bpy.data.collections.values():
        raise ValueError('Not of collection type: %s' % str(col))
    return col


def get_collection_objects(col):
    col = assert_collection(col)
    return col.objects


def link_collection(col, col_parent):
    col = assert_collection(col)
    col_parent = assert_collection(col_parent)
    col_parent.children.link(col)


def new_collection(col_name, col_parent=None, allow_duplicate=True):
    if not allow_duplicate:
        try:
            col = get_collection(col_name)
            if col is not None:
                raise ValueError('Collection already exists: %s' % str(col_name))
        except Exception as e:
            pass
    new_col = bpy.data.collections.new(col_name)
    if col_parent:
        link_collection(new_col, col_parent)
    else:
        bpy.context.scene.collection.children.link(new_col)
    #    bpy.context.view_layer.layer_collection.children[col_name] = new_col
    #    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[-1]
    #    bpy.context.scene.collection.children.link(new_col)
    return new_col


def hide_collection(col):
    col = assert_collection(col)
    #    col.hide_viewport = True
    #    for k, v in bpy.context.view_layer.layer_collection.children.items():
    #        print(k, " ", v)
    #    bpy.context.view_layer.layer_collection.children.get(col.name).hide_viewport = True
    get_layer_collection(col).hide_viewport = True


def unhide_collection(col):
    col = assert_collection(col)
    #    col.hide_viewport = False
    #    bpy.context.view_layer.layer_collection.children.get(col.name).hide_viewport = False
    get_layer_collection(col).hide_viewport = False


def collection_is_hidden(col):
    col = assert_collection(col)
    return get_layer_collection(col).hide_viewport


def get_scene_collections():
    return bpy.context.scene.collection.children

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
        if not os.path.exists(metadata_path):
            raise Fatal("无法找到Metadata.json文件，请确认是否存在该文件。")
        
        with open(metadata_path) as f:
            return ExtractedObject(**json.load(f))
    
@dataclass
class TempObject:
    name: str
    object: bpy.types.Object
    vertex_count: int = 0
    index_count: int = 0
    index_offset: int = 0


@dataclass
class MergedObjectComponent:
    objects: List[TempObject]
    vertex_count: int = 0
    index_count: int = 0

@dataclass
class MergedObjectShapeKeys:
    vertex_count: int = 0


@dataclass
class MergedObject:
    object: bpy.types.Object
    mesh: bpy.types.Mesh
    components: List[MergedObjectComponent]
    shapekeys: MergedObjectShapeKeys
    vertex_count: int = 0
    index_count: int = 0
    vg_count: int = 0


class OpenObject:
    def __init__(self, context, obj, mode='OBJECT'):
        self.mode = mode
        self.object = assert_object(obj)
        self.context = context
        self.user_context = get_user_context(context)
        self.was_hidden = object_is_hidden(self.object)

    def __enter__(self):
        deselect_all_objects()

        unhide_object(self.object)
        select_object(self.object)
        set_active_object(bpy.context, self.object)

        if self.object.mode == 'EDIT':
            self.object.update_from_editmode()

        set_mode(self.context, mode=self.mode)

        return self.object

    def __exit__(self, *args):
        if self.was_hidden:
            hide_object(self.object)
        else:
            unhide_object(self.object)
        set_user_context(self.context, self.user_context)


class ObjUtils:

    @classmethod
    def split_obj_by_loose_parts_to_collection(cls,obj,collection_name:str):
        
        new_collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(new_collection)

        # 复制原对象并链接到新的集合
        obj_copy = obj.copy()
        obj_copy.data = obj.data.copy()
        new_collection.objects.link(obj_copy)
        
        # 取消原对象的选择状态
        obj.select_set(False)
        
        # 设置活动对象为副本，并进入编辑模式
        bpy.context.view_layer.objects.active = obj_copy
        obj_copy.select_set(True)  # 确保副本被选中
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 分离松散部分
        bpy.ops.mesh.separate(type='LOOSE')
        
        # 返回到对象模式
        bpy.ops.object.mode_set(mode='OBJECT')

        # 清理：取消副本的选择状态，以防影响后续操作
        obj_copy.select_set(False)

    @classmethod
    def merge_objects(cls,obj_list, target_collection=None):
        """
        合并给定的对象列表。
        
        :param obj_list: 要合并的对象列表
        :param target_collection: 目标集合，如果为None，则使用当前场景的活动集合
        """
        # 确保至少有一个对象可以进行合并
        if len(obj_list) < 1:
            print("没有足够的对象进行合并")
            return
        
        # 如果目标集合未指定，则使用当前场景的默认集合
        if target_collection is None:
            target_collection = bpy.context.collection
        
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')

        # Select and make one of the objects in the list active
        for obj in obj_list:
            obj.select_set(True)
            if obj.name in bpy.context.view_layer.objects:
                bpy.context.view_layer.objects.active = obj
        
        # Ensure the active object is set to one of the objects to be merged
        active_obj = bpy.context.view_layer.objects.active
        
        # Perform the join operation
        bpy.ops.object.join()

        # After joining, the result is a single object. We can rename it if needed.
        joined_obj = bpy.context.view_layer.objects.active
        joined_obj.name = "MeshObject"
        
        # Optionally move the merged object to the specified collection
        for col in joined_obj.users_collection:
            col.objects.unlink(joined_obj)
        target_collection.objects.link(joined_obj)

    @classmethod
    def normalize_all(cls,obj):
        '''
        调用前需确保选中了这个obj，也就是当前的active对象是这个obj
        '''
        # print("Normalize All Weights For: " + obj.name)
        # 选择你要操作的对象，这里假设场景中只有一个导入的OBJ对象
        if obj and obj.type == 'MESH':
            # 进入权重编辑模式（如果需要）
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
            
            # 确保该对象是活动的，并且被选中
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            
            # 对所有顶点组应用 Normalize All
            bpy.ops.object.vertex_group_normalize_all()

            # 回到物体模式
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            print("没有找到合适的网格对象来执行规范化操作。")

    @classmethod
    def mesh_triangulate(cls,me):
        '''
        三角化一个mesh
        注意这个三角化之后就变成新的mesh了
        '''
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()

    @classmethod
    def get_bpy_context_object(cls):
        '''
        获取当前场景中的obj对象,如果为None则抛出Fatal异常
        '''
        obj = bpy.context.object
        if obj is None:
            # 为空时不导出
            raise Fatal('No object selected')
        
        return obj

    @classmethod
    def selected_obj_delete_loose(cls):
        
        # 获取当前选中的对象
        selected_objects = bpy.context.selected_objects
        # 检查是否选中了一个Mesh对象
        for obj in selected_objects:
            if obj.type == 'MESH':
                # 设置当前对象为活动对象 （不设置的话后面没法切换编辑模式，就会报错）
                bpy.context.view_layer.objects.active = obj
                # 获取选中的网格对象
                bpy.ops.object.mode_set(mode='EDIT')
                # 选择所有的顶点
                bpy.ops.mesh.select_all(action='SELECT')
                # 执行删除孤立顶点操作
                bpy.ops.mesh.delete_loose()
                # 切换回对象模式
                bpy.ops.object.mode_set(mode='OBJECT')

    @classmethod
    def is_contains_locked_weights(cls,obj):
        locked_groups = []
        # 确保对象类型为MESH，因为只有这种类型的对象才有顶点组
        if obj.type == 'MESH':
            # 遍历对象的所有顶点组
            for vg in obj.vertex_groups:
                # 如果顶点组被锁定，则添加到列表中
                if vg.lock_weight:
                    locked_groups.append(vg.name)
        if len(locked_groups) != 0:
            return True
        else:
            return False
        
    @classmethod
    def is_all_vertex_groups_locked(cls,obj):
        '''
        判断是否所有的顶点组都被锁定了，因为所有的顶点组都被锁定的话就无法对权重执行Normalize All了
        '''
        vgs_number = 0
        locked_groups = []
        # 确保对象类型为MESH，因为只有这种类型的对象才有顶点组
        if obj.type == 'MESH':
            # 遍历对象的所有顶点组
            for vg in obj.vertex_groups:
                vgs_number = vgs_number + 1
                # 如果顶点组被锁定，则添加到列表中
                if vg.lock_weight:
                    locked_groups.append(vg.name)
        if len(locked_groups) == vgs_number:
            return True
        else:
            return False

    @classmethod
    def copy_object(cls,context, obj, name=None, collection=None):
        with OpenObject(context, obj, mode='OBJECT') as obj:
            new_obj = obj.copy()
            new_obj.data = obj.data.copy()
            if name:
                rename_object(new_obj, name)
            if collection:
                link_object_to_collection(new_obj, collection)
            return new_obj
    
    @classmethod
    def build_merged_object(cls,extracted_object:ExtractedObject,draw_ib_collection):
        '''
        extracted_object 用于读取配置
        draw_ib_collection 用于控制TEMP_Object生成的位置
        '''
        # 1.Initialize components
        components = []
        for component in extracted_object.components: 
            components.append(
                MergedObjectComponent(
                    objects=[],
                    index_count=0,
                )
            )
        
        # 2.import_objects_from_collection
        # TODO 从这里开始进行修改
        # 这里是获取所有的obj，需要用咱们的方法来进行集合架构的遍历获取所有的obj
        componentname_modelcollection_list_dict:dict[str,list[ModelCollection]] = CollectionUtils.parse_drawib_collection_architecture(draw_ib_collection=draw_ib_collection)

        for component_name,model_collection_list in componentname_modelcollection_list_dict.items():
            for model_collection in model_collection_list:
                for obj_name in model_collection.obj_name_list:
                    obj = bpy.data.objects.get(obj_name)
                    # 跳过不满足component开头的对象

                    # print("ComponentName: " + component_name)
                    component_count = str(component_name)[10:]
                    # print("ComponentCount: " + component_count)

                    component_id = int(component_count) - 1 # 这里减去1是因为我们的Compoennt是从1开始的
                    
                    temp_obj = cls.copy_object(bpy.context, obj, name=f'TEMP_{obj.name}', collection=draw_ib_collection)

                    components[component_id].objects.append(TempObject(
                        name=obj.name,
                        object=temp_obj,
                    ))

        # 3.准备临时对象
        index_offset = 0

        for component_id, component in enumerate(components):

            component.objects.sort(key=lambda x: x.name)

            for temp_object in component.objects:
                temp_obj = temp_object.object
                # Remove muted shape keys
                if Properties_WWMI.ignore_muted_shape_keys() and temp_obj.data.shape_keys:
                    muted_shape_keys = []
                    for shapekey_id in range(len(temp_obj.data.shape_keys.key_blocks)):
                        shape_key = temp_obj.data.shape_keys.key_blocks[shapekey_id]
                        if shape_key.mute:
                            muted_shape_keys.append(shape_key)
                    for shape_key in muted_shape_keys:
                        temp_obj.shape_key_remove(shape_key)
                # Apply all modifiers to temporary object
                if Properties_WWMI.apply_all_modifiers():
                    with OpenObject(bpy.context, temp_obj) as obj:
                        selected_modifiers = [modifier.name for modifier in get_modifiers(obj)]
                        ShapeKeyUtils.apply_modifiers_for_object_with_shape_keys(bpy.context, selected_modifiers, None)
                # Triangulate temporary object, this step is crucial as export supports only triangles
                triangulate_object(bpy.context, temp_obj)
                # Handle Vertex Groups
                vertex_groups = get_vertex_groups(temp_obj)
                # Remove ignored or unexpected vertex groups
                if Properties_WWMI.import_merged_vgmap():
                    # Exclude VGs with 'ignore' tag or with higher id VG count from Metadata.ini for current component
                    total_vg_count = sum([component.vg_count for component in extracted_object.components])
                    ignore_list = [vg for vg in vertex_groups if 'ignore' in vg.name.lower() or vg.index >= total_vg_count]
                else:
                    # Exclude VGs with 'ignore' tag or with higher id VG count from Metadata.ini for current component
                    extracted_component = extracted_object.components[component_id]
                    total_vg_count = len(extracted_component.vg_map)
                    ignore_list = [vg for vg in vertex_groups if 'ignore' in vg.name.lower() or vg.index >= total_vg_count]
                remove_vertex_groups(temp_obj, ignore_list)
                # Rename VGs to their indicies to merge ones of different components together
                for vg in get_vertex_groups(temp_obj):
                    vg.name = str(vg.index)
                # Calculate vertex count of temporary object
                temp_object.vertex_count = len(temp_obj.data.vertices)
                # Calculate index count of temporary object, IB stores 3 indices per triangle
                temp_object.index_count = len(temp_obj.data.polygons) * 3
                # Set index offset of temporary object to global index_offset
                temp_object.index_offset = index_offset
                # Update global index_offset
                index_offset += temp_object.index_count
                # Update vertex and index count of custom component
                component.vertex_count += temp_object.vertex_count
                component.index_count += temp_object.index_count

        # build_merged_object:

        merged_object = []
        vertex_count, index_count = 0, 0
        for component in components:
            for temp_object in component.objects:
                merged_object.append(temp_object.object)
            vertex_count += component.vertex_count
            index_count += component.index_count
            
        join_objects(bpy.context, merged_object)

        obj = merged_object[0]

        rename_object(obj, 'TEMP_EXPORT_OBJECT')

        deselect_all_objects()
        select_object(obj)
        set_active_object(bpy.context, obj)

        mesh = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()

        merged_object = MergedObject(
            object=obj,
            mesh=mesh,
            components=components,
            vertex_count=len(obj.data.vertices),
            index_count=len(obj.data.polygons) * 3,
            vg_count=len(get_vertex_groups(obj)),
            shapekeys=MergedObjectShapeKeys(),
        )

        if vertex_count != merged_object.vertex_count:
            raise ValueError('vertex_count mismatch between merged object and its components')

        if index_count != merged_object.index_count:
            raise ValueError('index_count mismatch between merged object and its components')
        
        return merged_object
    
    @classmethod
    def reset_obj_rotation(cls,obj):
        if obj.type == "MESH":
            # 将旋转角度归零
            obj.rotation_euler[0] = 0.0  # X轴
            obj.rotation_euler[1] = 0.0  # Y轴
            obj.rotation_euler[2] = 0.0  # Z轴

    @classmethod
    def reset_obj_location(cls, obj):
        if obj.type == "MESH":
            # 将位置归零
            obj.location[0] = 0.0  # X轴
            obj.location[1] = 0.0  # Y轴
            obj.location[2] = 0.0  # Z轴

class SmoothNormal:
    '''
    SmoothNormal Algorithm.
    SupportedGame: GI,HI3,HSR,ZZZ,WuWa
    Designed For: ZZZ,WuWa 

    Nico：此方法不知道为什么只能近似还原TEXCOORD1中内容，猜测是缺少了加权平均？
    缺少相关知识太多了，暂时放着

    # 代码版权与来源：
    # function 
    # https://www.bilibili.com/video/BV13G411u75s/?spm_id_from=333.999.0.0 
    # by 给你柠檬椰果养乐多你会跟我玩吗

    # 将法线XY分量存储到UV贴图的坐标(X:法线x, Y:法线y)
    # 灵感来自smoothtool from github 
    # by dashu04

    # 整合 by 失乡のKnight
    # 拆解信息链、重构为工具类 by NicoMico
    '''
    @classmethod
    def vector_cross_product(cls,v1,v2):
        '''
        叉乘 (Cross Product): 两个不平行的三维向量的叉乘会生成一个新的向量，这个新向量与原来的两个向量都垂直。
        因此，对于给定的三角形，使用其两边进行叉乘可以得到一个垂直于该三角形平面的向量，这就是所谓的法线向量。
        '''
        return Vector((v1.y*v2.z-v2.y*v1.z,v1.z*v2.x-v2.z*v1.x,v1.x*v2.y-v2.x*v1.y))
    
    @classmethod
    def vector_dot_product (cls,a,b):
        return a.x*b.x+a.y*b.y+a.z*b.z
    
    @classmethod
    def vector_calc_length(cls,v):
        return sqrt(v.x*v.x+v.y*v.y+v.z*v.z)
    
    @classmethod
    def vector_normalize(cls,v):
        '''
        归一化 (Normalization): 
        之后对叉乘结果进行归一化（normalize），即调整法线向量的长度为1，这样可以确保法线向量只表示方向而不带有长度信息。
        这一步很重要，因为光照计算通常依赖于单位长度的法线向量来保证正确性。
        '''
        L = cls.vector_calc_length(v)
        if L != 0 :
            return v/L
        return 0
    
    @classmethod
    def vector_to_string(cls,v):
        '''
        把Vector变为string，方便放入dict
        '''
        return "x=" + str(v.x) + ",y=" + str(v.y) + ",z=" + str(v.z)
    
    @classmethod
    def need_outline(cls,vertex):
        '''
        仅用于测试，实际使用中应永远返回True
        '''
        need = False
        for g in vertex.groups:
            if g.group == 446:
                need = True
                break
        return True
    
    @classmethod
    def calculate_angle_between_vectors (cls,v1,v2):
        ASIZE = cls.vector_calc_length(v1)
        BSIZE = cls.vector_calc_length(v2)
        D = ASIZE*BSIZE
        if D != 0:
            degree = math.acos(cls.vector_dot_product(v1,v2)/(ASIZE*BSIZE))
            #S = ASIZE*BSIZE*math.sin(degree)
            return degree
        return 0
    
    @classmethod
    def smooth_normal_save_to_uv(cls):
        mesh = bpy.context.active_object.data
        uvdata = mesh.uv_layers.active.data

        # TODO 这里只计算一个UV和不填任何参数结果有什么区别？需要测试
        mesh.calc_tangents(uvmap="TEXCOORD.xy")
        # mesh.calc_tangents()

        co_str_data_dict = {}

        # 开始
        for vertex in mesh.vertices:
            co = vertex.co
            co_str = cls.vector_to_string(co)
            co_str_data_dict[co_str] = []
        print("========")

        for poly in mesh.polygons:
            # 获取三角形的三个顶点
            loop_0 = mesh.loops[poly.loop_start]
            loop_1 = mesh.loops[poly.loop_start+1]
            loop_2 = mesh.loops[poly.loop_start + 2]

            # 获取顶点数据
            vertex_loop0 = mesh.vertices[loop_0.vertex_index]
            vertex_loop1 = mesh.vertices[loop_1.vertex_index]
            vertex_loop2 = mesh.vertices[loop_2.vertex_index]

            # 顶点数据转换为字符串格式
            co0_str = cls.vector_to_string(vertex_loop0.co)
            co1_str = cls.vector_to_string(vertex_loop1.co)
            co2_str = cls.vector_to_string(vertex_loop2.co)

            # 使用CorssProduct计算法线
            normal_vector = cls.vector_cross_product(vertex_loop1.co-vertex_loop0.co,vertex_loop2.co-vertex_loop0.co)
            # 法线归一化使其长度保持为1
            normal_vector = cls.vector_normalize(normal_vector)

            if co0_str in co_str_data_dict and cls.need_outline(vertex_loop0):
                w = cls.calculate_angle_between_vectors(vertex_loop2.co-vertex_loop0.co,vertex_loop1.co-vertex_loop0.co)
                co_str_data_dict[co0_str].append({"n":normal_vector,"w":w,"l":loop_0})
            if co1_str in co_str_data_dict and cls.need_outline(vertex_loop1):
                w = cls.calculate_angle_between_vectors(vertex_loop2.co-vertex_loop1.co,vertex_loop0.co-vertex_loop1.co)
                co_str_data_dict[co1_str].append({"n":normal_vector,"w":w,"l":loop_1})
            if co2_str in co_str_data_dict and cls.need_outline(vertex_loop0):
                w = cls.calculate_angle_between_vectors(vertex_loop1.co-vertex_loop2.co,vertex_loop0.co-vertex_loop2.co)
                co_str_data_dict[co2_str].append({"n":normal_vector,"w":w,"l":loop_2})

        # 存入UV
        uv_layer = mesh.uv_layers.new(name="SmoothNormalMap")
        for poly in mesh.polygons:
            for loop_index in range(poly.loop_start,poly.loop_start+poly.loop_total):
                vertex_index=mesh.loops[loop_index].vertex_index
                vertex = mesh.vertices[vertex_index]

                # 初始化平滑法线和平滑权重
                smoothnormal=Vector((0,0,0))
                weight = 0

                # 基于相邻面的法线加权平均计算平滑法线
                if cls.need_outline(vertex):
                    costr=cls.vector_to_string(vertex.co)

                    if costr in co_str_data_dict:
                        a = co_str_data_dict[costr]
                        # 对于共享此顶点的所有面的数据，遍历它们
                        for d in a:
                            # 分别获取面的法线和权重
                            normal_vector=d['n']
                            w = d['w']
                            # 累加加权法线和权重
                            smoothnormal  += normal_vector*w
                            weight  += w
                if smoothnormal != Vector((0,0,0)):
                    smoothnormal /= weight
                    smoothnormal = cls.vector_normalize(smoothnormal)

                loop_normal = mesh.loops[loop_index].normal
                loop_tangent = mesh.loops[loop_index].tangent
                loop_bitangent = mesh.loops[loop_index].bitangent

                tx = cls.vector_dot_product(loop_tangent,smoothnormal)
                ty = cls.vector_dot_product(loop_bitangent,smoothnormal)
                tz = cls.vector_dot_product(loop_normal,smoothnormal)

                normalT=Vector((tx,ty,tz))
                # print("nor:",smoothnormal)

                # 将法线XY分量存储到UV贴图的坐标 (X:法线x, Y:法线y)
                # 需要根据实际调整，例如UE为（x,1+y）

                # uv = (normalT.x, 1 + normalT.y) 
                uv = (normalT.x, 1 + normalT.y) 
                uv_layer.data[loop_index].uv = uv

        # 重新计算物体的UV贴图以应用更改
        # bpy.ops.object.mode_set(mode="EDIT")
        # bpy.ops.uv.unwrap(method='ANGLE_BASED')
        # bpy.ops.object.mode_set(mode="OBJECT")