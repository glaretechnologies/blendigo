# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 Indigo Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Nicholas Chapman, Yves Collé
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
from extensions_framework import util as efutil

from indigo.export.materials.Base import AlbedoChannelMaterial, EmissionChannelMaterial, BumpChannelMaterial, NormalChannelMaterial, DisplacementChannelMaterial, AbsorptionChannelMaterial, MaterialBase

class CoatingMaterial(
    #AlbedoChannelMaterial,
    EmissionChannelMaterial,
    BumpChannelMaterial,
    NormalChannelMaterial,
    DisplacementChannelMaterial,
    AbsorptionChannelMaterial,
    
    # MaterialBase needs to be last in this list
    MaterialBase
    ):
    
    def get_format(self):
        element_name = 'coating'
        
        fmt = {
            'name': [self.material_name],
            'backface_emit': [str(self.material_group.indigo_material_emission.backface_emit).lower()],
            element_name: {
                'ior': [self.property_group.ior],
                'interference': [str(self.property_group.interference).lower()],
                'roughness': {
                    'constant': [self.property_group.roughness]
                },
                'thickness': {
                    'constant': [self.property_group.thickness * 0.000001] # Convert to m.
                },
                'fresnel_scale': {
                    'constant': [self.property_group.fresnel_scale]
                },
                'substrate_material_name': [self.property_group.substrate_material_index],
            }
        }
        
        #absorption = self.get_channel(self.material_group.indigo_material_colour, self.property_group.channel_name, 'colour')
        #absorption = self.get_channel(self.material_group.indigo_material_colour, self.property_group.absorption, 'colour')
        
        #absorption = self.get_channel(self.material_group.indigo_material_colour, self.property_group.absorption, 'absorption')
        #print("absorption: " + str(absorption))
        
        #fmt[element_name].update(absorption)
        
        fmt[element_name].update(self.get_channels())
        
        return fmt
