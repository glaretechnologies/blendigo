import bpy
import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem, NodeItemCustom

from bpy.types import NodeSocket, Node, ShaderNodeCustomGroup, NodeSocketInterface, NodeTree
from .. core import RENDERER_BL_IDNAME

def get_link(socket):
    """
    Returns the link if this socket is linked, None otherwise.
    All reroute nodes between this socket and the next non-reroute node are skipped.
    Muted nodes are ignored.
    """

    if not socket.is_linked or not socket.links:
        return None

    link = socket.links[0]
    return link
    while link.from_node.bl_idname == "NodeReroute" or link.from_node.mute:
        node = link.from_node

        if node.mute:
            if node.internal_links:
                # Only nodes defined in C can have internal_links in Blender
                links = node.internal_links[0].from_socket.links
                if links:
                    link = links[0]
                else:
                    return None
            else:
                if not link.from_socket.bl_idname.startswith("LuxCoreSocket") or not node.inputs:
                    return None

                # We can't define internal_links, so try to make up a link that makes sense.
                found_internal_link = False

                for input_socket in node.inputs:
                    if input_socket.links and link.from_socket.is_allowed_input(input_socket):
                        link = input_socket.links[0]
                        found_internal_link = True
                        break

                if not found_internal_link:
                    return None
        else:
            # Reroute node
            if node.inputs[0].is_linked:
                link = node.inputs[0].links[0]
            else:
                # If the left-most reroute has no input, it is like self.is_linked == False
                return None

    return link


class Color:
    material = (0.39, 0.78, 0.39, 1.0)
    color_texture = (0.78, 0.78, 0.16, 1.0)
    float_texture = (0.63, 0.63, 0.63, 1.0)
    vector_texture = (0.39, 0.39, 0.78, 1.0)
    fresnel_texture = (0.33, 0.6, 0.85, 1.0)
    volume = (1.0, 0.4, 0.216, 1.0)
    mat_emission = (0.9, 0.9, 0.9, 1.0)
    mapping_2d = (0.65, 0.55, 0.75, 1.0)
    mapping_3d = (0.50, 0.25, 0.60, 1.0)
    shape = (0.0, 0.68, 0.51, 1.0)

class IR_NodeSocket:
    bl_label = ""

    color = (1, 1, 1, 1)
    slider = False
    # default_value: bpy.props.FloatProperty()

    # allowed_inputs = {}

    def draw_prop(self, context, layout, node, text):
        """
        This method can be overriden by subclasses to draw their property differently
        (e.g. done by LuxCoreSocketColor)
        """
        layout.prop(self, "default_value", text=text, slider=self.slider)

    @classmethod
    def is_allowed_input(cls, socket):
        print(socket.__class__, socket.bl_idname, socket.__class__.__name__ in cls.allowed_inputs)
        return socket.__class__.__name__ in cls.allowed_inputs
        # for allowed_class in cls.allowed_inputs:
        #     if isinstance(socket, allowed_class):
        #         return True
        # return False

    # Optional function for drawing the socket input value
    def drawO(self, context, layout, node, text):
        self.draw_prop(context, layout, node, text)
        # if self.is_output or self.is_linked:
        #     layout.label(text=text)
        # else:
        #     layout.label(text=text)

    def draw(self, context, layout, node, text):
        # Check if the socket linked to this socket is in the set of allowed input socket classes.
        link = get_link(self)
        if link and hasattr(self, "allowed_inputs"):
            if not self.is_allowed_input(link.from_socket):
                layout.label(text="Wrong Input!", icon='ERROR')
                return

        has_default = hasattr(self, "default_value") and self.default_value is not None

        if self.is_output or self.is_linked or not has_default:
            layout.label(text=text)

            # Show a button that lets the user add a node for this socket instantly.
            # Sockets that only accept one node (e.g. volume, emission, fresnel) should have a default_node member
            show_operator = not self.is_output and not self.is_linked and hasattr(self, "default_node")
            # Don't show for volume sockets on volume output
            # if self.bl_idname == "LuxCoreSocketVolume" and node.bl_idname == "LuxCoreNodeVolOutput":
            #     show_operator = False

            if show_operator:
                # op = layout.operator("luxcore.add_node", icon='ADD')
                op = layout.operator("transform.translate", icon='ADD')
                op.node_type = self.default_node
                op.socket_type = self.bl_idname
                op.input_socket = self.name
        else:
            self.draw_prop(context, layout, node, text)

    # Socket color
    def draw_color(self, context, node):
        return self.color

class IR_Float_Socket(IR_NodeSocket, NodeSocket):
    bl_label = "Texture"
    color = Color.float_texture
    default_value: bpy.props.FloatProperty()
    allowed_inputs = {'NodeSocketColor', 'IR_Color_Socket', 'IR_Float_Socket'}

# TX - texture
# SP - spectrum+TX
# SH - shader+SP+TX
class IR_Color_Socket(IR_NodeSocket, NodeSocket):
    bl_label = "Texture"
    color = Color.color_texture
    default_value: bpy.props.FloatVectorProperty(subtype='COLOR', min=0, max=1)
    allowed_inputs = {'NodeSocketColor', 'IR_Color_Socket', 'IR_SP_Socket'}

class IR_SP_Socket(IR_NodeSocket, NodeSocket):
    bl_label = "Texture"
    color = Color.color_texture
    default_value: bpy.props.FloatVectorProperty(subtype='COLOR', min=0, max=1)
    allowed_inputs = {'NodeSocketColor', 'IR_Color_Socket', 'IR_SP_Socket'}

class IR_SH_Socket(IR_NodeSocket, NodeSocket):
    bl_label = "Texture"
    color = Color.color_texture
    default_value: bpy.props.FloatVectorProperty(subtype='COLOR', min=0, max=1)
    allowed_inputs = {'NodeSocketColor', 'IR_Color_Socket', 'IR_SP_Socket'}

class IR_MaterialNodeTree(NodeTree):
    '''Indigo Renderer Material Nodes'''
    bl_label = "Indigo Material"
    bl_icon = 'NODE_MATERIAL'

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == RENDERER_BL_IDNAME
    
    @classmethod
    def get_from_context(cls, context):
        """
        Switches the displayed node tree when user selects object/material
        """
        obj = context.active_object

        if obj and obj.type not in {"LIGHT", "CAMERA"}:
            mat = obj.active_material

            if mat:
                node_tree = mat.indigo_material.node_tree

                if node_tree:
                    return node_tree, mat, mat

        return None, None, None
    
    # This block updates the preview, when socket links change
    def update(self):
        print('update from tree')
    
    def interface_update(self, context):
        print('interface_update from tree')
