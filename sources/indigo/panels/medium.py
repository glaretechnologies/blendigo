# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 Indigo Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Marco Goebel
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

import bl_ui            #@UnresolvedImport

from extensions_framework.ui import property_group_renderer

from indigo import IndigoAddon
from indigo.properties.material import PROPERTY_GROUP_USAGE

class indigo_ui_material_panel_base(bl_ui.properties_material.MaterialButtonsPanel, property_group_renderer):
    COMPAT_ENGINES = {IndigoAddon.BL_IDNAME}

class world_panel(bl_ui.properties_world.WorldButtonsPanel, property_group_renderer):
    COMPAT_ENGINES = {IndigoAddon.BL_IDNAME}
    
@IndigoAddon.addon_register_class
class indigo_ui_material_medium(bl_ui.properties_material.MaterialButtonsPanel, property_group_renderer):
    bl_label = 'Indigo Medium'
   
    #INDIGO_COMPAT = PROPERTY_GROUP_USAGE['medium']
    COMPAT_ENGINES = {IndigoAddon.BL_IDNAME}
    display_property_groups = [
        ( ('material',), 'indigo_material_medium' )
    ]
    
    def draw(self, context):
        super().draw(context)

        if len(context.scene.indigo_material_medium.medium) > 0:
            current_med_ind = context.scene.indigo_material_medium.medium_index
            current_med = context.scene.indigo_material_medium.medium[current_med_ind]

            self.layout.prop(
                current_med, 'name'
            )

            for control in current_med.controls:
                self.draw_column(
                    control,
                    self.layout,
                    current_med,
                    context,
                    property_group=current_med
                )
