import bpy
import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem, NodeItemCustom
from xml.etree import ElementTree as ET

from bpy.types import NodeSocket, Node, ShaderNodeCustomGroup, NodeSocketInterface, NodeTree
from . import xml_utils as _xml
from .. core import RENDERER_BL_IDNAME
from . ubershader_utils import get_ubershader, new_eevee_node, get_material_group, ensure_node
from . tree import *
from .. properties.material import find_nkdata


####################
# TODO: gamma/ABC node to alter texture's ABC
# eevee node can take Original ABC output of eevee texture node.
# blendigo node can look for Alter ABC parent node of blendigo texture
# override ensure_eevee_upward_links in IR_Texture to connect ABC Original to Alter ABC

class IR_AlterABC(BlendigoNode, Node):
    bl_label = "(A) Brightness/(B) Scale/(C) Offset/Gamma"
    ubername = "_IndigoABCUberShader_v1"

    # TX_A: NodeProperty(bpy.props.FloatProperty, identifier='TX_A', name='(A) Brightness', precision=5,)
    # TX_B: NodeProperty(bpy.props.FloatProperty, identifier='TX_B', name='(B) Scale', precision=5, default=1)
    # TX_C: NodeProperty(bpy.props.FloatProperty, identifier='TX_C', name='(C) Offset', precision=5,)
    # TX_exponent: NodeProperty(bpy.props.FloatProperty, identifier='TX_exponent', name='Gamma', precision=5, default=2.2, min=0.001)

    foreign_input_translations = {
        "original_ABC_TX_rgb": ((('original_ABC', 'original_ABC_TX_rgb'),), None),
    }

    def init_inputs( self, context ):
        self.outputs.new(IR_TX_Socket.__name__, "Texture", identifier='out_TX_rgb')
        self.inputs.new(IR_TX_Socket.__name__, "Texture", identifier='original_ABC_TX_rgb')
        self.inputs.new(IR_Float_Socket.__name__, '(A) Brightness', identifier="TX_A")
        self.inputs.new(IR_Float_Socket.__name__, '(B) Scale', identifier="TX_B").default_value = 1
        self.inputs.new(IR_Float_Socket.__name__, '(C) Offset', identifier="TX_C")
        self.inputs.new(IR_Float_Socket.__name__, 'Gamma', identifier="TX_exponent").default_value = 2.2
    
    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement, link: bpy.types.NodeLink):
        ''' ABC XML '''
        # this node accepts only TX sockets, so let the texture complete the XML and then edit values.
        for i, link in self.iterate_inputs():
            link.from_node.complete_xml(material_xml, mat_data, link)
        
        # print('______35463574878538+')
        # print(ET.dump(mat_data.etree_element))
        # print(ET.dump(mat_data.find('a').etree_element))
        mat_data.find('.//a').etree_element.text = str(self.get_input('TX_A').default_value)
        mat_data.find('.//b').etree_element.text = str(self.get_input('TX_B').default_value)
        mat_data.find('.//c').etree_element.text = str(self.get_input('TX_C').default_value)
        mat_data.find('.//exponent').etree_element.text = str(self.get_input('TX_exponent').default_value)

class IR_Texture(BlendigoNode, Node):
    bl_label = "Texture"
    ubername = "_IndigoTextureABCUberShader_v1"

    foreign_input_translations = {
        "original_ABC_TX_rgb": ((('original_ABC', 'original_ABC_TX_rgb'),), None),
    }

    def image_notify_callback(self, eevee_node, update_input_name):
        eevee_tex = ensure_node(eevee_node, 'ShaderNodeTexImage', ((0, 'in_TX_rgb'),))
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
    
    def TX_uvset_notify_callback(self, eevee_node, update_input_name):
        print(self, eevee_node, update_input_name)
        try:
            from .ubershader_utils import ensure_node
            tex_node = ensure_node(eevee_node, 'ShaderNodeTexImage', ((0, 'in_TX_rgb'),))
            uv_node = ensure_node(tex_node, 'ShaderNodeUVMap')
            uv_node.uv_map = getattr(self, update_input_name)
        except:
            import traceback
            traceback.print_exc()

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
        self.outputs.new(IR_TX_Socket.__name__, "Texture", identifier='out_TX_rgb')
    
    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement, link: bpy.types.NodeLink):
        ''' Texture XML '''
        texture = mat_data.append_tag('texture')
        texture.append_tag('path', bpy.path.abspath(getattr(self.image, 'filepath', '')))
        texture.append_tag('a', self.TX_A)
        texture.append_tag('b', self.TX_B)
        texture.append_tag('c', self.TX_C)
        texture.append_tag('exponent', self.TX_exponent)

class _MaterialBlendingCallback:
    '''
    Mix-in class to handle null_A/B mix node inputs.
    Indigo treats null material as transparent while Blender see it as a solid black.
    This callback sets additional null_A/B parameter to tell mix shader whether input shader is connected.

    This is a callback for material node that is attaching to a mix node (in ensure_eevee_upward_links method).
    Mix node has to define its own set of callbacks when blendigo link is severed.

    Used also for other materials that take in sub-components.
    '''
    foreign_input_translations = BlendigoNode.foreign_input_translations.copy()
    
    def material_AB_attach(self, eevee_node, eevee_parent, blendigo_link):
        letter = blendigo_link.to_socket.identifier[-1:]
        eevee_parent.inputs['null_'+letter].default_value = 0
    
    def material_substrate_attach(self, eevee_node, eevee_parent, blendigo_link):
        eevee_parent.inputs['null_substrate'].default_value = 0
    
    def material_FB_attach(self, eevee_node, eevee_parent, blendigo_link):
        sufix = blendigo_link.to_socket.identifier.split('_')[1]
        eevee_parent.inputs['null_'+sufix].default_value = 0

    foreign_input_translations.update({
        "material_B": (((0, 'material_B'),), material_AB_attach),
        "material_A": (((0, 'material_A'),), material_AB_attach),
        "substrate": (((0, 'substrate'),), material_substrate_attach),
        "material_front": (((0, 'material_front'),), material_FB_attach),
        "material_back": (((0, 'material_back'),), material_FB_attach),
    })

