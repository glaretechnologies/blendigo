from dataclasses import dataclass
from functools import partial
from bpy import utils
from itertools import chain
from typing import Generator, TypedDict
import bpy
import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem, NodeItemCustom

from bpy.types import NodeSocket, Node, ShaderNodeCustomGroup, NodeSocketInterface, NodeTree
from .. core import RENDERER_BL_IDNAME
from . ubershader_utils import fast_lookup, get_ubershader, new_eevee_node
from . simple_profiler import SimpleProfiler
from .. core import BLENDIGO_DEV

def first(generator):
    """
    Return first element from generator or None if empty
    """
    try:
        return next(generator)
    except StopIteration:
        return None

def get_link(socket):
    """
    Returns the link if this socket is linked, None otherwise.
    All reroute nodes between this socket and the next non-reroute node are skipped.
    Muted nodes are ignored.
    """
    if not socket.is_linked:
        return None
    socket_links = socket.links
    if not socket_links:
        return None

    link = socket_links[0]
    return link

def c_hash(object):
    """ Use modulo because Python's long ints can't be used in C bpy prop dicts. """
    return hash(object) % 2147483647

def into_timer(func):
    '''
    @into_timer decorator to jump out of context/loop and avoid some Blender bugs
    ATTENTION: The decorator uses 'is_timer' function argument to avoid registering more timers in nested calls.
    This parameter needs to be defined in the function.
    If I'm correct, each timer call is a one frame (1/60 s) lag.
    '''
    # OK... bugs, bugs, bugs... In Blender 3+ it is impossible to update node's sockets
    # in the context of the node_tree update (but it worked in 2.93). Solution is to use timer 
    # to jump out of this context into the next loop (or something like that).
    def wrap(*args, **kwargs):
        if 'is_timer' in kwargs and kwargs['is_timer']:
            return func(*args, **kwargs)
        kwargs['is_timer'] = True
        bpy.app.timers.register(partial(func, *args, **kwargs))
    return wrap

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
    feature = (0.25, 0.205, 0.974, 1.0)

# ███╗   ██╗ ██████╗ ██████╗ ███████╗    ████████╗██████╗ ███████╗███████╗
# ████╗  ██║██╔═══██╗██╔══██╗██╔════╝    ╚══██╔══╝██╔══██╗██╔════╝██╔════╝
# ██╔██╗ ██║██║   ██║██║  ██║█████╗         ██║   ██████╔╝█████╗  █████╗  
# ██║╚██╗██║██║   ██║██║  ██║██╔══╝         ██║   ██╔══██╗██╔══╝  ██╔══╝  
# ██║ ╚████║╚██████╔╝██████╔╝███████╗       ██║   ██║  ██║███████╗███████╗
# ╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚══════╝       ╚═╝   ╚═╝  ╚═╝╚══════╝╚══════╝

# updated_nodes_cache = []#set()
updated_nodes_cache = dict()
class IR_MaterialNodeTree(NodeTree):
    '''Indigo Renderer Material Nodes'''
    bl_label = "Indigo Material"
    bl_icon = 'NODE_MATERIAL'

    active_output_name: bpy.props.StringProperty()
    LOCK_UPDATE: bpy.props.BoolProperty(default=False)

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
    
    def get_output_nodes(self):
        return (n for n in self.nodes if isinstance(n, IR_MaterialOutputType))
    
    # This block updates the preview, when socket links change
    def update(self):
        self.do_update()
        # SimpleProfiler.sum_time(self.do_update)()

    @SimpleProfiler.sum_time
    def do_update(self):
        if self.LOCK_UPDATE:
            print('lock')
            return
        print('+ update from tree', self)
        print('     updated nodes:', updated_nodes_cache)

        # This function is called after all nodes updated.
        # At this point we have a list of all nodes which inputs have changed.

        # changed_materials = set()
        # for node in updated_nodes_cache.keys():
        #     mat = node.find_successor(IR_MaterialType)
        #     if mat and mat.find_successor(IR_MaterialOutputType):
        #         changed_materials.add(mat)
        
        # print(')()() changed materials', changed_materials)

        # for mat in changed_materials:
        #     # print('ancest', mat.find_all_ancestors())
        #     print('mat props dict', mat.gather_properties(MaterialFamily))

        if not (bpy.context.object and bpy.context.object.active_material):
            return

        @into_timer
        @SimpleProfiler.sum_time
        def start_update_in_timer(is_timer=False):
            self.LOCK_UPDATE = True
            try:
                for node, input_names in updated_nodes_cache.items():
                    for input_name in input_names:
                        node.update_eevee(update_input_name=input_name, is_timer=is_timer)
            except:
                import traceback
                traceback.print_exc()
                print("Exception while updating node tree. Trying to hard reset EEVEE node tree...")
                from . ubershader_utils import recreate_shader_from_blendigo_nodes
                updated_nodes_cache.clear()
                update_history_cache.clear()
                recreate_shader_from_blendigo_nodes(bpy.context.object.active_material, hard_reset=True)
            finally:
                self.LOCK_UPDATE = False
                updated_nodes_cache.clear()
                update_history_cache.clear()

                if BLENDIGO_DEV:
                    print("Node/node tree updates took:", SimpleProfiler)
                    SimpleProfiler.reset()
        start_update_in_timer()
        
        # from . ubershader_utils import recreate_shader_from_blendigo_nodes
        # recreate_shader_from_blendigo_nodes(bpy.context.object.active_material)


    
    def interface_update(self, context):
        print('interface_update from tree', self)

