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

from bpy.types import NodeSocket, Node, ShaderNodeCustomGroup, NodeSocketInterface, NodeTree
from .. core import RENDERER_BL_IDNAME


"""

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


"""






from . tree import *


####################

# Mix-in class for all custom nodes in this tree type.
# Defines a poll function to enable instantiation.
class BlendigoNode:
    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == 'IR_MaterialNodeTree'

class IR_Texture(BlendigoNode, Node):
    bl_label = "Texture"

    image: bpy.props.PointerProperty(type=bpy.types.Image)
    emission_TX_A: bpy.props.FloatProperty()
    emission_TX_B: bpy.props.FloatProperty()
    emission_TX_C: bpy.props.FloatProperty()
    emission_TX_uvset: bpy.props.StringProperty()
    emission_TX_abc_from_tex: bpy.props.BoolProperty()
    emission_TX_smooth: bpy.props.BoolProperty()
    
    def draw_buttons( self, context, layout ):
        col = layout.column()
        col.template_ID_preview(self, "image", open="image.open")
        col.separator()
        
        col = layout.column(align=True)
        col.prop(self, 'emission_TX_A')
        col.prop(self, 'emission_TX_B')
        col.prop(self, 'emission_TX_C')
        col.enabled = self.emission_TX_abc_from_tex == False

        col = layout.column()
        col.prop_search(self, 'emission_TX_uvset', context.object.data, 'uv_layers', text="UV Set")

        row = col.row(align=True)
        row.prop(self, 'emission_TX_abc_from_tex')
        row.prop(self, 'emission_TX_smooth')
    
    def init( self, context ):
        self.outputs.new(IR_Color_Socket.__name__, "Output")
        self.inputs.new(IR_Color_Socket.__name__, "Input")

class IR_Diffuse(BlendigoNode, Node):
    bl_label = "Diffuse Material"
    bl_icon = 'MATERIAL'

    shadow_catcher: bpy.props.BoolProperty()
    sigma: bpy.props.FloatProperty()
    transmitter: bpy.props.BoolProperty()
    
    def draw_buttons( self, context, layout ):
        col = layout.column()
        col.prop(self, 'transmitter')
        if not self.transmitter:
            col.prop(self, 'sigma')
        col.prop(self, 'shadow_catcher')
    
    def init( self, context ):
        self.outputs.new(IR_Color_Socket.__name__, "Output")
        self.inputs.new(IR_Color_Socket.__name__, "Input")

