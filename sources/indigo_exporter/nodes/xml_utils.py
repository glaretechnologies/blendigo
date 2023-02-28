from xml.etree import ElementTree as ET

def append(element, tags:str | list[str], value=None):
    if isinstance(tags, str):
        tags = (tags,)
    
    if isinstance(element, XMLElement):
        element = element.etree_element
    
    last_el = element
    for tag in tags:
        el = ET.SubElement(last_el, tag)
        last_el = el
    
    if value is not None:
        if isinstance(value, bool):
            value = str(value).lower()
        
        last_el.text = str(value)
    
    return XMLElement(last_el)

class XMLElement:
    def __init__(self, tag, value=None):
        if isinstance(tag, ET.Element):
            self.etree_element = tag
            return
        
        self.etree_element = ET.Element(tag)
        if value:
            self.etree_element.text = value
    
    def append_tag(self, tags:str | list[str], value=None):
        return append(self, tags, value)
    
    def find(self, match, namespaces=None):
        return XMLElement(self.etree_element.find(match, namespaces))
    
    def __getattr__(self, __name: str):
        return getattr(self.etree_element, __name)

    @property
    def text(self):
        return self.etree_element.text
    
    @text.setter
    def text(self, value):
        self.etree_element.text = value

class wrap:
    @staticmethod
    def RGB(rgb: tuple[float]):
        return ' '.join(str(i) for i in rgb)

if __name__ == '__main__':
    main = XMLElement('main', 'test')
    sub = main.append_tag('sub', 'foo')
    
    assert sub.text == 'foo'
    found = main.find('.//sub')
    found.text = 'bar'
    assert sub.text == 'bar'