class IR_Phong(_MaterialBlendingCallback, IR_MaterialType, Node):
    bl_label = "Phong Material"
    bl_icon = 'NODE_MATERIAL'
    ubername = "_IndigoPhongUberShader_v1"
    
    def _update_node(self, context):
        # Update Node function
        IOR_socket = self.get_input('IOR')
        colour_SP_rgb_socket = self.get_input('colour_SP_rgb')
        
        if self.nk_data_type != 'none':
            if IOR_socket:
                self.inputs.remove(IOR_socket)
            if colour_SP_rgb_socket:
                self.inputs.remove(colour_SP_rgb_socket)
            return
        
        if self.specular_reflectivity:
            if not colour_SP_rgb_socket:
                self.inputs.new(IR_RGB_TX_SH_Socket.__name__, "Color", identifier='colour_SP_rgb')
                self.tag_update('colour_SP_rgb')
            if IOR_socket:
                self.inputs.remove(IOR_socket)
        else:
            if not colour_SP_rgb_socket:
                self.inputs.new(IR_RGB_TX_SH_Socket.__name__, "Color", identifier='colour_SP_rgb')
                self.tag_update('colour_SP_rgb')
            if not IOR_socket:
                self.inputs.new(IR_Float_Socket.__name__, "IOR", identifier='IOR').default_value = 1.5
                self.tag_update('IOR')

    specular_reflectivity: NodeProperty(bpy.props.BoolProperty, identifier='specular_reflectivity', name='Specular Reflectivity (metallic)', description='', update_node=_update_node)
    nk_data_type: NodeProperty(bpy.props.EnumProperty, identifier='nk_data_type', name="NK Type", items=[('none', 'None', 'Do not use NK data'), ('preset', 'Preset', 'Use an NK preset'), ('file', 'File', 'Use specified NK file')], default="none", update_node=_update_node)
    nk_data_preset: bpy.props.EnumProperty(name="NK Preset", items=find_nkdata)
    nk_data_file: bpy.props.StringProperty(name="NK Data", description="NK Data", default="", subtype="FILE_PATH")


    # fresnel_scale: NodeProperty(bpy.props.FloatProperty, identifier='fresnel_scale', description='Allows you to adjust the strength of the Fresnel reflection falloff.', name="Fresnel Scale", min=0.0, max=1.0)
    # IOR: NodeProperty(bpy.props.FloatProperty, identifier='IOR', description='Index Of Refraction.', name="IOR", min=0.0)
    
    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, 'nk_data_type')
        if self.nk_data_type == 'preset':
            col.prop(self, 'nk_data_preset')
            col.label(text="No viewport preview.", icon='INFO')
        elif self.nk_data_type == 'file':
            col.prop(self, 'nk_data_file')
            col.label(text="No viewport preview.", icon='INFO')
        else:
            col.prop(self, 'specular_reflectivity')
    
    def init_inputs(self, context):
        self.outputs.new(IR_Material_Socket.__name__, "Material")
        self.inputs.new(IR_RGB_TX_SH_Socket.__name__, "Color", identifier='colour_SP_rgb')
        self.inputs.new(IR_Float_Socket.__name__, "IOR", identifier='IOR').default_value = 1.5
        self.inputs.new(IR_Slider_F_TX_SH_Socket.__name__, "Fresnel Scale", identifier='fresnel_scale').default_value = 1
        self.inputs.new(IR_Slider_F_TX_SH_Socket.__name__, "Roughness", identifier='roughness').default_value = 0
        self.inputs.new(IR_F_Emission_Socket.__name__, "Emission", identifier='emission_bool')
        self.inputs.new(IR_F_Bump_Socket.__name__, "Bump", identifier='bump_bool')
        self.inputs.new(IR_F_Normal_Socket.__name__, "Normal", identifier='normal_bool')
        self.inputs.new(IR_F_Displacement_Socket.__name__, "Displacement", identifier='displacement_bool')
    
    def build_xml(self):
        ''' Phong xml '''
        mat_uid = get_uid(self)
        material = _xml.XMLElement('material')
        material.append_tag('uid', mat_uid)
        mat_name = f'{self.id_data.material.name}: {self.name}'
        material.append_tag('name', mat_name)
        
        phong = material.append_tag('phong')
        
        # self.id_data['emission_scaled_materials'] = dict()
        # self.id_data['is_emitting'] = False
        # connected_sockets = set()

        if self.nk_data_type == 'preset':
            phong.append_tag('nk_data', self.nk_data_preset)
        elif self.nk_data_type == 'file':
            phong.append_tag('nk_data', self.nk_data_file)

        for i, link in self.iterate_inputs(empty=True, invalid_as_empty=True):
            identifier = link.to_socket.identifier
            is_empty_socket = isinstance(link, EmptySocket)
            # connected_sockets.add(identifier)
            if isinstance(link.from_node, MaterialFeatureFamily) and not is_empty_socket:
                link.from_node.complete_xml(material, phong, link)
            elif identifier == 'colour_SP_rgb':
                if not is_empty_socket:
                    if self.specular_reflectivity:
                        mat_data = phong.append_tag('specular_reflectivity')
                    else:
                        mat_data = phong.append_tag('diffuse_albedo')
                    link.from_node.complete_xml(material, mat_data, link)
                else:
                    if self.specular_reflectivity:
                        rgb = phong.append_tag(('specular_reflectivity', 'constant', 'rgb'))
                    else:
                        rgb = phong.append_tag(('diffuse_albedo', 'constant', 'rgb'))
                    rgb.append_tag('rgb', _xml.wrap.RGB(self.get_input('colour_SP_rgb').default_value))
                    rgb.append_tag('gamma', 2.2)
            elif identifier == 'IOR':
                if not is_empty_socket:
                    mat_data = phong.append_tag('ior')
                    link.from_node.complete_xml(material, mat_data, link)
                else:
                    mat_data = phong.append_tag('ior', self.get_input('IOR').default_value)
            elif identifier == 'fresnel_scale':
                if not is_empty_socket:
                    mat_data = phong.append_tag('fresnel_scale')
                    link.from_node.complete_xml(material, mat_data, link)
                else:
                    mat_data = phong.append_tag(('fresnel_scale', 'constant'), self.get_input('fresnel_scale').default_value)
            elif identifier == 'roughness':
                if not is_empty_socket:
                    mat_data = phong.append_tag('roughness')
                    link.from_node.complete_xml(material, mat_data, link)
                else:
                    mat_data = phong.append_tag(('roughness', 'constant'), self.get_input('roughness').default_value)

        
        return (material.etree_element,)

class IR_Specular(_MaterialBlendingCallback, IR_MaterialType, Node):
    bl_label = "Specular Material"
    bl_icon = 'NODE_MATERIAL'
    ubername = "_IndigoSpecularUberShader_v1"
    
    def _update_node(self, context):
        # Update Node function
        glossy_roughness_socket = self.get_input('glossy_roughness')
        
        if self.mat_type == 'specular':
            if glossy_roughness_socket:
                self.inputs.remove(glossy_roughness_socket)
        elif self.mat_type == 'glossy_transparent':
            if not glossy_roughness_socket:
                self.inputs.new(IR_Slider_F_TX_SH_Socket.__name__, "Roughness", identifier='glossy_roughness').default_value = 0

    def type_update_callback(self, eevee_node, identifier):
        if self.mat_type == 'specular':
            eevee_node.inputs['type_specular_enum'].default_value = 1
            eevee_node.inputs['type_glossy_transparent_enum'].default_value = 0
        else:
            eevee_node.inputs['type_specular_enum'].default_value = 0
            eevee_node.inputs['type_glossy_transparent_enum'].default_value = 1

    mat_type: NodeProperty(bpy.props.EnumProperty, identifier='mat_type', name="Specular Type", description="Specular Type", default="specular", items=[
        ('specular', 'Specular', 'specular'),
        ('glossy_transparent', 'Glossy Transparent', 'glossy_transparent')
        ],
        notify_callback=type_update_callback,
        update_node=_update_node)

    spec_transparent_bool: NodeProperty(bpy.props.BoolProperty, identifier='spec_transparent_bool', name='Transparent', description='')
    spec_arch_glass_bool: NodeProperty(bpy.props.BoolProperty, identifier='spec_arch_glass_bool', name='Arch Glass', description='')
    spec_single_face: NodeProperty(bpy.props.BoolProperty, identifier='spec_single_face', name='Single Face', description='')
    medium_chooser: bpy.props.StringProperty()
    
    def draw_buttons(self, context, layout):
        col = layout.column()
        col.row().prop(self, 'mat_type', expand=True)
        if self.mat_type == "specular":
            col.prop(self, 'spec_transparent_bool')
            col.prop(self, 'spec_arch_glass_bool')
            sub = col.column()
            sub.prop(self, 'spec_single_face')
            sub.enabled = self.spec_arch_glass_bool
        col.prop_search(self, 'medium_chooser', context.scene.indigo_material_medium, 'medium')
    
    def init_inputs(self, context):
        self.outputs.new(IR_Material_Socket.__name__, "Material")
        self.inputs.new(IR_F_Absorption_Socket.__name__, "Absorption Layer", identifier='absorption_layer_bool')
        self.inputs.new(IR_F_Emission_Socket.__name__, "Emission", identifier='emission_bool')
        self.inputs.new(IR_F_Bump_Socket.__name__, "Bump", identifier='bump_bool')
        self.inputs.new(IR_F_Normal_Socket.__name__, "Normal", identifier='normal_bool')
        self.inputs.new(IR_F_Displacement_Socket.__name__, "Displacement", identifier='displacement_bool')
        self.inputs.new(IR_Slider_F_TX_SH_Socket.__name__, "Roughness", identifier='glossy_roughness')
    
    def build_xml(self):
        ''' Specular xml '''
        mat_uid = get_uid(self)
        material = _xml.XMLElement('material')
        material.append_tag('uid', mat_uid)
        mat_name = f'{self.id_data.material.name}: {self.name}'
        material.append_tag('name', mat_name)
        
        specular = material.append_tag('specular')
        if self.medium_chooser:
            specular.append_tag('internal_medium_uid', bpy.context.scene.indigo_material_medium.medium[self.medium_chooser].indigo_export_uid)
        else:
            specular.append_tag('internal_medium_uid', 8) # hardcoded basic medium uid TODO: handle this uid better
        
        if self.mat_type == 'specular':
            specular.append_tag('transparent', self.spec_transparent_bool)
            specular.append_tag('arch_glass', self.spec_arch_glass_bool)
            specular.append_tag('single_face', self.spec_single_face)

        for i, link in self.iterate_inputs(empty=True, invalid_as_empty=True):
            identifier = link.to_socket.identifier
            is_empty_socket = isinstance(link, EmptySocket)
            if isinstance(link.from_node, MaterialFeatureFamily) and not is_empty_socket:
                link.from_node.complete_xml(material, specular, link)
            elif identifier == 'glossy_roughness':
                if not is_empty_socket:
                    mat_data = specular.append_tag('glossy_roughness')
                    link.from_node.complete_xml(material, mat_data, link)
                else:
                    mat_data = specular.append_tag(('glossy_roughness', 'constant'), self.get_input('glossy_roughness').default_value)

        return (material.etree_element,)

