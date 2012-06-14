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
from extensions_framework import util as efutil

from indigo.export.materials.Base import AlbedoChannelMaterial, EmissionChannelMaterial, BumpChannelMaterial, DisplacementChannelMaterial, ExponentChannelMaterial, MaterialBase

class PhongMaterial(
	AlbedoChannelMaterial,
	EmissionChannelMaterial,
	BumpChannelMaterial,
	DisplacementChannelMaterial,
	ExponentChannelMaterial,
	
	# MaterialBase needs to be last in this list
	MaterialBase
	):
	def get_format(self):
		element_name = 'phong'
		
		fmt = {
			'name': [self.material_name],
			element_name: {
				'ior': [self.property_group.ior],
				'exponent': {
					'constant': [self.property_group.exponent]
				},
			}
		}
		
		fmt[element_name].update(self.get_channels())
		
		if self.property_group.specular_reflectivity:
			fmt[element_name]['specular_reflectivity'] = fmt[element_name]['diffuse_albedo']
			del fmt[element_name]['diffuse_albedo']
			del fmt[element_name]['ior']
		
		if self.property_group.nk_data_type == 'file' and self.property_group.nk_data_file != '':
			fmt[element_name]['nk_data'] = [efutil.path_relative_to_export(self.property_group.nk_data_file)]
			try:
				# doesn't matter if these keys don't exist, but remove them if they do
				del fmt[element_name]['ior']
				del fmt[element_name]['diffuse_albedo']
				del fmt[element_name]['specular_reflectivity']
			except: pass
			
		if self.property_group.nk_data_type == 'preset':
			fmt[element_name]['nk_data'] = [self.property_group.nk_data_preset]
			try:
				# doesn't matter if these keys don't exist, but remove them if they do
				del fmt[element_name]['ior']
				del fmt[element_name]['diffuse_albedo']
				del fmt[element_name]['specular_reflectivity']
			except: pass
		
		return fmt
