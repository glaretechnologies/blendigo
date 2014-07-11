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
from indigo.export.materials.Base import AlbedoChannelMaterial, EmissionChannelMaterial, BumpChannelMaterial, NormalChannelMaterial, DisplacementChannelMaterial, MaterialBase

class DiffuseMaterial(
    AlbedoChannelMaterial,
    EmissionChannelMaterial,
    BumpChannelMaterial,
    NormalChannelMaterial,
    DisplacementChannelMaterial,
    
    # MaterialBase needs to be last in this list
    MaterialBase
    ):
    def get_format(self):
        if self.property_group.transmitter:
            element_name = 'diffuse_transmitter'
        else:
            if self.property_group.sigma > 0:
                element_name = 'oren_nayar'
            else:
                element_name = 'diffuse'
        
        fmt = {
            'name': [self.material_name],
            element_name: self.get_channels()
        }
        
        if element_name == 'oren_nayar':
            fmt[element_name].update({
                'sigma': [self.property_group.sigma]
            })

        if self.property_group.shadow_catcher:
            fmt['shadow_catcher'] = ['true']
        
        return fmt
