import numpy
import struct
import re
from time import time
from ..properties.properties_wwmi import Properties_WWMI
from .m_export import get_buffer_ib_vb_fast

from ..migoto.migoto_format import *

from ..utils.collection_utils import *
from ..config.main_config import *
from ..utils.json_utils import *
from ..utils.timer_utils import *
from ..utils.migoto_utils import Fatal
from ..utils.obj_utils import ObjUtils

from ..migoto.migoto_format import ExtractedObject, ExtractedObjectHelper
from operator import attrgetter, itemgetter

import re
import bpy

from typing import List, Dict, Union
from dataclasses import dataclass, field
from enum import Enum
from dataclasses import dataclass

import bpy
import bmesh


class M_DrawIndexed:

    def __init__(self) -> None:
        self.DrawNumber = ""

        # 绘制起始位置
        self.DrawOffsetIndex = "" 

        self.DrawStartIndex = "0"

        # 代表一个obj具体的draw_indexed
        self.AliasName = "" 

        # 代表这个obj的顶点数
        self.UniqueVertexCount = 0 
    
    def get_draw_str(self) ->str:
        return "drawindexed = " + self.DrawNumber + "," + self.DrawOffsetIndex +  "," + self.DrawStartIndex


class TextureReplace:
    def  __init__(self):
        self.resource_name = ""
        self.filter_index = 0
        self.hash = ""
        self.style = ""
        



