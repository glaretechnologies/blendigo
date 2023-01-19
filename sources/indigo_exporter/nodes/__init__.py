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
    
    Won't work. Data can't be reliably stored in EEVEE shader nodes.
2. Creating nodes and altering them on demand. Keeping the node system inaccessible to the user.
    Pros:
        - should be easy to implement into the current system (unless I'm missing some vital points)
        - materials compatible with EEVEE and Cycles but nodes not accessible to the user unless other renderer is chosen
    Cons:
        - uses old panel ui system
        - needs a new system to create hidden texture nodes on demand and link them with interface
          There is no point in keeping current brush texture system if all textures need to be recreated in the nodes anyway.
    Currently in master
3. Syncing two separate node trees.
'''
import bpy
import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem, NodeItemCustom
from xml.etree import ElementTree as ET

from bpy.types import NodeSocket, Node, ShaderNodeCustomGroup, NodeSocketInterface, NodeTree
from . import xml_utils as _xml
from .. core import RENDERER_BL_IDNAME
from . ubershader_utils import fast_lookup, get_ubershader, new_eevee_node
from . tree import *

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








####################
# TODO: gamma/ABC node to alter texture's ABC
# eevee node can take Original ABC output of eevee texture node.
# blendigo node can look for Alter ABC parent node of blendigo texture
# override ensure_eevee_upward_links in IR_Texture to connect ABC Original to Alter ABC

class IR_Texture(BlendigoNode, Node):
    bl_label = "Texture"
    # ubername = "ShaderNodeTexImage"
    ubername = "_IndigoTextureUberShader_v1"

    def image_notify_callback(self, eevee_node, update_input_name):
        eevee_tex = eevee_node.node_tree.nodes['Image Texture']
        new_image = getattr(self, update_input_name)
        if eevee_tex.image is new_image:
            return
        eevee_tex.image = new_image
        if new_image:
            new_image.colorspace_settings.name = 'Raw'

    image: NodeProperty(bpy.props.PointerProperty, identifier='image', notify_callback=image_notify_callback, type=bpy.types.Image)
    TX_A: NodeProperty(bpy.props.FloatProperty, identifier='TX_A', name='(A) Brightness', precision=5,)
    TX_B: NodeProperty(bpy.props.FloatProperty, identifier='TX_B', name='(B) Scale', precision=5, default=1)
    TX_C: NodeProperty(bpy.props.FloatProperty, identifier='TX_C', name='(C) Offset', precision=5,)
    TX_exponent: NodeProperty(bpy.props.FloatProperty, identifier='TX_exponent', name='Gamma', precision=5, default=2.2, min=0.001)
    
    # def TX_uvset_notify_callback(self, eevee_node, update_input_name):
    #     print(self, eevee_node, update_input_name)
    #     try:
    #         from .ubershader_utils import _ensure_uv_node
    #         material = bpy.context.object.active_material
    #         uv_node = _ensure_uv_node(eevee_node, material)
    #         uv_node.uv_map = getattr(self, update_input_name)
    #     except:
    #         import traceback
    #         traceback.print_exc()
    def TX_uvset_notify_callback(self, eevee_node, update_input_name):
        eevee_uv = eevee_node.node_tree.nodes['UV Map']
        new_uv_map = getattr(self, update_input_name)
        if eevee_uv.uv_map != new_uv_map:
            eevee_uv.uv_map = new_uv_map

    TX_uvset: NodeProperty(bpy.props.StringProperty, identifier='TX_uvset', notify_callback=TX_uvset_notify_callback)
    # TX_abc_from_tex: NodeProperty(bpy.props.BoolProperty, identifier='TX_abc_from_tex', name='Use texture A,B,C')
    TX_smooth: NodeProperty(bpy.props.BoolProperty, identifier='TX_smooth', name='Smooth', description='Smooth the texture by up-converting from 8bit to 16bit (for bumpmaps etc)',)
    
    def draw_buttons( self, context, layout ):
        col = layout.column()
        col.template_ID_preview(self, "image", open="image.open")
        col.separator()
        
        col = layout.column(align=True)
        col.prop(self, 'TX_A')
        col.prop(self, 'TX_B')
        col.prop(self, 'TX_C')
        col.prop(self, 'TX_exponent')
        # col.enabled = self.TX_abc_from_tex == False

        col = layout.column()
        col.prop_search(self, 'TX_uvset', context.object.data, 'uv_layers', text="UV Set")

        row = col.row(align=True)
        # row.prop(self, 'TX_abc_from_tex')
        row.prop(self, 'TX_smooth')
    
    def init_inputs( self, context ):
        self.outputs.new(IR_TX_Socket.__name__, "Texture", identifier='colour_SP_rgb')
        # self.inputs.new(IR_Color_Socket.__name__, "Input")
    
    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement):
        ''' Emission XML '''
        texture = mat_data.append_tag('texture')
        texture.append_tag('path', getattr(self.image, 'filepath', ''))
        texture.append_tag('a', self.TX_A)
        texture.append_tag('b', self.TX_B)
        texture.append_tag('c', self.TX_C)
        texture.append_tag('exponent', self.TX_exponent)

class IR_Diffuse(IR_MaterialType, Node):
    bl_label = "Diffuse Material"
    bl_icon = 'NODE_MATERIAL'
    ubername = "_IndigoDiffuseUberShader_v1"

    shadow_catcher: NodeProperty(bpy.props.BoolProperty, identifier='shadow_catcher')
    sigma: NodeProperty(bpy.props.FloatProperty, identifier='sigma')
    transmitter: NodeProperty(bpy.props.BoolProperty, identifier='transmitter')
    
    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, 'transmitter')
        if not self.transmitter:
            col.prop(self, 'sigma')
        col.prop(self, 'shadow_catcher')
    
    def init_inputs(self, context):
        self.outputs.new(IR_Material_Socket.__name__, "Material")
        self.inputs.new(IR_Color_Socket.__name__, "Color", identifier='colour_SP_rgb')
        self.inputs.new(IR_F_Emission_Socket.__name__, "Emission", identifier='emission_bool')
        self.inputs.new(IR_F_Bump_Socket.__name__, "Bump", identifier='bump_bool')
        self.inputs.new(IR_F_Normal_Socket.__name__, "Normal", identifier='normal_bool')
        self.inputs.new(IR_F_Displacement_Socket.__name__, "Displacement", identifier='displacement_bool')
    
    def build_xml(self):
        ''' Diffuse xml '''
        mat_uid = get_uid(self)
        material = _xml.XMLElement('material')
        material.append_tag('uid', mat_uid)
        material.append_tag('name', self.id_data.material.name)

        # diffuse_transmitter
        # diffuse
        # oren_nayar sigma
        if self.shadow_catcher:
            material.append_tag('shadow_catcher', self.shadow_catcher)
        
        if self.transmitter:
            mat_data = material.append_tag('diffuse_transmitter')
        elif self.sigma != 0:
            mat_data = material.append_tag('oren_nayar')
            mat_data.append_tag('sigma', self.sigma)
        else:
            mat_data = material.append_tag('diffuse')

        connected_sockets = set()
        for i, link in self.iterate_inputs():
            identifier = link.to_socket.identifier
            connected_sockets.add(identifier)
            if isinstance(link.from_node, MaterialFeatureFamily):
                link.from_node.complete_xml(material, mat_data)
            elif identifier == 'colour_SP_rgb':
                albedo = mat_data.append_tag('albedo')
                link.from_node.complete_xml(material, albedo)
        print(connected_sockets)

        if 'colour_SP_rgb' not in connected_sockets:
            constant = mat_data.append_tag(('albedo', 'constant'))
            rgb = constant.append_tag('rgb')
            rgb.append_tag('rgb', _xml.wrap.RGB(self.get_input('colour_SP_rgb').default_value[:]))
            rgb.append_tag('gamma', 1)

        
        return (material.etree_element,)

processed_materials = dict()
class AlreadyProcessedException(Exception):
    def __init__(self, uid, message="UID already exists"):
        super().__init__(message)
        self.uid = uid

def get_uid(obj, offset=0):
    global processed_materials
    objhash = hash(obj)
    if objhash in processed_materials:
        # already processed
        raise AlreadyProcessedException(processed_materials[objhash])
    
    uid = processed_materials[objhash] = 10000 + len(processed_materials)
    return uid

class IR_Mix(IR_MaterialType, Node):
    bl_label = "Mix Materials"
    bl_icon = 'NODE_MATERIAL'
    ubername = "_IndigoBlendedUberShader_v1"

    step_blend: NodeProperty(bpy.props.BoolProperty, identifier='step_blend', description="Disables partial blends so the result is either material A or B, depending on whether the blend amount (constant or map) is >= 0.5.")
    
    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, 'step_blend')
    
    def init_inputs(self, context):
        self.outputs.new(IR_Material_Socket.__name__, "Material")
        # self.inputs.new(IR_Float_Socket.__name__, "Blend Amount", identifier="blend_amount").description="A constant blending factor; 1.0 means 100% of Material A is used, 0.0 means 100% of material B is used."
        self.inputs.new(IR_Slider_Socket.__name__, "Blend Amount", identifier="blend_amount").slider=True
        self.inputs.new(IR_Material_Socket.__name__, "Material B", identifier="material_B")
        self.inputs.new(IR_Material_Socket.__name__, "Material A", identifier="material_A")
    
    def build_xml(self) -> list[ET.Element]:
        ''' Blend XML '''
        mat_uid = get_uid(self)

        material = _xml.XMLElement('material')
        material.append_tag('uid', mat_uid)
        material.append_tag('name', self.id_data.material.name)
        mat_data = material.append_tag('blend')
        mat_data.append_tag('step_blend', self.step_blend)

        materials = [material.etree_element,]

        for i, link in self.iterate_inputs(empty=True):
            if isinstance(link, EmptySocket):
                if link.identifier == 'blend_amount':
                    mat_data.append_tag(('blend', 'constant'), link.default_value)
                elif link.identifier == 'material_B':
                    mat_data.append_tag('b_name', 'blendigo_null')
                elif link.identifier == 'material_A':
                    mat_data.append_tag('a_name', 'blendigo_null')
                
                continue

            identifier = link.to_socket.identifier

            if identifier == 'blend_amount':
                blend = mat_data.append_tag('blend')
                link.from_node.complete_xml(material, blend)
                continue

            # only identifier material_B or material_A are left

            sub_mats = link.from_node.build_xml()
            sub_mat = sub_mats[0]
            sub_mat_uid = int(sub_mat.find('uid').text)
            ab_mat_uid = 'b_mat_uid' if identifier == 'material_B' else 'a_mat_uid'
            mat_data.append_tag(ab_mat_uid, sub_mat_uid)
            materials.extend(sub_mats)
        
        return materials


class IR_MaterialOutput(IR_MaterialOutputType, Node):
    bl_label = "Material Output"
    bl_icon = 'MATERIAL'
    
    def init_inputs(self, context):
        self.inputs.new(IR_Material_Socket.__name__, "Material")
    
    def build_xml(self):
        ''' Start building xml from this node. '''
        # only one input
        for i, link in self.iterate_inputs():
            # return list of xml materials
            return link.from_node.build_xml()

class IR_F_Displacement(BlendigoNode, Node, MaterialFamily, MaterialFeatureFamily):
    bl_label = "Feature: Displacement Map"
    bl_icon = 'DISC'

    def init_inputs( self, context ):
        self.outputs.new(IR_F_Displacement_Socket.__name__, "Output", identifier='displacement_bool')
        self.inputs.new(IR_TX_Socket.__name__, "Texture", identifier='displacement_SP_rgb')

class IR_F_Normal(BlendigoNode, Node, MaterialFamily, MaterialFeatureFamily):
    bl_label = "Feature: Normal Map"
    bl_icon = 'DISC'

    def init_inputs( self, context ):
        self.outputs.new(IR_F_Normal_Socket.__name__, "Output", identifier='normal_bool')
        self.inputs.new(IR_TX_Socket.__name__, "Texture", identifier='normal_SP_rgb')

class IR_F_Bump(BlendigoNode, Node, MaterialFamily, MaterialFeatureFamily):
    bl_label = "Feature: Bump Map"
    bl_icon = 'DISC'

    def init_inputs( self, context ):
        self.outputs.new(IR_F_Bump_Socket.__name__, "Output", identifier='bump_bool')
        self.inputs.new(IR_TX_Socket.__name__, "Texture", identifier='bump_SP_rgb')
    
    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement):
        ''' Emission XML '''
        pass
    
class IR_F_Emission(BlendigoNode, Node, MaterialFamily, MaterialFeatureFamily):
    bl_label = "Feature: Emission"
    bl_icon = 'DISC'

    emission_bool: bpy.props.BoolProperty(default=True)

    emit_layer: bpy.props.StringProperty(name="Light Layer", description="lightlayer; leave blank to use default")
    # emit_power: bpy.props.FloatProperty(name="Power", description="Power", default=1500.0, min=0.0, max=1000000.0)
    emit_gain_val: bpy.props.FloatProperty(name="Gain", description="Gain", default=1.0, min=0.0, max=1.0)
    emit_gain_exp: bpy.props.IntProperty(name="*10^", description="Exponent", default=0, min=-30, max=30)
    # emission_scale: bpy.props.BoolProperty(name="Emission scale", description="Emission scale", default=False, update=lambda s,c: s.set_strength(c.material))

    def emission_scale_un(self, context):
        # Update Node function
        emission_scale_socket =  first(s for s in self.inputs if s.identifier == 'emission_scale_value')
        if not self.emission_scale and emission_scale_socket:
            self.inputs.remove(emission_scale_socket)
        else:
            self.emission_scale_source_update_node(context)
    
    def emission_scale_source_update_node(self, context):
        # Update Node function
        emission_scale_value_socket =  first(s for s in self.inputs if s.identifier == 'emission_scale_value')
        if self.emission_scale_source == 'MATERIAL':
            if not emission_scale_value_socket:
                self.inputs.new(IR_Float_Socket.__name__, "Emission Scale", identifier='emission_scale_value')
        elif self.emission_scale_source in {'OBJECT', 'DATA'}:
            if emission_scale_value_socket:
                self.inputs.remove(emission_scale_value_socket)

    # emission_scale: bpy.props.BoolProperty(name="Emission scale", description="Emission scale", default=False, update=lambda s,c: s.set_strength(c.material))
    emission_scale: NodeProperty(bpy.props.BoolProperty, identifier='emission_scale', update_node=emission_scale_un, name="Emission scale", description="Emission scale", default=False)
    emission_scale_measure: bpy.props.EnumProperty(name="Unit", description="Units for emission scale", default="luminous_flux", items=[
        ('luminous_flux', 'lm', 'Luminous flux'),
        ('luminous_intensity', 'cd', 'Luminous intensity (lm/sr)'),
        ('luminance', 'nits', 'Luminance (lm/sr/m/m)'),
        ('luminous_emittance', 'lux', 'Luminous emittance (lm/m/m)')
    ])
    emission_scale_value: bpy.props.FloatProperty(name="Value", description="Emission scale value", default=1.0, min=0.0, soft_min=0.0, max=10.0, soft_max=10.0)
    emission_scale_exp: bpy.props.IntProperty(name="*10^", description="Emission scale exponent", default=0, min=-30, max=30)
    # emission_scale_source: bpy.props.EnumProperty(name="Origin", description="Where emission scale is stored", default="MATERIAL", items=[
    emission_scale_source: NodeProperty(bpy.props.EnumProperty, identifier='emission_scale_source', update_node=emission_scale_source_update_node, name="Origin", description="Where emission scale is stored", default="MATERIAL", items=[
        ('MATERIAL', 'Material', 'One per Material'),
        ('OBJECT', 'Object', 'One per Object'),
    ])
    emit_ies: bpy.props.BoolProperty(name="IES Profile", description="IES Profile", default=False)
    emit_ies_path: bpy.props.StringProperty(subtype="FILE_PATH", name=" IES Path", description=" IES Path", default="")
    # backface_emit_bool: bpy.props.BoolProperty(name="Back face emission", description="Controls of back of face is emitting or not", default=False, update=lambda s, c: ubershader_utils.switch_bool(c.material, 'backface_emit', s.backface_emit),)
    backface_emit_bool: NodeProperty(bpy.props.BoolProperty, identifier='backface_emit_bool', name="Back face emission", description="Controls of back of face is emitting or not", default=False)
    em_sampling_mult: bpy.props.FloatProperty(name="Emission Sampling Multiplier", description="A multiplier for the amount of sampling emission from this light material will receive", default=1.0, min=0.0, max=99999.0)


    def draw_buttons( self, context, layout ):
        col = layout.column()
        col.prop_search(self, 'emit_layer', context.scene.indigo_lightlayers, 'lightlayers')
        
        # col.separator()
        # col.prop(self, 'emit_power')
        row = col.row(align=True)
        row.prop(self, 'emit_gain_val')
        row.prop(self, 'emit_gain_exp')
        
        col.prop(self, 'emission_scale')
        if self.emission_scale:
            row = col.row(align=True)
            row.prop(self, 'emission_scale_source', expand=True)
            if self.emission_scale_source == 'OBJECT':
                row = col.row(align=True)
                # TODO: move these to object properties
                row.prop(context.object.indigo_object, 'emission_scale_value')
                row.prop(context.object.indigo_object, 'emission_scale_exp')
                col.prop(context.object.indigo_object, 'emission_scale_measure')
            elif self.emission_scale_source == 'MATERIAL':
                col.prop(self, 'emission_scale_exp')
                col.prop(self, 'emission_scale_measure')
            elif self.emission_scale_source == 'DATA':
                row.prop(context.object.data.indigo_object, 'emission_scale_value')
                row.prop(context.object.data.indigo_object, 'emission_scale_exp')
                col.prop(context.object.data.indigo_object, 'emission_scale_measure')
        
        col.separator()    
        col.prop(self, 'em_sampling_mult')
        col.prop(self, 'emit_ies')
        if self.emit_ies:
            col.prop(self, 'emit_ies_path')
        
        col.prop(self, 'backface_emit_bool')
    
    def init_inputs( self, context ):
        self.outputs.new(IR_F_Emission_Socket.__name__, "Output", identifier='emission_bool')
        self.inputs.new(IR_Color_Socket.__name__, "Color", identifier='emission_SP_rgb')
        self.inputs.new(IR_Float_Socket.__name__, "Emit Power", identifier="emission_power")
    
    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement):
        ''' Emission XML '''

        material_xml.append_tag('emission_sampling_factor', self.em_sampling_mult)
        material_xml.append_tag('backface_emit', self.backface_emit_bool)
        
        power = self.get_input('emission_power').default_value**self.emit_gain_exp * self.emit_gain_val
        mat_data.append_tag(('base_emission', 'constant', 'uniform', 'value'), power)
        if self.emit_layer:
            layers = bpy.context.scene.indigo_lightlayers.enumerate()
            if self.emit_layer in layers:
                mat_data.append_tag('layer', bpy.context.scene.indigo_lightlayers.enumerate()[self.emit_layer])
        rgb = mat_data.append_tag(('emission', 'constant', 'rgb'))
        rgb.append_tag('rgb', _xml.wrap.RGB(self.get_input('emission_SP_rgb').default_value[:]))
        rgb.append_tag('gamma', 1)
        # TODO: get value of linked float/int inputs. These values can be extracted by simple getters.
        # E.g.: getattr(math_node, 'get_output_value_'+math_node_output.identifier)
        # Right now we don't have any float/int output node so it's pointless.

        # TODO: ies profiles. it should be saved in model2 tag.
        # Should ies profile be saved either in material (affects all objects)
        # or in the object data (only object), like emission scale?


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
    
    def init_inputs( self, context ):
        self.outputs.new(IR_SP_Socket.__name__, "Output")
        # super().init()

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
    
    def init_inputs( self, context ):
        # super().init()
        self.outputs.new(IR_SP_Socket.__name__, "Output")

class IR_RGB(BlendigoNode, Node):
    bl_label = "RGB"
    
    def draw_buttons( self, context, layout ):
        # mockup.
        if not hasattr(context.object, 'active_material'):
            return
        if not hasattr(context.object.active_material, 'indigo_material'):
            return
        indigo_material = context.object.active_material.indigo_material
        indigo_material_emission = indigo_material.indigo_material_emission
        
        col = layout.column()
        #
        row = col.row(align=True)
        row.prop(indigo_material_emission, 'emission_SP_rgb')
        #
    
    def init_inputs( self, context ):
        self.outputs.new(IR_Color_Socket.__name__, "Output")
        # super().init()

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
    def init_inputs(self, context):
        # self.inputs.new('CustomSocketType', "Hello")
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

class BlendigoNodeCategory( NodeCategory ):
    @classmethod
    def poll(cls, context):
        return (context.space_data.type == 'NODE_EDITOR' and
                context.space_data.tree_type == 'IR_MaterialNodeTree')

categories = [
    BlendigoNodeCategory( "IR_Materials", "Materials", items = [
        NodeItem(IR_Diffuse.__name__),
        NodeItem(IR_MaterialOutput.__name__),
        NodeItem(IR_Mix.__name__),
    ] ),
    BlendigoNodeCategory( "IR_Other", "Other Nodes", items = [
        NodeItem(IR_Texture.__name__),
        NodeItem(IR_RGB.__name__),
        NodeItem(IR_Uniform.__name__),
        NodeItem(IR_BlackBody.__name__),
        NodeItem(IR_MaterialOutput.__name__),
    ] ),
    BlendigoNodeCategory( "IR_Features", "Material Features", items = [
        NodeItem(IR_F_Emission.__name__),
        NodeItem(IR_F_Bump.__name__),
        NodeItem(IR_F_Normal.__name__),
    ] ),
]

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

def init_mat_node_tree(node_tree, material):
    node_tree.use_fake_user = True # TODO: check if still needed in the current Blender
    node_tree.material = material

    nodes = node_tree.nodes

    output = nodes.new("IR_MaterialOutput")
    output.location = 300, 200
    output.select = False

    diffuse = nodes.new("IR_Diffuse")
    diffuse.location = 50, 200

    node_tree.links.new(diffuse.outputs[0], output.inputs[0])

    # node_tree will not be accessible until next re-evaluation
    bpy.app.timers.register(lambda: node_tree.update())

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
        init_mat_node_tree(node_tree, mat)

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
        init_mat_node_tree(node_tree, mat)

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
        init_mat_node_tree(node_tree, mat)
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

class IR_OT_add_node(bpy.types.Operator):
    bl_idname = "blendigo.add_node"
    bl_label = "Add"
    bl_options = {'INTERNAL', 'REGISTER', 'UNDO'}

    node_type: bpy.props.StringProperty()
    identifier: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        if not hasattr(context, "node"):
            return False
        return context.node and not context.node.id_data.library
    
    def execute(self, context: bpy.types.Context):
        node = context.node
        node_tree = node.id_data
        new_node = node_tree.nodes.new(self.node_type)
        # Place new node a bit to the left and down
        offset_x = new_node.width + 50
        new_node.location = (node.location.x - offset_x, node.location.y - 100)

        this_socket = first(s for s in node.inputs if s.identifier == self.identifier)
        node_tree.links.new(new_node.outputs[0], this_socket)
        return {'FINISHED'}