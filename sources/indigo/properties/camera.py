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
import os.path

import bpy

from extensions_framework import declarative_property_group
from extensions_framework import util as efutil

from indigo import IndigoAddon
from indigo.core.util import get_worldscale
from indigo.export import indigo_log
from indigo.export import xml_builder

def aspect_ratio(context,p):
	return context.render.resolution_x / context.render.resolution_y

def f_stop(context, p):
	return p.fstop

def lens_sensor_dist(context,p):
	import math
	
	aspect = aspect_ratio(context,p)
	
	film = 0.001 * context.camera.data.sensor_width
	
	FOV = context.camera.data.angle
	if aspect < 1.0:
		FOV = FOV*aspect
	
	lsd = film/( 2.0*math.tan( FOV/2.0 ))
	#print('Lens Sensor Distance: %f'%lsd)
	return lsd

def aperture_radius(context,p):
	ar = lens_sensor_dist(context,p) / (2.0*f_stop(context,p))
	#print('Aperture Radius: %f' % ar)
	return ar

@IndigoAddon.addon_register_class
class indigo_camera(declarative_property_group, xml_builder):
	ef_attach_to = ['Camera']
	
	# declarative_property_group members
	
	controls = [
		['autofocus', 'vignetting'],
		['autoexposure', 'exposure'],
		['iso', 'fstop'],
		['whitebalance',
		#'motionblur'
		],
		['ad', 'ad_post'],
		'ad_obstacle',
		'ad_type',
		'ad_image',
		['ad_blades', 'ad_offset'],
		['ad_curvature', 'ad_angle'],
	]
	
	visibility = {
		'exposure':		{ 'autoexposure': False },
		
		'ad_post':		{ 'ad': True },
		'ad_type':		{ 'ad': True },
		'ad_obstacle':	{ 'ad': True },
		'ad_image':		{ 'ad': True, 'ad_type': 'image' },
		'ad_blades':	{ 'ad': True, 'ad_type': 'generated' },
		'ad_offset':	{ 'ad': True, 'ad_type': 'generated' },
		'ad_curvature':	{ 'ad': True, 'ad_type': 'generated' },
		'ad_angle':		{ 'ad': True, 'ad_type': 'generated' },
	}
	
	properties = [
		{
			'type': 'bool',
			'attr': 'autofocus',
			'name': 'Auto Focus',
			'description': 'Auto Focus',
			'default': True,
		},
		{
			'type': 'bool',
			'attr': 'vignetting',
			'name': 'Vignetting',
			'description': '',
			'default': True,
		},
		{
			'type': 'bool',
			'attr': 'autoexposure',
			'name': 'Auto Exposure',
			'description': 'Auto Exposure',
			'default': False,
		},
		{
			'type': 'bool',
			'attr': 'ad',
			'name': 'Aperture Diffraction',
			'description': 'Aperture Diffraction',
			'default': False,
		},
		{
			'type': 'bool',
			'attr': 'ad_post',
			'name': 'AD Post-Process',
			'description': 'AD Post-Process',
			'default': False,
		},
		{
			'type': 'int',
			'attr': 'iso',
			'name': 'Film ISO',
			'description': 'Film ISO',
			'default': 100,
			'min': 25,
			'soft_min': 25,
			'max': 10000,
			'soft_max': 10000,
		},
		{
			'type': 'int',
			'attr': 'exposure',
			'name': 'Exposure 1/',
			'description': 'Exposure 1/',
			'default': 125,
			'min': 1,
			'soft_min': 1,
			'max': 2000,
			'soft_max': 2000,
			'compute': lambda c, self: 1 / self.exposure
		},
		{
			'type': 'float',
			'attr': 'fstop',
			'name': 'f/Stop',
			'description': 'f/Stop',
			'default': 8,
			'min': 1,
			'soft_min': 1,
			'max': 128,
			'soft_max': 128,
		},
		{
			'type': 'enum',
			'attr': 'whitebalance',
			'name': 'White Balance',
			'description': 'White Balance Standard',
			'items': [
				('E','E','E'),
				('D50','D50','D50'),
				('D55','D55','D55'),
				('D65','D65','D65'),
				('D75','D75','D75'),
				('A','A','A'),
				('B','B','B'),
				('C','C','C'),
				('9300','9300','9300'),
				('F2','F2','F2'),
				('F7','F7','F7'),
				('F11','F11','F11'),
			],
		},
		{
			'type': 'bool',
			'attr': 'motionblur',
			'name': 'Camera MB',
			'description': 'Enable Camera Motion Blur',
			'default': False
		},
		{
			'type': 'enum',
			'attr': 'ad_type',
			'name': 'AD Type',
			'description': 'Aperture Diffraction Type',
			'items': [
				('image', 'Image', 'image'),
				('generated', 'Generated', 'generated'),
				('circular', 'Circular', 'circular'),
			],
		},
		{
			'type': 'int',
			'attr': 'ad_blades',
			'name': 'Blades',
			'description': 'Number of blades in the aperture',
			'default': 5,
			'min': 3,
			'soft_min': 3,
			'max': 20,
			'soft_max': 20,
		},
		{
			'type': 'float',
			'attr': 'ad_offset',
			'name': 'Offset',
			'description': 'Aperture blade offset',
			'default': 0.4,
			'min': 0,
			'soft_min': 0,
			'max': 0.5,
			'soft_max': 0.5,
		},
		{
			'type': 'int',
			'attr': 'ad_curvature',
			'name': 'Curvature',
			'description': 'Aperture blade curvature',
			'default': 3,
			'min': 0,
			'soft_min': 0,
			'max': 10,
			'soft_max': 10,
		},
		{
			'type': 'float',
			'attr': 'ad_angle',
			'name': 'Angle',
			'description': 'Aperture blade angle',
			'default': 0.2,
			'min': 0,
			'soft_min': 0,
			'max': 2,
			'soft_max': 2,
		},
		{
			'type': 'string',
			'attr': 'ad_image',
			'name': 'Image',
			'description': 'Image to use as the aperture opening. Must be power of two square, >= 512',
			'subtype': 'FILE_PATH',
		},
		{
			'type': 'string',
			'attr': 'ad_obstacle',
			'name': 'Obstacle Map',
			'description': 'Image to use as the aperture obstacle map. Must be power of two square, >= 512',
			'subtype': 'FILE_PATH',
		},
	]
	
	# xml_builder members
	
	def build_xml_element(self, scene):
		xml = self.Element('camera')
		
		xml_format = {
			'aperture_radius': [aperture_radius(scene, self)],
			'sensor_width': [scene.camera.data.sensor_width / 1000.0],
			'lens_sensor_dist': [lens_sensor_dist(scene, self)],
			'aspect_ratio': [aspect_ratio(scene, self)],
			'white_balance': 'whitebalance',
			'exposure_duration': 'exposure',
		}
		
		ws = get_worldscale(scene)
		
		cam_mat = scene.camera.matrix_world
		#if bpy.app.build_revision >= '42816':
		cam_mat = cam_mat.transposed()
		
		xml_format['pos']		= [ i*ws for i in cam_mat[3][0:3]]
		xml_format['forwards']	= [-i*ws for i in cam_mat[2][0:3]]
		xml_format['up']		= [ i*ws for i in cam_mat[1][0:3]]
		
		if self.autofocus:
			xml_format['autofocus'] = '' # is empty element
			xml_format['focus_distance'] = [10.0]  # any non-zero value will do
		else:
			if scene.camera.data.dof_object is not None:
				xml_format['focus_distance'] = [((scene.camera.location - scene.camera.data.dof_object.location).length*ws)]
			elif scene.camera.data.dof_distance > 0:
				xml_format['focus_distance'] = [scene.camera.data.dof_distance*ws]
			else: #autofocus
				xml_format['autofocus'] = '' # is empty element
				xml_format['focus_distance'] = [10.0]  # any non-zero value will do
		
		if self.ad:
			xml_format.update({
				'aperture_shape': {}
			})
			if self.ad_obstacle != '':
				ad_obstacle = efutil.filesystem_path(self.ad_obstacle)
				if os.path.exists(ad_obstacle):
					xml_format.update({
						'obstacle_map': {
							'path': [efutil.path_relative_to_export(ad_obstacle)]
						}
					})
				else:
					indigo_log('WARNING: Camera Obstacle Map specified, but image path is not valid')
			
			if self.ad_type == 'image':
				ad_image = efutil.filesystem_path(self.ad_image)
				if os.path.exists(ad_image):
					xml_format['aperture_shape'].update({
						'image': {
							'path': [efutil.path_relative_to_export(ad_image)]
						}
					})
				else:
					indigo_log('WARNING: Camera Aperture Diffraction type "Image" selected, but image path is not valid')
			
			elif self.ad_type == 'generated':
				xml_format['aperture_shape'].update({
					'generated': {
						'num_blades': [self.ad_blades],
						'start_angle': [self.ad_angle],
						'blade_offset': [self.ad_offset],
						'blade_curvature_radius': [self.ad_curvature]
					}
				})
			elif self.ad_type == 'circular':
				xml_format['aperture_shape'][self.ad_type] = {}
		
		aspect = aspect_ratio(scene, self)
		if scene.camera.data.shift_x != 0:
			sx = scene.camera.data.shift_x * 0.001*scene.camera.data.sensor_width
			if aspect < 1.0:
				sx /= aspect
			xml_format['lens_shift_right_distance'] = [sx]
			
		if scene.camera.data.shift_y != 0:
			sy = scene.camera.data.shift_y * 0.001*scene.camera.data.sensor_width
			if aspect < 1.0:
				sy /= aspect
			xml_format['lens_shift_up_distance'] = [sy]
		
		self.build_subelements(scene, xml_format, xml)
		
		return xml