class IR_FastSSS(_MaterialBlendingCallback, IR_MaterialType, Node):
    bl_label = "Fast SSS Material"
    bl_icon = 'NODE_MATERIAL'
    ubername = "_IndigoFastSSSUberShader_v1"
    
    medium_chooser: bpy.props.StringProperty()
    
    def draw_buttons(self, context, layout):
        layout.prop_search(self, 'medium_chooser', context.scene.indigo_material_medium, 'medium')
    
    def init_inputs(self, context):
        self.outputs.new(IR_Material_Socket.__name__, "Material")
        self.inputs.new(IR_RGB_TX_SH_Socket.__name__, "Color/Texture/Shader", identifier='colour_SP_rgb')
        self.inputs.new(IR_Slider_F_TX_SH_Socket.__name__, "Roughness", identifier='roughness').default_value = 0.3
        self.inputs.new(IR_Slider_F_TX_SH_Socket.__name__, "Fresnel Scale", identifier='fresnel_scale').default_value = 1
        self.inputs.new(IR_F_Emission_Socket.__name__, "Emission", identifier='emission_bool')
        self.inputs.new(IR_F_Bump_Socket.__name__, "Bump", identifier='bump_bool')
        self.inputs.new(IR_F_Normal_Socket.__name__, "Normal", identifier='normal_bool')
        self.inputs.new(IR_F_Displacement_Socket.__name__, "Displacement", identifier='displacement_bool')
    
    def build_xml(self):
        ''' Fast SSS xml '''
        mat_uid = get_uid(self)
        material = _xml.XMLElement('material')
        material.append_tag('uid', mat_uid)
        mat_name = f'{self.id_data.material.name}: {self.name}'
        material.append_tag('name', mat_name)
        fast_sss = material.append_tag('fast_sss')

        for i, link in self.iterate_inputs(empty=True, invalid_as_empty=True):
            identifier = link.to_socket.identifier
            is_empty_socket = isinstance(link, EmptySocket)
            # connected_sockets.add(identifier)
            if isinstance(link.from_node, MaterialFeatureFamily) and not is_empty_socket:
                link.from_node.complete_xml(material, fast_sss, link)
            elif identifier == 'colour_SP_rgb':
                if not is_empty_socket:
                    mat_data = fast_sss.append_tag('albedo')
                    link.from_node.complete_xml(material, mat_data, link)
                else:
                    rgb = fast_sss.append_tag(('albedo', 'constant', 'rgb'))
                    rgb.append_tag('rgb', _xml.wrap.RGB(self.get_input('colour_SP_rgb').default_value))
                    rgb.append_tag('gamma', 2.2)
            elif identifier == 'roughness':
                if not is_empty_socket:
                    mat_data = fast_sss.append_tag('roughness')
                    link.from_node.complete_xml(material, mat_data, link)
                else:
                    fast_sss.append_tag(('roughness', 'constant'), self.get_input('roughness').default_value)
            elif identifier == 'fresnel_scale':
                if not is_empty_socket:
                    mat_data = fast_sss.append_tag('fresnel_scale')
                    link.from_node.complete_xml(material, mat_data, link)
                else:
                    fast_sss.append_tag(('fresnel_scale', 'constant'), self.get_input('fresnel_scale').default_value)
        
        if self.medium_chooser:
            fast_sss.append_tag('internal_medium_uid', bpy.context.scene.indigo_material_medium.medium[self.medium_chooser].indigo_export_uid)
        else:
            fast_sss.append_tag('internal_medium_uid', 8) # hardcoded basic medium uid TODO: handle this uid better
        
        return (material.etree_element,)

class IR_Diffuse(_MaterialBlendingCallback, IR_MaterialType, Node):
    bl_label = "Diffuse Material"
    bl_icon = 'NODE_MATERIAL'
    ubername = "_IndigoDiffuseUberShader_v1"
    
    shadow_catcher: NodeProperty(bpy.props.BoolProperty, identifier='shadow_catcher', name='Shadow Catcher', description='Make this material a shadow catching material.  For use with the shadow pass.')
    sigma: NodeProperty(bpy.props.FloatProperty, identifier='sigma', description='Oren-Nayar Sigma Parameter', name="Sigma", min=0.0, max=20.0)
    transmitter: NodeProperty(bpy.props.BoolProperty, identifier='transmitter', name='Transmitter', description='Diffuse Transmitter')
    
    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, 'transmitter')
        if not self.transmitter:
            col.prop(self, 'sigma')
        col.prop(self, 'shadow_catcher')
    
    def init_inputs(self, context):
        self.outputs.new(IR_Material_Socket.__name__, "Material")
        self.inputs.new(IR_RGB_TX_SH_Socket.__name__, "Color/Texture/Shader", identifier='colour_SP_rgb')
        self.inputs.new(IR_F_Emission_Socket.__name__, "Emission", identifier='emission_bool')
        self.inputs.new(IR_F_Bump_Socket.__name__, "Bump", identifier='bump_bool')
        self.inputs.new(IR_F_Normal_Socket.__name__, "Normal", identifier='normal_bool')
        self.inputs.new(IR_F_Displacement_Socket.__name__, "Displacement", identifier='displacement_bool')
    
    def build_xml(self):
        ''' Diffuse xml '''
        mat_uid = get_uid(self)
        material = _xml.XMLElement('material')
        material.append_tag('uid', mat_uid)
        mat_name = f'{self.id_data.material.name}: {self.name}'
        material.append_tag('name', mat_name)

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
        
        # self.id_data['emission_scaled_materials'] = dict()
        # self.id_data['is_emitting'] = False
        connected_sockets = set()
        for i, link in self.iterate_inputs():
            identifier = link.to_socket.identifier
            connected_sockets.add(identifier)
            if isinstance(link.from_node, MaterialFeatureFamily):
                link.from_node.complete_xml(material, mat_data, link)
                # if (isinstance(link.from_node, IR_F_Emission)
                #     and link.from_node.emission_scale):
                    # store IR_F_Emission node for easier access to emission scale
                    # self.id_data['emission_scaled_materials'][mat_uid] = link.from_node # use matname for now as model2 is not implemented
                    # self.id_data['emission_scaled_materials'][mat_name] = link.from_node
            elif identifier == 'colour_SP_rgb':
                albedo = mat_data.append_tag('albedo')
                link.from_node.complete_xml(material, albedo, link)
        print(connected_sockets)

        if 'colour_SP_rgb' not in connected_sockets:
            constant = mat_data.append_tag(('albedo', 'constant'))
            rgb = constant.append_tag('rgb')
            rgb.append_tag('rgb', _xml.wrap.RGB(self.get_input('colour_SP_rgb').default_value[:]))
            rgb.append_tag('gamma', 1)

        
        return (material.etree_element,)

class MaterialLoopException(Exception):
    pass
# processed_materials = dict()
processed_materials = set()
class AlreadyProcessedException(Exception):
    def __init__(self, uid, message="UID already exists"):
        super().__init__(message)
        self.uid = uid

class NullMaterialException(Exception):
    def __init__(self, uid=5, message="Replacing with blendigo_null"):
        super().__init__(message)
        self.uid = uid

# def get_uid(obj, offset=0):
#     global processed_materials
#     objhash = hash(obj)
#     if objhash in processed_materials:
#         # already processed
#         raise AlreadyProcessedException(processed_materials[objhash])
    
#     uid = processed_materials[objhash] = 10000 + len(processed_materials)
#     return uid

def get_uid(obj, offset=0):
    if obj.indigo_export_uid in processed_materials:
        # already processed
        raise AlreadyProcessedException(obj.indigo_export_uid)
    
    return obj.indigo_export_uid

