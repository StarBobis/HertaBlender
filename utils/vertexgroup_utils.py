import bpy
import itertools

from mathutils import Vector,Matrix

from ..utils.migoto_utils import Fatal


class VertexGroupUtils:
    @classmethod
    def remove_unused_vertex_groups(cls,obj):
        '''
        移除给定obj的未使用的顶点组
        '''
        if obj.type == "MESH":
            # obj = bpy.context.active_object
            obj.update_from_editmode()
            vgroup_used = {i: False for i, k in enumerate(obj.vertex_groups)}

            for v in obj.data.vertices:
                for g in v.groups:
                    if g.weight > 0.0:
                        vgroup_used[g.group] = True

            for i, used in sorted(vgroup_used.items(), reverse=True):
                if not used:
                    obj.vertex_groups.remove(obj.vertex_groups[i])

    @classmethod
    def remove_all_vertex_groups(cls,obj):
        '''
        移除给定obj的未使用的顶点组
        '''
        if obj.type == "MESH":
            for x in obj.vertex_groups:
                obj.vertex_groups.remove(x)

    @classmethod
    def merge_vertex_groups_with_same_number(cls):
        # Author: SilentNightSound#7430
        # Combines vertex groups with the same prefix into one, a fast alternative to the Vertex Weight Mix that works for multiple groups
        # You will likely want to use blender_fill_vg_gaps.txt after this to fill in any gaps caused by merging groups together
        # Nico: we only need mode 3 here.

        selected_obj = [obj for obj in bpy.context.selected_objects]
        vgroup_names = []

        ##### USAGE INSTRUCTIONS
        # MODE 1: Runs the merge on a specific list of vertex groups in the selected object(s). Can add more names or fewer to the list - change the names to what you need
        # MODE 2: Runs the merge on a range of vertex groups in the selected object(s). Replace smallest_group_number with the lower bound, and largest_group_number with the upper bound
        # MODE 3 (DEFAULT): Runs the merge on ALL vertex groups in the selected object(s)

        # Select the mode you want to run:
        mode = 3

        # Required data for MODE 1:
        vertex_groups = ["replace_with_first_vertex_group_name", "second_vertex_group_name", "third_name_etc"]

        # Required data for MODE 2:
        smallest_group_number = 000
        largest_group_number = 999

        ######

        if mode == 1:
            vgroup_names = [vertex_groups]
        elif mode == 2:
            vgroup_names = [[f"{i}" for i in range(smallest_group_number, largest_group_number + 1)]]
        elif mode == 3:
            vgroup_names = [[x.name.split(".")[0] for x in y.vertex_groups] for y in selected_obj]
        else:
            raise Fatal("Mode not recognized, exiting")

        if not vgroup_names:
            raise Fatal(
                "No vertex groups found, please double check an object is selected and required data has been entered")

        for cur_obj, cur_vgroup in zip(selected_obj, itertools.cycle(vgroup_names)):
            for vname in cur_vgroup:
                relevant = [x.name for x in cur_obj.vertex_groups if x.name.split(".")[0] == f"{vname}"]

                if relevant:

                    vgroup = cur_obj.vertex_groups.new(name=f"x{vname}")

                    for vert_id, vert in enumerate(cur_obj.data.vertices):
                        available_groups = [v_group_elem.group for v_group_elem in vert.groups]

                        combined = 0
                        for v in relevant:
                            if cur_obj.vertex_groups[v].index in available_groups:
                                combined += cur_obj.vertex_groups[v].weight(vert_id)

                        if combined > 0:
                            vgroup.add([vert_id], combined, 'ADD')

                    for vg in [x for x in cur_obj.vertex_groups if x.name.split(".")[0] == f"{vname}"]:
                        cur_obj.vertex_groups.remove(vg)

                    for vg in cur_obj.vertex_groups:
                        if vg.name[0].lower() == "x":
                            vg.name = vg.name[1:]

            bpy.context.view_layer.objects.active = cur_obj
            bpy.ops.object.vertex_group_sort()


    @classmethod
    def fill_vertex_group_gaps(cls):
        # Author: SilentNightSound#7430
        # Fills in missing vertex groups for a model so there are no gaps, and sorts to make sure everything is in order
        # Works on the currently selected object
        # e.g. if the selected model has groups 0 1 4 5 7 2 it adds an empty group for 3 and 6 and sorts to make it 0 1 2 3 4 5 6 7
        # Very useful to make sure there are no gaps or out-of-order vertex groups

        # Can change this to another number in order to generate missing groups up to that number
        # e.g. setting this to 130 will create 0,1,2...130 even if the active selected object only has 90
        # Otherwise, it will use the largest found group number and generate everything up to that number
        largest = 0

        ob = bpy.context.active_object
        ob.update_from_editmode()

        for vg in ob.vertex_groups:
            try:
                if int(vg.name.split(".")[0]) > largest:
                    largest = int(vg.name.split(".")[0])
            except ValueError:
                print("Vertex group not named as integer, skipping")

        missing = set([f"{i}" for i in range(largest + 1)]) - set([x.name.split(".")[0] for x in ob.vertex_groups])
        for number in missing:
            ob.vertex_groups.new(name=f"{number}")

        bpy.ops.object.vertex_group_sort()


    # 由虹汐哥改进的版本，骨骼位置放到了几何中心
    @classmethod
    def create_armature_from_vertex_groups(cls,bone_length=0.1):
        # 验证选择对象
        obj = bpy.context.active_object
        if not obj or obj.type != 'MESH':
            raise Exception("请先选择一个网格物体")
        
        if not obj.vertex_groups:
            raise Exception("目标物体没有顶点组")

        # 预计算世界变换矩阵
        matrix = obj.matrix_world

        # 创建骨架物体
        armature = bpy.data.armatures.new("AutoRig_Armature")
        armature_obj = bpy.data.objects.new("AutoRig", armature)
        bpy.context.scene.collection.objects.link(armature_obj)

        # 设置活动对象
        bpy.context.view_layer.objects.active = armature_obj
        armature_obj.select_set(True)

        # 预收集顶点组数据 {顶点组索引: [顶点列表]}
        vg_verts = {vg.index: [] for vg in obj.vertex_groups}
        for v in obj.data.vertices:
            for g in v.groups:
                if g.group in vg_verts:
                    vg_verts[g.group].append(v)

        # 进入编辑模式创建骨骼
        bpy.ops.object.mode_set(mode='EDIT')
        try:
            for vg in obj.vertex_groups:
                verts = vg_verts.get(vg.index)
                if not verts:
                    continue

                # 计算几何中心（世界坐标）
                coords = [matrix @ v.co for v in verts]
                center = sum(coords, Vector()) / len(coords)

                # 创建垂直方向骨骼
                bone = armature.edit_bones.new(vg.name)
                bone.head = center
                bone.tail = center + Vector((0, 0, 0.1))  # 固定Z轴方向

        finally:
            bpy.ops.object.mode_set(mode='OBJECT')

    @classmethod
    def remove_not_number_vertex_groups(cls,obj):
        for vg in reversed(obj.vertex_groups):
            if vg.name.isdecimal():
                continue
            # print('Removing vertex group', vg.name)
            obj.vertex_groups.remove(vg)

    @classmethod
    def split_mesh_by_vertex_group(cls,obj):
        '''
        Code copied and modified from @Kail_Nethunter, very useful in some special meets.
        https://blenderartists.org/t/split-a-mesh-by-vertex-groups/438990/11
        '''
        origin_name = obj.name
        keys = obj.vertex_groups.keys()
        real_keys = []
        for gr in keys:
            bpy.ops.object.mode_set(mode="EDIT")
            # Set the vertex group as active
            bpy.ops.object.vertex_group_set_active(group=gr)

            # Deselect all verts and select only current VG
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.vertex_group_select()
            # bpy.ops.mesh.select_all(action='INVERT')
            try:
                bpy.ops.mesh.separate(type="SELECTED")
                real_keys.append(gr)
            except:
                pass
        for i in range(1, len(real_keys) + 1):
            bpy.data.objects['{}.{:03d}'.format(origin_name, i)].name = '{}.{}'.format(
                origin_name, real_keys[i - 1])
            
    @classmethod
    def get_vertex_group_weight(cls,vgroup, vertex):
        '''
        Credit to @Comilarex
        https://gamebanana.com/tools/19057
        '''
        for group in vertex.groups:
            if group.group == vgroup.index:
                return group.weight
        return 0.0

    @classmethod
    def calculate_vertex_influence_area(cls,obj):
        '''
        Credit to @Comilarex
        https://gamebanana.com/tools/19057
        '''
        vertex_area = [0.0] * len(obj.data.vertices)
        
        for face in obj.data.polygons:
            # Assuming the area is evenly distributed among the vertices
            area_per_vertex = face.area / len(face.vertices)
            for vert_idx in face.vertices:
                vertex_area[vert_idx] += area_per_vertex

        return vertex_area

    @classmethod
    def get_weighted_center(cls, obj, vgroup):
        '''
        Credit to @Comilarex
        https://gamebanana.com/tools/19057
        '''
        total_weight_area = 0.0
        weighted_position_sum = Vector((0.0, 0.0, 0.0))

        # Calculate the area influenced by each vertex
        vertex_influence_area = cls.calculate_vertex_influence_area(obj)

        for vertex in obj.data.vertices:
            weight = cls.get_vertex_group_weight(vgroup, vertex)
            influence_area = vertex_influence_area[vertex.index]
            weight_area = weight * influence_area

            if weight_area > 0:
                weighted_position_sum += obj.matrix_world @ vertex.co * weight_area
                total_weight_area += weight_area

        if total_weight_area > 0:
            return weighted_position_sum / total_weight_area
        else:
            return None

    @classmethod
    def match_vertex_groups(cls, base_obj, target_obj):
        '''
        Credit to @Comilarex
        https://gamebanana.com/tools/19057
        '''
        # Rename all vertex groups in base_obj to "unknown"
        for base_group in base_obj.vertex_groups:
            base_group.name = "unknown"

        # Precompute centers for all target vertex groups
        target_centers = {}
        for target_group in target_obj.vertex_groups:
            target_centers[target_group.name] = cls.get_weighted_center(target_obj, target_group)

        # Perform the matching and renaming process
        for base_group in base_obj.vertex_groups:
            base_center = cls.get_weighted_center(base_obj, base_group)
            if base_center is None:
                continue

            best_match = None
            best_distance = float('inf')

            for target_group_name, target_center in target_centers.items():
                if target_center is None:
                    continue

                distance = (base_center - target_center).length
                if distance < best_distance:
                    best_distance = distance
                    best_match = target_group_name

            if best_match:
                base_group.name = best_match

