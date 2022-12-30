import bpy
import bl_ui

from .. core import RENDERER_BL_IDNAME
from .. properties.material import PROPERTY_GROUP_USAGE

class texture_subpanel():
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "texture"
    
    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == RENDERER_BL_IDNAME \
            and context.texture
        # and context.object.active_material 
        # and context.texture
        # and context.object.active_material.texture_slots[context.object.active_material.active_texture_index] \

class INDIGO_PT_ui_texture(texture_subpanel, bpy.types.Panel):
    bl_label = 'Indigo Render Texture Settings'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        #row = self.layout.row(align=True)
        indigo_texture = context.texture.indigo_texture # context.object.active_material.texture_slots[context.object.active_material.active_texture_index].texture.indigo_texture
        row = col.row()
        row.prop(indigo_texture, 'image_ref', expand=True)
        if indigo_texture.image_ref == 'blender':
            col.prop_search(indigo_texture, 'image', bpy.data, 'images')
        elif indigo_texture.image_ref == 'file':
            col.prop(indigo_texture, 'path')
        col.prop(indigo_texture, 'gamma')
        col.prop(indigo_texture, 'A')
        col.prop(indigo_texture, 'B')
        col.prop(indigo_texture, 'C')

# class INDIGO_PT_ui_texture_list(texture_subpanel, bpy.types.Panel):
#     bl_label = 'Indigo Render Texture Settings'

#     # index: bpy.props.IntProperty()
    
#     @classmethod
#     def poll(cls, context):
#         return context.scene.render.engine == BL_IDNAME

#     def draw(self, context):
#         layout = self.layout
#         print(context.texture)
#         layout.template_ID(context.texture_user, "texture", new="texture.new")
#         layout.template_list("UI_UL_list", "INDIGO_PT_ui_texture_list", bpy.data, "textures", context.active_object.active_material.indigo_material, 'texture_list_index')