update_history_cache = set()
####################################
############# NODE BASES ###########
####################################

class FamilyInterface:
    family = Node
    # def find_all_ancestors(self):
    #     nodes_to_check = [l.to_node for s in self.inputs for l in s.links if isinstance(l.from_node, self.family)]
    #     return nodes_to_check
    #     # for node in nodes_to_check:
    #     while nodes_to_check:
    #         node = nodes_to_check.pop()
    #         if isinstance(node, node_class):
    #             return node
    #         nodes_to_check += [l.to_node for s in node.outputs for l in s.links]
    #     return None

class MaterialFamily(FamilyInterface):
    """ Mix-in class to support node-family constraints """
    pass

class MaterialOutputFamily(FamilyInterface):
    """ Mix-in class to support node-family constraints """
    pass

# unworthy_defaults = {'rna_type', 'type', 'location', 'width', 'width_hidden', 'height', 'dimensions', 'name', 'label', 'inputs', 'outputs', 'internal_links', 'parent', 'use_custom_color', 'color', 'select', 'show_options', 'show_preview', 'hide', 'mute', 'show_texture', 'bl_idname', 'bl_label', 'bl_description', 'bl_icon', 'bl_static_type', 'bl_width_default', 'bl_width_min', 'bl_width_max', 'bl_height_default', 'bl_height_min', 'bl_height_max'}
class EmptySocket:
    def __init__(self, socket):
        self.socket = socket
        # It crashed few times in the debugger here (probably) after modules reload.
        # I don't think this can be helped.
    
    def __getattr__(self, attr):
        return getattr(self.socket, attr)

class SocketLink:
    '''
    Probably, it is a bad idea to pass over socket links as references
    because creation of new links can refresh some collections and addresses breaking
    references and inducing Blender crashes.
    This class allows for passing links in a string format using path_from_id and path_resolve pairs.
    '''
    def __init__(self, link: bpy.types.NodeLink):
        self.node_tree = link.id_data.name
        self._from_node: str = link.from_node.path_from_id()
        self._from_socket: str = link.from_socket.path_from_id()
        self._to_node: str = link.to_node.path_from_id()
        self._to_socket: int = link.to_socket.path_from_id()
    
    @property
    def from_node(self):
        return bpy.data.node_groups[self.node_tree].path_resolve(self._from_node)
    
    @property
    def from_socket(self):
        return bpy.data.node_groups[self.node_tree].path_resolve(self._from_socket)

    @property
    def to_node(self):
        return bpy.data.node_groups[self.node_tree].path_resolve(self._to_node)

    @property
    def to_socket(self):
        return bpy.data.node_groups[self.node_tree].path_resolve(self._to_socket)


