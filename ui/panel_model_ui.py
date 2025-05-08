import bpy

from ..utils.obj_utils import ObjUtils
from ..utils.collection_utils import CollectionUtils
from ..utils.vertexgroup_utils import VertexGroupUtils


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


class PanelModelProcess(bpy.types.Panel):
    bl_label = "模型处理面板" 
    bl_idname = "VIEW3D_PT_Herta_ModelProcess_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Herta'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
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

        layout.operator(FillVertexGroupGaps.bl_idname)
        layout.operator(MergeVertexGroupsWithSameNumber.bl_idname)
        layout.separator()

        layout.operator(ModelRenameVertexGroupNameWithTheirSuffix.bl_idname)
        layout.operator(AddBoneFromVertexGroupV2.bl_idname)

        


        