# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 Indigo Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond, Yves Colle
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
from indigo.properties.material import PROPERTY_GROUP_USAGE

class indigo_ui_material_panel_base(bl_ui.properties_material.MaterialButtonsPanel, property_group_renderer):
    COMPAT_ENGINES = {IndigoAddon.BL_IDNAME}

class indigo_ui_texture_panel_base(bl_ui.properties_texture.TextureButtonsPanel, property_group_renderer):
    COMPAT_ENGINES = {IndigoAddon.BL_IDNAME}
    @classmethod
    def poll(cls, context):
        tex = context.texture
        return    tex and \
                (context.scene.render.engine in cls.COMPAT_ENGINES)

@IndigoAddon.addon_register_class
class indigo_ui_texture(indigo_ui_texture_panel_base):
    bl_label = 'Indigo Render Texture Settings'
    
    display_property_groups = [
        ( ('texture',), 'indigo_texture' ),
    ]

class indigo_ui_material_subpanel(indigo_ui_material_panel_base):
    INDIGO_COMPAT = set()
    
    @classmethod
    def poll(cls, context):
        return super().poll(context) and context.material.indigo_material.type in cls.INDIGO_COMPAT

@IndigoAddon.addon_register_class
class indigo_ui_material(indigo_ui_material_panel_base):
    bl_label = 'Indigo Render Material Settings'
    
    display_property_groups = [
        ( ('material',), 'indigo_material' ),
    ]

@IndigoAddon.addon_register_class
class indigo_ui_material_colour(indigo_ui_material_subpanel):
    bl_label = 'Material Colour'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['colour']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_colour' )
    ]

@IndigoAddon.addon_register_class
class indigo_ui_material_specular(indigo_ui_material_subpanel):
    bl_label = 'Material Specular Settings'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['specular']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_specular' )
    ]

@IndigoAddon.addon_register_class
class indigo_ui_material_phong(indigo_ui_material_subpanel):
    bl_label = 'Material Phong Settings'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['phong']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_phong' )
    ]
    
@IndigoAddon.addon_register_class
class indigo_ui_material_coating(indigo_ui_material_subpanel):
    bl_label = 'Material Coating Settings'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['coating']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_coating' )
    ]
    
@IndigoAddon.addon_register_class
class indigo_ui_material_doublesidedthin(indigo_ui_material_subpanel):
    bl_label = 'Material Double-Sided Thin Settings'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['doublesidedthin']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_doublesidedthin' )
    ]

@IndigoAddon.addon_register_class
class indigo_ui_material_transmittance(indigo_ui_material_subpanel):
    bl_label = 'Material Transmittance'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['transmittance']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_transmittance' )
    ]
    
    def draw_header(self, context):
        self.layout.prop(context.material.indigo_material.indigo_material_transmittance, "transmittance_enabled", text="")
        
@IndigoAddon.addon_register_class
class indigo_ui_material_absorption(indigo_ui_material_subpanel):
    bl_label = 'Material Absorption'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['absorption']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_absorption' )
    ]
    
    def draw_header(self, context):
        self.layout.prop(context.material.indigo_material.indigo_material_absorption, "absorption_enabled", text="")

@IndigoAddon.addon_register_class
class indigo_ui_material_diffuse(indigo_ui_material_subpanel):
    bl_label = 'Material Diffuse Settings'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['diffuse']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_diffuse' )
    ]

@IndigoAddon.addon_register_class
class indigo_ui_material_blended(indigo_ui_material_subpanel):
    bl_label = 'Material Blend Settings'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['blended']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_blended' )
    ]

@IndigoAddon.addon_register_class
class indigo_ui_material_external(indigo_ui_material_subpanel):
    bl_label = 'Material External Settings'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['external']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_external' )
    ]
    
    def draw(self, context):
        web_op = self.layout.operator('WM_OT_url_open', 'Open materials database', 'URL')
        web_op.url='http://www.indigorenderer.com/materials/'
        super().draw(context)

@IndigoAddon.addon_register_class
class indigo_ui_material_bumpmap(indigo_ui_material_subpanel):
    bl_label = 'Material Bump Map'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['bumpmap']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_bumpmap' )
    ]
    
    def draw_header(self, context):
        self.layout.prop(context.material.indigo_material.indigo_material_bumpmap, "bumpmap_enabled", text="")
        
@IndigoAddon.addon_register_class
class indigo_ui_material_normalmap(indigo_ui_material_subpanel):
    bl_label = 'Material Normal Map'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['normalmap']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_normalmap' )
    ]
    
    def draw_header(self, context):
        self.layout.prop(context.material.indigo_material.indigo_material_normalmap, "normalmap_enabled", text="")

@IndigoAddon.addon_register_class
class indigo_ui_material_displacement(indigo_ui_material_subpanel):
    bl_label = 'Material Displacement Map'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['displacement']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_displacement' )
    ]
    
    def draw_header(self, context):
        self.layout.prop(context.material.indigo_material.indigo_material_displacement, "displacement_enabled", text="")

@IndigoAddon.addon_register_class
class indigo_ui_material_exponent(indigo_ui_material_subpanel):
    bl_label = 'Material Exponent Map'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['exponent']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_exponent' )
    ]
    
    def draw_header(self, context):
        self.layout.prop(context.material.indigo_material.indigo_material_exponent, "exponent_enabled", text="")

@IndigoAddon.addon_register_class
class indigo_ui_material_blendmap(indigo_ui_material_subpanel):
    bl_label = 'Material Blend Map'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['blendmap']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_blendmap' )
    ]
    
    def draw_header(self, context):
        self.layout.prop(context.material.indigo_material.indigo_material_blendmap, "blendmap_enabled", text="")

@IndigoAddon.addon_register_class
class indigo_ui_material_emission(indigo_ui_material_subpanel):
    bl_label = 'Material Emission'
    
    INDIGO_COMPAT = PROPERTY_GROUP_USAGE['emission']
    
    display_property_groups = [
        ( ('material', 'indigo_material'), 'indigo_material_emission' )
    ]
    
    def draw_header(self, context):
        self.layout.prop(context.material.indigo_material.indigo_material_emission, "emission_enabled", text="")
