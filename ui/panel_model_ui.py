import bpy
import bmesh
import numpy

from bpy.props import BoolProperty,  CollectionProperty

from ..utils.obj_utils import ObjUtils,SmoothNormal
from ..utils.collection_utils import CollectionUtils
from ..utils.vertexgroup_utils import VertexGroupUtils
from ..utils.shapekey_utils import ShapeKeyUtils


class ModelSplitByLoosePart(bpy.types.Operator):
    bl_idname = "panel_model.split_by_loose_part"
    bl_label = "根据UV松散块儿分割模型"
    bl_description = "功能与Edit界面的Split => Split by Loose Parts相似，但是分割模型为松散块儿并放入新集合。"

    def execute(self, context):
        
        if len(bpy.context.selected_objects) == 0:
            self.report({'ERROR'}, "没有选中的对象！")
            return {'CANCELLED'}
        obj = bpy.context.selected_objects[0]
        # 创建一个新的集合，以原对象名命名
        collection_name = f"{obj.name}_LooseParts"
        ObjUtils.split_obj_by_loose_parts_to_collection(obj=obj,collection_name=collection_name)

        self.report({'INFO'}, "根据UV松散块儿分割模型成功!")
        return {'FINISHED'}


class ModelSplitByVertexGroup(bpy.types.Operator):
    bl_idname = "panel_model.split_by_vertex_group"
    bl_label = "根据共享与孤立顶点组分割模型"
    bl_description = "把模型根据共享的顶点组分开，方便快速分离身体上的小物件，方便后续刷权重不受小物件影响。"

    def execute(self, context):
        if len(bpy.context.selected_objects) == 0:
            self.report({'ERROR'}, "没有选中的对象！")
            return {'CANCELLED'}
        obj = bpy.context.selected_objects[0]
        # 创建一个新的集合，以原对象名命名
        collection_name = f"{obj.name}_Splits"
        ObjUtils.split_obj_by_loose_parts_to_collection(obj=obj,collection_name=collection_name)
        
        collection = CollectionUtils.get_collection_by_name(collection_name=collection_name)

        # 获取当前选中集合的所有obj
        CollectionUtils.select_collection_objects(collection)

        # 放列表里备用
        selected_objects = bpy.context.selected_objects

        number_vgnameset_dict = {}
        number_objlist_dict = {}

        for obj in selected_objects:

            # 先清除相同的顶点组
            VertexGroupUtils.remove_unused_vertex_groups(obj)
             
            # 获取对象的顶点组名称列表
            vertex_group_names = [vg.name for vg in obj.vertex_groups]

            vgname_set = set()

            # 遍历每个顶点组名称
            for vgname in vertex_group_names:
                    vgname_set.add(vgname)

            if len(number_vgnameset_dict) == 0:
                # 一个都没有的时候直接放进去
                number_vgnameset_dict[1] = vgname_set
                number_objlist_dict[1] = [obj]
            else:
                exists = False
                for number, tmp_vgname_set in number_vgnameset_dict.items():
                    # 取交集
                    vgname_jiaoji = tmp_vgname_set & vgname_set

                    if len(vgname_jiaoji) != 0:
                        # 取全集
                        vgname_quanji = tmp_vgname_set.union(vgname_set)

                        # 如果有交集就把全集放进来
                        number_vgnameset_dict[number] = vgname_quanji

                        exists = True
                        # 如果有交集，用全集替换后直接退出循环即可
                        break
                
                if not exists:
                    # 如果没找到交集，就新增一个进去
                    number_objlist_dict[len(number_objlist_dict) + 1] = [obj]
                    number_vgnameset_dict[len(number_vgnameset_dict) + 1] = vgname_set
                else:
                    # 如果找到了交集，就把这个对象放进去
                    number_objlist_dict[number].append(obj)

        # 输出查看一下 
        # print(number_vgnameset_dict.keys())
        # print("======================================")
        # for number in number_vgnameset_dict.keys():
        #     print(number_vgnameset_dict[number])
        # print("======================================")
        # for number, objlist in number_objlist_dict.items():
        #     print("Number: " + str(number) + " ObjList: " + str(objlist))
        #     print("---")

        # 到这里就可以合并obj了
        for number, objlist in number_objlist_dict.items():
            ObjUtils.merge_objects(obj_list=objlist,target_collection=collection)
        self.report({'INFO'}, "根据顶点组分割模型成功!")
        return {'FINISHED'}
    

