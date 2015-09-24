# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 Indigo Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# ***** END GPL LICENCE BLOCK *****
#
import bpy

from indigo.export import xml_builder
from indigo.export.materials.Base        import EmissionChannelMaterial, BumpChannelMaterial, NormalChannelMaterial, DisplacementChannelMaterial, ExponentChannelMaterial, AbsorptionLayerChannelMaterial, MaterialBase
from indigo.export.materials.spectra    import rgb, uniform



class SpecularMaterial(
    AbsorptionLayerChannelMaterial,
    EmissionChannelMaterial,
    BumpChannelMaterial,
    NormalChannelMaterial,
    DisplacementChannelMaterial,
    ExponentChannelMaterial,
    
    # MaterialBase needs to be last in this list
    MaterialBase
    ):
    def get_format(self):
        # will be specular or glossy_transparent
        element_name = self.property_group.type
        medium_name = self.property_group.medium_chooser 
        medium = bpy.context.scene.indigo_material_medium.medium
        
        medium_index = medium.find(medium_name)
        
        if (len(medium_name) == 0) or  (medium_index == -1):
            medium_index = len(medium) 
        else:
            medium_name = medium_name + '_medium'
            
        fmt = {
            'name': [self.material_name],
            'backface_emit': [str(self.material_group.indigo_material_emission.backface_emit).lower()],
            element_name: {
                'internal_medium_uid': [ medium_index + 10 ] # seems indigo medium uid starts at 10...
            }
        }
        
        if element_name == 'specular':
            if self.property_group.transparent:
                fmt[element_name]['transparent'] = ['true']
            else:
                fmt[element_name]['transparent'] = ['false']
                
            if self.property_group.arch_glass:
                fmt[element_name]['arch_glass'] = ['true']
            else:
                fmt[element_name]['arch_glass'] = ['false']

            if self.property_group.single_face and self.property_group.arch_glass:
                fmt[element_name]['single_face'] = ['true']
            else:
                fmt[element_name]['single_face'] = ['false']
        else:
            fmt[element_name]['exponent'] = [self.property_group.exponent]
        
        fmt[element_name].update(self.get_channels())
        
        return fmt
