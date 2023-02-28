from itertools import chain
import bpy

starting_uid = 100
counter = starting_uid

def reset():
    global starting_uid
    global counter
    counter = starting_uid

    data = (
        getattr(bpy.data, p.identifier)
        for p in bpy.data.bl_rna.properties
        if hasattr(getattr(bpy.data, p.identifier), '__iter__') and p.identifier not in {'filepath', 'version'}
    )

    mediums = (
        (m,) for s in bpy.data.scenes for m in s.indigo_material_medium.medium
    )

    for coll in chain(data, mediums):
        for obj in coll:
            if isinstance(obj, bpy.types.NodeTree):
                for node in obj.nodes:
                    node['_indigo_export_uid'] = 0
                continue
            
            # do not use hasattr because it would trigger the get_uid getter. search properties dict instead
            if not 'indigo_export_uid' in obj.bl_rna.properties:
                break

            obj['_indigo_export_uid'] = 0

def new_uid():
    global counter
    counter += 1
    return counter

def _get_uid(self):
    if '_indigo_export_uid' not in self:
        self['_indigo_export_uid'] = 0
    if self['_indigo_export_uid'] == 0:
        global counter
        counter += 1
        self['_indigo_export_uid'] = counter
    print('@@@@@@', self, self['_indigo_export_uid'])

    return self['_indigo_export_uid']

def register():
    bpy.types.ID.indigo_export_uid = bpy.props.IntProperty(get=_get_uid)
    bpy.types.Node.indigo_export_uid = bpy.props.IntProperty(get=_get_uid)

def unregister():
    del bpy.types.ID.indigo_export_uid
    del bpy.types.Node.indigo_export_uid