class IR_MaterialInput(_MaterialBlendingCallback, IR_MaterialType, Node):
    bl_label = "Material Input"
    bl_icon = 'NODE_MATERIAL'
    ubername = "ShaderNodeGroup"

    def eevee_on_create(self, eevee_node):
        eevee_node.node_tree = get_material_group(self.material)

    def material_notify_callback(self: BlendigoNode, eevee_node: bpy.types.ShaderNode, update_input_name:str):
        print(self, eevee_node, update_input_name)

    material: NodeProperty(bpy.props.PointerProperty,
        identifier='material',
        notify_callback=material_notify_callback,
        type=bpy.types.Material,
        poll=lambda self, material: not material.is_grease_pencil and material.indigo_material.node_tree and material is not self.id_data.material,
        name="Material",
        description="Material to use as input"
        )

    def draw_buttons(self, context, layout):
        # layout.use_property_split=True
        layout.prop(self, 'material', text='')
        # layout.prop_search(self, 'material', bpy.data, 'materials')
        
        # TODO: can be extended with eye-droper to select object to take material from.
        # ray casting can be used to find choosen face and its material

        if self.material and self.material is self.id_data.material:
            layout.label(text="Material loop detected.", icon="ERROR")

    def init_inputs(self, context):
        self.outputs.new(IR_Material_Socket.__name__, "Material", identifier='material')
    
    def build_xml(self):
        ''' Start building xml from this node. '''
        if not self.material:
            raise NullMaterialException
        
        if self.material is self.id_data.material:
            raise MaterialLoopException
        
        self.material.indigo_material.node_tree
        output = first(n for n in self.material.indigo_material.node_tree.get_output_nodes() if n.is_active_output)
        xml = output.build_xml()

        # handle emission scale
        inner_material_node_tree = output.get_material_node_tree()
        material_node_tree = self.get_material_node_tree()
        material_node_tree['_is_valid_light'] = inner_material_node_tree.is_valid_light
        material_node_tree['emission_scaled_materials'].update(inner_material_node_tree['emission_scaled_materials'])
        
        return xml
    
    def free(self):
        self.material = None

class IR_ShaderText(BlendigoNode, Node):
    bl_label = "Shader Text"
    # bl_icon = ''

    text: bpy.props.PointerProperty(type=bpy.types.Text)

    def draw_buttons(self, context, layout):
        layout.prop(self, 'text')
    
    def init_inputs(self, context):
        self.outputs.new(IR_SH_Socket.__name__, "Shader", identifier='shader')
    
    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement, link: bpy.types.NodeLink):
        ''' Shader XML '''
        shader = mat_data.append_tag('shader')
        if not self.text:
            return
        
        shader.etree_element.text = self.text.as_string()

class IR_ExternalMaterial(_MaterialBlendingCallback, IR_MaterialType, Node):
    bl_label = "External Material"
    bl_icon = 'MATERIAL'

    from .. properties.material import updated_event
    filename: bpy.props.StringProperty(subtype="FILE_PATH", name="IGM or PIGM file", description="IGM or PIGM file", default="", update=updated_event)
    material_name: bpy.props.StringProperty(name="Name")
    is_valid: bpy.props.BoolProperty(default=False)
    emit_ies: bpy.props.BoolProperty(name="IES Profile", description="IES Profile", default=False)
    emit_ies_path: bpy.props.StringProperty(subtype="FILE_PATH", name=" IES Path", description=" IES Path", default="")
    emission_enabled: bpy.props.BoolProperty(default=False)
    emission_scale: bpy.props.BoolProperty(name="Emission scale", description="Emission scale", default=False)
    emission_scale_measure: bpy.props.EnumProperty(name="Unit", description="Units for emission scale", default="luminous_flux", items=[('luminous_flux', 'lm', 'Luminous flux'), ('luminous_intensity', 'cd', 'Luminous intensity (lm/sr)'), ('luminance', 'nits', 'Luminance (lm/sr/m/m)'), ('luminous_emittance', 'lux', 'Luminous emittance (lm/m/m)')])
    emission_scale_value: bpy.props.FloatProperty(name="Value", description="Emission scale value", default=1.0, min=0.0, soft_min=0.0, max=10.0, soft_max=10.0)
    emission_scale_exp: bpy.props.IntProperty(name="*10^", description="Emission scale exponent", default=0, min=-30, max=30)


    def draw_buttons(self, context, layout):
        col = layout.column()
        col.operator('WM_OT_url_open', text='Open materials database', icon='URL').url = 'http://www.indigorenderer.com/materials/'
        col.prop(self, 'filename')
        col = col.column()
        col.prop(self, 'material_name')
        col.enabled = False
        col = layout.column()
        if self.emission_enabled:
            col.prop(self, 'emit_ies')
            if self.emit_ies:
                col.prop(self, 'emit_ies_path')
                        
            col.separator()
            col.prop(self, 'emission_scale')
            if self.emission_scale:
                row = col.row(align=True)
                row.prop(self, 'emission_scale_value')
                row.prop(self, 'emission_scale_exp')
                col.prop(self, 'emission_scale_measure')
    
    def init_inputs(self, context):
        self.outputs.new(IR_Material_Socket.__name__, "Material", identifier='material')
    
    def build_xml(self) -> list[ET.Element]:
        ''' External XML '''
        include = _xml.XMLElement('include')
        include.append_tag('material_name', self.material_name) # internal tag. not used by Indigo

        materials = [include.etree_element,]

        from .. extensions_framework.util import path_relative_to_export
        # try:
        include.append_tag('pathname', path_relative_to_export(bpy.path.abspath(self.filename)))
        # except Exception as e:
        #     print(e)
        
        
        # Model2 does not seem to support material names but external materials can't have uids
        # so use blended material as a wrapper that still supports mat names.
        mat_uid = get_uid(self)

        material = _xml.XMLElement('material')
        materials.append(material.etree_element)
        material.append_tag('uid', mat_uid)
        mat_name = f'{self.id_data.material.name}: {self.name}'
        material.append_tag('name', mat_name)
        mat_data = material.append_tag('blend')
        mat_data.append_tag('step_blend', True)
        mat_data.append_tag(('blend', 'constant'), 0)
        mat_data.append_tag('a_name', self.material_name)
        mat_data.append_tag('b_name', 'blendigo_null')

        return materials

