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
'''
These are xml_builder.format generators.

The values passed to the function should be either:
- string for a defined property name
- list for direct value insertion
'''

def peak(minimum, width, base, peak):
	return {
		'peak': {
			'peak_min': minimum,
			'peak_width': width,
			'base_value': base,
			'peak_value': peak
		}
	}
	
def blackbody(temp, gain):
	return {
		'blackbody': {
			'temperature': temp,
			'gain': gain,
		}
	}

def rgb(rgb, gamma=[1.0]):		# TODO: verify correct gamma value
	return {
		'rgb': {
			'rgb': rgb,
			'gamma': gamma
		}
	}
	
def uniform(value):
	return {
		'uniform': {
			'value': value
		}
	}

def regular_tabulated(start, end, values=[]):
	num_values = len(values)
	
	return {
		'regular_tabulated': {
			'start_wavelength': start,
			'end_wavelength': end,
			'num_values': [num_values],
			'values': values
		}
	}
