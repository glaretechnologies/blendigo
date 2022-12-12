attrs = [
        {
            'attr': 'emit_layer',
            'type': 'string',
            'name': 'Light Layer',
            'description': 'lightlayer; leave blank to use default'
        },
        {
            'type': 'prop_search',
            'attr': 'lightlayer_chooser',
            'src': lambda s,c: s.scene.indigo_lightlayers,
            'src_attr': 'lightlayers',
            'trg': lambda s,c: c.indigo_material_emission,
            'trg_attr': 'emit_layer',
            'name': 'Light Layer'
        },
]

#######################################################################################
# convert properties dicts to ordinary declarations
#######################################################################################
if __name__ == "__main__":
    import inspect
    out = ''
    for property in attrs:
        prop = property.copy()
        
        ptype = prop['type']
        # del prop['type']
        
        if ptype == 'bool':
            t = 'bpy.props.BoolProperty'
            a = {k: v for k,v in prop.items() if k in ["name",
                    "description","default","options","subtype","update"]}
        elif ptype == 'bool_vector':
            t = 'bpy.props.BoolVectorProperty'
            a = {k: v for k,v in prop.items() if k in ["name",
                    "description","default","options","subtype","size",
                    "update"]}
        elif ptype == 'collection':
            t = 'bpy.props.CollectionProperty'
            prop['type'] = prop['ptype']
            del prop['ptype']
            
            a = {k: v for k,v in prop.items() if k in ["type","name",
                    "description","default","options"]}
        elif ptype == 'enum':
            t = 'bpy.props.EnumProperty'
            a = {k: v for k,v in prop.items() if k in ["items","name",
                    "description","default","options","update"]}
        elif ptype == 'float':
            t = 'bpy.props.FloatProperty'
            a = {k: v for k,v in prop.items() if k in ["name",
                    "description","default","min","max","soft_min","soft_max",
                    "step","precision","options","subtype","unit","update", "get", "set"]}
        elif ptype == 'float_vector':
            t = 'bpy.props.FloatVectorProperty'
            a = {k: v for k,v in prop.items() if k in ["name",
                    "description","default","min","max","soft_min","soft_max",
                    "step","precision","options","subtype","size","update"]}
        elif ptype == 'int':
            t = 'bpy.props.IntProperty'
            a = {k: v for k,v in prop.items() if k in ["name",
                    "description","default","min","max","soft_min","soft_max",
                    "step","options","subtype","update"]}
        elif ptype == 'int_vector':
            t = 'bpy.props.IntVectorProperty'
            a = {k: v for k,v in prop.items() if k in ["name",
                    "description","default","min","max","soft_min","soft_max",
                    "options","subtype","size","update"]}
        elif ptype == 'pointer':
            t = 'bpy.props.PointerProperty'
            prop['type'] = prop['ptype']
            del prop['ptype']
            
            a = {k: v for k,v in prop.items() if k in ["type", "name",
                    "description","options","update"]}
        elif ptype == 'string':
            t = 'bpy.props.StringProperty'
            a = {k: v for k,v in prop.items() if k in ["name",
                    "description","default","maxlen","options","subtype",
                    "update"]}
        else:
            continue
        
        def unpack(d):
            s = ''
            for k, v in d.items():
                def strgfy(e):
                    if type(v) is str:
                        return '"'+v+'"'
                    elif callable(v):
                        return inspect.getsource(v).strip()[len("'update': "):]
                    else:
                        return v
                s += f"{k}={strgfy(v)}, "
            return s[:-2]

        out += f'{prop["attr"]}: {t}({unpack(a)})\n'
    print(out)

    import subprocess 
    subprocess.run("clip", text=True, input=out)
