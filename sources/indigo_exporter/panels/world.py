import bpy

from .. core import BL_IDNAME

class IndigoLightLayers(bpy.types.Panel):
    bl_idname = "view3d.indigo_light_layers"
    bl_label = "Indigo Light Layers"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "world"

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == BL_IDNAME
    
    def draw(self, context):
        indigo_engine = context.scene.indigo_engine
        
        col = self.layout.column()
        col.operator('indigo.lightlayer_add')
        col.prop(context.scene.indigo_lightlayers, 'ignore')
        
        row = self.layout.row()
        row.label("Default layer gain")
        row.prop(context.scene.indigo_lightlayers, 'default_gain', text="")
        
        for lg_index in range(len(context.scene.indigo_lightlayers.lightlayers)):
            lg = context.scene.indigo_lightlayers.lightlayers[lg_index]
            row = self.layout.row()
            
            row.prop(context.scene.indigo_lightlayers.lightlayers[lg_index], 'lg_enabled')
            row.prop(context.scene.indigo_lightlayers.lightlayers[lg_index], 'name')
            row.prop(context.scene.indigo_lightlayers.lightlayers[lg_index], 'gain')
            
            row.operator('indigo.lightlayer_remove', text="", icon="ZOOMOUT").lg_index=lg_index
            