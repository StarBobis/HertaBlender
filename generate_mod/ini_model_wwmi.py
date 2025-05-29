import shutil

from .m_ini_builder import *
from .m_drawib_model_wwmi import DrawIBModelWWMI
from ..config.main_config import GlobalConfig
from .m_ini_helper import M_IniHelper
from ..properties.properties_wwmi import Properties_WWMI
from ..properties.properties_generate_mod import Properties_GenerateMod
from ..utils.collection_utils import ModelCollection


class M_WWMIIniModel:
    '''
    WWMI专用
    '''
    drawib_drawibmodel_dict:dict[str,DrawIBModelWWMI] = {}
    shapekeys = {}

    global_key_index_constants = 0
    global_key_index_logic = 0
    global_generate_mod_number = 0


    # for texture filter_index function.
    texture_hash_filter_index_dict = {}


    @classmethod
    def initialzie(cls):
        '''
        You have to call this to clean cache data before generate mod.
        '''
        cls.drawib_drawibmodel_dict = {}
        cls.shapekeys = {}
        
        cls.global_key_index_constants = 0
        cls.global_key_index_logic = 0
        cls.global_generate_mod_number = 0

        cls.texture_hash_filter_index_dict = {}


    @classmethod
    def add_constants_section(cls,ini_builder:M_IniBuilder,draw_ib_model:DrawIBModelWWMI):
        constants_section = M_IniSection(M_SectionType.Constants)
        constants_section.append("[Constants]")
        constants_section.append("global $required_wwmi_version = 0.70")

        # object_guid值为原模型的总的index_count 在metadata.json中有记录
        constants_section.append("global $object_guid = " + str(draw_ib_model.extracted_object.index_count))
        # 导出模型的总顶点数
        constants_section.append("global $mesh_vertex_count = " + str(draw_ib_model.draw_number))

        # 哦，总算搞明白了，WWMI的代码中的注释也有问题，它说的Number of shapekeyed vertices in custom model原来不是字面意思，而是指的是shapekey_vertex_id的数量。
        # 因为这玩意是用来改变Shapekey的UAV的大小的
        constants_section.append("global $shapekey_vertex_count = " + str(len(draw_ib_model.shapekey_vertex_ids)))

        # WWMI中每个mod的mod_id都是-1000，暂时不知道是为了什么，难道是保留设计？不管了，为保证兼容性，暂时先留着
        constants_section.append("global $mod_id = -1000")

        # 只有Merged顶点组才需要用到$state_id
        if Properties_WWMI.import_merged_vgmap():
            constants_section.append("global $state_id = 0")

        constants_section.append("global $mod_enabled = 0")

        constants_section.append("global $object_detected = 0")

        constants_section.new_line()

        ini_builder.append_section(constants_section)
    
    @classmethod
    def add_present_section(cls,ini_builder:M_IniBuilder,draw_ib_model:DrawIBModelWWMI):
        present_section = M_IniSection(M_SectionType.Present)
        present_section.append("[Present]")

        present_section.append("if $object_detected")
        present_section.append("  if $mod_enabled")
        present_section.append("    post $object_detected = 0")

        # 只有Merged顶点组需要运行UpdateMergedSkeleton
        if Properties_WWMI.import_merged_vgmap():
            present_section.append("    run = CommandListUpdateMergedSkeleton")

        present_section.append("  else")
        present_section.append("    if $mod_id == -1000")
        present_section.append("      run = CommandListRegisterMod")
        present_section.append("    endif")
        present_section.append("  endif")
        present_section.append("endif")
        present_section.new_line()

        ini_builder.append_section(present_section)

    @classmethod
    def add_commandlist_section(cls,ini_builder:M_IniBuilder,draw_ib_model:DrawIBModelWWMI):
        commandlist_section = M_IniSection(M_SectionType.CommandList)

        # CommandListRegisterMod
        commandlist_section.append("[CommandListRegisterMod]")
        commandlist_section.append("$\\WWMIv1\\required_wwmi_version = $required_wwmi_version")
        commandlist_section.append("$\\WWMIv1\\object_guid = $object_guid")
        commandlist_section.append("Resource\\WWMIv1\\ModName = ref ResourceModName")
        commandlist_section.append("Resource\\WWMIv1\\ModAuthor = ref ResourceModAuthor")
        commandlist_section.append("Resource\\WWMIv1\\ModDesc = ref ResourceModDesc")
        commandlist_section.append("Resource\\WWMIv1\\ModLink = ref ResourceModLink")
        commandlist_section.append("Resource\\WWMIv1\\ModLogo = ref ResourceModLogo")
        commandlist_section.append("run = CommandList\\WWMIv1\\RegisterMod")
        commandlist_section.append("$mod_id = $\\WWMIv1\\mod_id")
        commandlist_section.append("if $mod_id >= 0")
        commandlist_section.append("  $mod_enabled = 1")
        commandlist_section.append("endif")
        commandlist_section.new_line()

        if Properties_WWMI.import_merged_vgmap():
        # CommandListUpdateMergedSkeleton
            commandlist_section.append("[CommandListUpdateMergedSkeleton]")
            commandlist_section.append("if $state_id")
            commandlist_section.append("  $state_id = 0")
            commandlist_section.append("else")
            commandlist_section.append("  $state_id = 1")
            commandlist_section.append("endif")
            commandlist_section.append("ResourceMergedSkeleton = copy ResourceMergedSkeletonRW")
            commandlist_section.append("ResourceExtraMergedSkeleton = copy ResourceExtraMergedSkeletonRW")
            commandlist_section.new_line()

            # CommandListMergeSkeleton
            commandlist_section.append("[CommandListMergeSkeleton]")
            commandlist_section.append("$\\WWMIv1\\custom_mesh_scale = 1.0")
            commandlist_section.append("cs-cb8 = ref vs-cb4")
            commandlist_section.append("cs-u6 = ResourceMergedSkeletonRW")
            commandlist_section.append("run = CustomShader\\WWMIv1\\SkeletonMerger")
            commandlist_section.append("cs-cb8 = ref vs-cb3")
            commandlist_section.append("cs-u6 = ResourceExtraMergedSkeletonRW")
            commandlist_section.append("run = CustomShader\\WWMIv1\\SkeletonMerger")
            commandlist_section.new_line()

        # CommandListTriggerResourceOverrides
        commandlist_section.append("[CommandListTriggerResourceOverrides]")
        commandlist_section.append("CheckTextureOverride = ps-t0")
        commandlist_section.append("CheckTextureOverride = ps-t1")
        commandlist_section.append("CheckTextureOverride = ps-t2")
        commandlist_section.append("CheckTextureOverride = ps-t3")
        commandlist_section.append("CheckTextureOverride = ps-t4")
        commandlist_section.append("CheckTextureOverride = ps-t5")
        commandlist_section.append("CheckTextureOverride = ps-t6")
        commandlist_section.append("CheckTextureOverride = ps-t7")

        # 只有Merged顶点组需要check vs-cb3和vs-cb4
        if Properties_WWMI.import_merged_vgmap():
            commandlist_section.append("CheckTextureOverride = vs-cb3")
            commandlist_section.append("CheckTextureOverride = vs-cb4")

        commandlist_section.new_line()

        # CommandListOverrideSharedResources
        # TODO 暂时先写死，后面再来改，因为要先走测试流程，测试通过再考虑灵活性以及其它数据类型的Mod的兼容问题

        commandlist_section.append("[ResourceBypassVB0]")
        commandlist_section.new_line()

        commandlist_section.append("[CommandListOverrideSharedResources]")
        commandlist_section.append("ResourceBypassVB0 = ref vb0")
        commandlist_section.append("ib = ResourceIndexBuffer")
        commandlist_section.append("vb0 = ResourcePositionBuffer")
        commandlist_section.append("vb1 = ResourceVectorBuffer")
        commandlist_section.append("vb2 = ResourceTexcoordBuffer")
        commandlist_section.append("vb3 = ResourceColorBuffer")
        commandlist_section.append("vb4 = ResourceBlendBuffer")

        if Properties_WWMI.import_merged_vgmap():
            commandlist_section.append("if vs-cb3 == 3381.7777")
            commandlist_section.append("  vs-cb3 = ResourceExtraMergedSkeleton")
            commandlist_section.append("endif")
            commandlist_section.append("if vs-cb4 == 3381.7777")
            commandlist_section.append("  vs-cb4 = ResourceMergedSkeleton")
            commandlist_section.append("endif")

        commandlist_section.new_line()

        # CommandListCleanupSharedResources
        # TODO 后续要搞清楚使用槽位恢复技术的原因是什么，以及测试0.62中不使用槽位恢复的缺点，以及0.70之后版本中使用槽位恢复的意义
        commandlist_section.append("[CommandListCleanupSharedResources]")
        commandlist_section.append("vb0 = ref ResourceBypassVB0")
        commandlist_section.new_line()

        # TODO ShapeKey的CommandList只有在ShapeKey存在时才加入，物体Mod不加入
        # CommandListSetupShapeKeys
        commandlist_section.append("[CommandListSetupShapeKeys]")
        commandlist_section.append("$\\WWMIv1\\shapekey_checksum = " + str(draw_ib_model.extracted_object.shapekeys.checksum))
        commandlist_section.append("cs-t33 = ResourceShapeKeyOffsetBuffer")
        commandlist_section.append("cs-u5 = ResourceCustomShapeKeyValuesRW")
        commandlist_section.append("cs-u6 = ResourceShapeKeyCBRW")
        commandlist_section.append("run = CustomShader\\WWMIv1\\ShapeKeyOverrider")
        commandlist_section.new_line()

        # CommandListLoadShapeKeys
        commandlist_section.append("[CommandListLoadShapeKeys]")
        commandlist_section.append("$\\WWMIv1\\shapekey_vertex_count = $shapekey_vertex_count")
        commandlist_section.append("cs-t0 = ResourceShapeKeyVertexIdBuffer")
        commandlist_section.append("cs-t1 = ResourceShapeKeyVertexOffsetBuffer")
        commandlist_section.append("cs-u6 = ResourceShapeKeyCBRW")
        commandlist_section.append("run = CustomShader\\WWMIv1\\ShapeKeyLoader")
        commandlist_section.new_line()

        # CommandListMultiplyShapeKeys
        commandlist_section.append("[CommandListMultiplyShapeKeys]")
        commandlist_section.append("$\\WWMIv1\\custom_vertex_count = $mesh_vertex_count")
        commandlist_section.append("run = CustomShader\\WWMIv1\\ShapeKeyMultiplier")
        commandlist_section.new_line()


        ini_builder.append_section(commandlist_section)

    @classmethod
    def add_resource_mod_info_section_default(cls,ini_builder:M_IniBuilder,draw_ib_model:DrawIBModelWWMI):
        '''
        这里第一个版本我们暂时不提供可以指定Mod信息的功能，所以全部都用的是默认的值
        TODO 这个可以放入M_IniHelper中
        '''
        resource_mod_info_section = M_IniSection(M_SectionType.ResourceModInfo)

        resource_mod_info_section.append("[ResourceModName]")
        resource_mod_info_section.append("type = Buffer")
        resource_mod_info_section.append("data = \"Unnamed Mod\"")
        resource_mod_info_section.new_line()

        resource_mod_info_section.append("[ResourceModAuthor]")
        resource_mod_info_section.append("type = Buffer")
        resource_mod_info_section.append("data = \"Unknown Author\"")
        resource_mod_info_section.new_line()

        resource_mod_info_section.append("[ResourceModDesc]")
        resource_mod_info_section.append("; type = Buffer")
        resource_mod_info_section.append("; data = \"Empty Mod Description\"")
        resource_mod_info_section.new_line()

        resource_mod_info_section.append("[ResourceModLink]")
        resource_mod_info_section.append("; type = Buffer")
        resource_mod_info_section.append("; data = \"Empty Mod Link\"")
        resource_mod_info_section.new_line()

        resource_mod_info_section.append("[ResourceModLogo]")
        resource_mod_info_section.append("; filename = Textures/Logo.dds")
        resource_mod_info_section.new_line()

        ini_builder.append_section(resource_mod_info_section)


    @classmethod
    def add_texture_override_mark_bone_data_cb(cls,ini_builder:M_IniBuilder,draw_ib_model:DrawIBModelWWMI):
        '''
        给VS-CB4的Hash值做一个filter_index标记
        '''
        texture_override_mark_bonedatacb_section = M_IniSection(M_SectionType.TextureOverrideGeneral)

        texture_override_mark_bonedatacb_section.append("[TextureOverrideMarkBoneDataCB]")
        texture_override_mark_bonedatacb_section.append("hash = " + draw_ib_model.extracted_object.cb4_hash)
        texture_override_mark_bonedatacb_section.append("match_priority = 0")
        texture_override_mark_bonedatacb_section.append("filter_index = 3381.7777")
        texture_override_mark_bonedatacb_section.new_line()

        ini_builder.append_section(texture_override_mark_bonedatacb_section)

    @classmethod
    def get_switchkey_drawindexed_list(cls,model_collection_list:list[ModelCollection],draw_ib_model:DrawIBModelWWMI,vlr_filter_index_indent:str,input_global_key_index_logic:int):
        '''
        生成按键开关集合喝按键切换集合的DrawIndexed以及对应注释
        是Catter集合架构的通用方法
        返回一个字符串列表和global_key_index_logic
        字符串列表需要放到对应的ini_section中，global_key_index_logic需要赋值给全局的对应变量
        '''
        drawindexed_list = []
        global_key_index_logic = input_global_key_index_logic

        toggle_type_number = 0
        toggle_model_collection_list:list[ModelCollection] = []
        switch_model_collection_list:list[ModelCollection] = []

        for toggle_model_collection in model_collection_list:
            if toggle_model_collection.type == "toggle":
                toggle_type_number = toggle_type_number + 1
                toggle_model_collection_list.append(toggle_model_collection)
            elif toggle_model_collection.type == "switch":
                switch_model_collection_list.append(toggle_model_collection)

        # 输出按键切换的DrawIndexed
        if toggle_type_number >= 2:
            for toggle_count in range(toggle_type_number):
                if toggle_count == 0:
                    drawindexed_list.append(vlr_filter_index_indent + "if $swapkey" + str(global_key_index_logic) + " == " + str(toggle_count))
                else:
                    drawindexed_list.append(vlr_filter_index_indent + "else if $swapkey" + str(global_key_index_logic) + " == " + str(toggle_count))

                toggle_model_collection = toggle_model_collection_list[toggle_count]
                for obj_name in toggle_model_collection.obj_name_list:
                    m_drawindexed = draw_ib_model.obj_name_drawindexed_dict[obj_name]
                    drawindexed_list.append(vlr_filter_index_indent + "; " + m_drawindexed.AliasName)
                    drawindexed_list.append(vlr_filter_index_indent  + m_drawindexed.get_draw_str())

            drawindexed_list.append("endif")
            drawindexed_list.append("\n")

            global_key_index_logic = global_key_index_logic + 1
        elif toggle_type_number != 0:
            for toggle_model_collection in toggle_model_collection_list:
                for obj_name in toggle_model_collection.obj_name_list:
                    m_drawindexed = draw_ib_model.obj_name_drawindexed_dict[obj_name]
                    drawindexed_list.append(vlr_filter_index_indent + "; " + m_drawindexed.AliasName)
                    drawindexed_list.append(vlr_filter_index_indent + m_drawindexed.get_draw_str())
                    drawindexed_list.append("\n")

        # 输出按键开关的DrawIndexed
        for switch_model_collection in switch_model_collection_list:
            drawindexed_list.append(vlr_filter_index_indent + "if $swapkey" + str(global_key_index_logic) + "  == 1")
            for obj_name in switch_model_collection.obj_name_list:
                m_drawindexed = draw_ib_model.obj_name_drawindexed_dict[obj_name]
                drawindexed_list.append(vlr_filter_index_indent + "; " + m_drawindexed.AliasName)
                drawindexed_list.append(vlr_filter_index_indent  + m_drawindexed.get_draw_str())
                drawindexed_list.append("\n")
            drawindexed_list.append(vlr_filter_index_indent + "endif")
            drawindexed_list.append("\n")
            global_key_index_logic = global_key_index_logic + 1
        
        return drawindexed_list, global_key_index_logic


    @classmethod
    def add_texture_override_component(cls,ini_builder:M_IniBuilder,draw_ib_model:DrawIBModelWWMI):
        texture_override_component = M_IniSection(M_SectionType.TextureOverrideIB)
        component_count = 0
        for merged_object_component in draw_ib_model.merged_object.components:
            component_name = "Component " + str(component_count + 1)
            component_count_str = str(component_count)
            component_object = draw_ib_model.extracted_object.components[component_count]
            # print(str(component_count))
            
            texture_override_component.append("[TextureOverrideComponent" + component_count_str + "]")
            texture_override_component.append("hash = " + draw_ib_model.extracted_object.vb0_hash)
            texture_override_component.append("match_first_index = " + str(component_object.index_offset))
            texture_override_component.append("match_index_count = " + str(component_object.index_count))
            texture_override_component.append("$object_detected = 1")
            texture_override_component.append("if $mod_enabled")

            if Properties_WWMI.import_merged_vgmap():
                state_id_var_str = "$state_id_" + component_count_str
                texture_override_component.append("  " + "local " + state_id_var_str)
                texture_override_component.append("  " + "if " + state_id_var_str + " != $state_id")
                texture_override_component.append("    " + state_id_var_str + " = $state_id")
                texture_override_component.append("    " + "$\\WWMIv1\\vg_offset = " + str(component_object.vg_offset))
                texture_override_component.append("    " + "$\\WWMIv1\\vg_count = " + str(component_object.vg_count))
                texture_override_component.append("    " + "run = CommandListMergeSkeleton")
                texture_override_component.append("  endif")

                texture_override_component.append("  " + "if ResourceMergedSkeleton !== null")
                texture_override_component.append("    " + "handling = skip")

                # 必须先判定这里是否有DrawIndexed才能去进行绘制以及调用CommandList
                model_collection_list = draw_ib_model.componentname_modelcollection_list_dict[component_name]
                drawindexed_list, added_global_key_index_logic = cls.get_switchkey_drawindexed_list(model_collection_list=model_collection_list, draw_ib_model=draw_ib_model,vlr_filter_index_indent="",input_global_key_index_logic=cls.global_key_index_logic)
                
                if len(drawindexed_list) != 0:
                    texture_override_component.append("    " + "run = CommandListTriggerResourceOverrides")
                    texture_override_component.append("    " + "run = CommandListOverrideSharedResources")
                    texture_override_component.append("    " + "; Draw Component " + component_count_str)

                    for drawindexed_str in drawindexed_list:
                        texture_override_component.append("    " + drawindexed_str)
                    cls.global_key_index_logic = added_global_key_index_logic

                    texture_override_component.append("    " + "run = CommandListCleanupSharedResources")
                texture_override_component.append("  endif")
            else:

                # 必须先判定这里是否有DrawIndexed才能去进行绘制以及调用CommandList
                model_collection_list = draw_ib_model.componentname_modelcollection_list_dict[component_name]
                drawindexed_list, added_global_key_index_logic = cls.get_switchkey_drawindexed_list(model_collection_list=model_collection_list, draw_ib_model=draw_ib_model,vlr_filter_index_indent="",input_global_key_index_logic=cls.global_key_index_logic)
                if len(drawindexed_list) != 0:
                    texture_override_component.append("  " + "handling = skip")
                    texture_override_component.append("  " + "run = CommandListTriggerResourceOverrides")
                    texture_override_component.append("  " + "run = CommandListOverrideSharedResources")
                    texture_override_component.append("  " + "; Draw Component " + component_count_str)

                    for drawindexed_str in drawindexed_list:
                        texture_override_component.append("  " + drawindexed_str)
                    cls.global_key_index_logic = added_global_key_index_logic

                    texture_override_component.append("  " + "run = CommandListCleanupSharedResources")

            texture_override_component.append("endif")
            texture_override_component.new_line()

            component_count = component_count + 1

        ini_builder.append_section(texture_override_component)
    
    @classmethod
    def add_texture_override_shapekeys(cls,ini_builder:M_IniBuilder,draw_ib_model:DrawIBModelWWMI):
        texture_override_shapekeys_section = M_IniSection(M_SectionType.TextureOverrideShapeKeys)

        shapekey_offsets_hash = draw_ib_model.extracted_object.shapekeys.offsets_hash
        if shapekey_offsets_hash != "":
            texture_override_shapekeys_section.append("[TextureOverrideShapeKeyOffsets]")
            texture_override_shapekeys_section.append("hash = " + shapekey_offsets_hash)
            texture_override_shapekeys_section.append("match_priority = 0")
            texture_override_shapekeys_section.append("override_byte_stride = 24")
            texture_override_shapekeys_section.append("override_vertex_count = $mesh_vertex_count")
            texture_override_shapekeys_section.new_line()

        shapekey_scale_hash = draw_ib_model.extracted_object.shapekeys.scale_hash
        if shapekey_scale_hash != "":
            texture_override_shapekeys_section.append("[TextureOverrideShapeKeyScale]")
            texture_override_shapekeys_section.append("hash = " + draw_ib_model.extracted_object.shapekeys.scale_hash)
            texture_override_shapekeys_section.append("match_priority = 0")
            texture_override_shapekeys_section.append("override_byte_stride = 4")
            texture_override_shapekeys_section.append("override_vertex_count = $mesh_vertex_count")
            texture_override_shapekeys_section.new_line()

        if shapekey_offsets_hash != "":
            texture_override_shapekeys_section.append("[TextureOverrideShapeKeyLoaderCallback]")
            texture_override_shapekeys_section.append("hash = " + draw_ib_model.extracted_object.shapekeys.offsets_hash)
            texture_override_shapekeys_section.append("match_priority = 0")
            texture_override_shapekeys_section.append("if $mod_enabled")

            if Properties_WWMI.import_merged_vgmap():
                texture_override_shapekeys_section.append("  " + "if cs == 3381.3333 && ResourceMergedSkeleton !== null")
            else:
                texture_override_shapekeys_section.append("  " + "if cs == 3381.3333")

            texture_override_shapekeys_section.append("    " + "handling = skip")
            texture_override_shapekeys_section.append("    " + "run = CommandListSetupShapeKeys")
            texture_override_shapekeys_section.append("    " + "run = CommandListLoadShapeKeys")
            texture_override_shapekeys_section.append("  " + "endif")

            texture_override_shapekeys_section.append("endif")
            texture_override_shapekeys_section.new_line()

        if shapekey_offsets_hash != "":
            texture_override_shapekeys_section.append("[TextureOverrideShapeKeyMultiplierCallback]")
            texture_override_shapekeys_section.append("hash = " + draw_ib_model.extracted_object.shapekeys.offsets_hash)
            texture_override_shapekeys_section.append("match_priority = 0")
            texture_override_shapekeys_section.append("if $mod_enabled")

            if Properties_WWMI.import_merged_vgmap():
                texture_override_shapekeys_section.append("  " + "if cs == 3381.4444 && ResourceMergedSkeleton !== null")
            else:
                texture_override_shapekeys_section.append("  " + "if cs == 3381.4444")

            texture_override_shapekeys_section.append("    " + "handling = skip")
            texture_override_shapekeys_section.append("    " + "run = CommandListMultiplyShapeKeys")
            texture_override_shapekeys_section.append("  " + "endif")
            texture_override_shapekeys_section.append("endif")
            texture_override_shapekeys_section.new_line()

        ini_builder.append_section(texture_override_shapekeys_section)

    @classmethod
    def add_resource_shapekeys(cls,ini_builder:M_IniBuilder,draw_ib_model:DrawIBModelWWMI):
        resource_shapekeys_section = M_IniSection(M_SectionType.ResourceShapeKeysOverride)

        # TODO 这些array后面的值可能是动态计算得到的
        resource_shapekeys_section.append("[ResourceShapeKeyCBRW]")
        resource_shapekeys_section.append("type = RWBuffer")
        resource_shapekeys_section.append("format = R32G32B32A32_UINT")
        resource_shapekeys_section.append("array = 66")

        resource_shapekeys_section.append("[ResourceCustomShapeKeyValuesRW]")
        resource_shapekeys_section.append("type = RWBuffer")
        resource_shapekeys_section.append("format = R32G32B32A32_FLOAT")
        resource_shapekeys_section.append("array = 32")

        ini_builder.append_section(resource_shapekeys_section)

    @classmethod
    def add_resource_merged_skeleton(cls,ini_builder:M_IniBuilder,draw_ib_model:DrawIBModelWWMI):
        resource_skeleton_section = M_IniSection(M_SectionType.ResourceSkeletonOverride)

        # TODO 这些array后面的值可能是动态计算得到的
        resource_skeleton_section.append("[ResourceMergedSkeleton]")
        resource_skeleton_section.new_line()

        resource_skeleton_section.append("[ResourceMergedSkeletonRW]")
        resource_skeleton_section.append("type = RWBuffer")
        resource_skeleton_section.append("format = R32G32B32A32_FLOAT")
        resource_skeleton_section.append("array = 768")
        resource_skeleton_section.new_line()

        resource_skeleton_section.append("[ResourceExtraMergedSkeleton]")
        resource_skeleton_section.new_line()

        resource_skeleton_section.append("[ResourceExtraMergedSkeletonRW]")
        resource_skeleton_section.append("type = RWBuffer")
        resource_skeleton_section.append("format = R32G32B32A32_FLOAT")
        resource_skeleton_section.append("array = 768")

        ini_builder.append_section(resource_skeleton_section)

    @classmethod
    def add_resource_buffer(cls,ini_builder:M_IniBuilder,draw_ib_model:DrawIBModelWWMI):
        resource_buffer_section = M_IniSection(M_SectionType.ResourceBuffer)

        # IndexBuffer
        resource_buffer_section.append("[ResourceIndexBuffer]")
        resource_buffer_section.append("type = Buffer")
        resource_buffer_section.append("format = DXGI_FORMAT_R32_UINT")
        resource_buffer_section.append("stride = 12")
        resource_buffer_section.append("filename = Buffer/" + draw_ib_model.draw_ib + "-" + "Component1.buf")
        resource_buffer_section.new_line()

        # CategoryBuffer
        for category_name,category_stride in draw_ib_model.d3d11GameType.CategoryStrideDict.items():
            resource_buffer_section.append("[Resource" + category_name + "Buffer]")
            resource_buffer_section.append("type = Buffer")

            # 根据不同的分类指定不同的format
            if category_name == "Position":
                resource_buffer_section.append("format = DXGI_FORMAT_R32G32B32_FLOAT")
            elif category_name == "Blend":
                resource_buffer_section.append("format = DXGI_FORMAT_R8_UINT")
            elif category_name == "Vector":
                resource_buffer_section.append("format = DXGI_FORMAT_R8G8B8A8_SNORM")
            elif category_name == "Color":
                resource_buffer_section.append("format = DXGI_FORMAT_R8G8B8A8_UNORM")
            elif category_name == "Texcoord":
                resource_buffer_section.append("format = DXGI_FORMAT_R16G16_FLOAT")
            
            resource_buffer_section.append("stride = " + str(category_stride))
            resource_buffer_section.append("filename = Buffer/" + draw_ib_model.draw_ib + "-" + category_name + ".buf")
            resource_buffer_section.new_line()

        # ShapeKeyBuffer
        resource_buffer_section.append("[ResourceShapeKeyOffsetBuffer]")
        resource_buffer_section.append("type = Buffer")
        resource_buffer_section.append("format = DXGI_FORMAT_R32G32B32A32_UINT")
        resource_buffer_section.append("stride = 16")
        resource_buffer_section.append("filename = Buffer/" + draw_ib_model.draw_ib + "-" + "ShapeKeyOffset.buf")
        resource_buffer_section.new_line()

        resource_buffer_section.append("[ResourceShapeKeyVertexIdBuffer]")
        resource_buffer_section.append("type = Buffer")
        resource_buffer_section.append("format = DXGI_FORMAT_R32_UINT")
        resource_buffer_section.append("stride = 4")
        resource_buffer_section.append("filename = Buffer/" + draw_ib_model.draw_ib + "-" + "ShapeKeyVertexId.buf")
        resource_buffer_section.new_line()

        resource_buffer_section.append("[ResourceShapeKeyVertexOffsetBuffer]")
        resource_buffer_section.append("type = Buffer")
        resource_buffer_section.append("format = DXGI_FORMAT_R16_FLOAT")
        resource_buffer_section.append("stride = 2")
        resource_buffer_section.append("filename = Buffer/" + draw_ib_model.draw_ib + "-" + "ShapeKeyVertexOffset.buf")
        resource_buffer_section.new_line()

        ini_builder.append_section(resource_buffer_section)


    @classmethod
    def generate_unreal_vs_config_ini(cls):
        '''
        Supported Games:
        - Wuthering Waves

        '''
        config_ini_builder = M_IniBuilder()

        M_IniHelper.generate_hash_style_texture_ini(ini_builder=config_ini_builder,drawib_drawibmodel_dict=cls.drawib_drawibmodel_dict)

        # Add namespace 
        M_IniHelper.add_namespace_sections_merged(ini_builder=config_ini_builder, drawib_drawibmodel_dict=cls.drawib_drawibmodel_dict)

        for draw_ib, draw_ib_model in cls.drawib_drawibmodel_dict.items():

            cls.add_constants_section(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)
            cls.add_present_section(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)
            cls.add_commandlist_section(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)

            cls.add_texture_override_mark_bone_data_cb(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)
            cls.add_texture_override_component(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)
            cls.add_texture_override_shapekeys(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)

            cls.add_resource_mod_info_section_default(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)
            cls.add_resource_shapekeys(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)

            if Properties_WWMI.import_merged_vgmap():
                cls.add_resource_merged_skeleton(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)

            cls.add_resource_buffer(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)
            
            # 移动槽位贴图
            M_IniHelper.move_slot_style_textures(draw_ib_model=draw_ib_model)

            cls.global_generate_mod_number = cls.global_generate_mod_number + 1

            config_ini_builder.save_to_file(GlobalConfig.path_generate_mod_folder() + GlobalConfig.workspacename + "_" + draw_ib + ".ini")
            config_ini_builder.clear()

        