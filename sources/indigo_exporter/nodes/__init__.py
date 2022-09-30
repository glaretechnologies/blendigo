'''
Issue:
Creating nodes that store information about Indigo and EEVEE/Cycles materials at the same time.
Blender material part must imitate Indigo material. System has to be easy to read for the user.

Problems:
1. New shader nodes cannot be created with Python API.
Workaround: ShaderNodeCustomGroup with a shader group needs to be used to wrap Blender builtin nodes.

2. Easy to read
Solution: Moving material options (like Bump map) to another option node (let's call it Option Shard?).
Additional options cannot be simply arranged in one node anyway because buttons and sockets are drawn seperately.
Instead of passing each property by one line let's track whole Option Shards instead.
That goes against Blender's conventions but should make more sense here.

3. Custom socket types cannot pass data to the wrapped group, e.g. Option Shard inner properties won't be passed anywhere.
Workaround:
    - Creating new shader group for each initialized ShaderNodeCustomGroup type node 
    - Reading properties of connected Option Shards and copying them to the inner group.
      Group should already represent all possible states (like option turned on/off, texture/color, texture scale, brightnesss)
    - Removing unused groups when parent node is removed

4. Filtering nodes in the shader editor (only Indigo nodes should be visible)
No solution at this moment.

5. Custom shaders take really long time to recompile (or start recompiling).
    E.g. seems like Blender does not know that a texture was connected even though color socket is part of the inner shader group...
    Switching area fullscreen initiates the refresh. Probably some refresh tag is needed.
    Update: Actually, CUSTOM type socket makes EEVEE/Cycles go into updating loop (node's update() function is called constantly)
    but actual changes do not get propagated.

=========

Two possible paths:
0. Creating Indigo-EEVEE-ubershader that will store and react to all material settings (common for all paths)
1. Storing material settings in nodes and parsing nodes during export.
    Pros:
        - building materials in a way that is more in line with Blender's conventions
        - possibly can be extended with other nodes like texture blending etc.
        - should be flexible and robust when done right
        - materials compatible with EEVEE and Cycles
        - simplyfies things like storing texture data by design
          Texture needs to be a node, not a filename/Blender ID/something else.
          Currently, this makes storing textures problematic, as back in the day,
          in the old Blender ways, textures were stored in the material data but now they have
          to be stored as brush textures with a fake user as there is no such thing as material texture anymore.
          Moving this to nodes solves this problem by desing.
    Cons:
        - a bit convoluted system
2. Creating nodes and altering them on demand. Keeping the node system inaccessible to the user.
    Pros:
        - should be easy to implement into the current system (unless I'm missing some vital points)
        - materials compatible with EEVEE and Cycles but nodes not accessible to the user unless other renderer is chosen
    Cons:
        - uses old panel ui system
        - needs a new system to create hidden texture nodes on demand and link them with interface
          There is no point in keeping current brush texture system if all textures need to be recreated in the nodes anyway.
'''
import bpy
import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem, NodeItemCustom

from bpy.types import NodeSocket, Node, ShaderNodeCustomGroup, NodeSocketInterface

class OptionShard:
    '''Mix-in class'''
    pass

class InputShard:
    '''Mix-in class'''
    pass

class IR_OptionShardSocket(NodeSocket):
    # Description string
    '''Indigo Material Options'''
    # Label for nice name display
    bl_label = "Material Option Socket"
    
    def __init__(self):
        # In Blender 3.3.0 is_multi_input is read only but it may change soon
        if not self.rna_type.properties['is_multi_input'].is_readonly:
            self.is_multi_input= True
        self.link_limit = 0
        self.display_shape = 'SQUARE' #  [CIRCLE, SQUARE, DIAMOND, CIRCLE_DOT, SQUARE_DOT, DIAMOND_DOT]
        # self.type = 'CUSTOM' # CUSTOM, VALUE, INT, BOOLEAN, VECTOR, STRING, RGBA, SHADER, OBJECT, IMAGE, GEOMETRY, COLLECTION, TEXTURE, MATERIAL

    # Optional function for drawing the socket input value
    def draw(self, context, layout, node, text):
        layout.label(text=text)
        return
        if self.is_output or self.is_linked:
            layout.label(text=text)
        else:
            layout.label(text=text)

    # Socket color
    def draw_color(self, context, node):
        return (0.25, 0.205, 0.974, 1.0)
    
    def socket_value_update(context):
        print('socket_value_update', context)

class IR_OptionShardSocketInterface(NodeSocketInterface):
    bl_socket_idname = IR_OptionShardSocket.__name__ # required, Blender will complain if it is missing
    # those are (at least) used under Interface in N-menu in
    # node editor when viewing a node group, for input and output sockets
    def draw(self, context, layout):
        pass
    def draw_color(self, context):
        return (0,1,1,1)

