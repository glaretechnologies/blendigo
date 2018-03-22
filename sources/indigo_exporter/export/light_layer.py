from . import xml_builder

class light_layer_xml(xml_builder):
    
    def build_xml_element(self, scene, idx, layer_name):
        xml = self.Element('layer_setting')
        if idx == 0: #default layer
            self.build_subelements(
                scene,
                {
                    'name':  ['default'],
                    'enabled': ['true'],
                    'layer_scale': {
                        'xyz': {
                            'xyz': ['1 1 1'],
                            'gain': [scene.indigo_lightlayers.default_gain],
                        }
                    },
                },
                xml
            )
        else:
            layer = scene.indigo_lightlayers.lightlayers.get(layer_name)
            self.build_subelements(
                scene,
                {
                    'name':  [layer_name],
                    'enabled': [str(layer.lg_enabled).lower()],
                    'layer_scale': {
                        'xyz': {
                            'xyz': ['1 1 1'],
                            'gain': [layer.gain],
                        }
                    },
                },
                xml
            )
        return xml