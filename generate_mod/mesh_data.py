import numpy
import bpy


class MeshData:
    '''
    MeshClass用于抽象每一个obj的mesh对象中的数据，加快导出速度。
    '''
    
    def __init__(self,mesh:bpy.types.Mesh) -> None:
        self.mesh = mesh
        
    def get_blendweights_blendindices_v2(self):
        '''
        升级版，支持多个SemanticIndex的BLENDWEIGHTS和BLENDINDICES
        '''
        mesh_loops = self.mesh.loops
        mesh_loops_length = len(mesh_loops)
        mesh_vertices = self.mesh.vertices
        
        loop_vertex_indices = numpy.empty(mesh_loops_length, dtype=int)
        mesh_loops.foreach_get("vertex_index", loop_vertex_indices)
        
        # 计算每个顶点的最大组数（向上取整到最近的4的倍数）
        max_groups_per_vertex = 0
        for v in mesh_vertices:
            group_count = len(v.groups)
            if group_count > max_groups_per_vertex:
                max_groups_per_vertex = group_count
        
        # 将最大组数对齐到4的倍数（每个语义索引包含4个权重）
        max_groups_per_vertex = ((max_groups_per_vertex + 3) // 4) * 4
        num_semantics = max_groups_per_vertex // 4  # 需要的语义索引数量
        
        # 为每个顶点存储所有组和权重（填充0）
        all_groups = numpy.zeros((len(mesh_vertices), max_groups_per_vertex), dtype=int)
        
        all_weights = numpy.zeros((len(mesh_vertices), max_groups_per_vertex), dtype=numpy.float32)
        
        # 填充权重和组数据
        for v_index, v in enumerate(mesh_vertices):
            groups = sorted(v.groups, key=lambda x: x.weight, reverse=True)
            
            # 提取权重并规格化
            weights = numpy.array([g.weight for g in groups], dtype=numpy.float32)

            # 这个归一化，我测试了，细分之后不管是否归一化都对最终效果没有影响
            # 所以这个代码实际上没啥用，但是仍然保留以防万一。
            # if len(weights) > 0:
            #     total_weight = numpy.sum(weights)
            #     if total_weight > 0:
            #         weights = weights / total_weight
            
            # 填充到数组中
            num_groups = min(len(groups), max_groups_per_vertex)
            all_groups[v_index, :num_groups] = [g.group for g in groups][:num_groups]
            all_weights[v_index, :num_groups] = weights[:num_groups]
        
        # 创建存储多个BLENDWEIGHTS/BLENDINDICES的字典
        blendweights_dict = {}
        blendindices_dict = {}
        
        # 为每个语义索引创建数据
        for semantic_index in range(num_semantics):
            start_idx = semantic_index * 4
            end_idx = start_idx + 4
            
            # 初始化loop级别的数组
            loop_blendweights = numpy.zeros((mesh_loops_length, 4), dtype=numpy.float32)
            # loop_blendweights = numpy.full((mesh_loops_length, 4), -1, dtype=int)


            loop_blendindices = numpy.zeros((mesh_loops_length, 4), dtype=numpy.uint32)
            
            # 映射顶点数据到loop
            valid_mask = (loop_vertex_indices >= 0) & (loop_vertex_indices < len(mesh_vertices))
            valid_indices = loop_vertex_indices[valid_mask]
            
            if len(valid_indices) > 0:
                # 获取当前语义索引对应的4个权重/组
                weights_slice = all_weights[valid_indices, start_idx:end_idx]
                groups_slice = all_groups[valid_indices, start_idx:end_idx]
                
                # 填充到loop数组
                loop_blendweights[valid_mask] = weights_slice
                loop_blendindices[valid_mask] = groups_slice
            
            # 存储到字典
            blendweights_dict[semantic_index] = loop_blendweights
            blendindices_dict[semantic_index] = loop_blendindices
        
        return blendweights_dict, blendindices_dict
