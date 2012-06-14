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
import os

from extensions_framework import declarative_property_group
from extensions_framework.validate import Logic_Operator as OP
from extensions_framework.util import path_relative_to_export, filesystem_path

from indigo import IndigoAddon
from indigo.export import xml_builder

@IndigoAddon.addon_register_class
class indigo_mesh(declarative_property_group, xml_builder):
	ef_attach_to = ['Mesh', 'SurfaceCurve', 'TextCurve', 'Curve']
	
	# declarative_property_group members
	
	controls = [
		'disable_smoothing',
		'exit_portal',
		'max_num_subdivisions',
		['subdivision_smoothing','merge_verts'],
		'view_dependent_subdivision',
		'subdivide_pixel_threshold',
		'subdivide_curvature_threshold',
		'displacement_error_threshold',
		
		'mesh_proxy',
		'mesh_path'
	]
	
	visibility = {
		'subdivision_smoothing':			{'max_num_subdivisions': OP({'not': 0}) },
		'merge_verts':						{'max_num_subdivisions': OP({'not': 0}) },
		'view_dependent_subdivision':		{'max_num_subdivisions': OP({'not': 0}) },
		'subdivide_pixel_threshold':		{'max_num_subdivisions': OP({'not': 0}) },
		'subdivide_curvature_threshold':	{'max_num_subdivisions': OP({'not': 0}) },
		'displacement_error_threshold':		{'max_num_subdivisions': OP({'not': 0}) },
		
		'mesh_path':						{ 'mesh_proxy': True }
	}
	
	properties = [
		{
			'type': 'bool',
			'attr': 'disable_smoothing',
			'name': 'Disable smoothing',
			'description': 'Treat all faces as flat shaded',
			'default': False
		},
		{
			'type': 'bool',
			'attr': 'exit_portal',
			'name': 'Exit Portal',
			'description': 'Use this mesh as an exit portal',
			'default': False
		},
		{
			'type': 'bool',
			'attr': 'subdivision_smoothing',
			'name': 'Subdivision Smoothing',
			'description': 'Smooth verts after subdivision',
			'default': False
		},
		{
			'type': 'bool',
			'attr': 'merge_verts',
			'name': 'Merge verts',
			'description': 'Merge vertices with same position and normal',
			'default': True
		},
		{
			'type': 'bool',
			'attr': 'view_dependent_subdivision',
			'name': 'View Dependent subdivision',
			'description': 'Use view-dependent (adaptive) subdivision',
			'default': False
		},
		{
			'type': 'int',
			'attr': 'max_num_subdivisions',
			'name': 'Number of subdivisions',
			'description': 'Level of mesh subdivision',
			'min': 0,
			'soft_min': 0,
			'max': 20,
			'soft_max': 20,
			'default': 0
		},
		{
			'type': 'float',
			'attr': 'subdivide_pixel_threshold',
			'name': 'Subdivision Pixel threshold',
			'description': 'Subdivision threshold in triangle screen-space pixels',
			'min': 0.0,
			'soft_min': 0.0,
			'max': 200.0,
			'soft_max': 200.0,
			'default': 4.0
		},
		{
			'type': 'float',
			'attr': 'subdivide_curvature_threshold',
			'name': 'Subdivision curvature threshold',
			'description': 'Subdivision curvature threshold',
			'min': 0.0,
			'soft_min': 0.0,
			'max': 2.0,
			'soft_max': 2.0,
			'default': 0.1
		},
		{
			'type': 'float',
			'attr': 'displacement_error_threshold',
			'name': 'Displacement_error_threshold',
			'description': 'Displacement error threshold',
			'min': 0.0,
			'soft_min': 0.0,
			'max': 2.0,
			'soft_max': 2.0,
			'default': 0.1
		},
		
		{
			'type': 'bool',
			'attr': 'mesh_proxy',
			'name': 'Proxy for external mesh',
			'description': 'Use an external igmesh or obj file in place of this object',
			'default': False
		},
		{
			'type': 'string',
			'subtype': 'FILE_PATH',
			'attr': 'mesh_path',
			'name': 'Mesh Path',
			'description': 'Path to external igmesh or obj file'
		},
	]
	
	def valid_proxy(self):
		proxy_path = filesystem_path(self.mesh_path)
		return self.mesh_proxy and os.path.exists(proxy_path)
	
	# xml_builder members
	def build_xml_element(self, obj, filename, exported_name=""):
		
		if exported_name == "":
			exported_name = obj.data.name
		
		xml = self.Element('mesh')
		
		xml_format = {
			'name': [exported_name],
			'normal_smoothing': [str(not self.disable_smoothing).lower()],
			'scale': [1.0],
			'external': {
				'path': [filename]
			}
		}
		
		if self.valid_proxy():
			xml_format['external']['path'] = [path_relative_to_export(self.mesh_path)]
		
		if self.max_num_subdivisions > 0:
			xml_format.update({
				'subdivision_smoothing':					[str(self.subdivision_smoothing).lower()],
				'max_num_subdivisions':						[self.max_num_subdivisions],
				'subdivide_pixel_threshold':				[self.subdivide_pixel_threshold],
				'subdivide_curvature_threshold':			[self.subdivide_curvature_threshold],
				'displacement_error_threshold':				[self.displacement_error_threshold],
				'view_dependent_subdivision':				[str(self.view_dependent_subdivision).lower()],
				'merge_vertices_with_same_pos_and_normal':	[str(self.merge_verts).lower()]
			})
		
		self.build_subelements(obj, xml_format, xml)
		
		return xml
