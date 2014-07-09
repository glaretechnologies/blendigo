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
from indigo.export.materials.Base import BlendChannelMaterial, MaterialBase

class BlendMaterial(
    BlendChannelMaterial,
    
    # MaterialBase needs to be last in this list
    MaterialBase
    ):
    def get_format(self):
        element_name = 'blend'
        
        if self.property_group.a_null:
            a_name = ['blendigo_null']
        else:
            a_name = [self.property_group.a_index]
        
        if self.property_group.b_null:
            b_name = ['blendigo_null']
        else:
            b_name = [self.property_group.b_index]
        
        fmt = {
            'name': [self.material_name],
            element_name: {
                'blend': { 'constant' : [self.property_group.factor] } ,
                'step_blend': [str(self.property_group.step).lower()],
                'a_name': a_name,
                'b_name': b_name,
            }
        }
        
        fmt[element_name].update(self.get_channels())
        
        return fmt
