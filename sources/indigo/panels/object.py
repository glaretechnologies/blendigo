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

from extensions_framework.ui  import property_group_renderer

from indigo import IndigoAddon

class object_panel_base(property_group_renderer):
	COMPAT_ENGINES = {IndigoAddon.BL_IDNAME}

@IndigoAddon.addon_register_class
class indigo_ui_object_mesh(bl_ui.properties_data_mesh.MeshButtonsPanel, object_panel_base):
	bl_label = 'Indigo Object Settings'
	
	display_property_groups = [
		( ('mesh',), 'indigo_mesh' )
	]

@IndigoAddon.addon_register_class
class indigo_ui_object_curve(bl_ui.properties_data_curve.CurveButtonsPanel, object_panel_base):
	bl_label = 'Indigo Object Settings'
	
	display_property_groups = [
		( ('curve',), 'indigo_mesh' )
	]