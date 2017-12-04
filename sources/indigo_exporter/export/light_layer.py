from . import xml_builder

class light_layer_xml(xml_builder):
    
    def build_xml_element(self, scene, index, name):
        xml = self.Element('layer_name')
        self.build_subelements(
            scene,
            {
                'layer_index': [index],
                'layer_name':  [name]
            },
            xml
        )
        return xml