class IR_F_Emission(BlendigoNode, Node):
    bl_label = "Feature: Emission"
    bl_icon = 'MATERIAL'

    emit_layer: bpy.props.StringProperty(name="Light Layer", description="lightlayer; leave blank to use default")
    emit_power: bpy.props.FloatProperty(name="Power", description="Power", default=1500.0, min=0.0, max=1000000.0, update=lambda s,c: s.set_strength(c.material))
    emit_gain_val: bpy.props.FloatProperty(name="Gain", description="Gain", default=1.0, min=0.0, max=1.0, update=lambda s,c: s.set_strength(c.material))
    emit_gain_exp: bpy.props.IntProperty(name="*10^", description="Exponent", default=0, min=-30, max=30, update=lambda s,c: s.set_strength(c.material))
    emission_scale: bpy.props.BoolProperty(name="Emission scale", description="Emission scale", default=False, update=lambda s,c: s.set_strength(c.material))
    emission_scale_measure: bpy.props.EnumProperty(name="Unit", description="Units for emission scale", default="luminous_flux", items=[
        ('luminous_flux', 'lm', 'Luminous flux'),
        ('luminous_intensity', 'cd', 'Luminous intensity (lm/sr)'),
        ('luminance', 'nits', 'Luminance (lm/sr/m/m)'),
        ('luminous_emittance', 'lux', 'Luminous emittance (lm/m/m)')
    ])
    emission_scale_value: bpy.props.FloatProperty(name="Value", description="Emission scale value", default=1.0, min=0.0, soft_min=0.0, max=10.0, soft_max=10.0, update=lambda s,c: s.set_strength(c.material))
    emission_scale_exp: bpy.props.IntProperty(name="*10^", description="Emission scale exponent", default=0, min=-30, max=30, update=lambda s,c: s.set_strength(c.material))
    emit_ies: bpy.props.BoolProperty(name="IES Profile", description="IES Profile", default=False)
    emit_ies_path: bpy.props.StringProperty(subtype="FILE_PATH", name=" IES Path", description=" IES Path", default="")
    backface_emit: bpy.props.BoolProperty(name="Back face emission", description="Controls of back of face is emitting or not", default=False, update=lambda s, c: ubershader_utils.switch_bool(c.material, 'backface_emit', s.backface_emit),)
    em_sampling_mult: bpy.props.FloatProperty(name="Emission Sampling Multiplier", description="A multiplier for the amount of sampling emission from this light material will receive", default=1.0, min=0.0, max=99999.0)

    def draw_buttons( self, context, layout ):
        # col = layout.column()
        # #
        # col.prop(self, 'emission_type')
        
        # if self.emission_type == 'texture':
        #     col = self.layout.column()
        #     col.prop_search(self, 'emission_TX_texture', bpy.data, 'textures')
            
        #     col = self.layout.column()
        #     col.prop(self, 'emission_TX_A')
        #     col.enabled = self.emission_TX_abc_from_tex == False

        #     col = self.layout.column()
        #     col.prop(self, 'emission_TX_B')
        #     col.enabled = self.emission_TX_abc_from_tex == False

        #     col = self.layout.column()
        #     col.prop(self, 'emission_TX_C')
        #     col.enabled = self.emission_TX_abc_from_tex == False

        #     col = self.layout.column()
        #     col.prop_search(self, 'emission_TX_uvset', context.object.data, 'uv_layers')

        #     row = col.row()
        #     row.prop(self, 'emission_TX_abc_from_tex')
        #     row.prop(self, 'emission_TX_smooth')
        # elif self.emission_type == 'spectrum':
        #     col.prop(self, 'emission_SP_type')
        #     if self.emission_SP_type == 'rgb':
        #         row = col.row()
        #         row.prop(self, 'emission_SP_rgb')
        #         #col.prop(self, 'emission_SP_rgb_gain')
        #     elif self.emission_SP_type == 'uniform':
        #         row = col.row(align=True)
        #         row.prop(self, 'emission_SP_uniform_val')
        #         row.prop(self, 'emission_SP_uniform_exp')
        #     elif self.emission_SP_type == 'blackbody':
        #         row = col.row(align=True)
        #         row.prop(self, 'emission_SP_blackbody_temp')
        #         row.prop(self, 'emission_SP_blackbody_gain')
        # col.separator()
        #
        #
        
        col = layout.column()
        col.prop_search(self, 'emit_layer', context.scene.indigo_lightlayers, 'lightlayers')
        
        col.separator()
        col.prop(self, 'emission_scale')
        if self.emission_scale:
            row = col.row(align=True)
            row.prop(self, 'emission_scale_value')
            row.prop(self, 'emission_scale_exp')
            col.prop(self, 'emission_scale_measure')
        else:
            col.prop(self, 'emit_power')
            row = col.row(align=True)
            row.prop(self, 'emit_gain_val')
            row.prop(self, 'emit_gain_exp')
        
        col.separator()    
        col.prop(self, 'em_sampling_mult')
        col.prop(self, 'emit_ies')
        if self.emit_ies:
            col.prop(self, 'emit_ies_path')
        
        col.prop(self, 'backface_emit')
    
    def init( self, context ):
        self.outputs.new(IR_Color_Socket.__name__, "Output")
        self.inputs.new(IR_Color_Socket.__name__, "Color", identifier="Emission Color")

def first(generator):
    """
    Return first element from generator or None if empty
    """
    try:
        return next(generator)
    except StopIteration:
        return None

def NodeProperty(type, /, *, update_node=None, **opts):
    ''' Wrap normal property and its update function with additional function updating the node (sockets etc.) '''
    if 'update' in opts and update_node:
        foreign_f = opts['update']
        def f(self, context):
            update_node(self, context)
            return foreign_f(self, context)
        opts['update'] = f
    elif update_node:
        opts['update'] = update_node
    return type(**opts)

