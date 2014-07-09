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

class camera_described_context(bl_ui.properties_data_camera.CameraButtonsPanel, property_group_renderer):
    COMPAT_ENGINES = {IndigoAddon.BL_IDNAME}

@IndigoAddon.addon_register_class
class indigo_ui_camera(camera_described_context):
    bl_label = 'Indigo Settings'
    
    display_property_groups = [
        ( ('camera',), 'indigo_camera' )
    ]

@IndigoAddon.addon_register_class
class indigo_ui_tonemapping(camera_described_context):
    bl_label = 'Indigo Tonemapping'
    
    display_property_groups = [
        ( ('camera',), 'indigo_tonemapping') 
    ]
