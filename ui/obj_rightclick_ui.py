from ..utils.shapekey_utils import *
from ..utils.vertexgroup_utils import VertexGroupUtils
from ..utils.obj_utils import SmoothNormal,ObjUtils
import bmesh
from mathutils import Vector,Matrix
import random
from ..utils.migoto_utils import Fatal
import bpy
import itertools

from bpy.props import BoolProperty,  CollectionProperty

# XXX Blender4.2开始class中不能出现bl_options，所以我们全部都去掉了。
# XXX bl_idname必须小写，单词之间以下划线分割，否则报错无法加载



class RenameAmatureFromGame(bpy.types.Operator):
    bl_idname = "object.rename_amature_from_game"
    bl_label = "重命名选中Amature的骨骼名称(GI)(测试)"
    bl_description = "用于把游戏里解包出来的骨骼重命名，方便我们直接一键绑定到提取出的Mod模型上，Credit to Leotorrez"
    def execute(self, context):
        # Copied from https://github.com/zeroruka/GI-Bones 
        # Select the armature and then run script
        armature_name = bpy.context.active_object.name

        object_name_original = 'Body'
        if not bpy.context.active_object:
            raise RuntimeError("The selected object is not an armature.")
        if bpy.context.active_object.type != "ARMATURE" or armature_name not in bpy.data.objects:
            raise RuntimeError("Error: No object selected.")

        bpy.ops.object.scale_clear()
        bpy.context.view_layer.objects.active = bpy.data.objects[armature_name]
        bpy.ops.object.mode_set(mode='OBJECT')
        # 这里mirror是因为我们的3Dmigoto提取出来的模型天生就是相反的方向
        bpy.ops.transform.mirror(constraint_axis=(True, False, False))
        bpy.ops.object.transform_apply(scale=True, rotation=False)

        vertex_groups = [vg.name for vg in bpy.data.objects[object_name_original].vertex_groups]
        pairs = {old:new for old,new in zip(vertex_groups, sorted(vertex_groups))}
        name_mapping = {new: str(i) for i, (_, new) in enumerate(pairs.items())}
        for vertex_group in bpy.data.objects[object_name_original].vertex_groups:
            armature_obj = bpy.data.objects[armature_name].data
            armature_obj.bones[vertex_group.name].name = vertex_group.name = name_mapping[vertex_group.name]

        new_armature_name = f"{armature_name}_sorted"
        bpy.data.objects[armature_name].name = new_armature_name
        bpy.context.view_layer.objects.active = bpy.data.objects[new_armature_name]
        obj = bpy.data.objects.get(new_armature_name)
        obj.parent = None
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        obj.rotation_euler[0] = -1.5708
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        obj.rotation_euler[0] = 1.5708

        for obj in bpy.data.objects:
            if obj.name != new_armature_name:
                for child in obj.children:
                    bpy.data.objects.remove(child)
                bpy.data.objects.remove(obj)
        return {'FINISHED'}










class RecalculateTANGENTWithVectorNormalizedNormal(bpy.types.Operator):
    bl_idname = "object.recalculate_tangent_arithmetic_average_normal"
    bl_label = "使用向量相加归一化算法重计算TANGENT"
    bl_description = "近似修复轮廓线算法，可以达到99%的轮廓线相似度，适用于GI,HSR,ZZZ,HI3 2.0之前的老角色" 
    def execute(self, context):
        for obj in bpy.context.selected_objects:
            if obj.type == "MESH":
                if obj.get("3DMigoto:RecalculateTANGENT",False):
                    obj["3DMigoto:RecalculateTANGENT"] = not obj["3DMigoto:RecalculateTANGENT"]
                else:
                    obj["3DMigoto:RecalculateTANGENT"] = True
                self.report({'INFO'},"重计算TANGENT设为:" + str(obj["3DMigoto:RecalculateTANGENT"]))
        return {'FINISHED'}


class RecalculateCOLORWithVectorNormalizedNormal(bpy.types.Operator):
    bl_idname = "object.recalculate_color_arithmetic_average_normal"
    bl_label = "使用算术平均归一化算法重计算COLOR"
    bl_description = "近似修复轮廓线算法，可以达到99%的轮廓线相似度，仅适用于HI3 2.0新角色" 

    def execute(self, context):
        for obj in bpy.context.selected_objects:
            if obj.type == "MESH":
                if obj.get("3DMigoto:RecalculateCOLOR",False):
                    obj["3DMigoto:RecalculateCOLOR"] = not obj["3DMigoto:RecalculateCOLOR"]
                else:
                    obj["3DMigoto:RecalculateCOLOR"] = True
                self.report({'INFO'},"重计算COLOR设为:" + str(obj["3DMigoto:RecalculateCOLOR"]))
        return {'FINISHED'}