class BlendigoNode:
    """
    Mix-in class for all custom nodes in this tree type.
    """
    initialized: bpy.props.BoolProperty(default=False)
    id: bpy.props.IntProperty()
    local_props = set()
    ubername = None

    def finalize_init(self):
        self.update()

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == 'IR_MaterialNodeTree'
    
    def fast_lookup(self, eevee_node_tree, eevee_node=None, clear=False):
        id = str(self.id)
        # if not material_node_tree:
        #     material.use_nodes = True
            # material.use_nodes = True
        if not 'lookup_table' in eevee_node_tree:
            eevee_node_tree['lookup_table'] = dict()

        if eevee_node:
            eevee_node_tree['lookup_table'][id] = eevee_node.name
            return
        
        if id in eevee_node_tree['lookup_table']:
            if clear:
                del eevee_node_tree['lookup_table'][id]
                return None
            # return material_node_tree['lookup_table'][id]
            node_name = eevee_node_tree['lookup_table'][id]
            if node_name in eevee_node_tree.nodes:
                return eevee_node_tree.nodes[node_name]
            del eevee_node_tree['lookup_table'][id]
            return None
        return None
    
    def get_value_from_socket(self, identifier):
        """ Get value from output socket by its identifier. """
        raise NotImplementedError
    
    # def notify_update(self, context, identifier=None):
    #     """ General node's property and input socket update notification. """
    #     raise NotImplementedError
    
    @SimpleProfiler.measure_this("Property's notify_update")
    def notify_update(self, context, identifier, value, callback=None):
        """
        General node's property and input socket update notification.
        This method should call self.forward_notification_to_material(identifier, value) to propagate changes to material master
        """
        # is_timer=True to prevent firing a timer. This update does not involve any socket manipulation.
        if not self.find_successor(IR_MaterialOutputType):
            return
        self.update_eevee(update_input_name=identifier, is_timer=True, only_disconnected=True, callback=callback)
        # print(self, context, identifier)
        # print(self.__dir__(), context.__dir__())
        # self.forward_notification_to_material(identifier, value)
    
    def forward_notification_to_material(self, identifier, value):
        '''
        Mechanism to forward notifications to IR_MaterialType node.
        Currently this looks obsolete but may still come in handy.
        '''
        if isinstance(self, IR_MaterialType):
            # TODO: do something to refresh eevee shader
            print("Material", self, "notified of", identifier, value)
            self.update_property(identifier, value)
        else:
            for link in self.iterate_outputs():
                # if not link.from_socket.is_allowed_input(link.to_socket):
                #     continue
                link.to_node.forward_notification_to_material(identifier, value)
    
    def iterate_outputs(self) -> Generator[NodeSocket, None, None]:
        for out in self.outputs:
            for link in out.links:
                if not link.from_socket.is_allowed_input(link.to_socket):
                    continue
                yield link
    
    def iterate_inputs(self, *, empty=False, family_limit: FamilyInterface = None) -> Generator[tuple[int, NodeSocket], None, None]:
        for i, inp in enumerate(self.inputs):
            links = inp.links # because NodeSocket.links takes ``O(len(nodetree.links))`` time.
            if empty and not links:
                # yield i, EmptyLink(inp.identifier)
                yield i, EmptySocket(inp)
            for link in links:
                if not link.from_socket.is_allowed_input(link.to_socket):
                    continue
                if family_limit and not isinstance(link.from_node, family_limit):
                    continue
                yield i, link
    
    def find_successor(self, node_class):
        ''' Takes a class to compare with. Returns a node or None. '''
        if isinstance(self, node_class):
                return self

        nodes_to_check = [l.to_node for s in self.outputs for l in s.links]
        # for node in nodes_to_check:
        while nodes_to_check:
            node = nodes_to_check.pop()
            if isinstance(node, node_class):
                return node
            nodes_to_check += [l.to_node for s in node.outputs for l in s.links]
        return None
    
    special_props = dict()

    def gather_properties(self, family_limit: FamilyInterface = None):
        """ Gathers properties and returns dict. Currently obsolete. """
        # Gathers property dict of all nodes in the family e.g.:
        # Diffuse Material, Feature: Emission
        out_dict = dict()
        if hasattr(self.bl_rna, '__annotations__'):
            prop_names = [prop for prop in self.bl_rna.__annotations__.keys() if prop not in self.local_props]
            out_dict = dict.fromkeys(prop_names)
            for name in prop_names:
                out_dict[name] = getattr(self, name)
        
        for i, link in self.iterate_inputs(family_limit=family_limit):
            # if isinstance(link, EmptyLink):
            #     continue
            out_dict.update(link.from_node.gather_properties())
        
        return out_dict
    
    def _update_annotated_props(self, eevee_node, update_input_name: str=None):
        """ Updates annotated props in the EEVEE node"""

        # gather annotated props
        if hasattr(self.bl_rna, '__annotations__'):
            # update only update_input_name if passed
            # if update_input_name and hasattr(self, update_input_name):
            if update_input_name:
                if not hasattr(self, update_input_name):
                    return
                if update_input_name in eevee_node.inputs:
                    eevee_node.inputs[update_input_name].default_value = getattr(self, update_input_name, 0)
                elif hasattr(eevee_node, update_input_name):
                    setattr(eevee_node, update_input_name, getattr(self, update_input_name, None))
                return
            
            for prop_name in (prop for prop in self.bl_rna.__annotations__.keys() if prop not in self.local_props and prop in eevee_node.inputs):
                eevee_node.inputs[prop_name].default_value = getattr(self, prop_name, 0)

    def _update_socket_props(self, eevee_node, is_timer=True, update_input_name=None):
        for i, link in self.iterate_inputs(empty=True):
            if isinstance(link, EmptySocket):
                if update_input_name and link.identifier != update_input_name:
                    continue
                
                eevee_socket = eevee_node.inputs.get(link.identifier)
                if not eevee_socket:
                    continue
                
                # detach eevee link if exists
                eevee_input_link = first(l for l in eevee_socket.links)
                if eevee_input_link:
                    source_node = eevee_input_link.from_node
                    eevee_node.id_data.links.remove(eevee_input_link)
                    # remove the node if the node is not connected
                    if not any(socket for socket in source_node.outputs if socket.is_linked):
                        eevee_node.id_data.nodes.remove(source_node)

                if not hasattr(link, 'default_value'):
                    continue

                val = link.default_value
                if not isinstance(val, (float, int, bool)) and len(val) == 3:
                    val = (*val, 1)
                eevee_node.inputs[link.identifier].default_value = val
                continue
            
            if update_input_name and link.to_socket.identifier != update_input_name:
                    continue
            link.from_node.update_eevee(eevee_parent=eevee_node, blendigo_link=link, is_timer=is_timer)
        return


        # for socket in self.inputs:
        #     if not socket.is_linked and socket.identifier in eevee_node.inputs:
        #         eevee_node.inputs[socket.identifier].default_value = (*socket.default_value, 1) if len(socket.default_value) == 3 else socket.default_value
        #         continue
        #     elif not socket.is_linked:
        #         continue
        #     elif not socket.is_allowed_input(socket.links[0].from_socket):
        #         continue
        #     link = socket.links[0]
        #     # link.from_node.update_eevee(eevee_parent=eevee_node, link=SocketLink(link), is_timer=is_timer)
        #     link.from_node.update_eevee(eevee_parent=eevee_node, link=link, is_timer=is_timer)

    def init(self, context):
        # print('@$@# init', self)
        # new_links = []
        # for link in self.iterate_inputs():
        #     new_links.append(link)
        # self['linked_inputs'] = new_links
        self.id_data.LOCK_UPDATE=True
        self.init_inputs(context)
        self.id = c_hash(self)
        self['linked_inputs'] = dict()
        old_links = self['linked_inputs']
        for i, link in self.iterate_inputs(empty=True):
            if isinstance(link, EmptySocket):
                old_links[link.identifier] = None
            else:
                old_links[link.to_socket.identifier] = c_hash(link.from_socket)
        # print(old_links.to_dict())
        self.initialized = True
        self.id_data.LOCK_UPDATE=False
        self.id_data.update()
    
    def init_inputs(self):
        return None
    
    def copy(self, orig_node):
        self.id = c_hash(self)
    
    def free(self):
        try:
            material = bpy.context.object.active_material
        except:
            return
        
        eevee_node_tree = material.node_tree
        if material.indigo_material.node_tree is not self.id_data:
            return
        
        # Only independent nodes (with self.ubername) should be deleted so
        # nodes without self.ubername like Emission cannot delete their parents.
        if self.ubername:
            # Do not delete the eevee node so its children can still be used.
            # The node itself will get deleted later anyway. It's enough to delete the reference from fast_lookup
            
            # eevee_node = fast_lookup(eevee_node_tree, self.id)
            # if eevee_node:
            #     eevee_node_tree.nodes.remove(eevee_node)
            fast_lookup(eevee_node_tree, self.id, clear=True)
        
        # This is a good place to clear unconnected EEVEE nodes
        nodes_to_delete = [n for n in eevee_node_tree.nodes if 'blendigo_node' in n and not any(True for s in n.outputs if s.is_linked)]
        for eevee_node in nodes_to_delete:
            eevee_node_tree.nodes.remove(eevee_node)

    def update(self):
        '''
        Inherited method. Use hook to allow simple profiling.
        Fires for each node on every node tree change before node_tree update.
        '''
        self.do_update()

    @SimpleProfiler.sum_time
    def do_update(self):
        from time import perf_counter
        t1_start = perf_counter()
        ''' Callback on node tree topology changes '''

        if not self.initialized:
            return
        if not isinstance(self, IR_MaterialOutputType) and not self.outputs[0].is_linked:
            return
        if self.id_data.LOCK_UPDATE:
            print('node update LOCKED')
            return

        old_links = self['linked_inputs']#.to_dict()
        new_links = dict()
        for i, link in self.iterate_inputs(empty=True):
            if isinstance(link, EmptySocket):
                new_links[link.identifier] = None
            else:
                new_links[link.to_socket.identifier] = c_hash(link.from_socket)

        changed = set(new_links.items()) ^ set(old_links.items())
        # changed = {l[0] for l in changed}

        if not changed:
            return
        
        for identifier, hsh in changed:
            # if self in updated_nodes_cache:
            #     continue
            socket = first(s for s in self.inputs if s.identifier == identifier)
            
            # updated_nodes_cache.append(self)
            if not self in updated_nodes_cache:
                updated_nodes_cache[self] = set()
            updated_nodes_cache[self].add(identifier)

            if not socket and identifier in old_links:
                del old_links[identifier]
                continue
            
            socket_links = socket.links
            if socket_links:
                old_links[identifier] = c_hash(socket_links[0].from_socket)
            else:
                old_links[identifier] = None

        t1_stop = perf_counter()
        print("     perf:", self.name, t1_stop-t1_start, changed)
    

    # @into_timer
    def update_eevee(self, *,
            eevee_parent=None,
            blendigo_link:SocketLink=None,
            is_timer: bool = False,
            update_input_name: str = None,
            only_disconnected: bool = False,
            callback = None) -> None:
        '''
        Use this method to update EEVEE node tree from a node.
        :param eevee_parent: Node representing an EEVEE parent node or direct counterpart of the node that this method
            is invoked for. For example, an EEVEE's material output can be a Blendigo Diffuse's eevee_parent.
            Can be None if update is triggered for a non-root node (soft update).
        :type: BlendigoNode
        '''
        if not only_disconnected:
            if ((self.name, None) in update_history_cache
                or (self.name, update_input_name) in update_history_cache):
                return
            update_history_cache.add((self.name, update_input_name))
        
        if eevee_parent:
            eevee_tree = eevee_parent.id_data
        else:
            material = bpy.context.object.active_material
            if not material.node_tree:
                material.use_nodes = True
            eevee_tree = material.node_tree


        if self.ubername:
            # Node that creates independent EEVEE node (e.g.: diffuse, mix, phong)
            eevee_node = self.fast_lookup(eevee_tree)
            if not eevee_node and eevee_parent:
                eevee_node = new_eevee_node(eevee_tree.nodes, self.ubername)
                self.fast_lookup(eevee_tree, eevee_node)
            elif not eevee_node and not eevee_parent:
                # should not happen
                # but happens when duplicating multiple nodes
                # should be enough to return from here
                return
                # from .ubershader_utils import recreate_shader_from_blendigo_nodes
                # print("update_eevee E1: not eevee_material and not eevee_parent")
                # recreate_shader_from_blendigo_nodes(material, hard_reset=False)
                # raise Exception("update_eevee E1: not eevee_material and not eevee_parent")
        else:
            # Dependent node like Features (e.g.: Emission)
            if eevee_parent:
                # Update called from a parent node
                eevee_node = eevee_parent
                # fast_lookup(eevee_tree, self.id, eevee_material)
                self.fast_lookup(eevee_tree, eevee_node)
            else:
                # Update called from this node (change detected).
                # Try to find this node's counterpart.
                # eevee_material = fast_lookup(eevee_tree, self.id)
                eevee_node = self.fast_lookup(eevee_tree)
        
                if not eevee_node:
                    raise Exception("update_eevee E2: TODO: trigger full tree reevaluation")
                    print("update_eevee E2: TODO: trigger full tree reevaluation")
                    return
                    # TODO: trigger full tree reevaluation
        
        assert eevee_node is not None

        # update_input_name suggests that this node should be updated only downward.
        # Do not try to check upward connections if update_input_name is not None
        if not update_input_name and not only_disconnected:
            self.ensure_eevee_upward_links(eevee_node, eevee_parent, blendigo_link)

        # gather annotated props
        self._update_annotated_props(eevee_node, update_input_name)
  
        # gather input sockets
        self._update_socket_props(eevee_node, is_timer, update_input_name)

        # print('DISABLE LOCK: ',self)
        # self.id_data.LOCK_UPDATE = False
    
    inputs_translation = {
        "Material": 0,
    }
    def ensure_eevee_upward_links(self, eevee_node, eevee_parent, blendigo_link):
        '''
        Overload this method to define how the eevee node should connect itself to parent eevee node.
        For most of the nodes these standard method should suffice.

        Names of EEVEE sockets should match Blendigo sockets for ease of use.

        Create this node's output links.
        Delete this node's unnecessary input links
        '''
        if eevee_node is eevee_parent:
            return
        # Diffuse, Mix can be linked to Mix, Material Output
        eevee_tree = eevee_node.id_data
        socket_name = self.inputs_translation.get(blendigo_link.to_socket.identifier, blendigo_link.to_socket.identifier)
        # socket_name = self.inputs_translation[blendigo_link.to_socket.identifier]
        if not first(l for l in eevee_node.outputs[0].links if l.to_node == eevee_parent and l.to_socket.identifier == socket_name):
            eevee_tree.links.new(eevee_node.outputs[0], eevee_parent.inputs[socket_name])
    
    # def _get_eevee_node(self, eevee_tree):
    #     if not self.ubername:
    #         return
        
    #     # eevee_material = fast_lookup(eevee_tree, self.id)
    #     eevee_material = self.fast_lookup(eevee_tree)
    #     if not eevee_material:
    #         eevee_material = new_eevee_node(eevee_tree.nodes, self.ubername)
    #         # fast_lookup(eevee_tree, self.id, eevee_material)
    #         self.fast_lookup(eevee_tree, eevee_material)