class ModelDeleteLoosePoint(bpy.types.Operator):
    bl_idname = "panel_model.delete_loose_point"
    bl_label = "删除模型中的松散点"
    bl_description = "删除模型中的松散点，避免影响后续的模型处理。"

    def execute(self, context):
        
        if len(bpy.context.selected_objects) == 0:
            self.report({'ERROR'}, "没有选中的对象！")
            return {'CANCELLED'}
        
        ObjUtils.selected_obj_delete_loose()

        self.report({'INFO'}, "删除松散点成功!")
        return {'FINISHED'}
    
class ModelRenameVertexGroupNameWithTheirSuffix(bpy.types.Operator):
    bl_idname = "panel_model.rename_vertex_group_name_with_their_suffix"
    bl_label = "用模型名称作为前缀重命名顶点组"
    bl_description = "用模型名称作为前缀重命名顶点组，方便后续合并到一个物体后同名称的顶点组不会合在一起冲突，便于后续一键绑定骨骼。"

    def execute(self, context):
        
        if len(bpy.context.selected_objects) == 0:
            self.report({'ERROR'}, "没有选中的对象！")
            return {'CANCELLED'}
        
        # 遍历所有选中的对象
        for obj in context.selected_objects:
            # 仅处理网格对象
            if obj.type == 'MESH':
                model_name = obj.name
                
                # 遍历顶点组并重命名
                for vertex_group in obj.vertex_groups:
                    original_name = vertex_group.name
                    new_name = f"{model_name}_{original_name}"
                    vertex_group.name = new_name

        self.report({'INFO'}, "用模型名称作为前缀重命名顶点组成功!")
        return {'FINISHED'}
    

class RemoveAllVertexGroupOperator(bpy.types.Operator):
    bl_idname = "object.remove_all_vertex_group"
    bl_label = "移除所有顶点组"
    bl_description = "移除当前选中obj的所有顶点组"

    def execute(self, context):
        if len(bpy.context.selected_objects) == 0:
            self.report({'ERROR'}, "没有选中的对象！")
            return {'CANCELLED'}
        
        for obj in bpy.context.selected_objects:
            VertexGroupUtils.remove_all_vertex_groups(obj)
        self.report({'INFO'}, "移除所有顶点组成功!")
        return {'FINISHED'}



class RemoveUnusedVertexGroupOperator(bpy.types.Operator):
    bl_idname = "object.remove_unused_vertex_group"
    bl_label = "移除未使用的空顶点组"
    bl_description = "移除当前选中obj的所有空顶点组，也就是移除未使用的顶点组"

    def execute(self, context):
        if len(bpy.context.selected_objects) == 0:
            self.report({'ERROR'}, "没有选中的对象！")
            return {'CANCELLED'}
        
        # Original design from https://blenderartists.org/t/batch-delete-vertex-groups-script/449881/23
        for obj in bpy.context.selected_objects:
            VertexGroupUtils.remove_unused_vertex_groups(obj)
        self.report({'INFO'}, "移除未使用的空顶点组成功!")
        return {'FINISHED'}
    

class MergeVertexGroupsWithSameNumber(bpy.types.Operator):
    bl_idname = "object.merge_vertex_group_with_same_number"
    bl_label = "合并具有相同数字前缀名称的顶点组"
    bl_description = "把当前选中obj的所有数字前缀名称相同的顶点组进行合并"

    def execute(self, context):
        if len(bpy.context.selected_objects) == 0:
            self.report({'ERROR'}, "没有选中的对象！")
            return {'CANCELLED'}
        VertexGroupUtils.merge_vertex_groups_with_same_number()
        self.report({'INFO'}, self.bl_label + " 成功!")
        return {'FINISHED'}

class FillVertexGroupGaps(bpy.types.Operator):
    bl_idname = "object.fill_vertex_group_gaps"
    bl_label = "填充数字顶点组的间隙"
    bl_description = "把当前选中obj的所有数字顶点组的间隙用数字命名的空顶点组填补上，比如有顶点组1,2,5,8则填补后得到1,2,3,4,5,6,7,8"

    def execute(self, context):
        if len(bpy.context.selected_objects) == 0:
            self.report({'ERROR'}, "没有选中的对象！")
            return {'CANCELLED'}
        VertexGroupUtils.fill_vertex_group_gaps()
        self.report({'INFO'}, self.bl_label + " 成功!")
        return {'FINISHED'}
    

