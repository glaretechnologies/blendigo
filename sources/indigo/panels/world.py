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
import bl_ui			#@UnresolvedImport

from extensions_framework.ui import property_group_renderer

from indigo import IndigoAddon

class world_panel(bl_ui.properties_world.WorldButtonsPanel, property_group_renderer):
	COMPAT_ENGINES = {IndigoAddon.BL_IDNAME}

@IndigoAddon.addon_register_class
class indigo_ui_lightlayers(world_panel):
	bl_label = 'Indigo Light Layers'
	
	display_property_groups = [
		( ('scene',), 'indigo_lightlayers' )
	]
	
	# overridden in order to draw a 'non-standard' panel
	def draw(self, context):
		super().draw(context)
		
		row = self.layout.row()
		row.label("Default layer gain")
		row.prop(context.scene.indigo_lightlayers, 'default_gain', text="")
		
		for lg_index in range(len(context.scene.indigo_lightlayers.lightlayers)):
			lg = context.scene.indigo_lightlayers.lightlayers[lg_index]
			row = self.layout.row()
			for control in lg.controls:
				self.draw_column(
					control,
					row.column(),
					lg,
					context,
					property_group = lg
				)
			row.operator('indigo.lightlayer_remove', text="", icon="ZOOMOUT").lg_index=lg_index