class IR_MaterialType(BlendigoNode, MaterialOutputFamily, MaterialFamily):
    """ Mix-in class for main material type nodes """
    family = MaterialFamily
    def init(self, context):
        super().init(context)
        # self.properties = dict() # I guess this one won't work without proper bpy.props property annotation
        self['properties'] = dict()
        get_ubershader(self.ubername)

    def update_property(self, identifier, value):
        self['properties'][identifier] = value
        print("Mat Props:", self['properties'])
        # TODO:
        # self.ubershader.update_prop(identifier, value)
    
    # def gather_properties(self):
    #     all_props = dict()

    #     for link in self.iterate_inputs():
    #         # if isinstance(link.from_node, IR_MaterialType):
    #         #     props = link.from_node.gather_properties()
    #         # else:
    #         #     pass
    #         if hasattr(link.from_node, 'gather_properties'):
    #             all_props.update(link.from_node.gather_properties())

def get_theme(context):
    current_theme_name = context.preferences.themes.items()[0][0]
    return context.preferences.themes[current_theme_name]

class IR_MaterialOutputType(BlendigoNode, MaterialOutputFamily):
    """ Mix-in class for main output type nodes """
    family = MaterialOutputFamily
    is_active_output: bpy.props.BoolProperty()
    # select: bpy.props.BoolProperty(update=lambda self, context: print("selected output"))

    def fast_lookup(self, material_node_tree, eevee_node=None, clear=False):
        '''
        IR_MaterialOutputType does not have self.ubername, blendigo_node property,
        nor should it be stored in the fast lookup, as the user can change the active output.

        fast_lookup does not create nodes but in this case let's make an exception, as the existence of
        the output is my invariant.
        '''
        eevee_root = material_node_tree.get_output_node('ALL')
        if not eevee_root:
            eevee_root = material_node_tree.new('ShaderNodeOutputMaterial')
        
        return eevee_root
    
    # @classmethod
    # def poll(cls, node_tree):
    #     print('poll')
    #     if first(n for n in node_tree.nodes if isinstance(n, cls)):
    #         return False
    #     return True
    
    # def poll_instance(self, node_tree):
    #     print('poll instance')
    #     if first(n for n in node_tree.nodes if isinstance(n, IR_MaterialOutputType)):
    #         return False
    #     return True

    def set_active(self, active):
        self.is_active_output = active

        # Update color
        theme = get_theme(bpy.context)
        # We can only set a tuple with 3 elements, not 4
        color = theme.node_editor.node_backdrop[:3]

        if self.is_active_output:
            # Like the theme color, but a bit lighter and greener
            self.color = [color[0] * 0.8, color[1] * 1.5, color[2] * 0.8]
            node_tree = self.id_data
            node_tree.active_output_name = self.name
        else:
            # Like the theme color, but a bit darker
            self.color = [x * 0.6 for x in color]

    
    def disable_other_outputs(self):
        node_tree = self.id_data
        if node_tree is None:
            return
        for node in node_tree.get_output_nodes():
            if node == self:
                continue

            if node.is_active_output:
                node.set_active(False)
                # There can only be one active output at a time, so
                # we don't need to check the others
                break

    def copy(self, orig_node):
        super().copy()
        self.disable_other_outputs()

    def update(self):
        ''' Callback on node tree topology changes '''
        if self.is_active_output:
            node_tree = self.id_data
            node_tree.active_output_name = self.name
        super().update()
    
    def init(self, context):
        self.use_custom_color = True
        self.disable_other_outputs()
        self.set_active(True)
        super().init(context)


