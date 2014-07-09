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
import bl_ui            #@UnresolvedImport

from extensions_framework.ui import property_group_renderer

from indigo import IndigoAddon

class lamp_described_context(bl_ui.properties_data_lamp.DataButtonsPanel, property_group_renderer):
    COMPAT_ENGINES = {IndigoAddon.BL_IDNAME}

narrowui = 180

@IndigoAddon.addon_register_class
class indigo_ui_lamps(lamp_described_context):
    bl_label = 'Indigo Lamps'
    
    # Overridden here and in each sub-type UI to draw some of blender's lamp controls
    def draw(self, context):
        if context.lamp is not None:
            wide_ui = context.region.width > narrowui
            
            if wide_ui:
                self.layout.prop(context.lamp, "type", expand=True)
            else:
                self.layout.prop(context.lamp, "type", text="")
            
            super().draw(context)
            
            if context.lamp.type not in ('SUN', 'HEMI'):
                self.layout.label('Unsupported lamp type')

@IndigoAddon.addon_register_class
class indigo_ui_lamp_sun(lamp_described_context):
    bl_label = 'Indigo Sun+Sky Lamp'
    
    display_property_groups = [
        ( ('lamp',), 'indigo_lamp_sun' )
    ]
    
    @classmethod
    def poll(cls, context):
        return super().poll(context) and context.lamp.type == 'SUN'

@IndigoAddon.addon_register_class
class indigo_ui_lamp_hemi(lamp_described_context):
    bl_label = 'Indigo Hemi Lamp'
    
    display_property_groups = [
        ( ('lamp',), 'indigo_lamp_hemi' )
    ]
    
    @classmethod
    def poll(cls, context):
        return super().poll(context) and context.lamp.type == 'HEMI'

