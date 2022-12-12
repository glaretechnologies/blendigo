import re
import bpy
from dataclasses import dataclass, field

import pickle
from pathlib import Path

# TODO:
# Coating, DoubleSidedThin materials use references to other materials, so it is not really suitable for the current node system. Best to leave it till full material nodes implementation.

current_uber_name = "_IndigoUberShader_v1"

@dataclass
class ParsedNode:
    inputs: dict
    nodes: dict
    links: list
    name: str
    
    def generate_group(self):
        '''
        Current limitations:
            Don't use multiple links from group input node (use reroute).
            Group output has one output.
        '''
        # re.search(r'\[(\d+)\]$', 'nodes["Group"].in[213231].outputs[0]').group(1)

#        sort links
        # sorted_names = [i['name'] for i in self.inputs]
        # sorted_gil = [l for name in sorted_names for l in self.links if l[0][0]=='Group Input' and l[0][1]==name]
        # other_gil = [l for l in self.links if not l[0][0]=='Group Input']
        # sorted_links = sorted_gil + other_gil
        
        new_group = bpy.data.node_groups.new(self.name, 'ShaderNodeTree')
        nodes = new_group.nodes
        links = new_group.links
#        inp = nodes.new("NodeGroupInput")
#        out = nodes.new("NodeGroupOutput")
        
        for node_dict in self.nodes:
            bl_idname = node_dict.pop('bl_idname')
            parent = node_dict.pop('parent')
            node = nodes.new(bl_idname)
            node['parent'] = parent
            if parent:
                node['location'] = node_dict.pop('location')
            for key, val in node_dict.items():
                setattr(node, key, val)
            if bl_idname == 'NodeGroupInput':
                for input_dict in self.inputs:
                    soc = new_group.inputs.new(input_dict['bl_socket_idname'], input_dict['name'])
                    for key, val in input_dict.items():
                        if not hasattr(soc, key): # different Blender version
                            print(key, 'not found in', soc)
                            continue
                        setattr(soc, key, val)
            elif bl_idname == 'NodeGroupOutput':
                soc = new_group.outputs.new('NodeSocketShader', 'Shader')
        
#        set frames
        for node in nodes:
            if node['parent']:
                node.parent = nodes[node['parent']]
                node.location = node['location']
        
        for link in self.links:
            from_comp, to_comp = link
            print(from_comp, to_comp)
            from_soc = nodes[from_comp[0]].outputs[from_comp[1]]
            to_soc = nodes[to_comp[0]].inputs[to_comp[1]]
            links.new(from_soc, to_soc)

        return new_group
            
        

def nodes2dict():
    active_node_group = bpy.context.object.active_material.node_tree.nodes.active
    def _str(prop, val):
        # print list-like objects as lists
        if isinstance(val, bpy.types.Node):
            return val.name
        if hasattr(val, '__getitem__'):
            print(prop, prop.identifier, val)
            return val[:]
        return val
    inputs = []
    for input in active_node_group.node_tree.inputs:
        inputs.append( {prop.identifier: _str(prop, getattr(input, prop.identifier)) for prop in input.rna_type.properties if not prop.is_readonly and prop.type in {'STRING', 'INT', 'BOOLEAN', 'FLOAT', 'ENUM'}} )
        
    nodes = []
    for node in active_node_group.node_tree.nodes:
        nodes.append( {prop.identifier: _str(prop, getattr(node, prop.identifier)) for prop in node.rna_type.properties if not prop.is_readonly and prop.type in {'STRING', 'INT', 'BOOLEAN', 'FLOAT', 'POINTER'} and prop.identifier not in {'node_tree'}} )
    
    links = []
    def sid(soc):
        return int(re.search(r'\[(\d+)\]$', soc.path_from_id()).group(1))

    for link in active_node_group.node_tree.links:
        links.append( ((link.from_node.name, sid(link.from_socket)), (link.to_node.name, sid(link.to_socket))) )
    
    parsed = ParsedNode(inputs, nodes, links, current_uber_name)
#    print(parsed)
    return parsed




class OT_BR_ExportUberShaderNodes(bpy.types.Operator):
    """Export selected node group as Blendigo UberShader (for dev only)"""
    bl_idname = "blendigo.export_node_group"
    bl_label = "Export Group as UberShader"
    
    def execute(self, context):
        parsed_node=nodes2dict()
        path = Path(__file__).parent/'UberShader.bin'
        import os
        if os.path.isfile(path):
            path0 = Path(__file__).parent/'UberShader.bin0'
            if os.path.isfile(path0):
                os.remove(path0)
            os.rename(path, path0)
        
        with open(path, 'wb') as f:
            pickle.dump(parsed_node, f)
                
        return {'FINISHED'}

def first(generator):
    """
    Return first element from generator or None if empty
    """
    try:
        return next(generator)
    except StopIteration:
        return None