def apply_modifiers_for_object_with_shape_keys(context, selectedModifiers, disable_armatures):
    # ------------------------------------------------------------------------------
    # The MIT License (MIT)
    #
    # Copyright (c) 2015 Przemysław Bągard
    #
    # Permission is hereby granted, free of charge, to any person obtaining a copy
    # of this software and associated documentation files (the "Software"), to deal
    # in the Software without restriction, including without limitation the rights
    # to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    # copies of the Software, and to permit persons to whom the Software is
    # furnished to do so, subject to the following conditions:
    #
    # The above copyright notice and this permission notice shall be included in
    # all copies or substantial portions of the Software.
    #
    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    # FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    # LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    # OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
    # THE SOFTWARE.
    # ------------------------------------------------------------------------------

    # Date: 01 February 2015
    # Blender script
    # Description: Apply modifier and remove from the stack for object with shape keys
    # (Pushing 'Apply' button in 'Object modifiers' tab result in an error 'Modifier cannot be applied to a mesh with shape keys').

    # Algorithm (old):
    # - Duplicate active object as many times as the number of shape keys
    # - For each copy remove all shape keys except one
    # - Removing last shape does not change geometry data of object
    # - Apply modifier for each copy
    # - Join objects as shapes and restore shape keys names
    # - Delete all duplicated object except one
    # - Delete old object
    # Original object should be preserved (to keep object name and other data associated with object/mesh). 

    # Algorithm (new):
    # Don't make list of copies, handle it one shape at time.
    # In this algorithm there shouldn't be more than 3 copy of object at time, so it should be more memory-friendly.
    #
    # - Copy object which will hold shape keys
    # - For original object (which will be also result object), remove all shape keys, then apply modifiers. Add "base" shape key
    # - For each shape key except base copy temporary object from copy. Then for temporaryObject:
    #     - remove all shape keys except one (done by removing all shape keys, then transfering the right one from copyObject)
    #     - apply modifiers
    #     - merge with originalObject
    #     - delete temporaryObject
    # - Delete copyObject.
    
    if len(selectedModifiers) == 0:
        return

    list_properties = []
    properties = ["interpolation", "mute", "name", "relative_key", "slider_max", "slider_min", "value", "vertex_group"]
    shapesCount = 0
    vertCount = -1
    startTime = time.time()
    
    # Inspect modifiers for hints used in error message if needed.
    contains_mirror_with_merge = False
    for modifier in context.object.modifiers:
        if modifier.name in selectedModifiers:
            if modifier.type == 'MIRROR' and modifier.use_mirror_merge == True:
                contains_mirror_with_merge = True

    # Disable armature modifiers.
    disabled_armature_modifiers = []
    if disable_armatures:
        for modifier in context.object.modifiers:
            if modifier.name not in selectedModifiers and modifier.type == 'ARMATURE' and modifier.show_viewport == True:
                disabled_armature_modifiers.append(modifier)
                modifier.show_viewport = False
    
    # Calculate shape keys count.
    if context.object.data.shape_keys:
        shapesCount = len(context.object.data.shape_keys.key_blocks)
    
    # If there are no shape keys, just apply modifiers.
    if(shapesCount == 0):
        for modifierName in selectedModifiers:
            bpy.ops.object.modifier_apply(modifier=modifierName)
        return (True, None)
    
    # We want to preserve original object, so all shapes will be joined to it.
    originalObject = context.view_layer.objects.active
    bpy.ops.object.select_all(action='DESELECT')
    originalObject.select_set(True)
    
    # Copy object which will holds all shape keys.
    bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked":False, "mode":'TRANSLATION'}, TRANSFORM_OT_translate={"value":(0, 0, 0), "orient_type":'GLOBAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'GLOBAL', "constraint_axis":(False, False, False), "mirror":True, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":False, "snap_target":'CLOSEST', "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "release_confirm":False, "use_accurate":False})
    copyObject = context.view_layer.objects.active
    copyObject.select_set(False)
    
    # Return selection to originalObject.
    context.view_layer.objects.active = originalObject
    originalObject.select_set(True)
    
    # Save key shape properties
    for i in range(0, shapesCount):
        key_b = originalObject.data.shape_keys.key_blocks[i]
        print (originalObject.data.shape_keys.key_blocks[i].name, key_b.name)
        properties_object = {p:None for p in properties}
        properties_object["name"] = key_b.name
        properties_object["mute"] = key_b.mute
        properties_object["interpolation"] = key_b.interpolation
        properties_object["relative_key"] = key_b.relative_key.name
        properties_object["slider_max"] = key_b.slider_max
        properties_object["slider_min"] = key_b.slider_min
        properties_object["value"] = key_b.value
        properties_object["vertex_group"] = key_b.vertex_group
        list_properties.append(properties_object)

    # Handle base shape in "originalObject"
    print("applyModifierForObjectWithShapeKeys: Applying base shape key")
    bpy.ops.object.shape_key_remove(all=True)
    for modifierName in selectedModifiers:
        bpy.ops.object.modifier_apply(modifier=modifierName)
    vertCount = len(originalObject.data.vertices)
    bpy.ops.object.shape_key_add(from_mix=False)
    originalObject.select_set(False)
    
    # Handle other shape-keys: copy object, get right shape-key, apply modifiers and merge with originalObject.
    # We handle one object at time here.
    for i in range(1, shapesCount):
        currTime = time.time()
        elapsedTime = currTime - startTime

        print("applyModifierForObjectWithShapeKeys: Applying shape key %d/%d ('%s', %0.2f seconds since start)" % (i+1, shapesCount, list_properties[i]["name"], elapsedTime))
        context.view_layer.objects.active = copyObject
        copyObject.select_set(True)
        
        # Copy temp object.
        bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked":False, "mode":'TRANSLATION'}, TRANSFORM_OT_translate={"value":(0, 0, 0), "orient_type":'GLOBAL', "orient_matrix":((1, 0, 0), (0, 1, 0), (0, 0, 1)), "orient_matrix_type":'GLOBAL', "constraint_axis":(False, False, False), "mirror":True, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":False, "snap_target":'CLOSEST', "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "release_confirm":False, "use_accurate":False})
        tmpObject = context.view_layer.objects.active
        bpy.ops.object.shape_key_remove(all=True)
        copyObject.select_set(True)
        copyObject.active_shape_key_index = i
        
        # Get right shape-key.
        bpy.ops.object.shape_key_transfer()
        context.object.active_shape_key_index = 0
        bpy.ops.object.shape_key_remove()
        bpy.ops.object.shape_key_remove(all=True)
        
        # Time to apply modifiers.
        for modifierName in selectedModifiers:
            bpy.ops.object.modifier_apply(modifier=modifierName)
        
        # Verify number of vertices.
        if vertCount != len(tmpObject.data.vertices):
        
            errorInfoHint = ""
            if contains_mirror_with_merge == True:
                errorInfoHint = "There is mirror modifier with 'Merge' property enabled. This may cause a problem."
            if errorInfoHint:
                errorInfoHint = "\n\nHint: " + errorInfoHint
            errorInfo = ("Shape keys ended up with different number of vertices!\n"
                         "All shape keys needs to have the same number of vertices after modifier is applied.\n"
                         "Otherwise joining such shape keys will fail!%s" % errorInfoHint)
            return (False, errorInfo)
    
        # Join with originalObject
        copyObject.select_set(False)
        context.view_layer.objects.active = originalObject
        originalObject.select_set(True)
        bpy.ops.object.join_shapes()
        originalObject.select_set(False)
        context.view_layer.objects.active = tmpObject
        
        # Remove tmpObject
        tmpMesh = tmpObject.data
        bpy.ops.object.delete(use_global=False)
        bpy.data.meshes.remove(tmpMesh)
    
    # Restore shape key properties like name, mute etc.
    context.view_layer.objects.active = originalObject
    for i in range(0, shapesCount):
        key_b = context.view_layer.objects.active.data.shape_keys.key_blocks[i]
        # name needs to be restored before relative_key
        key_b.name = list_properties[i]["name"]
        
    for i in range(0, shapesCount):
        key_b = context.view_layer.objects.active.data.shape_keys.key_blocks[i]
        key_b.interpolation = list_properties[i]["interpolation"]
        key_b.mute = list_properties[i]["mute"]
        key_b.slider_max = list_properties[i]["slider_max"]
        key_b.slider_min = list_properties[i]["slider_min"]
        key_b.value = list_properties[i]["value"]
        key_b.vertex_group = list_properties[i]["vertex_group"]
        rel_key = list_properties[i]["relative_key"]
    
        for j in range(0, shapesCount):
            key_brel = context.view_layer.objects.active.data.shape_keys.key_blocks[j]
            if rel_key == key_brel.name:
                key_b.relative_key = key_brel
                break
    
    # Remove copyObject.
    originalObject.select_set(False)
    context.view_layer.objects.active = copyObject
    copyObject.select_set(True)
    tmpMesh = copyObject.data
    bpy.ops.object.delete(use_global=False)
    bpy.data.meshes.remove(tmpMesh)
    
    # Select originalObject.
    context.view_layer.objects.active = originalObject
    context.view_layer.objects.active.select_set(True)
    
    if disable_armatures:
        for modifier in disabled_armature_modifiers:
            modifier.show_viewport = True
    
    return (True, None)


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