class AddBoneFromVertexGroupV2(bpy.types.Operator):
    bl_idname = "object.add_bone_from_vertex_group_v2"
    bl_label = "根据顶点组生成基础骨骼"
    bl_description = "把当前选中的obj的每个顶点组都生成一个默认位置的骨骼，方便接下来手动调整骨骼位置和父级关系来绑骨，虹汐哥改进版本"
    def execute(self, context):
        if len(bpy.context.selected_objects) == 0:
            self.report({'ERROR'}, "没有选中的对象！")
            return {'CANCELLED'}
        VertexGroupUtils.create_armature_from_vertex_groups()
        self.report({'INFO'}, self.bl_label + " 成功!")
        return {'FINISHED'}


class RemoveNotNumberVertexGroup(bpy.types.Operator):
    bl_idname = "object.remove_not_number_vertex_group"
    bl_label = "移除非数字名称的顶点组"
    bl_description = "把当前选中的obj的所有不是纯数字命名的顶点组都移除"

    def execute(self, context):
        if len(bpy.context.selected_objects) == 0:
            self.report({'ERROR'}, "没有选中的对象！")
            return {'CANCELLED'}
        
        for obj in bpy.context.selected_objects:
            VertexGroupUtils.remove_not_number_vertex_groups(obj)
        
        self.report({'INFO'}, self.bl_label + " 成功!")
        return {'FINISHED'}
    

class SplitMeshByCommonVertexGroup(bpy.types.Operator):
    bl_idname = "object.split_mesh_by_common_vertex_group"
    bl_label = "根据顶点组将模型打碎为松散块儿"
    bl_description = "把当前选中的obj按顶点组进行分割，适用于部分精细刷权重并重新组合模型的场景"
    
    def execute(self, context):
        for obj in bpy.context.selected_objects:
            VertexGroupUtils.split_mesh_by_vertex_group(obj)
        self.report({'INFO'}, self.bl_label + " 成功!")
        return {'FINISHED'}
    


class MMTResetRotation(bpy.types.Operator):
    bl_idname = "object.mmt_reset_rotation"
    bl_label = "重置模型x,y,z的旋转角度为0"
    bl_description = "把当前选中的obj的x,y,z的旋转角度全部归0"
    
    def execute(self, context):
        for obj in bpy.context.selected_objects:
            ObjUtils.reset_obj_rotation(obj=obj)

        self.report({'INFO'}, self.bl_label + " 成功!")
        return {'FINISHED'}

class SmoothNormalSaveToUV(bpy.types.Operator):
    bl_idname = "object.smooth_normal_save_to_uv"
    bl_label = "平滑法线存UV(近似)"
    bl_description = "平滑法线存UV算法，可用于修复ZZZ,WuWa的某些UV(只是近似实现60%的效果)" 

    def execute(self, context):
        SmoothNormal.smooth_normal_save_to_uv()
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

class ModelResetLocation(bpy.types.Operator):
    bl_idname = "herta.model_reset_location"
    bl_label = "重置模型在x,y,z轴上的位置为0"
    bl_description = "把当前选中的obj的x,y,z轴上的位置全部重置为0，使模型回到坐标原点"
    
    def execute(self, context):
        for obj in bpy.context.selected_objects:
            ObjUtils.reset_obj_location(obj=obj)

        self.report({'INFO'}, self.bl_label + " 成功!")
        return {'FINISHED'}
    
class ModelSortVertexGroupByName(bpy.types.Operator):
    bl_idname = "object.sort_vertex_group_by_name"
    bl_label = "根据顶点组名称对顶点组进行排序"
    bl_description = "和Blender顶点组权重那里自带的Sort=>By Name功能一样，放在这里方便快速调用"
    def execute(self, context):
        if len(bpy.context.selected_objects) == 0:
            self.report({'ERROR'}, "没有选中的对象！")
            return {'CANCELLED'}
        
        # for obj in bpy.context.selected_objects:
        bpy.ops.object.vertex_group_sort(sort_type='NAME')
        
        self.report({'INFO'}, self.bl_label + " 成功!")
        return {'FINISHED'}
    
