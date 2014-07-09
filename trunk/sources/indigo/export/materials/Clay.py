# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 Indigo Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# ***** END GPL LICENCE BLOCK *****
#
from indigo.export import xml_builder
from indigo.export.materials.spectra import rgb

class ClayMaterial(xml_builder):
    '''
    A dummy/placeholder 'clay' material
    '''
    
    def build_xml_element(self, context):
        xml = self.Element('material')
        self.build_subelements(
            context,
            {
                'name': ['blendigo_clay'],
                'diffuse': {
                    'albedo': {
                        'constant':  rgb([0.8, 0.8, 0.8])
                    }
                }
            },
            xml
        )
        return xml

class NullMaterial(xml_builder):
    '''
    The Null material
    '''
    
    def build_xml_element(self, context):
        xml = self.Element('material')
        self.build_subelements(
            context,
            {
                'name': ['blendigo_null'],
                'null_material': {}
            },
            xml
        )
        return xml