class IR_MaterialSpectrumSocket(NodeSocket):
    '''Indigo Material Spectrum Type'''
    bl_label = "Indigo Spectrum"
    
    def __init__(self):
        self.link_limit = 1
        self.display_shape = 'SQUARE' #  [CIRCLE, SQUARE, DIAMOND, CIRCLE_DOT, SQUARE_DOT, DIAMOND_DOT]

    # Optional function for drawing the socket input value
    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text=text)
        else:
            layout.label(text=text)

    # Socket color
    def draw_color(self, context, node):
        return (0.9, 0.9, 0.1, 1.0)

class IR_M_Diffuse(ShaderNodeCustomGroup):
    '''Indigo Render Diffuse'''
    bl_label = "Indigo Diffuse"
    eevee_type_name = "ShaderNodeBsdfDiffuse"
    
    # def draw_buttons( self, context, layout ):
    #     layout.label(text="Draw buttons")
    
    def init( self, context ):
        self.group_builder(self.eevee_type_name)
        # self.node_tree = bpy.data.node_groups['Diffuse']
        self.inputs.new('IR_OptionShardSocket', 'Option Shards')
    
    def group_builder(self, ntype: str):
        # Create new group for each node, so each node can manipulate its insides.
        gname = f'_{ntype}'
        self.node_tree = bpy.data.node_groups.new(gname, 'ShaderNodeTree')
        
        nodes = self.node_tree.nodes
        links = self.node_tree.links
        node = nodes.new(self.eevee_type_name)
        inp = nodes.new("NodeGroupInput")
        out = nodes.new("NodeGroupOutput")

        for input in node.inputs:
            links.new(inp.outputs[-1], input)
        
        for output in node.outputs:
            links.new(output, out.inputs[-1])

    def free(self):
        bpy.data.node_groups.remove(self.node_tree)
    
    def copy(self, node):
        self.group_builder(self.eevee_type_name)


    # def socket_value_update(context):
    #     print('socket_value_update', context)
    
    def update(self):
        print("update", self)

class IR_S_Emission(OptionShard, Node):
    '''Indigo Render Emission Shard'''
    bl_label = "Emission Shard"
    
    def draw_buttons( self, context, layout ):
        # mockup.
        indigo_material = context.object.active_material.indigo_material
        indigo_material_emission = indigo_material.indigo_material_emission
        
        col = layout.column()
        #
        #
        
        col.prop_search(indigo_material_emission, 'emit_layer', context.scene.indigo_lightlayers, 'lightlayers')
        
        col.separator()
        col.prop(indigo_material_emission, 'emission_scale')
        if indigo_material_emission.emission_scale:
            row = col.row(align=True)
            row.prop(indigo_material_emission, 'emission_scale_value')
            row.prop(indigo_material_emission, 'emission_scale_exp')
            col.prop(indigo_material_emission, 'emission_scale_measure')
        else:
            col.prop(indigo_material_emission, 'emit_power')
            row = col.row(align=True)
            row.prop(indigo_material_emission, 'emit_gain_val')
            row.prop(indigo_material_emission, 'emit_gain_exp')
        
        col.separator()    
        col.prop(indigo_material_emission, 'em_sampling_mult')
        col.prop(indigo_material_emission, 'emit_ies')
        if indigo_material_emission.emit_ies:
            col.prop(indigo_material_emission, 'emit_ies_path')
        
        col.prop(indigo_material_emission, 'backface_emit')
    
    def init( self, context ):
        self.outputs.new('IR_OptionShardSocket', "Output")
        self.inputs.new('IR_MaterialSpectrumSocket', "Color", identifier="Emission Color")

