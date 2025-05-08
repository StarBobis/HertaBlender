import bpy

from ..utils.obj_utils import ObjUtils
from ..utils.collection_utils import CollectionUtils
from ..utils.vertexgroup_utils import VertexGroupUtils




class ModelSplitByLoosePart(bpy.types.Operator):
    bl_idname = "panel_model.split_by_loose_part"
    bl_label = "根据松散块儿分割模型(测试用)"
    bl_description = "功能与Edit界面的Split => Split by Loose Parts相同，分割模型为松散块儿并放入新集合。"

    def execute(self, context):
        
        if len(bpy.context.selected_objects) == 0:
            self.report({'ERROR'}, "没有选中的对象！")
            return {'CANCELLED'}
        obj = bpy.context.selected_objects[0]
        # 创建一个新的集合，以原对象名命名
        collection_name = f"{obj.name}_LooseParts"
        ObjUtils.split_obj_by_loose_parts_to_collection(obj=obj,collection_name=collection_name)
        return {'FINISHED'}




class ModelMergeBySameVertexGroup(bpy.types.Operator):
    bl_idname = "panel_model.merge_by_same_vertex_group"
    bl_label = "根据相同顶点组合并模型(测试用)"
    bl_description = "一般用于按松散块儿分割后的模型的集合，选中集合执行此方法，然后就能按照是否共享相同的顶点组来合并"

    def execute(self, context):

        # 获取当前选中的集合
        collection = bpy.context.collection

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
        print(number_vgnameset_dict.keys())
        print("======================================")
        for number in number_vgnameset_dict.keys():
            print(number_vgnameset_dict[number])
        print("======================================")
        for number, objlist in number_objlist_dict.items():
            print("Number: " + str(number) + " ObjList: " + str(objlist))
            print("---")

        # 到这里就可以合并obj了
        for number, objlist in number_objlist_dict.items():
            ObjUtils.merge_objects(obj_list=objlist)
        return {'FINISHED'}
    

class ModelSplitByVertexGroup(bpy.types.Operator):
    bl_idname = "panel_model.split_by_vertex_group"
    bl_label = "根据顶点组分割模型"
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
        print(number_vgnameset_dict.keys())
        print("======================================")
        for number in number_vgnameset_dict.keys():
            print(number_vgnameset_dict[number])
        print("======================================")
        for number, objlist in number_objlist_dict.items():
            print("Number: " + str(number) + " ObjList: " + str(objlist))
            print("---")

        # 到这里就可以合并obj了
        for number, objlist in number_objlist_dict.items():
            ObjUtils.merge_objects(obj_list=objlist,target_collection=collection)
        
        return {'FINISHED'}
    

class PanelModelProcess(bpy.types.Panel):
    bl_label = "模型处理面板" 
    bl_idname = "VIEW3D_PT_Herta_ModelProcess_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Herta'
    

    def draw(self, context):
        layout = self.layout

        layout.operator("panel_model.split_by_loose_part")
        # layout.operator("panel_model.merge_by_same_vertex_group")
        layout.operator("panel_model.split_by_vertex_group")


        