class ModelVertexGroupRenameByLocation(bpy.types.Operator):
    bl_idname = "herta.vertex_group_rename_by_location"
    bl_label = "将目标obj的顶点组按位置对应关系改名"
    bl_description = "先选中一个源obj，再选中一个目标obj，再点击此按钮，会根据顶点组对应位置把目标obj的顶点组改名为源obj的顶点组名称，目标obj的顶点组中，和源obj顶点组位置相近的顶点组将被改名为源obj对应位置的顶点组的名称，未能识别的顶点组将被命名为unknown"

    def execute(self, context):
        if len(bpy.context.selected_objects) < 2:
            self.report({'ERROR'}, "选中的obj数量不足!请先选中源obj，再选中目标obj，一般目标obj就是你自己的模型，源obj就是游戏源模型")
            return {'CANCELLED'}
        
        active_obj = bpy.context.view_layer.objects.active
        selected_objs = bpy.context.selected_objects

        # 判断哪个是后选的（即激活对象）
        if active_obj in selected_objs:
            target_obj = active_obj
            source_obj = [obj for obj in selected_objs if obj != target_obj][0]
        
        VertexGroupUtils.match_vertex_groups(target_obj, source_obj)
        self.report({'INFO'}, self.bl_label + " 成功!")

        return {'FINISHED'}
    

class ExtractSubmeshOperator(bpy.types.Operator):
    bl_idname = "mesh.extract_submesh"
    bl_label = "Split By DrawIndexed"
    bl_options = {'REGISTER', 'UNDO'}

    start_index: bpy.props.IntProperty(
        name="Start Index",
        description="Starting index in the index buffer",
        default=0,
        min=0
    ) # type: ignore

    index_count: bpy.props.IntProperty(
        name="Index Count",
        description="Number of indices to include (must be multiple of 3)",
        default=3,
        min=3
    ) # type: ignore

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}

        # 原始网格数据
        original_mesh = obj.data
        original_mesh.calc_loop_triangles()
        # original_mesh.calc_normals_split()

        # 获取顶点索引数据
        loop_count = len(original_mesh.loops)
        orig_indices = numpy.zeros(loop_count, dtype=numpy.int32)
        original_mesh.loops.foreach_get('vertex_index', orig_indices)

        start = self.start_index
        count = self.index_count
        end_index = start + count - 1

        # 输入验证
        if start + count > loop_count:
            self.report({'ERROR'}, "Index range exceeds buffer")
            return {'CANCELLED'}
        if count % 3 != 0:
            self.report({'ERROR'}, "Index count must be multiple of 3")
            return {'CANCELLED'}

        # 提取子集索引
        subset_indices = orig_indices[start:start+count]

        # 创建唯一顶点映射
        unique_verts, inverse = numpy.unique(subset_indices, return_inverse=True)
        
        # 创建新网格
        new_mesh = bpy.data.meshes.new(f"Submesh_{start}_{end_index}")
        new_mesh.from_pydata(
            [original_mesh.vertices[i].co for i in unique_verts],
            [],
            []
        )

        # 使用BMesh构建几何
        bm = bmesh.new()
        bm.from_mesh(new_mesh)
        bm.verts.ensure_lookup_table()

        # 添加面
        for i in range(0, count, 3):
            try:
                face_verts = [bm.verts[inverse[i+j]] for j in range(3)]
                bm.faces.new(face_verts)
            except:
                pass

        # 传输网格数据
        bm.to_mesh(new_mesh)
        bm.free()

        # 复制法线数据
        loop_normals = [original_mesh.loops[start+i].normal for i in range(count)]
        # new_mesh.use_auto_smooth = True
        new_mesh.normals_split_custom_set(loop_normals)
        new_mesh.update()

        # 复制UV数据
        if original_mesh.uv_layers:
            uv_data = original_mesh.uv_layers.active.data
            new_uv = new_mesh.uv_layers.new(name="UVMap")
            for i in range(count):
                new_uv.data[i].uv = uv_data[start+i].uv

        # 创建集合
        collection_name = f"Mesh_{start}_{end_index}"
        collection = bpy.data.collections.get(collection_name) or \
                     bpy.data.collections.new(collection_name)
        
        if not collection.users:
            context.scene.collection.children.link(collection)

        # 创建新对象
        new_obj = bpy.data.objects.new(new_mesh.name, new_mesh)
        new_obj.matrix_world = obj.matrix_world  # 保持变换矩阵
        
        # 添加到集合
        for coll in new_obj.users_collection:
            coll.objects.unlink(new_obj)
        collection.objects.link(new_obj)

        context.view_layer.objects.active = new_obj
        new_obj.select_set(True)

        return {'FINISHED'}
    