class SkeletonType(Enum):
    Merged = 'Merged'
    PerComponent = 'Per-Component'


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

def copy_object(context, obj, name=None, collection=None):
    with OpenObject(context, obj, mode='OBJECT') as obj:
        new_obj = obj.copy()
        new_obj.data = obj.data.copy()
        if name:
            rename_object(new_obj, name)
        if collection:
            link_object_to_collection(new_obj, collection)
        return new_obj


def build_merged_object(extracted_object:ExtractedObject,draw_ib_collection, componentname_modelcollection_list_dict:dict[str,list[ModelCollection]]):
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

    for component_name,model_collection_list in componentname_modelcollection_list_dict.items():
        for model_collection in model_collection_list:
            for obj_name in model_collection.obj_name_list:
                obj = bpy.data.objects.get(obj_name)
                # 跳过不满足component开头的对象

                print("ComponentName: " + component_name)
                component_count = str(component_name)[10:]
                print("ComponentCount: " + component_count)

                component_id = int(component_count) - 1 # 这里减去1是因为我们的Compoennt是从1开始的
                
                temp_obj = copy_object(bpy.context, obj, name=f'TEMP_{obj.name}', collection=draw_ib_collection)

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
                    apply_modifiers_for_object_with_shape_keys(bpy.context, selected_modifiers, None)
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