def load_ubershader() -> ParsedNode:
    with open(Path(__file__).parent/'UberShader.bin', 'rb') as f:
        parsed_node = pickle.load(f)
    return parsed_node

def ensure_ubershader():
    # Create new group for each node, so each node can manipulate its insides.
    if current_uber_name in bpy.data.node_groups:
        return bpy.data.node_groups[current_uber_name]
    
    parsed_node = load_ubershader()
    return parsed_node.generate_group()

class UberShaderException(Exception):
    pass

def _get_ubernode(material):
    def node_tree_nodes(material):
        if not material.use_nodes:
            material.use_nodes = True
        return material.node_tree.nodes

    material_output = first(n for n in node_tree_nodes(material) if n.type=='OUTPUT_MATERIAL' and n.is_active_output)
    out_links = material_output.inputs[0].links
    try:
        if not out_links:
            raise UberShaderException
        ubernode = out_links[0].from_node
        if ubernode.type != 'GROUP':
            raise UberShaderException
        if not (ubernode.node_tree and ubernode.node_tree.name == current_uber_name):
            raise UberShaderException
            
        # assert ubernode.bl_idname == 'ShaderNodeGroup'
        # assert ubernode.bl_idname == 'IR_BlendigoUberShader'
    except UberShaderException:
        # create IR_BlendigoUberShader and link
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        # ubernode = nodes.new('IR_BlendigoUberShader')
        ubernode = nodes.new('ShaderNodeGroup')
        ubernode.node_tree = ensure_ubershader()
        links.new(ubernode.outputs[0], material_output.inputs[0])
    return ubernode

def switch_enum(material, element, element_list):
    print(material, element, element_list)
    ubernode = _get_ubernode(material)
    for e in element_list:
        name = f'{e}_enum'
        if not name in ubernode.inputs:
            continue
        ubernode.inputs[name].default_value = 0
    name = f'{element}_enum'
    if name in ubernode.inputs:
        ubernode.inputs[name].default_value = 1

def switch_bool(material, element, value: bool):
    print(material, element, value)
    ubernode = _get_ubernode(material)
    name = f'{element}_bool'
    if name in ubernode.inputs:
        ubernode.inputs[name].default_value = 1 if value else 0
    
    # Make sure it's ready for transparency.
    # Could be put somewhere else but it's the first thing that came to mind
    material.blend_method = 'HASHED'

def switch_texture(material, element, value):
    ubernode = _get_ubernode(material)
    
    name = f'{element}_SP_rgb'
    # print(element, name, value)
    if name in ubernode.inputs:
        link = first(l for l in material.node_tree.links if l.to_socket == ubernode.inputs[name])
        if link:
            # TODO: assert node type image
            texnode = link.from_node
            if value in bpy.data.textures:
                texnode.image = bpy.data.textures[value].image
            else:
                texnode.image = None
        else:
            print('create image node')
            im = material.node_tree.nodes.new('ShaderNodeTexImage')
            if value in bpy.data.textures:
                im.image = bpy.data.textures[value].image
            material.node_tree.links.new(im.outputs[0], ubernode.inputs[name])

def switch_rgb(material, element, value):
    ubernode = _get_ubernode(material)
    name = f'{element}_rgb'
    # print(name)
    if name in ubernode.inputs:
        link = first(l for l in material.node_tree.links if l.to_socket == ubernode.inputs[name])
        if link:
            print('tex exist.')
            for n in [l.from_node for l in material.node_tree.links if l.to_node == link.from_node]:
                material.node_tree.nodes.remove(n)
            material.node_tree.nodes.remove(link.from_node)
        ubernode.inputs[name].default_value[:3] = value

def _ensure_uv_node(texnode, material):
    if texnode.inputs['Vector'].links and texnode.inputs['Vector'].links[0].from_node.bl_idname == 'ShaderNodeUVMap':
        return texnode.inputs['Vector'].links[0].from_node
    else:
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        uv_node = nodes.new('ShaderNodeUVMap')
        links.new(uv_node.outputs[0], texnode.inputs[0])
        return uv_node

def switch_uv(material, element, value):
    ubernode = _get_ubernode(material)
    name_texslot = f'{element}_SP_rgb'
    if name_texslot in ubernode.inputs:
        try:
            texnode = ubernode.inputs[name_texslot].links[0].from_node
            uv_node = _ensure_uv_node(texnode, material)
            uv_node.uv_map = value
        except:
            import traceback
            traceback.print_exc()


def set_float(material, element, value):
    ubernode = _get_ubernode(material)
    print(material, element, value)
    if element in ubernode.inputs:
        ubernode.inputs[element].default_value = value

if __name__ == "__main__":
#    generate dict from selected node group
   p=nodes2dict()
   import pprint
   pprint.pprint(p)

#    use dict to create node group
    # group.generate_group('_IndigoUberShader')