class IR_F_Emission2(BlendigoNode, Node):
    bl_label = "Feature: Emission2"
    bl_icon = 'MATERIAL'

    emit_layer: bpy.props.StringProperty(name="Light Layer", description="lightlayer; leave blank to use default")
    emit_power: bpy.props.FloatProperty(name="Power", description="Power", default=1500.0, min=0.0, max=1000000.0, update=lambda s,c: s.set_strength(c.material))
    emit_gain_val: bpy.props.FloatProperty(name="Gain", description="Gain", default=1.0, min=0.0, max=1.0, update=lambda s,c: s.set_strength(c.material))
    emit_gain_exp: bpy.props.IntProperty(name="*10^", description="Exponent", default=0, min=-30, max=30, update=lambda s,c: s.set_strength(c.material))
    # emission_scale: bpy.props.BoolProperty(name="Emission scale", description="Emission scale", default=False, update=lambda s,c: s.set_strength(c.material))
    
    # template for replacing sockets
    # def emission_scale_un(self, context):
    #     if self.emission_scale:
    #         if 'Emit Power' in self.inputs:
    #             self.inputs.new(IR_Color_Socket.__name__, "Emission Scale")
    #             self.inputs.remove(self.inputs['Emit Power'])
    #     else:
    #         if 'Emission Scale' in self.inputs:
    #             self.inputs.new(IR_Color_Socket.__name__, "Emit Power")
    #             self.inputs.remove(self.inputs['Emission Scale'])
    
    def emission_scale_un(self, context):
        if self.emission_scale:
            first(s for s in self.inputs if s.identifier == 'emit_scale_power').name = "Emit Scale"
        else:
            first(s for s in self.inputs if s.identifier == 'emit_scale_power').name = "Emit Power"
    
    # def set_strength(self, m):
    #     print('set_strength', self, m)
    emission_scale: NodeProperty(bpy.props.BoolProperty, update_node=emission_scale_un, name="Emission scale", description="Emission scale", default=False, update=lambda s,c: s.set_strength(c.material))
    emission_scale_measure: bpy.props.EnumProperty(name="Unit", description="Units for emission scale", default="luminous_flux", items=[
        ('luminous_flux', 'lm', 'Luminous flux'),
        ('luminous_intensity', 'cd', 'Luminous intensity (lm/sr)'),
        ('luminance', 'nits', 'Luminance (lm/sr/m/m)'),
        ('luminous_emittance', 'lux', 'Luminous emittance (lm/m/m)')
    ])
    emission_scale_value: bpy.props.FloatProperty(name="Value", description="Emission scale value", default=1.0, min=0.0, soft_min=0.0, max=10.0, soft_max=10.0, update=lambda s,c: s.set_strength(c.material))
    emission_scale_exp: bpy.props.IntProperty(name="*10^", description="Emission scale exponent", default=0, min=-30, max=30, update=lambda s,c: s.set_strength(c.material))
    emit_ies: bpy.props.BoolProperty(name="IES Profile", description="IES Profile", default=False)
    emit_ies_path: bpy.props.StringProperty(subtype="FILE_PATH", name=" IES Path", description=" IES Path", default="")
    backface_emit: bpy.props.BoolProperty(name="Back face emission", description="Controls of back of face is emitting or not", default=False, update=lambda s, c: ubershader_utils.switch_bool(c.material, 'backface_emit', s.backface_emit),)
    em_sampling_mult: bpy.props.FloatProperty(name="Emission Sampling Multiplier", description="A multiplier for the amount of sampling emission from this light material will receive", default=1.0, min=0.0, max=99999.0)

    def draw_buttons( self, context, layout ):
        col = layout.column()
        col.prop_search(self, 'emit_layer', context.scene.indigo_lightlayers, 'lightlayers')
        
        # col.separator()
        col.prop(self, 'emission_scale')
        if self.emission_scale:
            row = col.row(align=True)
            # row.prop(self, 'emission_scale_value')
            row.prop(self, 'emission_scale_exp')
            col.prop(self, 'emission_scale_measure')
        else:
            # col.prop(self, 'emit_power')
            row = col.row(align=True)
            row.prop(self, 'emit_gain_val')
            row.prop(self, 'emit_gain_exp')
        
        col.separator()    
        col.prop(self, 'em_sampling_mult')
        col.prop(self, 'emit_ies')
        if self.emit_ies:
            col.prop(self, 'emit_ies_path')
        
        col.prop(self, 'backface_emit')
    
    def init( self, context ):
        self.outputs.new(IR_Color_Socket.__name__, "Output")
        self.inputs.new(IR_Color_Socket.__name__, "Color")
        self.inputs.new(IR_Float_Socket.__name__, "Emit Power", identifier="emit_scale_power")

#######
class IR_BlackBody(BlendigoNode, Node):
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
        self.outputs.new(IR_SP_Socket.__name__, "Output")

class IR_Uniform(BlendigoNode, Node):
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
        self.outputs.new(IR_SP_Socket.__name__, "Output")