class IR_DoubleSidedThin(_MaterialBlendingCallback, IR_MaterialType, Node):
    bl_label = "Double-Sided Thin Material"
    bl_icon = 'NODE_MATERIAL'
    ubername = "_IndigoDoubleSidedThinUberShader_v1"
    icon = 'MATERIAL'

    def material_FB_detach(self, eevee_node, identifier):
        sufix = identifier.split('_')[1]
        eevee_node.inputs['null_'+sufix].default_value = 1

    input_detach_callbacks = {
        "material_front": material_FB_detach,
        "material_back": material_FB_detach,
    }
    
    def init_inputs(self, context):
        self.outputs.new(IR_Material_Socket.__name__, "Material")
        self.inputs.new(IR_RGB_SP_TX_SH_Socket.__name__, "Transmittance", identifier="transmittance")
        self.inputs.new(IR_Float_Socket.__name__, "IOR", identifier="ior").default_value = 1
        self.inputs.new(IR_Slider_F_TX_SH_Socket.__name__, "Reflection Fraction", identifier="r_f").default_value = 0.5
        self.inputs.new(IR_Slider_F_TX_SH_Socket.__name__, "Front Fresnel Scale", identifier="front_fresnel_scale").default_value = 1
        self.inputs.new(IR_Slider_F_TX_SH_Socket.__name__, "Back Fresnel Scale", identifier="back_fresnel_scale").default_value = 1
        self.inputs.new(IR_Slider_F_TX_SH_Socket.__name__, "Front Roughness", identifier="front_roughness").default_value = 0.3
        self.inputs.new(IR_Slider_F_TX_SH_Socket.__name__, "Back Roughness", identifier="back_roughness").default_value = 0.3
        self.inputs.new(IR_Material_Socket.__name__, "Front Material", identifier="material_front")
        self.inputs.new(IR_Material_Socket.__name__, "Back Material", identifier="material_back")
        
        self.inputs.new(IR_F_Emission_Socket.__name__, "Emission", identifier='emission_bool')
        self.inputs.new(IR_F_Bump_Socket.__name__, "Bump", identifier='bump_bool')
        self.inputs.new(IR_F_Normal_Socket.__name__, "Normal", identifier='normal_bool')
        self.inputs.new(IR_F_Displacement_Socket.__name__, "Displacement", identifier='displacement_bool')
    
    def build_xml(self) -> list[ET.Element]:
        ''' Double-Sided Thin XML '''
        mat_uid = get_uid(self)

        material = _xml.XMLElement('material')
        material.append_tag('uid', mat_uid)
        mat_name = f'{self.id_data.material.name}: {self.name}'
        material.append_tag('name', mat_name)
        mat_data = material.append_tag('double_sided_thin')

        materials = [material.etree_element,]

        for i, link in self.iterate_inputs(empty=True, invalid_as_empty=True):
            identifier = link.to_socket.identifier
            is_empty_socket = isinstance(link, EmptySocket)
            if isinstance(link.from_node, MaterialFeatureFamily):
                link.from_node.complete_xml(material, mat_data, link)
            elif identifier in {'material_front', 'material_back'}:
                ab_mat_uid = 'front_material_uid' if identifier == 'material_front' else 'back_material_uid'
                if not is_empty_socket:
                    try:
                        sub_mats = link.from_node.build_xml()
                        sub_mat = sub_mats[0]
                        sub_mat_uid = sub_mat.find('uid')
                        if sub_mat_uid is not None:
                            mat_data.append_tag(ab_mat_uid, sub_mat_uid.text)
                        else:
                            sub_mat_name = sub_mat.find('material_name').text
                            mat_data.append_tag(ab_mat_uid[0]+'_name', sub_mat_name)
                        materials.extend(sub_mats)
                    except (AlreadyProcessedException, NullMaterialException) as e:
                        mat_data.append_tag(ab_mat_uid, e.uid)
                else:
                    mat_data.append_tag(ab_mat_uid.split('_')[0]+'_material_name', 'blendigo_null')

            elif identifier == 'ior':
                if not is_empty_socket:
                    ior = mat_data.append_tag('ior')
                    link.from_node.complete_xml(material, ior, link)
                else:
                    mat_data.append_tag('ior', self.get_input('ior').default_value)
            elif identifier == 'transmittance':
                if not is_empty_socket:
                    transmittance = mat_data.append_tag('transmittance')
                    link.from_node.complete_xml(material, transmittance, link)
                else:
                    rgb = mat_data.append_tag(('transmittance', 'constant', 'rgb'))
                    rgb.append_tag('rgb', _xml.wrap.RGB(self.get_input('transmittance').default_value))
                    rgb.append_tag('gamma', 2.2)
            elif identifier in {'r_f', 'front_fresnel_scale', 'back_fresnel_scale', 'front_roughness', 'back_roughness'}:
                if not is_empty_socket:
                    data = mat_data.append_tag(identifier)
                    link.from_node.complete_xml(material, data, link)
                else:
                    mat_data.append_tag((identifier, 'constant'), self.get_input(identifier).default_value)
        # reverse materials to avoid problems with included external mats that use names instead of uids
        materials.reverse()
        return materials

class IR_Coating(_MaterialBlendingCallback, IR_MaterialType, Node):
    bl_label = "Coating Material"
    bl_icon = 'NODE_MATERIAL'
    ubername = "_IndigoCoatingUberShader_v1"
    icon = 'MATERIAL'

    interference: NodeProperty(bpy.props.BoolProperty, identifier='interference', name="Interference", description="Enabled interference effects in the coating layer.")

    def draw_buttons(self, context, layout):
        layout.prop(self, 'interference')

    def material_detach(self, eevee_node, identifier):
        eevee_node.inputs['null_substrate'].default_value = 1

    input_detach_callbacks = {
        "substrate": material_detach,
    }

    def init_inputs(self, context):
        self.outputs.new(IR_Material_Socket.__name__, "Material")
        self.inputs.new(IR_RGB_SP_TX_SH_Socket.__name__, "Absorption", identifier="absorption_SP_rgb")
        self.inputs.new(IR_Float_Socket.__name__, "IOR", identifier="ior").default_value = 1.5
        self.inputs.new(IR_Slider_F_TX_SH_Socket.__name__, "Roughness", identifier="roughness").default_value = 0.3
        self.inputs.new(IR_Slider_F_TX_SH_Socket.__name__, "Thickness [μm]", identifier="thickness").default_value = 1
        self.inputs.new(IR_Slider_F_TX_SH_Socket.__name__, "Fresnel Scale", identifier="fresnel_scale").default_value = 1
        self.inputs.new(IR_Material_Socket.__name__, "Substrate", identifier='substrate')
        
        self.inputs.new(IR_F_Emission_Socket.__name__, "Emission", identifier='emission_bool')
        self.inputs.new(IR_F_Bump_Socket.__name__, "Bump", identifier='bump_bool')
        self.inputs.new(IR_F_Normal_Socket.__name__, "Normal", identifier='normal_bool')
        self.inputs.new(IR_F_Displacement_Socket.__name__, "Displacement", identifier='displacement_bool')
    
    def build_xml(self) -> list[ET.Element]:
        ''' Coating XML '''
        mat_uid = get_uid(self)

        material = _xml.XMLElement('material')
        material.append_tag('uid', mat_uid)
        mat_name = f'{self.id_data.material.name}: {self.name}'
        material.append_tag('name', mat_name)
        mat_data = material.append_tag('coating')
        
        mat_data.append_tag('interference', self.interference)

        materials = [material.etree_element,]

        for i, link in self.iterate_inputs(empty=True, invalid_as_empty=True):
            identifier = link.to_socket.identifier
            is_empty_socket = isinstance(link, EmptySocket)
            if isinstance(link.from_node, MaterialFeatureFamily):
                link.from_node.complete_xml(material, mat_data, link)
            elif identifier == 'substrate':
                if not is_empty_socket:
                    try:
                        sub_mats = link.from_node.build_xml()
                        sub_mat = sub_mats[0]
                        sub_mat_uid = sub_mat.find('uid')
                        if sub_mat_uid is not None:
                            mat_data.append_tag('substrate_material_uid', sub_mat_uid.text)
                        else:
                            sub_mat_name = sub_mat.find('material_name').text
                            mat_data.append_tag('substrate_material_name', sub_mat_name)
                        materials.extend(sub_mats)
                    except (AlreadyProcessedException, NullMaterialException) as e:
                        mat_data.append_tag('substrate_material_uid', e.uid)
                else:
                    mat_data.append_tag('substrate_material_name', 'blendigo_null')

            elif identifier == 'ior':
                if not is_empty_socket:
                    ior = mat_data.append_tag('ior')
                    link.from_node.complete_xml(material, ior, link)
                else:
                    mat_data.append_tag('ior', self.get_input('ior').default_value)
            elif identifier == 'absorption_SP_rgb':
                if not is_empty_socket:
                    absorption = mat_data.append_tag('absorption')
                    link.from_node.complete_xml(material, absorption, link)
                else:
                    rgb = mat_data.append_tag(('absorption', 'constant', 'rgb'))
                    rgb.append_tag('rgb', _xml.wrap.RGB(self.get_input('absorption_SP_rgb').default_value))
                    rgb.append_tag('gamma', 2.2)
            elif identifier in {'fresnel_scale', 'roughness', 'thickness'}:
                if not is_empty_socket:
                    data = mat_data.append_tag(identifier)
                    link.from_node.complete_xml(material, data, link)
                else:
                    mat_data.append_tag((identifier, 'constant'), self.get_input(identifier).default_value)
        # reverse materials to avoid problems with included external mats that use names instead of uids
        materials.reverse()
        return materials

