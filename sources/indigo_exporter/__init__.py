'''
Created by Marcin Zielinski, Doug Hammond, Thomas Ludwig, Nicholas Chapman, Yves Colle

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
    "version": (4, 0, 4),
    "blender": (2, 79, 0),
    "location": "View3D",
    "warning": "This addon is still in development.",
    "wiki_url": "",
    "category": "Object" }


import bpy

# load and reload submodules
##################################

import importlib
from . import developer_utils
importlib.reload(developer_utils)
modules = developer_utils.setup_addon_modules(__path__, __name__, "bpy" in locals())



# register
##################################

import traceback

def register():
    try: bpy.utils.register_module(__name__)
    except: traceback.print_exc()
    
    from . properties.render_settings import Indigo_Engine_Properties
    bpy.types.Scene.indigo_engine = bpy.props.PointerProperty(name="Indigo Engine Properties", type = Indigo_Engine_Properties)
    
    from . properties.camera import Indigo_Camera_Properties
    bpy.types.Camera.indigo_camera = bpy.props.PointerProperty(name="Indigo Camera Properties", type = Indigo_Camera_Properties)
    
    from . properties.environment import Indigo_Lightlayers_Properties
    bpy.types.Scene.indigo_lightlayers = bpy.props.PointerProperty(name="Indigo Lightlayers Properties", type = Indigo_Lightlayers_Properties)
    
    from . properties.lamp import Indigo_Lamp_Sun_Properties, Indigo_Lamp_Hemi_Properties
    bpy.types.Lamp.indigo_lamp_sun = bpy.props.PointerProperty(name="Indigo Lamp Sun Properties", type = Indigo_Lamp_Sun_Properties)
    bpy.types.Lamp.indigo_lamp_hemi = bpy.props.PointerProperty(name="Indigo Lamp Hemi Properties", type = Indigo_Lamp_Hemi_Properties)
    
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
    
    
    print("Registered {} with {} modules".format(bl_info["name"], len(modules)))

def unregister():
    try: bpy.utils.unregister_module(__name__)
    except: traceback.print_exc()

    print("Unregistered {}".format(bl_info["name"]))