class IR_RGB(BlendigoNode, Node):
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
        self.outputs.new(IR_Color_Socket.__name__, "Output")

#######



# from .ubershader_utils import current_uber_name, ensure_ubershader

# class IR_BlendigoUberShader(ShaderNodeCustomGroup):
#     '''Blendigo UberShader for Indigo Render'''
#     bl_label = "Blendigo UberShader"
    
#     # def draw_buttons( self, context, layout ):
#     #     layout.label(text="Draw buttons")
    
#     def init( self, context ):
#         self.node_tree = ensure_ubershader()


#     def socket_value_update(context):
#         print('socket_value_update', context)
    
#     def update(self):
#         print("update", self)



# Custom socket type
class MyCustomSocket(NodeSocket):
    # Description string
    '''Custom node socket type'''
    # Optional identifier string. If not explicitly defined, the python class name is used.
    bl_idname = 'CustomSocketType'
    # Label for nice name display
    bl_label = "Custom Node Socket"

    # Enum items list
    my_items = (
        ('DOWN', "Down", "Where your feet are"),
        ('UP', "Up", "Where your head should be"),
        ('LEFT', "Left", "Not right"),
        ('RIGHT', "Right", "Not left"),
    )

    my_enum_prop: bpy.props.EnumProperty(
        name="Direction",
        description="Just an example",
        items=my_items,
        default='UP',
    )

    # Optional function for drawing the socket input value
    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            col = layout.column(align=True)
            col.label(text=text)
            col.label(text='text 2')
            if not 'World 2' in node.inputs:
                s = node.inputs.new('NodeSocketFloat', "World 2")
            # node.inputs.remove(s)
        else:
            layout.prop(self, "my_enum_prop", text=text)

    # Socket color
    def draw_color(self, context, node):
        return (1.0, 0.4, 0.216, 0.5)


# Derived from the Node base type.
class IR_NodeMatOutput(BlendigoNode, Node):
    '''Indigo Renderer Material Output'''
    # Label for nice name display
    bl_label = "Material Output"
    # Icon identifier
    bl_icon = 'MATERIAL'

    # === Custom Properties ===
    # These work just like custom properties in ID data blocks
    # Extensive information can be found under
    # http://wiki.blender.org/index.php/Doc:2.6/Manual/Extensions/Python/Properties
    my_string_prop: bpy.props.StringProperty()
    my_float_prop: bpy.props.FloatProperty(default=3.1415926)

    # === Optional Functions ===
    # Initialization function, called when a new node is created.
    # This is the most common place to create the sockets for a node, as shown below.
    # NOTE: this is not the same as the standard __init__ function in Python, which is
    #       a purely internal Python method and unknown to the node system!
    def init(self, context):
        self.inputs.new('CustomSocketType', "Hello")
        self.inputs.new('NodeSocketFloat', "World")
        self.inputs.new('NodeSocketVector', "!")

        self.outputs.new('NodeSocketColor', "How")
        self.outputs.new('NodeSocketColor', "are")
        self.outputs.new('NodeSocketFloat', "you")

    # Copy function to initialize a copied node from an existing one.
    def copy(self, node):
        print("Copying from node ", node)

    # Free function to clean up on removal.
    def free(self):
        print("Removing node ", self, ", Goodbye!")

    # Additional buttons displayed on the node.
    def draw_buttons(self, context, layout):
        layout.label(text="Node settings")
        layout.prop(self, "my_float_prop")

    # Detail buttons in the sidebar.
    # If this function is not defined, the draw_buttons function is used instead
    def draw_buttons_ext(self, context, layout):
        layout.prop(self, "my_float_prop")
        # my_string_prop button will only be visible in the sidebar
        layout.prop(self, "my_string_prop")

    # Optional: custom label
    # Explicit user label overrides this, but here we can define a label dynamically
    def draw_label(self):
        return "I am a custom node"

class IR_NodeDiffuse(BlendigoNode, Node):
    '''Indigo Renderer Material Output'''
    # Label for nice name display
    bl_label = "Diffuse Material"
    # Icon identifier
    bl_icon = 'MATERIAL'

    def init(self, context):
        self.outputs.new('NodeSocketColor', "How")

class BlendigoNodeCategory( NodeCategory ):
    @classmethod
    def poll(cls, context):
        return (context.space_data.type == 'NODE_EDITOR' and
                context.space_data.tree_type == 'IR_MaterialNodeTree')

