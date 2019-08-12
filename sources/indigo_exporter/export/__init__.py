import collections, xml.etree.cElementTree as ET, time, os
from ..extensions_framework import log, util as efutil

REPORTER = None
PRINT_CONSOLE = efutil.find_config_value('indigo', 'defaults', 'console_output', False)

OBJECT_ANALYSIS = os.getenv('B25_OBJECT_ANALYSIS', False)

def indigo_log(message, popup=False, message_type='INFO'):
    global REPORTER, PRINT_CONSOLE
    if REPORTER == None or PRINT_CONSOLE:
        log('%s: %s' % (message_type, message), popup, module_name='Indigo')
    else:
        REPORTER({message_type}, '[Indigo %s] %s' % (time.strftime('%Y-%b-%d %H:%M:%S'), message))

class xml_cdata(str):
    pass

class xml_multichild(list):
    pass

class xml_builder(object):
    """Formatting functions for various data types"""
    format_types = {
        'bool': lambda c,x: str(x).lower(),
        'collection': lambda c,x: x,
        'enum': lambda c,x: x,
        'float': lambda c,x: x,
        'int': lambda c,x: x,
        'pointer': lambda c,x: x,
        'string': lambda c,x: x,
    }
    
    Element = ET.Element
    SubElement = ET.SubElement
    
    def build_subelements(self, context, d, elem):
        """Parse the values in the format dict d and collect the
        formatted data into XML structure starting elem
        
        """
        
        for key in d.keys():
            # tuple and xml_multichild provides multiple child elements
            if type(d[key]) in (tuple, xml_multichild):
                for cd in d[key]:
                    self.build_subelements(context, {key:cd}, elem)
                continue # don't create empty element for tuple child
            
            x = self.SubElement(elem, key)
            
            if type(d[key]) is xml_cdata:
                # Since CDATA handling is near impossible, we'll use
                # substitute sentinels for characters that would otherwise
                # get entity-encoded, and substitute them back as we write
                # to disk
                cdata = '\n<![CDATA[\n%s\n]]>\n' % d[key]
                cdata = cdata.replace('<', '{_LESSTHAN_}')
                cdata = cdata.replace('>', '{_GREATERTHAN_}')
                x.text = cdata
                continue
            
            # dictionary provides nested elements
            if type(d[key]) is dict:
                self.build_subelements(context, d[key], x)
                
            # list provides direct value insertion
            elif type(d[key]) is list:
                x.text = ' '.join([str(i) for i in d[key]])
            
            # else look up property
            else:
                for p in self.properties:
                    if d[key] == p['attr']:
                        if 'compute' in p.keys():
                            x.text = str(p['compute'](context, self))
                        else:
                            x.text = str(
                                self.format_types[p['type']](
                                    context,
                                    getattr(self, d[key])
                                )
                            )
                            
class InvalidGeometryException(Exception):
    pass

class UnexportableObjectException(Exception):
    pass

class ExportCache(object):
    
    name = 'Cache'
    cache_keys = set()
    cache_items = collections.OrderedDict()
    
    def __init__(self, name):
        self.name = name
        self.cache_keys = set()
        self.cache_items = collections.OrderedDict()
    
    def have(self, ck):
        return ck in self.cache_keys
    
    def add(self, ck, ci):
        self.cache_keys.add(ck)
        self.cache_items[ck] = ci
    
    def get(self, ck):
        if self.have(ck):
            return self.cache_items[ck]
        else:
            raise Exception('Item %s not found in %s!' % (ck, self.name))
    
    def get_all(self):
        return self.cache_items.items()
    
    def count(self):
        return len(self.cache_keys)

class SceneIterator(object):
    progress_thread_action = "Exporting"
    
    supported_mesh_types = [
        'MESH',
        'CURVE',
        'SURFACE',
        'FONT',
        'LIGHT'
    ]
    
    scene = None
    abort = False
    
    def canAbort(self):
        return self.abort
    
    def iterateScene(self, depsgraph):
        self.scene = depsgraph.scene_eval

        for ob_inst in depsgraph.object_instances:
            if ob_inst.is_instance:  # Real dupli instance
                obj = ob_inst.instance_object
                parent = ob_inst.parent
            else:  # Usual object
                obj = ob_inst.object
    
            if self.canAbort(): break
            if OBJECT_ANALYSIS: indigo_log('Analysing object %s : %s' % (obj, obj.type))
                
            try:
                # Export only objects which are enabled for render (in the outliner) and visible on a render layer
                if obj.is_instancer and not obj.show_instancer_for_render:
                    raise UnexportableObjectException(' -> not visible')
                
                if not obj.type in self.supported_mesh_types:
                    raise UnexportableObjectException('Unsupported object type')
                
                if obj.type == 'LIGHT':
                    self.handleLamp(obj)
                elif obj.type in ('MESH', 'CURVE', 'SURFACE', 'FONT'):
                    self.handleMesh(ob_inst)
            
            except UnexportableObjectException as err:
                if OBJECT_ANALYSIS: indigo_log(' -> Unexportable object: %s : %s : %s' % (obj, obj.type, err))