"""
class IR_BlackBody(InputShard, Node):
    '''Indigo Render Emission Shard'''
    bl_label = "Black Body"
    
    def draw_buttons( self, context, layout ):
        # mockup.
        indigo_material = context.object.active_material.indigo_material
        indigo_material_emission = indigo_material.indigo_material_emission
        
        col = layout.column()
        #
        row = col.row(align=True)
        row.prop(indigo_material_emission, 'emission_SP_blackbody_temp')
        row.prop(indigo_material_emission, 'emission_SP_blackbody_gain')
        #
    
    def init( self, context ):
        self.outputs.new('IR_MaterialSpectrumSocket', "Output")

class IR_Uniform(InputShard, Node):
    bl_label = "Uniform"
    
    def draw_buttons( self, context, layout ):
        # mockup.
        indigo_material = context.object.active_material.indigo_material
        indigo_material_emission = indigo_material.indigo_material_emission
        
        col = layout.column()
        #
        row = col.row(align=True)
        row.prop(indigo_material_emission, 'emission_SP_uniform_val')
        row.prop(indigo_material_emission, 'emission_SP_uniform_exp')
        #
    
    def init( self, context ):
        self.outputs.new('IR_MaterialSpectrumSocket', "Output")

class IR_RGB(InputShard, Node):
    bl_label = "RGB"
    
    def draw_buttons( self, context, layout ):
        # mockup.
        indigo_material = context.object.active_material.indigo_material
        indigo_material_emission = indigo_material.indigo_material_emission
        
        col = layout.column()
        #
        row = col.row(align=True)
        row.prop(indigo_material_emission, 'emission_SP_rgb')
        #
    
    def init( self, context ):
        self.outputs.new('IR_MaterialSpectrumSocket', "Output")
"""
class IR_Spectrum(InputShard, Node):
    bl_label = "Spectrum"
    
    def draw_buttons( self, context, layout ):
        # mockup.
        indigo_material = context.object.active_material.indigo_material
        indigo_material_emission = indigo_material.indigo_material_emission
        
        col = layout.column()
        #
        col.prop(indigo_material_emission, 'emission_SP_type')
        if indigo_material_emission.emission_SP_type == 'rgb':
            row = col.row()
            row.prop(indigo_material_emission, 'emission_SP_rgb')
            #col.prop(indigo_material_emission, 'emission_SP_rgb_gain')
        elif indigo_material_emission.emission_SP_type == 'uniform':
            row = col.row(align=True)
            row.prop(indigo_material_emission, 'emission_SP_uniform_val')
            row.prop(indigo_material_emission, 'emission_SP_uniform_exp')
        elif indigo_material_emission.emission_SP_type == 'blackbody':
            row = col.row(align=True)
            row.prop(indigo_material_emission, 'emission_SP_blackbody_temp')
            row.prop(indigo_material_emission, 'emission_SP_blackbody_gain')
        #
    
    def init( self, context ):
        self.outputs.new('IR_MaterialSpectrumSocket', "Output")

class IR_Texture(InputShard, Node):
    bl_label = "Texture"

    image : bpy.props.PointerProperty(type=bpy.types.Image)
    
    def draw_buttons( self, context, layout ):
        # mockup.
        indigo_material = context.object.active_material.indigo_material
        indigo_material_emission = indigo_material.indigo_material_emission
        
        col = layout.column()
        # col.template_image(self, 'image', self.)
        # col.template_any_ID(self, 'image', 'image')
        # col.template_ID(self, 'image', new='image.new', open='image.open')
        col.template_ID_preview(self, "image", open="image.open")
        col.separator()
        #
        # col.prop_search(indigo_material_emission, 'emission_TX_texture', bpy.data, 'textures')
        
        col = layout.column()
        col.prop(indigo_material_emission, 'emission_TX_A')
        col.enabled = indigo_material_emission.emission_TX_abc_from_tex == False

        col = layout.column()
        col.prop(indigo_material_emission, 'emission_TX_B')
        col.enabled = indigo_material_emission.emission_TX_abc_from_tex == False

        col = layout.column()
        col.prop(indigo_material_emission, 'emission_TX_C')
        col.enabled = indigo_material_emission.emission_TX_abc_from_tex == False

        col = layout.column()
        col.prop_search(indigo_material_emission, 'emission_TX_uvset', context.object.data, 'uv_layers')

        row = col.row()
        row.prop(indigo_material_emission, 'emission_TX_abc_from_tex')
        row.prop(indigo_material_emission, 'emission_TX_smooth')
        #
    
    def init( self, context ):
        self.outputs.new('IR_MaterialSpectrumSocket', "Output")











class BlendigoNodeCategory( NodeCategory ):
    @classmethod
    def poll(cls, context):
        return (context.space_data.type == 'NODE_EDITOR' and
                context.space_data.tree_type == 'ShaderNodeTree')

categories = [ BlendigoNodeCategory( "IRNodes", "Indigo Render Nodes", items = [
    NodeItem('IR_M_Diffuse'),
    NodeItem('IR_S_Emission'),
    # NodeItem('IR_BlackBody'),
    # NodeItem('IR_Uniform'),
    # NodeItem('IR_RGB'),
    NodeItem('IR_Spectrum'),
    NodeItem('IR_Texture'),
] ) ]

classes={
    IR_M_Diffuse,
    # IR_OptionShardSocket,
}

def register():
    nodeitems_utils.register_node_categories( "IRNodes", categories )
    for c in classes:
        bpy.utils.register_class( c )

def unregister():
    nodeitems_utils.unregister_node_categories( "IRNodes" )
    for c in classes:
        bpy.utils.unregister_class( c )