# categories = [ BlendigoNodeCategory( "IRNodes", "Indigo Render Nodes", items = [
#     NodeItem('IR_M_Diffuse'),  # type: ignore
#     NodeItem('IR_S_Emission'),  # type: ignore
#     # NodeItem('IR_BlackBody'),
#     # NodeItem('IR_Uniform'),
#     # NodeItem('IR_RGB'),
#     NodeItem('IR_Spectrum'),  # type: ignore
#     NodeItem('IR_Texture'),  # type: ignore
#     NodeItem('IR_BlendigoUberShader'),  # type: ignore
# ] ) ]
categories = [ BlendigoNodeCategory( "IR_Nodes", "Blendigo Nodes", items = [
    NodeItem(IR_Texture.__name__),
    NodeItem(IR_RGB.__name__),
    NodeItem(IR_Uniform.__name__),
    NodeItem(IR_BlackBody.__name__),
    NodeItem(IR_F_Emission.__name__),
    NodeItem(IR_F_Emission2.__name__),
] ) ]

classes={
    # IR_M_Diffuse,
    # IR_OptionShardSocket,
    # IR_BlendigoUberShader,
}

def register():
    nodeitems_utils.register_node_categories( "IRNodes", categories )
    for c in classes:
        bpy.utils.register_class( c )

def unregister():
    nodeitems_utils.unregister_node_categories( "IRNodes" )
    for c in classes:
        bpy.utils.unregister_class( c )

#####################

def show_node_tree(context, node_tree):
    for area in context.screen.areas:
        if area.type == "NODE_EDITOR":
            for space in area.spaces:
                if space.type == "NODE_EDITOR" and not space.pin and space.tree_type in {'', 'ShaderNodeTree', 'IR_MaterialNodeTree'}:
                    space.tree_type = node_tree.bl_idname
                    space.node_tree = node_tree
                    return True
    return False

class IR_OT_material_show_node_tree(bpy.types.Operator):
    bl_idname = "blendigo.material_show_node_tree"
    bl_label = "Show Nodes"
    bl_description = "Show nodes of this material"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.active_material and obj.active_material.indigo_material.node_tree

    def execute(self, context):
        mat = context.active_object.active_material
        node_tree = mat.indigo_material.node_tree

        if show_node_tree(context, node_tree):
            return {"FINISHED"}

        self.report({"ERROR"}, "Open a node editor first")
        return {"CANCELLED"}

def init_mat_node_tree(node_tree):
    node_tree.use_fake_user = True # TODO: check if still needed in the current Blender

    nodes = node_tree.nodes

    output = nodes.new("IR_NodeMatOutput")
    output.location = 300, 200
    output.select = False

    diffuse = nodes.new("IR_NodeDiffuse")
    diffuse.location = 50, 200

    node_tree.links.new(diffuse.outputs[0], output.inputs[0])

class IR_OT_material_node_tree_new(bpy.types.Operator):
    bl_idname = "blendigo.material_node_tree_new"
    bl_label = "New"
    bl_description = "Create a material node tree"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object and not context.object.library

    def execute(self, context):
        mat = context.object.active_material
        if mat:
            name = make_nodetree_name(mat.name)
        else:
            name = "IR Material Node Tree"

        node_tree = bpy.data.node_groups.new(name=name, type="IR_MaterialNodeTree")
        init_mat_node_tree(node_tree)

        if mat:
            mat.indigo_material.node_tree = node_tree

        show_node_tree(context, node_tree)
        return {"FINISHED"}

def make_nodetree_name(material_name):
    return "Nodes_IR_" + material_name

class _NodeOperator():
    @classmethod
    def poll(cls, context):
        return context.object and not context.object.library

class IR_OT_mat_nodetree_new(bpy.types.Operator, _NodeOperator):
    bl_idname = "blendigo.mat_nodetree_new"
    bl_label = "New"
    bl_description = "Create a material node tree"
    bl_options = {"UNDO"}

    def execute(self, context):
        mat = context.object.active_material
        if mat:
            name = make_nodetree_name(mat.name)
        else:
            name = "IR Material Node Tree"

        node_tree = bpy.data.node_groups.new(name=name, type="IR_MaterialNodeTree")
        init_mat_node_tree(node_tree)

        if mat:
            mat.indigo_material.node_tree = node_tree

        show_node_tree(context, node_tree)
        return {"FINISHED"}

