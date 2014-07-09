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

from indigo.export.materials.Base import EmissionChannelMaterial, BumpChannelMaterial, DisplacementChannelMaterial, TransmittanceChannelMaterial, MaterialBase

class DoubleSidedThinMaterial(
    EmissionChannelMaterial,
    BumpChannelMaterial,
    DisplacementChannelMaterial,
    TransmittanceChannelMaterial,
    
    # MaterialBase needs to be last in this list
    MaterialBase
    ):
    
    def get_format(self):
        element_name = 'double_sided_thin'
        
        fmt = {
            'name': [self.material_name],
            element_name: {
                'ior': [self.property_group.ior],
                'front_roughness': {
                    'constant': [self.property_group.front_roughness]
                },
                'back_roughness': {
                    'constant': [self.property_group.back_roughness]
                },
                'r_f': {
                    'constant': [self.property_group.r_f]
                },
                'front_fresnel_scale': {
                    'constant': [self.property_group.front_fresnel_scale]
                },
                'back_fresnel_scale': {
                    'constant': [self.property_group.back_fresnel_scale]
                },
                'front_material_name': [self.property_group.front_material_index],
                'back_material_name': [self.property_group.back_material_index],
            }
        }
        
        fmt[element_name].update(self.get_channels())
        
        return fmt