# ███████╗ ██████╗  ██████╗██╗  ██╗███████╗████████╗███████╗
# ██╔════╝██╔═══██╗██╔════╝██║ ██╔╝██╔════╝╚══██╔══╝██╔════╝
# ███████╗██║   ██║██║     █████╔╝ █████╗     ██║   ███████╗
# ╚════██║██║   ██║██║     ██╔═██╗ ██╔══╝     ██║   ╚════██║
# ███████║╚██████╔╝╚██████╗██║  ██╗███████╗   ██║   ███████║
# ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝
                                                          
class IR_NodeSocket:
    bl_label = ""

    color = (1, 1, 1, 1)
    slider = False
    hidden_value = False
    # default_value: bpy.props.FloatProperty()

    # allowed_inputs = {}

    def notify_update(self, context, identifier=None):
        identifier = identifier if identifier else self.identifier
        self.node.notify_update(context, identifier, self.default_value if hasattr(self, 'default_value') else None)

    def draw_prop(self, context, layout, node, text):
        """
        This method can be overriden by subclasses to draw their property differently
        (e.g. done by LuxCoreSocketColor)
        """
        layout.prop(self, "default_value", text=text, slider=self.slider)

    @classmethod
    def is_allowed_input(cls, socket):
        # print('is_allowed_input:', socket.node, socket, socket.__class__, socket.bl_idname, socket.__class__.__name__ in cls.allowed_inputs)
        return socket.__class__.__name__ in cls.allowed_inputs
        # for allowed_class in cls.allowed_inputs:
        #     if isinstance(socket, allowed_class):
        #         return True
        # return False

    # Optional function for drawing the socket input value
    def draw(self, context, layout, node, text):
        # Check if the socket linked to this socket is in the set of allowed input socket classes.
        link = get_link(self)
        if link and hasattr(self, "allowed_inputs"):
            if not self.is_allowed_input(link.from_socket):
                layout.label(text="Wrong Input!", icon='ERROR')
                return

        has_default = hasattr(self, "default_value") and self.default_value is not None

        if self.is_output or self.is_linked or not has_default or self.hidden_value:
            layout.label(text=text)

            # Show a button that lets the user add a node for this socket instantly.
            # Sockets that only accept one node (e.g. volume, emission, fresnel) should have a default_node member
            show_operator = not self.is_output and not self.is_linked and hasattr(self, "default_node")
            if show_operator:
                op = layout.operator("blendigo.add_node", icon='ADD', text="")
                op.node_type = self.default_node
                op.identifier = self.identifier
        else:
            self.draw_prop(context, layout, node, text)

    # Socket color
    def draw_color(self, context, node):
        return self.color
    
    def get_value(self):
        link = get_link(self)
        if link and hasattr(self, "allowed_inputs"):
            if not self.is_allowed_input(link.from_socket):
                # raise WrongInputError
                return
            # TODO: implement node.get_value_from_socket(identifier)
            return link.from_node.get_value_from_socket(link.from_socket.identifier)
        elif hasattr(self, 'default_value'):
            return self.default_value

