'''
Created by Styriam Sp. z. o.o., Marcin Zielinski, Doug Hammond, Thomas Ludwig, Nicholas Chapman, Yves Colle

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

bl_info = {
    "name": "Blendigo - Indigo Exporter",
    "description": "This Addon will allow you to render your scenes with the Indigo render engine.",
    "author": "Glare Technologies Ltd.",
    "version": (4, 3, 0),
    "blender": (2, 80, 0),
    "location": "View3D",
    "wiki_url": "",
    "category": "Render" }


import bpy

# register
##################################

from . import auto_load

auto_load.init(ignore=("addon_updater", "addon_updater_ops"), make_annotations=True)

def register():
    auto_load.register()

    # addon updater code and configurations
    # in case of broken version, try to register the updater first
    # so that users can revert back to a working version
    from . import addon_updater_ops
    addon_updater_ops.register(bl_info)
    from .addon_updater import Updater as updater
    updater.user = "glaretechnologies"
    updater.repo = "blendigo"
    updater.addon = "blendigo"
    # updater.include_branche_list = ["master", "dev"]
    updater.subfolder_path = "sources/indigo_exporter/"

    addon_updater_ops.check_for_update_background()
    
    from . properties.render_settings import Indigo_Engine_Properties
    bpy.types.Scene.indigo_engine = bpy.props.PointerProperty(name="Indigo Engine Properties", type = Indigo_Engine_Properties)
    
    from . properties.camera import Indigo_Camera_Properties
    bpy.types.Camera.indigo_camera = bpy.props.PointerProperty(name="Indigo Camera Properties", type = Indigo_Camera_Properties)
    
    from . properties.environment import Indigo_Lightlayers_Properties
    bpy.types.Scene.indigo_lightlayers = bpy.props.PointerProperty(name="Indigo Lightlayers Properties", type = Indigo_Lightlayers_Properties)
    
    from . properties.lamp import Indigo_Lamp_Sun_Properties, Indigo_Lamp_Hemi_Properties
    bpy.types.Light.indigo_lamp_sun = bpy.props.PointerProperty(name="Indigo Lamp Sun Properties", type = Indigo_Lamp_Sun_Properties)
    bpy.types.Light.indigo_lamp_hemi = bpy.props.PointerProperty(name="Indigo Lamp Hemi Properties", type = Indigo_Lamp_Hemi_Properties)
    
    from . properties.material import Indigo_Material_Properties, Indigo_Texture_Properties
    bpy.types.Material.indigo_material = bpy.props.PointerProperty(name="Indigo Material Properties", type = Indigo_Material_Properties)
    bpy.types.Texture.indigo_texture = bpy.props.PointerProperty(name="Indigo Texture Properties", type = Indigo_Texture_Properties)
    
    from . properties.medium import Indigo_Material_Medium_Properties
    bpy.types.Scene.indigo_material_medium = bpy.props.PointerProperty(name="Indigo Material Medium Properties", type = Indigo_Material_Medium_Properties)
    bpy.types.Material.indigo_material_medium = bpy.props.PointerProperty(name="Indigo Material Medium Properties", type = Indigo_Material_Medium_Properties)
    
    from . properties.object import Indigo_Mesh_Properties
    bpy.types.Mesh.indigo_mesh = bpy.props.PointerProperty(name="Indigo Mesh Properties", type = Indigo_Mesh_Properties)
    bpy.types.SurfaceCurve.indigo_mesh = bpy.props.PointerProperty(name="Indigo Mesh Properties", type = Indigo_Mesh_Properties)
    bpy.types.TextCurve.indigo_mesh = bpy.props.PointerProperty(name="Indigo Mesh Properties", type = Indigo_Mesh_Properties)
    bpy.types.Curve.indigo_mesh = bpy.props.PointerProperty(name="Indigo Mesh Properties", type = Indigo_Mesh_Properties)
    
    from . properties.tonemapping import Indigo_Tonemapping_Properties
    bpy.types.Camera.indigo_tonemapping = bpy.props.PointerProperty(name="Indigo Tonemapping Properties", type = Indigo_Tonemapping_Properties)

def unregister():
    auto_load.unregister()
    addon_updater_ops.unregister()
