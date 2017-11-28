from extensions_framework import util as efutil
from .. materials.Base import EmissionChannelMaterial, MaterialBase

class NullMaterial(
        EmissionChannelMaterial,
        MaterialBase
        ):
    '''
    The Null material
    '''
    
    def get_format(self):
        element_name = 'null_material'
        
        fmt = {
            'name': [self.material_name],
            element_name: {}
        }        
        return fmt