class ImportConfig:
    '''
    在一键导入工作空间时，Import.json会记录导入的GameType，在生成Mod时需要用到
    所以这里我们读取Import.json来确定要从哪个提取出来的数据类型文件夹中读取
    然后读取tmp.json来初始化D3D11GameType
    '''
    def __init__(self,draw_ib:str):
        self.draw_ib = draw_ib # DrawIB

        self.category_hash_dict = {}
        self.import_model_list = []
        self.match_first_index_list = []
        self.part_name_list = []

        self.vertex_limit_hash = ""
        self.work_game_type = ""

        self.TextureResource_Name_FileName_Dict:dict[str,str] = {} # 自动贴图配置项
        self.PartName_SlotTextureReplaceDict_Dict:dict[str,dict[str,TextureReplace]] = {} # 自动贴图配置项

        self.parse_attributes()

    def parse_attributes(self):
        workspace_import_json_path = os.path.join(GlobalConfig.path_workspace_folder(), "Import.json")
        draw_ib_gametypename_dict = JsonUtils.LoadFromFile(workspace_import_json_path)
        gametypename = draw_ib_gametypename_dict.get(self.draw_ib,"")

        # 新版本中，我们把数据类型的信息写到了tmp.json中，这样我们就能够读取tmp.json中的内容来决定生成Mod时的数据类型了。
        extract_gametype_folder_path = GlobalConfig.path_extract_gametype_folder(draw_ib=self.draw_ib,gametype_name=gametypename)
        tmp_json_path = os.path.join(extract_gametype_folder_path,"tmp.json")
        if os.path.exists(tmp_json_path):
            self.d3d11GameType:D3D11GameType = D3D11GameType(tmp_json_path)
        else:
            raise Fatal("Can't find your tmp.json for generate mod:" + tmp_json_path)
        
        '''
        读取tmp.json中的内容，后续会用于生成Mod的ini文件
        需要在确定了D3D11GameType之后再执行
        '''
        extract_gametype_folder_path = GlobalConfig.path_extract_gametype_folder(draw_ib=self.draw_ib,gametype_name=self.d3d11GameType.GameTypeName)
        tmp_json_path = os.path.join(extract_gametype_folder_path,"tmp.json")
        tmp_json_dict = JsonUtils.LoadFromFile(tmp_json_path)

        self.category_hash_dict = tmp_json_dict["CategoryHash"]
        self.import_model_list = tmp_json_dict["ImportModelList"]
        self.match_first_index_list = tmp_json_dict["MatchFirstIndex"]
        self.part_name_list = tmp_json_dict["PartNameList"]
        # print(self.partname_textureresourcereplace_dict)
        self.vertex_limit_hash = tmp_json_dict["VertexLimitVB"]
        self.work_game_type = tmp_json_dict["WorkGameType"]

        # 自动贴图依赖于这个字典
        partname_textureresourcereplace_dict:dict[str,str] = tmp_json_dict["PartNameTextureResourceReplaceList"]

        print(tmp_json_path)
        print(partname_textureresourcereplace_dict)
        for partname, texture_resource_replace_list in partname_textureresourcereplace_dict.items():
            slot_texture_replace_dict = {}
            for texture_resource_replace in texture_resource_replace_list:
                splits = texture_resource_replace.split("=")
                slot_name = splits[0].strip()
                texture_filename = splits[1].strip()

                resource_name = "Resource_" + os.path.splitext(texture_filename)[0]

                filename_splits = os.path.splitext(texture_filename)[0].split("_")
                texture_hash = filename_splits[2]

                texture_replace = TextureReplace()
                texture_replace.hash = texture_hash
                texture_replace.resource_name = resource_name
                texture_replace.style = filename_splits[3]

                slot_texture_replace_dict[slot_name] = texture_replace

                self.TextureResource_Name_FileName_Dict[resource_name] = texture_filename

            self.PartName_SlotTextureReplaceDict_Dict[partname] = slot_texture_replace_dict