class WrongInputError(Exception):
    pass

def NodeProperty(type, /, *, update_node=None, identifier, **opts):
    ''' Wrap normal property and its update function with additional function updating the node (sockets etc.). Also calls node's general property update '''
    if 'update' in opts and update_node:
        foreign_f = opts['update']
        def f(self, context):
            update_node(self, context)
            foreign_f(self, context)
            self.notify_update(context, identifier, getattr(self, identifier))
        opts['update'] = f
    elif update_node:
        def f(self, context):
            update_node(self, context)
            self.notify_update(context, identifier, getattr(self, identifier))
        opts['update'] = f
    else:
        opts['update'] = lambda self, context: self.notify_update(context, identifier, getattr(self, identifier))
    return type(**opts)

def SocketProperty(type, /, *, update_node=None, identifier=None, **opts):
    ''' Wrap normal property and its update function with additional function updating the node (sockets etc.). Also calls node's general property update '''
    if 'update' in opts and update_node:
        foreign_f = opts['update']
        def f(self, context):
            update_node(self, context)
            foreign_f(self, context)
            self.notify_update(context, identifier)
        opts['update'] = f
    elif update_node:
        def f(self, context):
            update_node(self, context)
            self.notify_update(context, identifier)
        opts['update'] = f
    else:
        opts['update'] = lambda self, context: self.notify_update(context, identifier)
    return type(**opts)

