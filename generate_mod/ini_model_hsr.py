import shutil
import math

from .m_ini_builder import *
from .m_drawib_model import *
from .m_ini_helper import M_IniHelper

from ..properties.properties_generate_mod import Properties_GenerateMod



class M_HSRIniModel:
    '''
    此模板用于崩铁3.2或以上版本，目前仍在测试中，将跟随老外的XXMI-Tools同步更新。
    '''
    drawib_drawibmodel_dict:dict[str,DrawIBModel] = {}
    # 代表全局声明了几个Key
    global_key_index_constants = 0
    # 
    global_key_index_logic = 0
    # 这个数量代表一共生成了几个DrawIB的Mod，每个DrawIB都是一个Mod
    global_generate_mod_number = 0
    # VertexLimitRaise导致的缩进
    vlr_filter_index_indent = ""
    # 贴图filter_index功能
    texture_hash_filter_index_dict = {}


    @classmethod
    def initialzie(cls):
        '''
        在生成Mod之前必须调用这个初始化所有内容，因为静态类的变量是全局共享的.
        '''
        cls.drawib_drawibmodel_dict = {}
        
        cls.global_key_index_constants = 0
        cls.global_key_index_logic = 0
        cls.global_generate_mod_number = 0

        cls.vlr_filter_index_indent = ""
        cls.texture_hash_filter_index_dict = {}


    @classmethod
    def add_vertex_limit_raise_section(cls,config_ini_builder:M_IniBuilder,draw_ib_model:DrawIBModel):
        '''
        VertexLimitRaise部分，用于突破顶点数限制
        '''
        d3d11GameType = draw_ib_model.d3d11GameType
        draw_ib = draw_ib_model.draw_ib

        if d3d11GameType.GPU_PreSkinning:
            vertexlimit_section = M_IniSection(M_SectionType.TextureOverrideVertexLimitRaise)

            vertexlimit_section.append("[TextureOverride_" + draw_ib + "_" + draw_ib_model.draw_ib_alias + "_VertexLimitRaise" + "]")
            vertexlimit_section.append("hash = " + draw_ib_model.vertex_limit_hash)

            vertexlimit_section.append("override_byte_stride = " + str(d3d11GameType.CategoryStrideDict["Position"]))
            vertexlimit_section.append("override_vertex_count = " + str(draw_ib_model.draw_number))

            # TODO 处理多个IB在同一ini中的问题。
            vertexlimit_section.append("if DRAW_TYPE != 8 && DRAW_TYPE != 1 && $_blend_ > 0")
            vertexlimit_section.append("  $_blend_ = $_blend_ - 1")
            vertexlimit_section.append("  this = ref Resource_" + draw_ib + "_DrawCS")
            vertexlimit_section.append("endif")
            vertexlimit_section.new_line()

            config_ini_builder.append_section(vertexlimit_section)


    @classmethod
    def add_resource_texture_sections(cls,ini_builder,draw_ib_model:DrawIBModel):
        '''
        Add texture resource.
        只有槽位风格贴图会用到，因为Hash风格贴图有专门的方法去声明这个。
        '''
        if Properties_GenerateMod.forbid_auto_texture_ini():
            return 
        
        resource_texture_section = M_IniSection(M_SectionType.ResourceTexture)
        for resource_name, texture_filename in draw_ib_model.TextureResource_Name_FileName_Dict.items():
            if "_Slot_" in texture_filename:
                resource_texture_section.append("[" + resource_name + "]")
                resource_texture_section.append("filename = Texture/" + texture_filename)
                resource_texture_section.new_line()

        ini_builder.append_section(resource_texture_section)


    @classmethod
    def add_texture_override_vb_sections(cls,config_ini_builder:M_IniBuilder,draw_ib_model:DrawIBModel):
        # 声明TextureOverrideVB部分，只有使用GPU-PreSkinning时是直接替换hash对应槽位
        d3d11GameType = draw_ib_model.d3d11GameType
        draw_ib = draw_ib_model.draw_ib

        if d3d11GameType.GPU_PreSkinning:
            texture_override_vb_section = M_IniSection(M_SectionType.TextureOverrideVB)
            texture_override_vb_section.append("; " + draw_ib + " ----------------------------")
            for category_name in d3d11GameType.OrderedCategoryNameList:
                category_hash = draw_ib_model.category_hash_dict[category_name]
                category_slot = d3d11GameType.CategoryExtractSlotDict[category_name]

                texture_override_vb_namesuffix = "VB_" + draw_ib + "_" + draw_ib_model.draw_ib_alias + "_" + category_name

                if category_name != "Position":
                    texture_override_vb_section.append("[TextureOverride_" + texture_override_vb_namesuffix + "]")
                    texture_override_vb_section.append("hash = " + category_hash)

                    if category_name != "Texcoord":
                        texture_override_vb_section.append("handling = skip")

                # 如果出现了VertexLimitRaise，Texcoord槽位需要检测filter_index才能替换
                filterindex_indent_prefix = ""
                if category_name == d3d11GameType.CategoryDrawCategoryDict["Texcoord"]:
                    if cls.vlr_filter_index_indent != "":
                        texture_override_vb_section.append("if vb0 == " + str(3000 + cls.global_generate_mod_number))

                # 遍历获取所有在当前分类hash下进行替换的分类，并添加对应的资源替换
                for original_category_name, draw_category_name in d3d11GameType.CategoryDrawCategoryDict.items():
                    position_category_slot = d3d11GameType.CategoryExtractSlotDict["Position"]
                    blend_category_slot = d3d11GameType.CategoryExtractSlotDict["Blend"]
                     
                    if category_name == draw_category_name:
                        if original_category_name == "Position":
                            # XXMI中直接使用Blend进行渲染了，Position啥也不干，不需要了直接。
                            pass

                            # texture_override_vb_section.append(blend_category_slot + " = Resource" + draw_ib + "Blend")
                            # texture_override_vb_section.append("if DRAW_TYPE == 1")
                            # texture_override_vb_section.append("  " + position_category_slot + " = Resource" + draw_ib + "Position")

                            # dispatch_number = int(math.ceil(draw_ib_model.draw_number / 64)) + 1
                            # texture_override_vb_section.append("draw = " + str(dispatch_number) + ", 0")
                            # texture_override_vb_section.append("endif")

                        elif original_category_name == "Blend":
                            texture_override_vb_section.append("vb2 = Resource" + draw_ib + "Blend")
                            texture_override_vb_section.append("if DRAW_TYPE == 1")
                            texture_override_vb_section.append("  vb0 = Resource" + draw_ib + "Position")
                            texture_override_vb_section.append("draw = " + str(draw_ib_model.draw_number) + ", 0")
                            texture_override_vb_section.append("endif")
                            texture_override_vb_section.append("Resource_" + draw_ib + "_DrawCS = copy " + "Resource_" + draw_ib + "_DrawCS")
                            texture_override_vb_section.append("if DRAW_TYPE == 8")
                            texture_override_vb_section.append("  Resource\\SRMI\\PositionBuffer = ref Resource" + draw_ib + "PositionCS" )
                            texture_override_vb_section.append("  Resource\\SRMI\\BlendBuffer = ref Resource" + draw_ib + "BlendCS" )
                            texture_override_vb_section.append("  Resource\\SRMI\\DrawBuffer = ref Resource_" + draw_ib + "_DrawCS" )
                            texture_override_vb_section.append("  $\\SRMI\\vertcount = " + str(draw_ib_model.draw_number))
                            texture_override_vb_section.append("elif DRAW_TYPE != 1")
                            texture_override_vb_section.append("  $_blend_ = 2")
                            texture_override_vb_section.append("endif")
                            
                        else:
                            category_original_slot = d3d11GameType.CategoryExtractSlotDict[original_category_name]
                            texture_override_vb_section.append(filterindex_indent_prefix  + category_original_slot + " = Resource" + draw_ib + original_category_name)

                # 对应if vb0 == 3000的结束
                if category_name == d3d11GameType.CategoryDrawCategoryDict["Texcoord"]:
                    if cls.vlr_filter_index_indent != "":
                        texture_override_vb_section.append("endif")
                
                # 分支架构，如果是Position则需提供激活变量
                if category_name == d3d11GameType.CategoryDrawCategoryDict["Position"]:
                    if draw_ib_model.key_number != 0:
                        texture_override_vb_section.append("$active" + str(cls.global_generate_mod_number) + " = 1")

                texture_override_vb_section.new_line()
            config_ini_builder.append_section(texture_override_vb_section)
            
            
    @classmethod
    def add_texture_override_ib_sections(cls,config_ini_builder:M_IniBuilder,draw_ib_model:DrawIBModel):
        texture_override_ib_section = M_IniSection(M_SectionType.TextureOverrideIB)
        draw_ib = draw_ib_model.draw_ib
        d3d11GameType = draw_ib_model.d3d11GameType

        # texture_override_ib_section.append("[TextureOverride_IB_" + draw_ib + "_" + draw_ib_model.draw_ib_alias + "]")
        # texture_override_ib_section.append("hash = " + draw_ib)
        # texture_override_ib_section.append("handling = skip")
        # texture_override_ib_section.new_line()

        # texture_override_ib_section.append("drawindexed = auto")

        for count_i in range(len(draw_ib_model.part_name_list)):
            match_first_index = draw_ib_model.match_first_index_list[count_i]
            part_name = draw_ib_model.part_name_list[count_i]

            style_part_name = "Component" + part_name
            ib_resource_name = "Resource_" + draw_ib+ "_" + style_part_name

            texture_override_ib_namesuffix = "IB_" + draw_ib  + "_" + draw_ib_model.draw_ib_alias  + "_" + style_part_name
            texture_override_ib_section.append("[TextureOverride_" + texture_override_ib_namesuffix + "]")
            texture_override_ib_section.append("hash = " + draw_ib)
            texture_override_ib_section.append("match_first_index = " + match_first_index)
            texture_override_ib_section.append("handling = skip")

            if cls.vlr_filter_index_indent != "":
                texture_override_ib_section.append("if vb0 == " + str(3000 + cls.global_generate_mod_number))

            # texture_override_ib_section.append(cls.vlr_filter_index_indent + "handling = skip")


            # If ib buf is emprt, continue to avoid add ib resource replace.
            ib_buf = draw_ib_model.componentname_ibbuf_dict.get("Component " + part_name,None)
            if ib_buf is None or len(ib_buf) == 0:
                texture_override_ib_section.new_line()
                continue

            # Add ib replace
            texture_override_ib_section.append(cls.vlr_filter_index_indent + "ib = " + ib_resource_name)

            # Add slot style texture slot replace.
            if not Properties_GenerateMod.forbid_auto_texture_ini():
                slot_texturereplace_dict = draw_ib_model.PartName_SlotTextureReplaceDict_Dict.get(part_name,None)
                # It may not have auto texture
                if slot_texturereplace_dict is not None:
                    for slot,texture_replace_obj in slot_texturereplace_dict.items():
                        if texture_replace_obj.style == "Slot":
                            texture_override_ib_section.append(cls.vlr_filter_index_indent + slot + " = " + texture_replace_obj.resource_name)

            # 如果不使用GPU-Skinning即为Object类型，此时需要在ib下面替换对应槽位
            if not d3d11GameType.GPU_PreSkinning:
                for category_name in d3d11GameType.OrderedCategoryNameList:
                    category_hash = draw_ib_model.category_hash_dict[category_name]
                    category_slot = d3d11GameType.CategoryExtractSlotDict[category_name]

                    for original_category_name, draw_category_name in d3d11GameType.CategoryDrawCategoryDict.items():
                        if original_category_name == draw_category_name:
                            category_original_slot = d3d11GameType.CategoryExtractSlotDict[original_category_name]
                            texture_override_ib_section.append(cls.vlr_filter_index_indent + category_original_slot + " = Resource" + draw_ib + original_category_name)
            

            # Component DrawIndexed输出
            component_name = "Component " + part_name 
            model_collection_list = draw_ib_model.componentname_modelcollection_list_dict[component_name]

            drawindexed_list, added_global_key_index_logic = M_IniHelper.get_switchkey_drawindexed_list(model_collection_list=model_collection_list, draw_ib_model=draw_ib_model,vlr_filter_index_indent=cls.vlr_filter_index_indent,input_global_key_index_logic=cls.global_key_index_logic)
            for drawindexed_str in drawindexed_list:
                texture_override_ib_section.append(drawindexed_str)
            cls.global_key_index_logic = added_global_key_index_logic
            
            if cls.vlr_filter_index_indent != "":
                texture_override_ib_section.append("endif")
                texture_override_ib_section.new_line()


        config_ini_builder.append_section(texture_override_ib_section)

    @classmethod
    def add_unity_cs_resource_vb_sections(cls,config_ini_builder:M_IniBuilder,draw_ib_model:DrawIBModel):
        '''
        Add Resource VB Section (HSR3.2)
        '''
        resource_vb_section = M_IniSection(M_SectionType.ResourceBuffer)

        # 先加入普通的Buffer
        for category_name in draw_ib_model.d3d11GameType.OrderedCategoryNameList:
            resource_vb_section.append("[Resource" + draw_ib_model.draw_ib + category_name + "]")
            resource_vb_section.append("type = Buffer")
            resource_vb_section.append("stride = " + str(draw_ib_model.d3d11GameType.CategoryStrideDict[category_name]))
            resource_vb_section.append("filename = Buffer/" + draw_ib_model.draw_ib + "-" + category_name + ".buf")
            # resource_vb_section.append(";VertexCount: " + str(draw_ib_model.draw_number))
            resource_vb_section.new_line()
        
        # 再加入CS的Buffer，主要是Position和Blend
        for category_name in draw_ib_model.d3d11GameType.OrderedCategoryNameList:
            if category_name == "Position" or category_name == "Blend":
                resource_vb_section.append("[Resource" + draw_ib_model.draw_ib + category_name + "CS]")
                resource_vb_section.append("type = StructuredBuffer")
                resource_vb_section.append("stride = " + str(draw_ib_model.d3d11GameType.CategoryStrideDict[category_name]))
                resource_vb_section.append("filename = Buffer/" + draw_ib_model.draw_ib + "-" + category_name + ".buf")
                # resource_vb_section.append(";VertexCount: " + str(draw_ib_model.draw_number))
                resource_vb_section.new_line()

        '''
        Add Resource IB Section

        We default use R32_UINT because R16_UINT have a very small number limit.
        '''
        for count_i in range(len(draw_ib_model.part_name_list)):
            partname = draw_ib_model.part_name_list[count_i]
            style_partname = "Component" + partname
            ib_resource_name = "Resource_" + draw_ib_model.draw_ib + "_" + style_partname

            
            resource_vb_section.append("[" + ib_resource_name + "]")
            resource_vb_section.append("type = Buffer")
            resource_vb_section.append("format = DXGI_FORMAT_R32_UINT")
            resource_vb_section.append("filename = Buffer/" + draw_ib_model.draw_ib + "-" + style_partname + ".buf")
            resource_vb_section.new_line()
        
        config_ini_builder.append_section(resource_vb_section)
    


    @classmethod
    def add_texture_filter_index(cls,ini_builder:M_IniBuilder):
        if not Properties_GenerateMod.slot_style_texture_add_filter_index():
            return 

        filter_index_count = 0
        for draw_ib, draw_ib_model in cls.drawib_drawibmodel_dict.items():
            for partname,slot_texture_replace_dict in draw_ib_model.PartName_SlotTextureReplaceDict_Dict.items():
                for slot, texture_replace in slot_texture_replace_dict.items():
                    if texture_replace.hash in cls.texture_hash_filter_index_dict:
                        continue
                    else:
                        filter_index = 6000 + filter_index_count
                        filter_index_count = filter_index_count + 1
                        cls.texture_hash_filter_index_dict[texture_replace.hash] = filter_index
        

        texture_filter_index_section = M_IniSection(M_SectionType.TextureOverrideTexture)
        for hash_value, filter_index in cls.texture_hash_filter_index_dict.items():
            texture_filter_index_section.append("[TextureOverride_Texture_" + hash_value + "]")
            texture_filter_index_section.append("hash = " + hash_value)
            texture_filter_index_section.append("filter_index = " + str(filter_index))
            texture_filter_index_section.new_line()

        ini_builder.append_section(texture_filter_index_section)

    @classmethod
    def add_hsr32_constants(cls,ini_builder):
        '''
        添加$_blend_ 和 RWStructuredBuffer的Resource
        '''
        constants_section = M_IniSection(M_SectionType.Constants)
        constants_section.SectionName = "Constants"
        constants_section.append("global $_blend_ = 0" )
        
        ini_builder.append_section(constants_section)




    @classmethod
    def add_hsr32_resource(cls,ini_builder,draw_ib_model:DrawIBModel):
        '''
        添加$_blend_ 和 RWStructuredBuffer的Resource
        '''
        resource_section = M_IniSection(M_SectionType.ResourceBuffer)
        resource_section.append("[Resource_" + draw_ib_model.draw_ib + "_DrawCS]")
        resource_section.append("type = RWStructuredBuffer")
        resource_section.append("array = " + str(draw_ib_model.draw_number))
        resource_section.append("data = R32_FLOAT 1 2 3 4 5 6 7 8 9 10")
        resource_section.new_line()
        ini_builder.append_section(resource_section)

    @classmethod
    def generate_unity_cs_config_ini(cls):
        '''
        test
        '''
        config_ini_builder = M_IniBuilder()

        M_IniHelper.generate_hash_style_texture_ini(ini_builder=config_ini_builder,drawib_drawibmodel_dict=cls.drawib_drawibmodel_dict)


        if Properties_GenerateMod.slot_style_texture_add_filter_index():
            cls.add_texture_filter_index(ini_builder= config_ini_builder)

        # 多个drawib目前测试共用一个就行了。
        cls.add_hsr32_constants(ini_builder=config_ini_builder)

        for draw_ib, draw_ib_model in cls.drawib_drawibmodel_dict.items():

            # 按键开关与按键切换声明部分
            M_IniHelper.add_switchkey_constants_section(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model,global_generate_mod_number=cls.global_generate_mod_number,global_key_index_constants=cls.global_key_index_constants)
            M_IniHelper.add_switchkey_present_section(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model,global_generate_mod_number=cls.global_generate_mod_number)
            global_key_index_counstants_added = M_IniHelper.add_switchkey_sections(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model,global_generate_mod_number=cls.global_generate_mod_number,input_global_key_index_constants=cls.global_key_index_constants) 
            cls.global_key_index_constants = global_key_index_counstants_added

            # 每个drawIB添加一个resource
            cls.add_hsr32_resource(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)
            # [TextureOverrideVertexLimitRaise]
            cls.add_vertex_limit_raise_section(config_ini_builder=config_ini_builder,draw_ib_model=draw_ib_model) 
            # [TextureOverrideVB]
            cls.add_texture_override_vb_sections(config_ini_builder=config_ini_builder,draw_ib_model=draw_ib_model) 
            # [TextureOverrideIB]
            cls.add_texture_override_ib_sections(config_ini_builder=config_ini_builder,draw_ib_model=draw_ib_model) 

            # Resource.ini
            cls.add_unity_cs_resource_vb_sections(config_ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)
            cls.add_resource_texture_sections(ini_builder=config_ini_builder,draw_ib_model=draw_ib_model)

            M_IniHelper.move_slot_style_textures(draw_ib_model=draw_ib_model)

            cls.global_generate_mod_number = cls.global_generate_mod_number + 1

        config_ini_builder.save_to_file(GlobalConfig.path_generate_mod_folder() + GlobalConfig.workspacename + ".ini")
        