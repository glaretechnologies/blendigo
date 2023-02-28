def updated_event(self, context):
    try:
        self.material_name, self.emission_enabled = get_material_filename_and_emission_from_external_mat(self, context)
    except:
        pass
attrs = [
        {
            'type': 'string',
            'subtype': 'FILE_PATH',
            'attr': 'filename',
            'name': 'IGM or PIGM file',
            'description': 'IGM or PIGM file',
            'default': '',
            'update': updated_event
        },
        {
            'type': 'string',
            'attr': 'material_name',
            'name': 'Name'
        },
        # NOTE: is_valid is not used any more.
        {
            'type': 'bool',
            'attr': 'is_valid',
            'default': False
        },
        # ies profile (exports with geometry)
        {
            'type': 'bool',
            'attr': 'emit_ies',
            'name': 'IES Profile',
            'description': 'IES Profile',
            'default': False,
        },
        {
            'type': 'string',
            'subtype': 'FILE_PATH',
            'attr': 'emit_ies_path',
            'name': ' IES Path',
            'description': ' IES Path',
            'default': '',
        },
        {
            'type': 'bool',
            'attr': 'emission_enabled',
            'default': False
        },
        # emission scale (exports with geometry)
        {
            'type': 'bool',
            'attr': 'emission_scale',
            'name': 'Emission scale',
            'description': 'Emission scale',
            'default': False,
        },
        {
            'type': 'enum',
            'attr': 'emission_scale_measure',
            'name': 'Unit',
            'description': 'Units for emission scale',
            'default': 'luminous_flux',
            'items': [
                ('luminous_flux', 'lm', 'Luminous flux'),
                ('luminous_intensity', 'cd', 'Luminous intensity (lm/sr)'),
                ('luminance', 'nits', 'Luminance (lm/sr/m/m)'),
                ('luminous_emittance', 'lux', 'Luminous emittance (lm/m/m)')
            ],
        },
        {
            'type': 'float',
            'attr': 'emission_scale_value',
            'name': 'Value',
            'description': 'Emission scale value',
            'default': 1.0,
            'min': 0.0,
            'soft_min': 0.0,
            'max': 10.0,
            'soft_max': 10.0,
        },
        {
            'type': 'int',
            'attr': 'emission_scale_exp',
            'name': '*10^',
            'description': 'Emission scale exponent',
            'default': 0,
            'min': -30,
            'max': 30
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