class PanelModelProcess(bpy.types.Panel):
    '''
    在这里放一份的意义是萌新根本不知道右键菜单能触发这些功能，萌新的话如果你不给他送到嘴边，他是不会吃的。
    所以面板里放一份方便萌新使用，当然默认是关闭状态也不影响视觉，萌新用的多了成为大佬之后就会用右键菜单里的选项了。
    '''
    bl_label = "模型处理面板" 
    bl_idname = "VIEW3D_PT_Herta_ModelProcess_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Herta'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.operator(ModelResetLocation.bl_idname)
        layout.operator(MMTResetRotation.bl_idname)
        layout.operator(ModelDeleteLoosePoint.bl_idname)
        layout.separator()



        layout.operator(RemoveAllVertexGroupOperator.bl_idname)
        layout.operator(RemoveUnusedVertexGroupOperator.bl_idname)
        layout.operator(RemoveNotNumberVertexGroup.bl_idname)
        layout.separator()

        layout.operator(ModelSortVertexGroupByName.bl_idname)
        layout.operator(FillVertexGroupGaps.bl_idname)
        layout.operator(MergeVertexGroupsWithSameNumber.bl_idname)
        layout.operator(ModelVertexGroupRenameByLocation.bl_idname)
        layout.separator()

        layout.operator(ModelRenameVertexGroupNameWithTheirSuffix.bl_idname)
        layout.operator(AddBoneFromVertexGroupV2.bl_idname)
        layout.separator()

        layout.operator(WWMI_ApplyModifierForObjectWithShapeKeysOperator.bl_idname)
        layout.operator(SmoothNormalSaveToUV.bl_idname)
        layout.operator(RenameAmatureFromGame.bl_idname)
        layout.separator()
        
        layout.operator(RecalculateTANGENTWithVectorNormalizedNormal.bl_idname)
        layout.operator(RecalculateCOLORWithVectorNormalizedNormal.bl_idname)

class PanelModelSplit(bpy.types.Panel):
    '''
    由于功能特别多，所以按照使用类型对模型分割单独划分出一块儿面板使用
    '''
    bl_label = "模型分割" 
    bl_idname = "VIEW3D_PT_Herta_ModelSplit_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Herta'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        layout.operator(ModelSplitByLoosePart.bl_idname)
        layout.operator(SplitMeshByCommonVertexGroup.bl_idname)
        layout.operator(ModelSplitByVertexGroup.bl_idname)
        layout.separator()

        scene = context.scene

        layout.prop(scene, "submesh_start")
        layout.prop(scene, "submesh_count")
        
        op = layout.operator("mesh.extract_submesh")
        op.start_index = scene.submesh_start
        op.index_count = scene.submesh_count


class CatterRightClickMenu(bpy.types.Menu):
    '''
    光在Herta面板上放着也不行，因为部分用户的插件数量特别多的时候根本看不到Herta面板
    所以在右键的3Dmigoto菜单中也放上一份，这样方便查找。
    '''
    bl_idname = "VIEW3D_MT_object_3Dmigoto"
    bl_label = "3Dmigoto"
    bl_description = "适用于3Dmigoto Mod制作的常用功能"
    
    def draw(self, context):
        layout = self.layout
        layout.operator(ModelResetLocation.bl_idname)
        layout.operator(MMTResetRotation.bl_idname)
        layout.operator(ModelDeleteLoosePoint.bl_idname)
        layout.separator()

        layout.operator(ModelSplitByLoosePart.bl_idname)
        layout.operator(SplitMeshByCommonVertexGroup.bl_idname)
        layout.operator(ModelSplitByVertexGroup.bl_idname)
        layout.separator()

        layout.operator(RemoveAllVertexGroupOperator.bl_idname)
        layout.operator(RemoveUnusedVertexGroupOperator.bl_idname)
        layout.operator(RemoveNotNumberVertexGroup.bl_idname)
        layout.separator()

        layout.operator(ModelSortVertexGroupByName.bl_idname)
        layout.operator(FillVertexGroupGaps.bl_idname)
        layout.operator(MergeVertexGroupsWithSameNumber.bl_idname)
        layout.operator(ModelVertexGroupRenameByLocation.bl_idname)
        layout.separator()

        layout.operator(ModelRenameVertexGroupNameWithTheirSuffix.bl_idname)
        layout.operator(AddBoneFromVertexGroupV2.bl_idname)
        layout.separator()


        layout.operator(WWMI_ApplyModifierForObjectWithShapeKeysOperator.bl_idname)
        layout.operator(SmoothNormalSaveToUV.bl_idname)
        
        layout.operator(RenameAmatureFromGame.bl_idname)
        layout.separator()
        layout.operator(RecalculateTANGENTWithVectorNormalizedNormal.bl_idname)
        layout.operator(RecalculateCOLORWithVectorNormalizedNormal.bl_idname)
        


def menu_func_migoto_right_click(self, context):
    self.layout.separator()
    self.layout.menu(CatterRightClickMenu.bl_idname)