class IR_Mix(_MaterialBlendingCallback, IR_MaterialType, Node):
    bl_label = "Mix Materials"
    bl_icon = 'NODE_MATERIAL'
    ubername = "_IndigoBlendedUberShader_v1"

    step_blend: NodeProperty(bpy.props.BoolProperty, identifier='step_blend', description="Disables partial blends so the result is either material A or B, depending on whether the blend amount (constant or map) is >= 0.5.")

    def material_AB_detach(self, eevee_node, identifier):
        letter = identifier[-1:]
        eevee_node.inputs['null_'+letter].default_value = 1

    input_detach_callbacks = {
        "material_B": material_AB_detach,
        "material_A": material_AB_detach,
    }
    
    def draw_buttons(self, context, layout):
        # col = layout.column()
        # col.prop(self, 'step_blend')
        layout.prop(self, 'step_blend')
    
    def init_inputs(self, context):
        self.outputs.new(IR_Material_Socket.__name__, "Material")
        # self.inputs.new(IR_Float_Socket.__name__, "Blend Amount", identifier="blend_amount").description="A constant blending factor; 1.0 means 100% of Material A is used, 0.0 means 100% of material B is used."
        self.inputs.new(IR_Slider_F_TX_SH_Socket.__name__, "Blend Amount", identifier="blend_amount").slider=True
        self.inputs.new(IR_Material_Socket.__name__, "Material A", identifier="material_A")
        self.inputs.new(IR_Material_Socket.__name__, "Material B", identifier="material_B")
    
    def build_xml(self) -> list[ET.Element]:
        ''' Blend XML '''
        mat_uid = get_uid(self)

        material = _xml.XMLElement('material')
        material.append_tag('uid', mat_uid)
        mat_name = f'{self.id_data.material.name}: {self.name}'
        material.append_tag('name', mat_name)
        mat_data = material.append_tag('blend')
        mat_data.append_tag('step_blend', self.step_blend)

        materials = [material.etree_element,]

        for i, link in self.iterate_inputs(empty=True):
            # no link
            if isinstance(link, EmptySocket):
                if link.identifier == 'blend_amount':
                    mat_data.append_tag(('blend', 'constant'), link.default_value)
                elif link.identifier == 'material_B':
                    mat_data.append_tag('b_name', 'blendigo_null')
                elif link.identifier == 'material_A':
                    mat_data.append_tag('a_name', 'blendigo_null')
                
                continue

            # link
            identifier = link.to_socket.identifier

            if identifier == 'blend_amount':
                blend = mat_data.append_tag('blend')
                link.from_node.complete_xml(material, blend, link)
                continue

            # only identifier material_B or material_A are left

            ab_mat_uid = 'b_mat_uid' if identifier == 'material_B' else 'a_mat_uid'
            try:
                sub_mats = link.from_node.build_xml()
                sub_mat = sub_mats[0]
                sub_mat_uid = sub_mat.find('uid')
                if sub_mat_uid is not None:
                    mat_data.append_tag(ab_mat_uid, sub_mat_uid.text)
                else:
                    sub_mat_name = sub_mat.find('material_name').text
                    mat_data.append_tag(ab_mat_uid[0]+'_name', sub_mat_name)
                materials.extend(sub_mats)
            except (AlreadyProcessedException, NullMaterialException) as e:
                mat_data.append_tag(ab_mat_uid, e.uid)
        
        # reverse materials to avoid problems with included external mats that use names instead of uids
        materials.reverse()
        return materials


class IR_MaterialOutput(IR_MaterialOutputType, Node):
    bl_label = "Material Output"
    bl_icon = 'MATERIAL'
    
    def init_inputs(self, context):
        self.inputs.new(IR_Material_Socket.__name__, "Material")
    
    def build_xml(self):
        ''' Start building xml from this node. '''
        # model2 element helpers. better do it in the export operator
        # material_node_tree = self.get_material_node_tree()
        # material_node_tree['emission_scaled_materials'] = dict()
        # material_node_tree['_is_valid_light'] = False

        # only one input
        for i, link in self.iterate_inputs():
            # return list of xml materials
            return link.from_node.build_xml()
    
    def get_main_mat_uid(self):
        for i, link in self.iterate_inputs():
            # if isinstance(link.from_node, IR_ExternalMaterial):
            #     return ('material_name', link.from_node.material_name)
            # else:
            #     return ('uid', link.from_node.indigo_export_uid)
            return link.from_node.indigo_export_uid
    
    def get_main_material(self):
        for i, link in self.iterate_inputs():
            return link.from_node


class IR_F_Displacement(BlendigoNode, Node, MaterialFamily, MaterialFeatureFamily):
    bl_label = "Feature: Displacement Map"
    bl_icon = 'DISC'

    def init_inputs( self, context ):
        self.outputs.new(IR_F_Displacement_Socket.__name__, "Output", identifier='displacement_bool').default_value = 1
        self.inputs.new(IR_F_TX_Socket.__name__, "Texture", identifier='displacement_SP_rgb')
    
    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement, link: bpy.types.NodeLink):
        ''' Displacement XML '''
        displacement = mat_data.append_tag('displacement')
        for i, link in self.iterate_inputs(empty=True, invalid_as_empty=True):
            if isinstance(link, EmptySocket):
                displacement.append_tag('constant', self.get_input('displacement_SP_rgb').default_value)
            else:
                link.from_node.complete_xml(material_xml, displacement, link)

class IR_F_Normal(BlendigoNode, Node, MaterialFamily, MaterialFeatureFamily):
    bl_label = "Feature: Normal Map"
    bl_icon = 'DISC'

    def init_inputs( self, context ):
        self.outputs.new(IR_F_Normal_Socket.__name__, "Output", identifier='normal_bool').default_value = 1
        self.inputs.new(IR_TX_Socket.__name__, "Texture", identifier='normal_SP_rgb')
    
    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement, link: bpy.types.NodeLink):
        ''' Normal XML '''
        normal_map = mat_data.append_tag('normal_map')
        for i, link in self.iterate_inputs():
            link.from_node.complete_xml(material_xml, normal_map, link)

class IR_F_AbsorptionLayer(BlendigoNode, Node, MaterialFamily, MaterialFeatureFamily):
    bl_label = "Feature: Absorption Layer"
    bl_icon = 'DISC'

    # absorption_layer_bool: bpy.props.BoolProperty(default=True)
    def init_inputs( self, context ):
        self.outputs.new(IR_F_Absorption_Socket.__name__, "Output", identifier='absorption_layer_bool').default_value = 1
        self.inputs.new(IR_RGB_SP_TX_SH_Socket.__name__, "Texture", identifier='absorption_layer')
    
    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement, link: bpy.types.NodeLink):
        ''' Absorption XML '''
        absorption_layer_transmittance = mat_data.append_tag('absorption_layer_transmittance')
        for i, link in self.iterate_inputs(empty=True, invalid_as_empty=True):
            is_empty_socket = isinstance(link, EmptySocket)
            if not is_empty_socket:
                link.from_node.complete_xml(material_xml, absorption_layer_transmittance, link)
            else:
                rgb = absorption_layer_transmittance.append_tag(('constant', 'rgb'))
                rgb.append_tag('rgb', _xml.wrap.RGB(self.get_input('absorption_layer').default_value))
                rgb.append_tag('gamma', 2.2)

class IR_F_Bump(BlendigoNode, Node, MaterialFamily, MaterialFeatureFamily):
    bl_label = "Feature: Bump Map"
    bl_icon = 'DISC'

    def init_inputs( self, context ):
        self.outputs.new(IR_F_Bump_Socket.__name__, "Output", identifier='bump_bool').default_value = 1
        self.inputs.new(IR_TX_Socket.__name__, "Texture", identifier='bump_SP_rgb')
    
    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement, link: bpy.types.NodeLink):
        ''' Bump XML '''
        bump = mat_data.append_tag('bump')
        for i, link in self.iterate_inputs():
            link.from_node.complete_xml(material_xml, bump, link)
    
