import bpy
from extensions_framework import util as efutil
from .. materials.Base        import AlbedoChannelMaterial, BumpChannelMaterial, NormalChannelMaterial, DisplacementChannelMaterial, RoughnessChannelMaterial, FresnelScaleChannelMaterial, EmissionChannelMaterial, MaterialBase

class FastSSSMaterial(
        AlbedoChannelMaterial,
        BumpChannelMaterial,
        NormalChannelMaterial,
        DisplacementChannelMaterial,
        RoughnessChannelMaterial,
        FresnelScaleChannelMaterial,
        EmissionChannelMaterial,
        MaterialBase
        ):
    '''
    The Fast SSS material
    '''
    
    def get_format(self):
        element_name = 'fast_sss'
        medium_name = self.property_group.medium_chooser 
        # get medium index
        medium_index = bpy.context.scene.indigo_material_medium.medium.find(medium_name)
        # TODO:
        # medium check <-> name
        if (len(medium_name) == 0) or  (medium_index == -1):
            medium_name = "basic"
            medium_index = 10190137
                     
        else:
            medium_name = medium_name + '_medium'
            
        fmt = {
            'name': [self.material_name],
            element_name: {
                'fresnel_scale': {
                    'constant': [self.property_group.fresnel_scale]
                },
                'roughness': {
                    'constant': [self.property_group.roughness]
                },
                'internal_medium_uid': [ +medium_index + 10000 ]
            }
        }
        
        fmt[element_name].update(self.get_channels())
        
            
        return fmt