class IR_Float_Socket(IR_NodeSocket, NodeSocket):
    bl_label = "Float"
    color = Color.float_texture
    default_value: SocketProperty(bpy.props.FloatProperty)
    allowed_inputs = {'NodeSocketColor', 'IR_Color_Socket', 'IR_Float_Socket', 'IR_Slider_Socket'}

class IR_Slider_Socket(IR_NodeSocket, NodeSocket):
    bl_label = "Slider"
    color = Color.float_texture
    default_value: SocketProperty(bpy.props.FloatProperty, min=0, max=1)
    allowed_inputs = {'NodeSocketColor', 'IR_Color_Socket', 'IR_Float_Socket', 'IR_Slider_Socket'}

# class IR_Slider_SocketInterface(bpy.types.NodeSocketInterface):
#     bl_idname = 'IR_Slider_SocketInterface'
#     bl_socket_idname = 'IR_Slider_Socket'
#     bl_label = 'IR_Slider_SocketInterface'
#     def draw(self, context, layout):
#         pass
#     def draw_color(self, context):
#         return (0,1,1,1)

class IR_Material_Socket(IR_NodeSocket, NodeSocket):
    bl_label = "Material"
    color = Color.material
    allowed_inputs = {'IR_Material_Socket'}

class IR_Feature_Socket(IR_NodeSocket, NodeSocket):
    bl_label = "Feature"
    color = Color.feature
    allowed_inputs = {'IR_Feature_Socket'}
    hidden_value = True