class IR_F_Emission(BlendigoNode, Node, MaterialFamily, MaterialFeatureFamily):
    bl_label = "Feature: Emission"
    bl_icon = 'DISC'

    # emission_bool: bpy.props.BoolProperty(default=True)

    emit_layer: bpy.props.StringProperty(name="Light Layer", description="lightlayer; leave blank to use default")
    # emit_power: bpy.props.FloatProperty(name="Power", description="Power", default=1500.0, min=0.0, max=1000000.0)
    emit_gain_val: bpy.props.FloatProperty(name="Gain", description="Gain", default=1.0, min=0.0, max=1.0)
    emit_gain_exp: bpy.props.IntProperty(name="*10^", description="Exponent", default=0, min=-30, max=30)
    # emission_scale: bpy.props.BoolProperty(name="Emission scale", description="Emission scale", default=False, update=lambda s,c: s.set_strength(c.material))

    # def emission_scale_un(self, context):
    #     # Update Node function
    #     emission_scale_socket =  first(s for s in self.inputs if s.identifier == 'emission_scale_value')
    #     if not self.emission_scale and emission_scale_socket:
    #         self.inputs.remove(emission_scale_socket)
    #     else:
    #         self.emission_scale_source_update_node(context)
    
    # def emission_scale_source_update_node(self, context):
    #     # Update Node function
    #     emission_scale_value_socket =  first(s for s in self.inputs if s.identifier == 'emission_scale_value')
    #     if self.emission_scale_source == 'MATERIAL':
    #         if not emission_scale_value_socket:
    #             self.inputs.new(IR_Float_Socket.__name__, "Emission Scale", identifier='emission_scale_value')
    #     elif self.emission_scale_source in {'OBJECT', 'DATA'}:
    #         if emission_scale_value_socket:
    #             self.inputs.remove(emission_scale_value_socket)

    # emission_scale: bpy.props.BoolProperty(name="Emission scale", description="Emission scale", default=False, update=lambda s,c: s.set_strength(c.material))
    # emission_scale: NodeProperty(bpy.props.BoolProperty, identifier='emission_scale', update_node=emission_scale_un, name="Emission scale", description="Emission scale", default=False)
    emission_scale: NodeProperty(bpy.props.BoolProperty, identifier='emission_scale', name="Emission scale", description="Emission scale", default=False)
    emission_scale_measure: bpy.props.EnumProperty(name="Unit", description="Units for emission scale", default="luminous_flux", items=[
        ('luminous_flux', 'lm', 'Luminous flux'),
        ('luminous_intensity', 'cd', 'Luminous intensity (lm/sr)'),
        ('luminance', 'nits', 'Luminance (lm/sr/m/m)'),
        ('luminous_emittance', 'lux', 'Luminous emittance (lm/m/m)')
    ])
    emission_scale_value: bpy.props.FloatProperty(name="Value", description="Emission scale value", default=1.0, min=0.0, soft_min=0.0, max=10.0, soft_max=10.0)
    emission_scale_exp: bpy.props.IntProperty(name="*10^", description="Emission scale exponent", default=0, min=-30, max=30)
    # emission_scale_source: NodeProperty(bpy.props.EnumProperty, identifier='emission_scale_source', update_node=emission_scale_source_update_node, name="Origin", description="Where emission scale is stored", default="MATERIAL", items=[
    emission_scale_source: NodeProperty(bpy.props.EnumProperty, identifier='emission_scale_source', name="Origin", description="Where emission scale is stored", default="MATERIAL", items=[
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
        # row = col.row(align=True)
        # row.prop(self, 'emit_gain_val')
        # row.prop(self, 'emit_gain_exp')
        
        col.prop(self, 'emission_scale')
        if self.emission_scale:
            box = col.box()
            scol = box.column(align=True)
            srow = scol.row(align=True)
            srow.prop(self, 'emission_scale_source', expand=True)
            srow = scol.row(align=True)
            if self.emission_scale_source == 'OBJECT':
                # TODO: move these to object properties
                srow.prop(context.object.indigo_object, 'emission_scale_value')
                srow.prop(context.object.indigo_object, 'emission_scale_exp')
                scol.prop(context.object.indigo_object, 'emission_scale_measure')
            elif self.emission_scale_source == 'MATERIAL':
                srow.prop(self, 'emission_scale_value')
                srow.prop(self, 'emission_scale_exp')
                scol.prop(self, 'emission_scale_measure')
            elif self.emission_scale_source == 'DATA':
                srow.prop(context.object.data.indigo_object, 'emission_scale_value')
                srow.prop(context.object.data.indigo_object, 'emission_scale_exp')
                scol.prop(context.object.data.indigo_object, 'emission_scale_measure')
        
        col.separator()    
        col.prop(self, 'em_sampling_mult')
        col.prop(self, 'emit_ies')
        if self.emit_ies:
            col.prop(self, 'emit_ies_path')
        
        col.prop(self, 'backface_emit_bool')
    
    def init_inputs( self, context ):
        self.width = 225
        self.outputs.new(IR_F_Emission_Socket.__name__, "Output", identifier='emission_bool').default_value = 1
        self.inputs.new(IR_RGB_SP_TX_SH_Socket.__name__, "Emission Multiplier", identifier='emission_SP_rgb')
        self.inputs.new(IR_RGB_SP_Socket.__name__, "Emission Power", identifier="emission_power")
    
    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement, link: bpy.types.NodeLink):
        ''' Emission XML '''
        print('# 4949909890 Emission XML')

        material_xml.append_tag('emission_sampling_factor', self.em_sampling_mult)
        material_xml.append_tag('backface_emit', self.backface_emit_bool)
        

        connected_sockets = set()
        for i, link in self.iterate_inputs():
            identifier = link.to_socket.identifier
            connected_sockets.add(identifier)
            if identifier == 'emission_SP_rgb':
                emission = mat_data.append_tag('emission')
                link.from_node.complete_xml(material_xml, emission, link)
            elif identifier == 'emission_power':
                base_emission = mat_data.append_tag('base_emission')
                # value = mat_data.append_tag(('base_emission', 'constant', 'uniform', 'value'))
                # link.from_node.complete_xml(material_xml, value, link)
                link.from_node.complete_xml(material_xml, base_emission, link)

                # value = mat_data.find('.//base_emission/constant/uniform/value')
                # if value:
                #     value.etree_element.text = str(float(value.text) * 10**self.emit_gain_exp * self.emit_gain_val)
        
        
        if 'emission_SP_rgb' not in connected_sockets:
            rgb = mat_data.append_tag(('emission', 'constant', 'rgb'))
            rgb.append_tag('rgb', _xml.wrap.RGB(self.get_input('emission_SP_rgb').default_value[:]))
            rgb.append_tag('gamma', 1)

        if 'emission_power' not in connected_sockets:
            power = self.get_input('emission_power').default_value# * 10**self.emit_gain_exp * self.emit_gain_val
            mat_data.append_tag(('base_emission', 'constant', 'uniform', 'value'), power)
        
        if self.emit_layer:
            layers = bpy.context.scene.indigo_lightlayers.enumerate()
            if self.emit_layer in layers:
                mat_data.append_tag('layer', bpy.context.scene.indigo_lightlayers.enumerate()[self.emit_layer])
        # TODO: get value of linked float/int inputs. These values can be extracted by simple getters.
        # E.g.: getattr(math_node, 'get_output_value_'+math_node_output.identifier)
        # Right now we don't have any float/int output node so it's pointless.

        # TODO: ies profiles. it should be saved in model2 tag.
        # Should ies profile be saved either in material (affects all objects)
        # or in the object data (only object), like emission scale?

        # TODO: validate
        material_node_tree = self.get_material_node_tree()
        material_node_tree['_is_valid_light'] = True
        link.to_node['_is_valid_light'] = True
        if self.emission_scale:
            mat_uid = material_xml.find('uid').text
            material_node_tree['emission_scaled_materials'][mat_uid] = (material_node_tree.name, self.name)


#######

class IR_Float(BlendigoNode, Node):
    bl_label = "Float"
    ubername = "ShaderNodeValue"

    # prop name matches eevee node 'Color' output
    Value = NodeProperty(bpy.props.FloatProperty, identifier='Value', name='Value')
    
    def draw_buttons( self, context, layout ):
        col = layout.column()
        row = col.row(align=True)
        row.prop(self, 'Value')
    
    def init_inputs( self, context ):
        self.outputs.new(IR_Float_Socket.__name__, "Value", identifier='value')

    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement, link: bpy.types.NodeLink):
        if isinstance(link.to_socket, IR_Slider_F_TX_SH_Socket, IR_F_TX_Socket):
            mat_data.append_tag('constant', self.Value)
        elif isinstance(link.to_socket, (IR_RGB_SP_Socket, IR_SP_Socket)):
            mat_data.append_tag(('constant', 'uniform', 'value'), self.Value)
        else:
            mat_data.etree_element.text = str(self.Value)

class IR_BlackBody(BlendigoNode, Node):
    bl_label = "Black Body"
    ubername = "_IndigoBlackbodyUberShader_v1"

    def update_callback(self, eevee_node, update_input_name):
        eevee_node.inputs[0].default_value = self.blackbody_temp

    blackbody_temp = NodeProperty(bpy.props.FloatProperty, identifier='blackbody_temp', min=1000, max=10_000, name='Temperature', default=6500, notify_callback=update_callback)
    blackbody_gain = NodeProperty(bpy.props.FloatProperty, identifier='blackbody_gain', min=0, name='Gain', default=1, notify_callback=update_callback)
    
    def draw_buttons( self, context, layout ):
        col = layout.column(align=True)
        col.prop(self, 'blackbody_temp')
        col.prop(self, 'blackbody_gain')
    
    def init_inputs( self, context ):
        self.outputs.new(IR_SP_Socket.__name__, "Spectrum", identifier='output')
    
    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement, link: bpy.types.NodeLink):
        blackbody = mat_data.append_tag(('constant', 'blackbody'))
        blackbody.append_tag('temperature', self.blackbody_temp)
        blackbody.append_tag('gain', self.blackbody_gain)