class IR_OT_material_new(bpy.types.Operator, _NodeOperator):
    bl_idname = "blendigo.material_new"
    bl_label = "New"
    bl_description = "Create a new material and node tree"
    bl_options = {"UNDO"}

    def execute(self, context):
        mat = bpy.data.materials.new(name="Material")
        tree_name = make_nodetree_name(mat.name)
        node_tree = bpy.data.node_groups.new(name=tree_name, type="IR_MaterialNodeTree")
        init_mat_node_tree(node_tree)
        mat.indigo_material.node_tree = node_tree

        obj = context.active_object
        if obj.material_slots:
            obj.material_slots[obj.active_material_index].material = mat
        else:
            obj.data.materials.append(mat)

        # For viewport render, we have to update the object
        # because the newly created material is not yet assigned there
        obj.update_tag()
        show_node_tree(context, node_tree)

        return {"FINISHED"}

class IR_OT_material_unlink(bpy.types.Operator, _NodeOperator):
    bl_idname = "blendigo.material_unlink"
    bl_label = "Unlink data-block"
    bl_description = "Unlink data-block"
    bl_options = {"UNDO"}

    def execute(self, context):
        obj = context.active_object
        if obj.material_slots:
            obj.material_slots[obj.active_material_index].material = None
        return {"FINISHED"}

class IR_OT_material_copy(bpy.types.Operator, _NodeOperator):
    bl_idname = "blendigo.material_copy"
    bl_label = "Copy"
    bl_description = "Duplicate and make material single user"
    bl_options = {"UNDO"}

    def execute(self, context):
        current_mat = context.active_object.active_material

        # Create a copy of the material
        new_mat = current_mat.copy()

        current_node_tree = current_mat.indigo_material.node_tree

        if current_node_tree:
            # Create a copy of the node_tree as well
            new_node_tree = new_mat.indigo_material.node_tree = current_node_tree.copy()
            new_node_tree.name = make_nodetree_name(new_mat.name)
            new_node_tree.use_fake_user = True

        context.active_object.active_material = new_mat

        return {"FINISHED"}

node_tree_cache = None
class IR_OT_ctx_menu_material_copy(bpy.types.Operator):
    bl_idname = "blendigo.cxt_menu_material_copy"
    bl_label = "Copy Material"
    bl_description = "Copy the material settings and nodes"
    bl_options = {"UNDO", "REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.object and not context.object.library and context.object.active_material

    def execute(self, context):
        global node_tree_cache
        bpy.ops.material.copy()
        current_mat = context.active_object.active_material
        current_node_tree = current_mat.indigo_material.node_tree
        if current_node_tree:
            copy = current_node_tree.copy()
            copy.use_fake_user = False
            node_tree_cache = copy.name
        else:
            node_tree_cache = None

        return {"FINISHED"}

class IR_OT_ctx_menu_material_paste(bpy.types.Operator):
    bl_idname = "blendigo.cxt_menu_material_paste"
    bl_label = "Paste Material"
    bl_description = "Paste the material settings and nodes"
    bl_options = {"UNDO", "REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.object and not context.object.library and context.object.active_material

    def execute(self, context):
        global node_tree_cache
        bpy.ops.material.paste()
        current_mat = context.active_object.active_material
        if not node_tree_cache or node_tree_cache not in bpy.data.node_groups:
            return {"FINISHED"}
        copy = bpy.data.node_groups[node_tree_cache].copy()
        copy.use_fake_user = True
        current_mat.indigo_material.node_tree = copy

        return {"FINISHED"}

def name_with_lib_prefix(material):
    return material.name if not material.library else "L " + material.name

class IR_OT_material_select(bpy.types.Operator, _NodeOperator):
    """ Material selection dropdown """
    bl_idname = "blendigo.material_select"
    bl_label = "Select Material"
    bl_property = "material"

    callback_list = []

    def mat_list_cb(self, context):
        mats = [(str(index), name_with_lib_prefix(mat), "") for index, mat in enumerate(bpy.data.materials) if not mat.is_grease_pencil]
        # Blender docs:
        # There is a known bug with using a callback, Python must keep a reference
        # to the strings returned by the callback or Blender will misbehave or even crash.
        IR_OT_material_select.callback_list = mats
        return mats

    material: bpy.props.EnumProperty(name="Materials", items=mat_list_cb)

    def execute(self, context):
        mat_idx = int(self.material)
        mat = bpy.data.materials[mat_idx]
        context.object.active_material = mat
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}