'''
TODO 
由于WWMI有形态键，要想支持自定义形态键，我们就不得不先对obj进行融合得到统一的一个obj
然后在这个obj上进行操作，这样才能保证形态键索引的正确性，否则只能受限于分部位形态键。
'''
class DrawIBModelWWMI:
    # 通过default_factory让每个类的实例的变量分割开来，不再共享类的静态变量
    def __init__(self,draw_ib_collection,merge_objects:bool):
        '''
        根据3Dmigoto的架构设计，每个DrawIB都是一个独立的Mod
        '''
        # 从集合名称中获取当前DrawIB和别名
        drawib_collection_name_splits = CollectionUtils.get_clean_collection_name(draw_ib_collection.name).split("_")
        self.draw_ib = drawib_collection_name_splits[0]
        self.draw_ib_alias = drawib_collection_name_splits[1]

        # (1) 读取工作空间中配置文件的配置项
        self.import_config = ImportConfig(draw_ib=self.draw_ib)
        self.d3d11GameType:D3D11GameType = self.import_config.d3d11GameType
        # 读取WWMI专属配置
        self.extracted_object:ExtractedObject = None
        metadatajsonpath = GlobalConfig.path_extract_gametype_folder(draw_ib=self.draw_ib,gametype_name=self.d3d11GameType.GameTypeName)  + "Metadata.json"
        if os.path.exists(metadatajsonpath):
            self.extracted_object = ExtractedObjectHelper.read_metadata(metadatajsonpath)


        # (2) 解析集合架构，获得每个DrawIB中，每个Component对应的obj列表及其相关属性
        self.componentname_modelcollection_list_dict:dict[str,list[ModelCollection]] = CollectionUtils.parse_drawib_collection_architecture(draw_ib_collection=draw_ib_collection)

        # (3) 解析当前有多少个key
        self.key_number = CollectionUtils.parse_key_number(draw_ib_collection=draw_ib_collection)

        # (4) 根据之前解析集合架构的结果，读取obj对象内容到字典中
        self.__obj_name_ib_dict:dict[str,list] = {} 
        self.__obj_name_category_buffer_list_dict:dict[str,list] =  {} 
        self.obj_name_drawindexed_dict:dict[str,M_DrawIndexed] = {} # 给每个obj的属性统计好，后面就能直接用了。
        self.__obj_name_index_vertex_id_dict:dict[str,dict] = {} # 形态键功能必备
        self.componentname_ibbuf_dict = {} # 所有Component共用一个IB文件。
        self.__categoryname_bytelist_dict = {} # 每个Category都生成一个CategoryBuffer文件。

        self.draw_number = 0 # 每个DrawIB都有总的顶点数，对应CategoryBuffer里的顶点数。
        self.total_index_count = 0 # 每个DrawIB都有总的IndexCount数，也就是所有的IB中的所有顶点索引数量

        self.merged_object = build_merged_object(
            extracted_object=self.extracted_object,
            draw_ib_collection=draw_ib_collection,
            componentname_modelcollection_list_dict=self.componentname_modelcollection_list_dict
        )

        # print(self.merged_object)
        # raise Fatal("暂停")

        # TODO 执行下面这个方法之前，需要对obj进行融合处理，这里直接用WWMI-Tools里的代码融合就行了。
        # TODO 此外export的方法也要进行修改，确保能接受融合好的临时obj
        self.__parse_obj_name_ib_category_buffer_dict()
        
        self.__read_component_ib_buf_dict_merged()
            
        # 构建每个Category的VertexBuffer
        self.__read_categoryname_bytelist_dict()

        # WWMI专用，因为它非得用到metadata.json的东西
        # 目前只有WWMI会需要读取ShapeKey数据
        # 用于形态键导出
        self.shapekey_offsets = []
        self.shapekey_vertex_ids = []
        self.shapekey_vertex_offsets = []

        self.__read_shapekey_cateogry_buf_dict()
       

        # (5) 导出Buffer文件，Export Index Buffer files, Category Buffer files. (And Export ShapeKey Buffer Files.(WWMI))
        # 用于写出IB时使用
        self.PartName_IBResourceName_Dict = {}
        self.PartName_IBBufferFileName_Dict = {}
        self.combine_partname_ib_resource_and_filename_dict()
        self.write_buffer_files()
    


    def __parse_obj_name_ib_category_buffer_dict(self):
        '''
        把之前统计的所有obj都转为ib和category_buffer_dict格式备用
        '''
        for model_collection_list in self.componentname_modelcollection_list_dict.values():
            for model_collection in model_collection_list:
                for obj_name in model_collection.obj_name_list:
                    obj = bpy.data.objects[obj_name]
                    
                    # 选中当前obj对象
                    bpy.context.view_layer.objects.active = obj

                    # XXX 我们在导出具体数据之前，先对模型整体的权重进行normalize_all预处理，才能让后续的具体每一个权重的normalize_all更好的工作
                    # 使用这个的前提是当前obj中没有锁定的顶点组，所以这里要先进行判断。
                    # TODO 这里要确定一下WWMI-Tools是否需要NormalizeAll
                    if "Blend" in self.d3d11GameType.OrderedCategoryNameList:
                        all_vgs_locked = ObjUtils.is_all_vertex_groups_locked(obj)
                        if not all_vgs_locked:
                            ObjUtils.normalize_all(obj)

                    ib, category_buffer_dict,index_vertex_id_dict = get_buffer_ib_vb_fast(self.d3d11GameType)
                    self.__obj_name_index_vertex_id_dict[obj_name] = index_vertex_id_dict
                    self.__obj_name_ib_dict[obj.name] = ib
                    self.__obj_name_category_buffer_list_dict[obj.name] = category_buffer_dict
                    # self.__obj_name_index_vertex_id_dict[obj.name] = index_vertex_id_dict


    def __read_component_ib_buf_dict_merged(self):
        '''
        一个DrawIB的所有Component共享整体的IB文件。
        也就是一个DrawIB的所有绘制中，所有的MatchFirstIndex都来源于一个IndexBuffer文件。
        是游戏原本的做法，但是不分开的话，一个IndexBuffer文件会遇到135W顶点索引数的上限。
        
        由于在WWMI中只能使用一个IB文件，而在GI、HSR、HI3、ZZZ等Unity游戏中天生就能使用多个IB文件
        所以这里只有WWMI会用到，其它游戏如果不是必要尽量不要用，避免135W左右的顶点索引数限制。
        '''
        vertex_number_ib_offset = 0
        ib_buf = []
        draw_offset = 0
        for component_name, moel_collection_list in self.componentname_modelcollection_list_dict.items():
            for model_collection in moel_collection_list:
                for obj_name in model_collection.obj_name_list:
                    # print("processing: " + obj_name)
                    ib = self.__obj_name_ib_dict.get(obj_name,None)

                    # ib的数据类型是list[int]
                    unique_vertex_number_set = set(ib)
                    unique_vertex_number = len(unique_vertex_number_set)

                    if ib is None:
                        print("Can't find ib object for " + obj_name +",skip this obj process.")
                        continue

                    offset_ib = []
                    for ib_number in ib:
                        offset_ib.append(ib_number + vertex_number_ib_offset)
                    
                    # print("Component name: " + component_name)
                    # print("Draw Offset: " + str(vertex_number_ib_offset))
                    ib_buf.extend(offset_ib)

                    drawindexed_obj = M_DrawIndexed()
                    draw_number = len(offset_ib)
                    drawindexed_obj.DrawNumber = str(draw_number)
                    drawindexed_obj.DrawOffsetIndex = str(draw_offset)
                    drawindexed_obj.UniqueVertexCount = unique_vertex_number
                    drawindexed_obj.AliasName = "[" + model_collection.model_collection_name + "] [" + obj_name + "]  (" + str(unique_vertex_number) + ")"
                    self.obj_name_drawindexed_dict[obj_name] = drawindexed_obj
                    draw_offset = draw_offset + draw_number

                    # Add UniqueVertexNumber to show vertex count in mod ini.
                    # print("Draw Number: " + str(unique_vertex_number))
                    vertex_number_ib_offset = vertex_number_ib_offset + unique_vertex_number

                    # LOG.newline()
        # 累加完毕后draw_offset的值就是总的index_count的值，正好作为WWMI的$object_id
        self.total_index_count = draw_offset

        for component_name, moel_collection_list in self.componentname_modelcollection_list_dict.items():
            # Only export if it's not empty.
            if len(ib_buf) != 0:
                self.componentname_ibbuf_dict[component_name] = ib_buf
            else:
                LOG.warning(self.draw_ib + " collection: " + component_name + " is hide, skip export ib buf.")


    def __read_shapekey_cateogry_buf_dict(self):
        '''
        从模型中读取形态键部分，生成形态键数据所需的Buffer

        TODO 形态键合并问题：
        目前带有形态键的物体如果放到其它部位就会导致形态键炸裂，需要排查原因。
        '''
        # TimerUtils.Start("read shapekey data")

        shapekey_index_list = []
        shapekey_data = {}

        vertex_count_offset = 0

        for obj_name, drawindexed_obj in self.obj_name_drawindexed_dict.items():
            obj = bpy.data.objects[obj_name]
            print("Processing obj: " + obj_name)
            mesh = obj.data
            
            # 如果这个obj的mesh没有形态键，那就直接跳过不处理
            mesh_shapekeys = mesh.shape_keys
            if mesh_shapekeys is None:
                print("obj: " + obj_name + " 不含有形态键，跳过处理")
                # 即使跳过了这个obj，这个顶点数偏移依然要加上，否则得到的结果是不正确的
                # 测试过了，这个地方和形态键合并无关
                vertex_count_offset = vertex_count_offset + len(mesh.vertices)
                # print("vertex_count_offset: " + str(vertex_count_offset))
                continue   
            else:
                print(obj_name + "'s shapekey number: " + str(len(mesh.shape_keys.key_blocks)))

            base_data = mesh_shapekeys.key_blocks['Basis'].data
            for shapekey in mesh_shapekeys.key_blocks:
                # 截取形态键名称中的形态键shapekey_id，获取不到就跳过
                shapekey_pattern = re.compile(r'.*(?:deform|custom)[_ -]*(\d+).*')
                match = shapekey_pattern.findall(shapekey.name.lower())
                if len(match) == 0:
                    # print("当前形态键名称:" +shapekey.name + " 不是以Deform开头的，进行跳过")
                    continue
                # else:
                #     print(shapekey.name)

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
                    offseted_vertex_index = vertex_index + vertex_count_offset

                    if offseted_vertex_index not in shapekey_data:
                        shapekey_data[offseted_vertex_index] = {}

                    # 如果相差太小，说明无效或者是一样的，说明这个顶点没有ShapeKey，此时向ShapeKeyOffsets中添加空的0
                    if vertex_offset.length < 0.000000001:
                        # print("相差太小，跳过处理。")
                        continue
                    
                    # 此时如果能获取到，说明有效，此时可以直接放入准备好的字典
                    shapekey_data[offseted_vertex_index][shapekey_index] = list(vertex_offset)

                # break
            # 对于每一个obj的每个顶点，都从0到128获取它的形态键对应偏移值
            vertex_count_offset = vertex_count_offset + len(mesh.vertices)
            # print("vertex_count_offset: " + str(vertex_count_offset))
        
        LOG.newline()

        # 转换格式问题
        shapekey_cache = {shapekey_id:{} for shapekey_id in shapekey_index_list}

        # 通过这种方式避免了必须合并obj的问题，总算是不用重构了。
        # TODO 我感觉这里少处理了什么，如果对应位置有形态键，但是跳过处理的话，这会不会炸掉？
        global_index_offset = 0
        global_vertex_offset = 0
        for obj_name, drawindexed_obj in self.obj_name_drawindexed_dict.items():
            obj = bpy.data.objects[obj_name]
            print("Processing obj: " + obj_name)
            mesh = obj.data

            # 获取当前obj每个Index对应的VertexId
            index_vertex_id_dict = self.__obj_name_index_vertex_id_dict[obj_name]
            for index_id,vertex_id in index_vertex_id_dict.items():
                # 这样VertexId加上全局偏移，就能获取到对应位置的形态键数据：
                vertex_shapekey_data = shapekey_data.get(vertex_id + global_vertex_offset, None)
                if vertex_shapekey_data is not None:
                    for shapekey_index,vertex_offsets in vertex_shapekey_data.items():
                        # 然后这里IndexId加上全局IndexId偏移，就得到了obj整体的IndexId，存到对应的ShapeKeyIndex上面
                        shapekey_cache[shapekey_index][index_id + global_index_offset] = vertex_offsets

            global_index_offset = global_index_offset + drawindexed_obj.UniqueVertexCount
            global_vertex_offset = global_vertex_offset + len(mesh.vertices)
        
            print("global_index_offset: " + str(global_index_offset))
            # print("global_vertex_offset: " + str(global_vertex_offset))
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

        # LOG.newline()
        # print("shapekey_offsets: " + str(len(self.shapekey_offsets))) # 128 WWMI:128
        # print("shapekey_vertex_ids: " + str(len(self.shapekey_vertex_ids))) # 29161 WWMI:29404
        # print("shapekey_vertex_offsets: " + str(len(self.shapekey_vertex_offsets))) # 174966  WWMI:29404 * 6  = 176424 * 2 = 352848
        # TimerUtils.End("read shapekey data")


    def __read_categoryname_bytelist_dict(self):
        # TimerUtils.Start("__read_categoryname_bytelist_dict")
        for component_name, model_collection_list in self.componentname_modelcollection_list_dict.items():
            for model_collection in model_collection_list:
                for obj_name in model_collection.obj_name_list:
                    category_buffer_list = self.__obj_name_category_buffer_list_dict.get(obj_name,None)
                    
                    if category_buffer_list is None:
                        print("Can't find vb object for " + obj_name +",skip this obj process.")
                        continue

                    for category_name in self.d3d11GameType.OrderedCategoryNameList:
                        

                        if category_name not in self.__categoryname_bytelist_dict:
                            self.__categoryname_bytelist_dict[category_name] =  category_buffer_list[category_name]
                        else:
                            existing_array = self.__categoryname_bytelist_dict[category_name]
                            buffer_array = category_buffer_list[category_name]

                            # 确保两个数组都是NumPy数组
                            existing_array = numpy.asarray(existing_array)
                            buffer_array = numpy.asarray(buffer_array)

                            # 使用 concatenate 连接两个数组，确保传递的是一个序列（如列表或元组）
                            concatenated_array = numpy.concatenate((existing_array, buffer_array))

                            # 更新字典中的值
                            self.__categoryname_bytelist_dict[category_name] = concatenated_array


                            # self.__categoryname_bytelist_dict[category_name] = numpy.concatenate(self.__categoryname_bytelist_dict[category_name],category_buffer_list[category_name])
        
        # 顺便计算一下步长得到总顶点数
        # print(self.d3d11GameType.CategoryStrideDict)
        position_stride = self.d3d11GameType.CategoryStrideDict["Position"]
        position_bytelength = len(self.__categoryname_bytelist_dict["Position"])
        self.draw_number = int(position_bytelength/position_stride)

        # TimerUtils.End("__read_categoryname_bytelist_dict")  
        # 耗时大概1S左右




    def combine_partname_ib_resource_and_filename_dict(self):
        '''
        拼接每个PartName对应的IB文件的Resource和filename,这样生成ini的时候以及导出Mod的时候就可以直接使用了。
        '''
        for partname in self.part_name_list:
            style_part_name = "Component" + partname
            ib_resource_name = "Resource_" + self.draw_ib + "_" + style_part_name
            ib_buf_filename = self.draw_ib + "-" + style_part_name + ".buf"
            self.PartName_IBResourceName_Dict[partname] = ib_resource_name
            self.PartName_IBBufferFileName_Dict[partname] = ib_buf_filename

    def write_buffer_files(self):
        '''
        导出当前Mod的所有Buffer文件
        '''
        buf_output_folder = GlobalConfig.path_generatemod_buffer_folder(draw_ib=self.draw_ib)
        # print("Write Buffer Files::")
        # Export Index Buffer files.
        for partname in self.part_name_list:
            component_name = "Component " + partname
            ib_buf = self.componentname_ibbuf_dict.get(component_name,None)

            if ib_buf is None:
                print("Export Skip, Can't get ib buf for partname: " + partname)
            else:
                ib_path = buf_output_folder + self.PartName_IBBufferFileName_Dict[partname]

                packed_data = struct.pack(f'<{len(ib_buf)}I', *ib_buf)
                with open(ib_path, 'wb') as ibf:
                    ibf.write(packed_data) 
            
            # 这里break是因为WWMI只需要一个IB文件
            if GlobalConfig.get_game_category() == GameCategory.UnrealVS or GlobalConfig.get_game_category() == GameCategory.UnrealCS: 
                break
            
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