class IR_Uniform(BlendigoNode, Node):
    bl_label = "Uniform"
    ubername = "ShaderNodeValue"
    width = 250

    def update_callback(self, eevee_node, update_input_name):
        eevee_node.outputs[0].default_value = self.uniform_val * 10**self.uniform_exp * self.uniform_gain

    uniform_val = NodeProperty(bpy.props.FloatProperty, identifier='uniform_val', min=0, name='Value', default=1, notify_callback=update_callback)
    uniform_exp = NodeProperty(bpy.props.IntProperty, identifier='uniform_exp', min=-5, max=5, name='Exponent (*10^)', notify_callback=update_callback)
    uniform_gain: NodeProperty(bpy.props.FloatProperty, identifier='uniform_gain', name="Gain", description="Gain", default=1.0, min=0.0, max=1.0, notify_callback=update_callback)
    
    def draw_buttons( self, context, layout ):
        col = layout.column(align=True)
        col.prop(self, 'uniform_gain')
        col.prop(self, 'uniform_exp')
        col.separator()
        col.prop(self, 'uniform_val')
    
    def init_inputs( self, context ):
        self.outputs.new(IR_SP_Socket.__name__, "Spectrum", identifier='output')
    
    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement, link: bpy.types.NodeLink):
        mat_data.append_tag(('constant', 'uniform', 'value'), self.uniform_val * 10**self.uniform_exp * self.uniform_gain)

class IR_RGB(BlendigoNode, Node):
    bl_label = "RGB"
    ubername = "ShaderNodeRGB"

    # prop name matches eevee node 'Color' output
    Color = NodeProperty(bpy.props.FloatVectorProperty, identifier='Color', subtype='COLOR', min=0, max=1, name='Color', default=(.8, .8, .8))
    
    def draw_buttons( self, context, layout ):
        col = layout.column()
        row = col.row(align=True)
        row.prop(self, 'Color')
    
    def init_inputs( self, context ):
        self.outputs.new(IR_RGB_Socket.__name__, "Color", identifier='rgb_color')

    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement, link: bpy.types.NodeLink):
        rgb = mat_data.append_tag(('constant', 'rgb'))
        rgb.append_tag('rgb', _xml.wrap.RGB(self.Color))
        rgb.append_tag('gamma', 1)

class IR_RGB_Gamma(BlendigoNode, Node):
    bl_label = "RGB Gamma"
    ubername = "ShaderNodeGamma"

    def eevee_on_create(self, eevee_node):
        eevee_node.inputs['Gamma'].default_value = 1
    
    def init_inputs( self, context ):
        self.inputs.new(IR_RGB_Socket.__name__, "Color", identifier='Color')
        self.inputs.new(IR_Float_Socket.__name__, "Gamma", identifier='Gamma')
        self.outputs.new(IR_RGB_Socket.__name__, "Color", identifier='Color')

    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement, link: bpy.types.NodeLink):
        for i, link in self.iterate_inputs(empty=True, invalid_as_empty=True):
            identifier = link.identifier if isinstance(link, EmptySocket) else link.to_socket.identifier

            if identifier == 'Color':
                if isinstance(link, EmptySocket):
                    rgb = mat_data.append_tag(('constant', 'rgb'))
                    rgb.append_tag('rgb', _xml.wrap.RGB(self.get_input('Color').default_value[:]))
                    rgb.append_tag('gamma', self.get_input('Gamma').default_value)
                else:
                    link.from_node.complete_xml(material_xml, mat_data, link)
        
            elif identifier == 'Gamma':
                if isinstance(link, EmptySocket):
                    mat_data.find('.//gamma').etree_element.text = str(self.get_input('Gamma').default_value)
                else:
                    # TODO: get float value. currently threre's no float node
                    mat_data.find('.//gamma').etree_element.text # = ???

class IR_RGB_sRGB(BlendigoNode, Node):
    bl_label = "Linear RGB as sRGB"
    ubername = "ShaderNodeGamma"

    def eevee_on_create(self, eevee_node):
        eevee_node.inputs['Gamma'].default_value = 2.2
    
    def init_inputs( self, context ):
        self.inputs.new(IR_RGB_Socket.__name__, "Color", identifier='Color')
        self.outputs.new(IR_RGB_Socket.__name__, "Color", identifier='Color')

    def complete_xml(self, material_xml:_xml.XMLElement, mat_data:_xml.XMLElement, link: bpy.types.NodeLink):
        for i, link in self.iterate_inputs(empty=True, invalid_as_empty=True):
            identifier = link.identifier if isinstance(link, EmptySocket) else link.to_socket.identifier

            if identifier == 'Color':
                if isinstance(link, EmptySocket):
                    rgb = mat_data.append_tag(('constant', 'rgb'))
                    rgb.append_tag('rgb', _xml.wrap.RGB(self.get_input('Color').default_value[:]))
                    rgb.append_tag('gamma', '2.2')
                else:
                    link.from_node.complete_xml(material_xml, mat_data, link)
                    mat_data.find('.//gamma').etree_element.text = '2.2'
        
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
        NodeItem(IR_Coating.__name__),
        NodeItem(IR_Diffuse.__name__),
        NodeItem(IR_DoubleSidedThin.__name__),
        NodeItem(IR_ExternalMaterial.__name__),
        NodeItem(IR_FastSSS.__name__),
        NodeItem(IR_MaterialInput.__name__),
        NodeItem(IR_MaterialOutput.__name__),
        NodeItem(IR_Mix.__name__),
        NodeItem(IR_Phong.__name__),
        NodeItem(IR_Specular.__name__),
    ] ),
    BlendigoNodeCategory( "IR_Color", "Spectrum/Color/Texture", items = [
        NodeItem(IR_Texture.__name__),
        NodeItem(IR_AlterABC.__name__),
        NodeItem(IR_RGB.__name__),
        NodeItem(IR_RGB_Gamma.__name__),
        NodeItem(IR_RGB_sRGB.__name__),
        NodeItem(IR_Float.__name__),
        NodeItem(IR_Uniform.__name__),
        NodeItem(IR_BlackBody.__name__),
        NodeItem(IR_ShaderText.__name__),
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

from bpy.app.handlers import persistent
@persistent
def load_handler(dummy):
    # remove materials that have 0 users (excluding material.indigo_material.node_tree.material)
    no_user_mats = [mat for mat in bpy.data.materials
                    if not mat.use_fake_user
                        and mat.indigo_material.node_tree
                        and mat.users <= 1]
    for mat in no_user_mats:
        print("Removed unused material:", mat)
        bpy.data.materials.remove(mat)

def register():
    nodeitems_utils.register_node_categories( "IRNodes", categories )
    for c in classes:
        bpy.utils.register_class( c )
    
    bpy.app.handlers.load_post.append(load_handler)

def unregister():
    nodeitems_utils.unregister_node_categories( "IRNodes" )
    for c in classes:
        bpy.utils.unregister_class( c )
    
    bpy.app.handlers.load_post.remove(load_handler)

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

def get_random_id():
    import string, random
    letters = string.ascii_letters+string.digits
    return ''.join(random.choice(letters) for i in range(6))

def init_mat_node_tree(node_tree, material):
    material.use_nodes = True
    # node_tree.use_fake_user = True # TODO: check if still needed in the current Blender
    node_tree.material = material

    nodes = node_tree.nodes

    output = nodes.new("IR_MaterialOutput")
    output.location = 300, 200
    output.select = False

    diffuse = nodes.new("IR_Diffuse")
    diffuse.location = 50, 200

    node_tree.links.new(diffuse.outputs[0], output.inputs[0])

    # l.id = str(time_ns()) + ''.join(random.choice('0123456789ABCDEFGHIJKLMNOPRSTUWXYZ') for i in range(4))
    node_tree.id = get_random_id()

    material.indigo_material.node_tree = node_tree

    # node_tree will not be accessible until next re-evaluation
    bpy.app.timers.register(lambda: node_tree.update())

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
            new_node_tree.material = new_mat
            new_node_tree.id = get_random_id()

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
    ''' Add Feature node '''
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