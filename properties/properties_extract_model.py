import bpy

class Properties_ExtractModel(bpy.types.PropertyGroup):
    only_match_gpu :bpy.props.BoolProperty(
        name="Only Extract GPU-PreSkinning Models",
        description="Only extract models that are pre-skinned by the GPU, skipping those that are not.",
        default=True
    ) # type: ignore

    @classmethod
    def only_match_gpu(cls):
        '''
        bpy.context.scene.properties_extract_model.only_match_gpu
        '''
        return bpy.context.scene.properties_extract_model.only_match_gpu
    
    