class IR_F_Emission_Socket(IR_Feature_Socket, NodeSocket):
    bl_label = "Emission"
    color = Color.feature
    allowed_inputs = {'IR_F_Emission_Socket'}
    default_node: bpy.props.StringProperty(default='IR_F_Emission')
    default_value: bpy.props.BoolProperty()

class IR_F_Displacement_Socket(IR_Feature_Socket, NodeSocket):
    bl_label = "Displacement"
    color = Color.feature
    allowed_inputs = {'IR_F_Displacement_Socket'}
    default_node: bpy.props.StringProperty(default='IR_F_Displacement')
    default_value: bpy.props.BoolProperty()

class IR_F_Normal_Socket(IR_Feature_Socket, NodeSocket):
    bl_label = "Normal"
    color = Color.feature
    allowed_inputs = {'IR_F_Normal_Socket'}
    default_node: bpy.props.StringProperty(default='IR_F_Normal')
    default_value: bpy.props.BoolProperty()

class IR_F_Bump_Socket(IR_Feature_Socket, NodeSocket):
    bl_label = "Bump"
    color = Color.feature
    allowed_inputs = {'IR_F_Bump_Socket'}
    default_node: bpy.props.StringProperty(default='IR_F_Bump')
    default_value: bpy.props.BoolProperty()

# TX - texture
# SP - spectrum+TX
# SH - shader+SP+TX
class IR_Color_Socket(IR_NodeSocket, NodeSocket):
    bl_label = "Texture"
    color = Color.color_texture
    default_value: SocketProperty(bpy.props.FloatVectorProperty, subtype='COLOR', min=0, max=1)
    allowed_inputs = {'NodeSocketColor', 'IR_Color_Socket', 'IR_SP_Socket'}

class IR_SP_Socket(IR_NodeSocket, NodeSocket):
    bl_label = "Texture"
    color = Color.color_texture
    default_value: SocketProperty(bpy.props.FloatVectorProperty, subtype='COLOR', min=0, max=1)
    allowed_inputs = {'NodeSocketColor', 'IR_Color_Socket', 'IR_SP_Socket'}

class IR_SH_Socket(IR_NodeSocket, NodeSocket):
    bl_label = "Texture"
    color = Color.color_texture
    default_value: SocketProperty(bpy.props.FloatVectorProperty, subtype='COLOR', min=0, max=1)
    allowed_inputs = {'NodeSocketColor', 'IR_Color_Socket', 'IR_SP_Socket'}


import bpy
from bpy.app.handlers import persistent
@persistent
def clear_node_history_handler(scene):
    ''' Clear nodes to prevent crashes. '''
    print('cleaning')
    update_history_cache.clear()
    updated_nodes_cache.clear()

# def register():
    # bpy.app.handlers.load_pre.append(clear_node_history_handler)
#     bpy.utils.register_class(IR_Slider_SocketInterface)


# def unregister():
    # bpy.app.handlers.load_pre.remove(clear_node_history_handler)
#     bpy.utils.unregister_class(IR_Slider_SocketInterface)