class PropertyCollectionModifierItem(bpy.types.PropertyGroup):
    checked: BoolProperty(
        name="", 
        default=False
    ) # type: ignore
bpy.utils.register_class(PropertyCollectionModifierItem)

class WWMI_ApplyModifierForObjectWithShapeKeysOperator(bpy.types.Operator):
    bl_idname = "wwmi_tools.apply_modifier_for_object_with_shape_keys"
    bl_label = "在有形态键的模型上应用修改器"
    bl_description = "Apply selected modifiers and remove from the stack for object with shape keys (Solves 'Modifier cannot be applied to a mesh with shape keys' error when pushing 'Apply' button in 'Object modifiers'). Sourced by Przemysław Bągard"
 
    def item_list(self, context):
        return [(modifier.name, modifier.name, modifier.name) for modifier in bpy.context.object.modifiers]
    
    my_collection: CollectionProperty(
        type=PropertyCollectionModifierItem
    ) # type: ignore
    
    disable_armatures: BoolProperty(
        name="Don't include armature deformations",
        default=True,
    ) # type: ignore
 
    def execute(self, context):
        ob = bpy.context.object
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = ob
        ob.select_set(True)
        
        selectedModifiers = [o.name for o in self.my_collection if o.checked]
        
        if not selectedModifiers:
            self.report({'ERROR'}, 'No modifier selected!')
            return {'FINISHED'}
        
        success, errorInfo = ShapeKeyUtils.apply_modifiers_for_object_with_shape_keys(context, selectedModifiers, self.disable_armatures)
        
        if not success:
            self.report({'ERROR'}, errorInfo)
        
        return {'FINISHED'}
        
    def draw(self, context):
        if context.object.data.shape_keys and context.object.data.shape_keys.animation_data:
            self.layout.separator()
            self.layout.label(text="Warning:")
            self.layout.label(text="              Object contains animation data")
            self.layout.label(text="              (like drivers, keyframes etc.)")
            self.layout.label(text="              assigned to shape keys.")
            self.layout.label(text="              Those data will be lost!")
            self.layout.separator()
        #self.layout.prop(self, "my_enum")
        box = self.layout.box()
        for prop in self.my_collection:
            box.prop(prop, "checked", text=prop["name"])
        #box.prop(self, "my_collection")
        self.layout.prop(self, "disable_armatures")
 
    def invoke(self, context, event):
        self.my_collection.clear()
        for i in range(len(bpy.context.object.modifiers)):
            item = self.my_collection.add()
            item.name = bpy.context.object.modifiers[i].name
            item.checked = False
        return context.window_manager.invoke_props_dialog(self)
    

class SmoothNormalSaveToUV(bpy.types.Operator):
    bl_idname = "object.smooth_normal_save_to_uv"
    bl_label = "平滑法线存UV(近似)"
    bl_description = "平滑法线存UV算法，可用于修复ZZZ,WuWa的某些UV(只是近似实现60%的效果)" 

    def execute(self, context):
        SmoothNormal.smooth_normal_save_to_uv()
        
        return {'FINISHED'}
 

    
 
class CatterRightClickMenu(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_object_3Dmigoto"
    bl_label = "3Dmigoto"
    bl_description = "适用于3Dmigoto Mod制作的常用功能"
    
    def draw(self, context):
        layout = self.layout
        layout.operator(WWMI_ApplyModifierForObjectWithShapeKeysOperator.bl_idname)
        layout.operator(SmoothNormalSaveToUV.bl_idname)
        # 
        layout.operator(RenameAmatureFromGame.bl_idname)
        layout.separator()
        layout.operator(RecalculateTANGENTWithVectorNormalizedNormal.bl_idname)
        layout.operator(RecalculateCOLORWithVectorNormalizedNormal.bl_idname)
        


def menu_func_migoto_right_click(self, context):
    self.layout.separator()
    self.layout.menu(CatterRightClickMenu.bl_idname)


