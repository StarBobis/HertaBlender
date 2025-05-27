import bpy

class Properties_ImportModel(bpy.types.PropertyGroup):
    model_scale: bpy.props.FloatProperty(
        name="模型导入大小比例",
        description="默认为1.0",
        default=1.0,
    ) # type: ignore

    @classmethod
    def model_scale(cls):
        '''
        bpy.context.scene.properties_import_model.model_scale
        '''
        return bpy.context.scene.properties_import_model.model_scale

    import_flip_scale_x :bpy.props.BoolProperty(
        name="设置Scale的X分量为-1避免模型镜像",
        description="勾选后在导入模型时把缩放的X分量乘以-1，实现镜像效果，还原游戏中原本的样子，解决导入后镜像对调的问题",
        default=False
    ) # type: ignore

    @classmethod
    def import_flip_scale_x(cls):
        '''
        bpy.context.scene.properties_import_model.import_flip_scale_x
        '''
        return bpy.context.scene.properties_import_model.import_flip_scale_x
    
    import_flip_scale_y :bpy.props.BoolProperty(
        name="设置Scale的Y分量为-1来改变模型朝向",
        description="勾选后在导入模型时把缩放的Y分量乘以-1，实现改变朝向效果，主要用于方便后续绑MMD骨",
        default=False
    ) # type: ignore



    @classmethod
    def import_flip_scale_y(cls):
        '''
        bpy.context.scene.properties_import_model.import_flip_scale_y
        '''
        return bpy.context.scene.properties_import_model.import_flip_scale_y