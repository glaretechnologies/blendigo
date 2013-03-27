# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 Indigo Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond, Nicholas Chapman
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

import bpy

import mathutils		#@UnresolvedImport

import time
import math
import hashlib

from extensions_framework import util as efutil

from indigo.core.util import get_worldscale
from indigo.export import ( indigo_log,
							ExportProgressThread,
							ExportCache,
							xml_builder,
							SceneIterator, OBJECT_ANALYSIS,
							indigo_visible
							)
from indigo.export.igmesh import igmesh_writer

class DupliExportProgressThread(ExportProgressThread):
	message = '...  %i%% ...'

class model_base(xml_builder):
	element_type = 'model'
	
	def __init__(self, scene):
		self.scene = scene
		super().__init__()
	
	def get_additional_elements(self, obj):
		return {}
	
	def get_transform(self, obj, matrix, xml_format='matrix'):
		#------------------------------------------------------------------------------
		# get appropriate loc, rot, scale data
		if matrix is not None:
			lv, rm, sv = matrix.decompose()
		else: 
			lv, rm, sv = obj.matrix_world.decompose()
		
		rm = rm.to_matrix()
		#------------------------------------------------------------------------------
		# Process loc, rot, scale data 
		# get a rotation matrix that doesn't include scale info ...
		# ... apply the world scale ...
		# ... and invert it ...
		ws = get_worldscale(self.scene)
		
		# ... then apply non-uniform scaling to rotation matrix
		sv_axes = mathutils.Matrix.Identity(3)
		for i in range(3):
			rm = rm * mathutils.Matrix.Scale(1/sv[i], 3, sv_axes.row[i])
		
		rm_inverted = rm.inverted() * ws
		
		xform = {
			'pos': [str(co*ws) for co in lv],
		}
		
		if xml_format=='quat':
			rmq = rm_inverted.to_quaternion()
			xform['rotation_quaternion'] = {
				'axis': list(rmq.axis),
				'angle': [-rmq.angle]
			}
		
		elif xml_format=='matrix':
			
			#if bpy.app.build_revision >= '42816':
			rm_inverted = rm_inverted.transposed()
			
			# convert the matrix to list of strings
			rmr = []
			for row in rm_inverted.transposed().col:
				rmr.extend(row)
			
			xform['rotation'] = { 'matrix': rmr }
		
		return xform
	
	def get_format(self, obj, mesh_name, matrix_list):
		if len(matrix_list) > 0:
			matrix = matrix_list[0]
		else:
			matrix = None
		
		xml_format = {
			'mesh_name': [mesh_name],
			# scale == 1.0 because scale data is included in rot matrix
			'scale': [1.0],
		}
		
		xml_format.update(self.get_transform(obj, matrix))
		xml_format.update(self.get_additional_elements(obj))
		return xml_format
	
	def build_xml_element(self, obj, mesh_name, matrix_list):
		xml = self.Element(self.element_type)
		
		xml_format = self.get_format(obj, mesh_name, matrix_list)
		
		self.build_subelements(obj, xml_format, xml)
		
		return xml
	
class model_object(model_base):
	
	# <model> supports IES illumination data and emission_scale
	def get_additional_elements(self, obj):
		d = {}
		
		for ms in obj.material_slots:
			mat = ms.material
			if mat == None: continue
			ie = mat.indigo_material.indigo_material_emission
			if ie.emission_enabled and ie.emit_ies:
				d['ies_profile'] = {
					'material_name': [mat.name],
					'path': [efutil.filesystem_path(ie.emit_ies_path)]
				}
		
		for ms in obj.material_slots:
			mat = ms.material
			if mat == None: continue
			ie = mat.indigo_material.indigo_material_emission
			if ie.emission_enabled and ie.emission_scale:
				d['emission_scale'] = {
					'material_name': [mat.name],
					'measure': [ie.emission_scale_measure],
					'value': [ie.emission_scale_value * 10**ie.emission_scale_exp]
				}
		
		return d
	
	def get_format(self, obj, mesh_name, matrix_list):
		xml_format = {
			'mesh_name': [mesh_name],
			# scale == 1.0 because scale data is included in rot matrix
			'scale': [1.0],
		}
		
		# Add a base static rotation
		xml_format.update(self.get_transform(obj, matrix_list[0], xml_format='matrix'))
		del(xml_format['pos'])
		
		if len(matrix_list) > 1:
			if matrix_list[0] == None:
				base_matrix = obj.matrix_world
			else:
				base_matrix = matrix_list[0]
			
			rm_0, sm_0 = base_matrix.decompose()[1:]
			
			# insert keyframes
			keyframes = []
			for i, matrix in enumerate(matrix_list):
				
				# Diff matrix is the transform from base_matrix to matrix.
				diff_matrix = matrix * base_matrix.inverted()
				
				if matrix==None or matrix_list[0]==None:
					matrix_kf = matrix
				else:
					# construct keyframes with rotation differences from base rotation
					# and absolute positions
					lm_k, rm_k, sm_k = matrix.decompose()
								
					# Get the rotation component of the difference matrix.
					r_diff = diff_matrix.decompose()[1]

					matrix_kf = mathutils.Matrix.Translation(lm_k) * \
								mathutils.Matrix.Rotation(r_diff.angle, 4, r_diff.axis)
				
				xform = self.get_transform(obj, matrix_kf, xml_format='quat')
				
				xform['time'] = [i/(len(matrix_list)-1)]
				
				keyframes.append(xform)
			
			xml_format['keyframe'] = tuple(keyframes)
		else:
			xml_format.update(self.get_transform(obj, matrix_list[0]))
		
		xml_format.update(self.get_additional_elements(obj))
		return xml_format
	
class exit_portal(model_base):
	element_type = 'exit_portal'
	
	
class SectionPlane(xml_builder):	
	def __init__(self, pos, normal, cull_geometry):
		self.pos = pos
		self.normal = normal
		self.cull_geometry = cull_geometry
		super().__init__()
		
	def build_xml_element(self):
		xml = self.Element('section_plane')
		self.build_subelements(
			self,
			{
				'point':  list(self.pos)[0:3],
				'normal':  list(self.normal)[0:3],
				'cull_geometry': [str(self.cull_geometry).lower()]
			},
			xml
		)
		return xml
		
class SpherePrimitive(xml_builder):	
	def __init__(self, matrix_world, obj):
		self.matrix_world = matrix_world
		self.obj = obj
		super().__init__()
		
	def build_xml_element(self):
	
		mat = ""
		for ms in self.obj.material_slots:
			mat = ms.material.name
			
			
		# Compute radius in object space from bounding box
		bb = self.obj.bound_box # Get object-space bounding box
		bb_min = bb[0]
		bb_max = bb[6]
		
		#print("min")
		#for i in range(0, 8):
		#	print("bb[" + str(i) + "]:")
		#	for c in range(0, 3):
		#		print(str(bb[i][c]))
				
		bb_radius = max(bb_max[0] - bb_min[0], bb_max[1] - bb_min[1], bb_max[2] - bb_min[2]) * 0.5
		
		pos = self.matrix_world.col[3]
		
		# Compute object->world space scale, use the max of the scalings to scale the sphere radius.
		scale_vec = self.matrix_world.to_scale()
		scale = max(math.fabs(scale_vec[0]), math.fabs(scale_vec[1]), math.fabs(scale_vec[2]))
		
		radius_ws = bb_radius * scale
		
		#print("pos: " + str(pos))
		#print("bb_radius: " + str(bb_radius))
		#print("scale: " + str(scale))
					
		xml = self.Element('sphere')
		self.build_subelements(
			self,
			{
				'center':  list(pos)[0:3],
				'radius':  [radius_ws],
				'material_name': [mat]
			},
			xml
		)
		return xml
		

class GeometryExporter(SceneIterator):
	scene = None
	background_set = None
	exporting_duplis = False
	
	ExportedMaterials = None
	ExportedMeshes = None
	ExportedObjects = None
	ExportedDuplis = None
	ExportedLamps = None
	
	mesh_uses_shading_normals = {} # Map from exported_mesh_name to boolean
	
	callbacks = {}
	valid_duplis_callbacks = []
	valid_particles_callbacks = []
	valid_objects_callbacks = []
	
	# serial counter for instances exported
	object_id = 0

	def __init__(self, scene, background_set=None):
		self.scene = scene
		self.background_set = background_set
		
		self.exporting_duplis = False
		
		self.callbacks = {
			'duplis': {
				'FACES': self.handler_Duplis_GENERIC,
				'GROUP': self.handler_Duplis_GENERIC,
				'VERTS': self.handler_Duplis_GENERIC,
			},
			'particles': {
				'OBJECT': self.handler_Duplis_GENERIC,
				'GROUP': self.handler_Duplis_GENERIC,
				#'PATH': handler_Duplis_PATH,
			},
			'objects': {
				'MESH': self.handler_MESH,
				'CURVE': self.handler_MESH,
				'SURFACE': self.handler_MESH,
				'FONT': self.handler_MESH,
				'LAMP': self.handler_LAMP
			}
		}
		
		self.valid_duplis_callbacks = self.callbacks['duplis'].keys()
		self.valid_particles_callbacks = self.callbacks['particles'].keys()
		self.valid_objects_callbacks = self.callbacks['objects'].keys()
		
		self.ExportedMaterials = ExportCache('ExportedMaterials')
		self.ExportedMeshes = ExportCache('ExportedMeshes')
		self.ExportedObjects = ExportCache('ExportedObjects')
		self.ExportedDuplis = ExportCache('ExportedObjectDuplis')
		self.ExportedLamps = ExportCache('ExportedObjectLamps')
	
	def handler_Duplis_GENERIC(self, obj, *args, **kwargs):
		try:
			if self.ExportedDuplis.have(obj):
				indigo_log('Duplis for object %s already exported'%obj)
				return
			
			self.ExportedDuplis.add(obj, True)
			
			try:
				obj.dupli_list_create(self.scene)
				if not obj.dupli_list:
					raise Exception('cannot create dupli list for object %s' % obj.name)
			except Exception as err:
				indigo_log('%s'%err)
				return
			
			# Create our own DupliOb list to work around incorrect layers
			# attribute when inside create_dupli_list()..free_dupli_list()
			duplis = []
			for dupli_ob in obj.dupli_list:
				if dupli_ob.object.type not in self.valid_objects_callbacks:
					continue
				if not indigo_visible(self.scene, dupli_ob.object, is_dupli=True):
					continue
				
				duplis.append(
					(
						dupli_ob.object,
						dupli_ob.matrix.copy()
					)
				)
			
			obj.dupli_list_clear()
			
			det = DupliExportProgressThread()
			if self.scene.indigo_engine.console_output:
				det.start(len(duplis))
			
			self.exporting_duplis = True
			
			# dupli object, dupli matrix
			for do, dm in duplis:
				
				# Check for group layer visibility, if the object is in a group
				gviz = len(do.users_group) == 0
				for grp in do.users_group:
					gviz |= True in [a&b for a,b in zip(do.layers, grp.layers)]
				if not gviz:
					continue
				
				det.exported_objects += 1
				
				self.exportModelElements(
					obj,
					self.buildMesh(do),
					matrix=dm
				)
			
			del duplis
			
			self.exporting_duplis = False
			
			if self.scene.indigo_engine.console_output:
				det.stop()
				det.join()
			
			indigo_log('... done, exported %s duplis' % det.exported_objects)
			
		except SystemError as err:
			indigo_log('Error with handler_Duplis_GENERIC and object %s: %s' % (obj, err))
	
	def handler_LAMP(self, obj, *args, **kwargs):
		if OBJECT_ANALYSIS: indigo_log(' -> handler_LAMP: %s' % obj)
		
		if obj.data.type == 'AREA':
			pass
		if obj.data.type == 'HEMI':
			self.ExportedLamps.add(obj.name, [obj.data.indigo_lamp_hemi.build_xml_element(obj, self.scene)])
		if obj.data.type == 'SUN':
			self.ExportedLamps.add(obj.name, [obj.data.indigo_lamp_sun.build_xml_element(obj, self.scene)])
	
	def handler_MESH(self, obj, *args, **kwargs):
		if OBJECT_ANALYSIS: indigo_log(' -> handler_MESH: %s' % obj)
		
		if 'matrix' in kwargs.keys():
			self.exportModelElements(
				obj,
				self.buildMesh(obj),
				matrix=kwargs['matrix']
			)
		else:
			self.exportModelElements(
				obj,
				self.buildMesh(obj)
			)
	
	def buildMesh(self, obj):
		"""
		Process the mesh into required format.
		"""
		
		return self.exportMeshElement(obj)
	
	def exportMeshElement(self, obj):
		if OBJECT_ANALYSIS: indigo_log('exportMeshElement: %s' % obj)
		
		if obj.type in self.valid_objects_callbacks:
			
			# Compute a hash of the material names.  We will only use an existing mesh if it has the same materials assigned.
			hash_m = hashlib.sha224()
			for ms in obj.material_slots:
				if ms.material != None:
					hash_m.update(ms.material.name.encode(encoding='UTF-8'))
	
			exported_mesh_name = obj.data.name + '_' + hash_m.hexdigest()
			
			exported_mesh_name = bpy.path.clean_name(exported_mesh_name)
			
			if self.ExportedMeshes.have(exported_mesh_name): return self.ExportedMeshes.get(exported_mesh_name)
			
			rel_mesh_path = '%s/%s/%05i' % (efutil.scene_filename(), bpy.path.clean_name(self.scene.name), self.scene.frame_current)
			
			mesh_path = '/'.join([efutil.export_path, rel_mesh_path])
			
			#print('MESH PATH %s' % mesh_path)
			
			if not os.path.exists(mesh_path):
				os.makedirs(mesh_path)
			
			#print('REL MESH PATH %s' % rel_mesh_path)
			
			mesh_filename = exported_mesh_name + '.igmesh'
			full_mesh_path = efutil.filesystem_path( '/'.join([mesh_path, mesh_filename]) )
			
			#print('FULL MESH PATH %s' % full_mesh_path)
			
			# Use binary igmesh format instead of <embedded>
			indigo_log('Mesh Export: %s' % exported_mesh_name )
			indigo_log(' -> %s' % full_mesh_path)
			start_time = time.time()
			
			# pass the full mesh path to write to filesystem if the object is not a proxy
			if hasattr(obj.data, 'indigo_mesh') and not obj.data.indigo_mesh.valid_proxy():
				if os.path.exists(full_mesh_path) and self.scene.indigo_engine.skip_existing_meshes:
					# if skipping mesh write, parse faces to gather used mats
					
					# Create mesh with applied modifiers
					create_mesh = len(obj.modifiers) > 0 or obj.type in ['SURFACE', 'FONT', 'CURVE']
					if create_mesh:
						mesh = obj.to_mesh(self.scene, True, 'RENDER')
					else:
						mesh = obj.data
					
					used_mat_indices = set()
					for face in mesh.faces:
						used_mat_indices.add(face.material_index)
					
					if create_mesh:
						# Remove mesh with applied modifiers
						bpy.data.meshes.remove(mesh)
				else:
					# else let the igmesh_writer do it's thing
					(used_mat_indices, use_shading_normals) = igmesh_writer.factory(self.scene, obj, full_mesh_path, debug=OBJECT_ANALYSIS)
					self.mesh_uses_shading_normals[full_mesh_path] = use_shading_normals
			else:
				# Assume igmesh has same number of mats as the proxy object
				used_mat_indices = range(len(obj.material_slots))
			
			# Export materials used by this mesh
			if len(obj.material_slots) > 0:
				for mi in used_mat_indices:
					mat = obj.material_slots[mi].material
					if mat == None or self.ExportedMaterials.have(mat.name): continue
					mat_xmls = mat.indigo_material.factory(obj, mat, self.scene)
					self.ExportedMaterials.add(mat.name, mat_xmls)
			
			# .. put the relative path in the mesh element
			filename = '/'.join([rel_mesh_path, mesh_filename])
			
			#print('MESH FILENAME %s' % filename)
			
			shading_normals = True
			if full_mesh_path in self.mesh_uses_shading_normals:
				shading_normals = self.mesh_uses_shading_normals[full_mesh_path]
			
			xml = obj.data.indigo_mesh.build_xml_element(obj, filename, shading_normals, exported_name=exported_mesh_name)
			
			mesh_definition = (exported_mesh_name, xml)
			
			self.ExportedMeshes.add(exported_mesh_name, mesh_definition)
			
			return mesh_definition
	
	def exportModelElements(self, obj, mesh_definition, matrix=None):
		if OBJECT_ANALYSIS: indigo_log('exportModelElements: %s, %s, %s' % (obj, mesh_definition, matrix==None))
		
		# Special handling for section planes:  If object has the section_plane attribute set, then export it as a section plane.
		if(obj.data != None and obj.data.indigo_mesh.section_plane):
			xml = SectionPlane(obj.matrix_world.col[3], obj.matrix_world.col[2], obj.data.indigo_mesh.cull_geometry).build_xml_element()
			
			model_definition = (xml,)
			
			self.ExportedObjects.add(self.object_id, model_definition)
			self.object_id += 1
			return
			
		# Special handling for sphere primitives
		if(obj.data != None and obj.data.indigo_mesh.sphere_primitive):
			xml = SpherePrimitive(obj.matrix_world, obj).build_xml_element()
			
			model_definition = (xml,)
			
			self.ExportedObjects.add(self.object_id, model_definition)
			self.object_id += 1
			return
			
		
		mesh_name = mesh_definition[0]
		
		if obj.type == 'MESH' and obj.data.indigo_mesh.exit_portal:
			xml = exit_portal(self.scene).build_xml_element(obj, mesh_name, [matrix])
		else:
			if self.scene.indigo_engine.motionblur and not self.exporting_duplis:
				blur_amount = (self.scene.render.fps/self.scene.render.fps_base)/self.scene.camera.data.indigo_camera.exposure
				obj_matrices = self.get_motion_matrices(obj, matrix, frame_offset=blur_amount)
			else:
				obj_matrices = [matrix]
			
			xml = model_object(self.scene).build_xml_element(obj, mesh_name, obj_matrices)
		
		model_definition = (xml,)
		
		self.ExportedObjects.add(self.object_id, model_definition)
		self.object_id += 1
		
		
	# frame_offset seems to be something like the shutter open period measured in fractions of a frame.
	def get_motion_matrices(self, obj, base_matrix, frame_offset=1, ignore_scale=False):
		if obj.animation_data != None and obj.animation_data.action != None and len(obj.animation_data.action.fcurves)>0:
		
			motion_matrices = []
			
			offsets = [0] + [i+1 for i in range(int(frame_offset))] + [frame_offset]
						
			for offset in offsets:
			
				next_frame = self.scene.frame_current + offset
				
				anim_location = obj.location.copy()
				anim_rotation = obj.rotation_euler.copy()
				anim_scale    = obj.scale.copy()
				
				for fc in obj.animation_data.action.fcurves:
					if fc.data_path == 'location':
						anim_location[fc.array_index] = fc.evaluate(next_frame)
					if fc.data_path == 'rotation_euler':
						anim_rotation[fc.array_index] = fc.evaluate(next_frame)
					if fc.data_path == 'scale':
						anim_scale[fc.array_index] = fc.evaluate(next_frame)
				
				next_matrix  = mathutils.Matrix.Translation( mathutils.Vector(anim_location) )
				anim_rotn_e = mathutils.Euler(anim_rotation)
				anim_rotn_e.make_compatible(obj.rotation_euler)
				anim_rotn_e = anim_rotn_e.to_matrix().to_4x4()
				next_matrix *= anim_rotn_e
				
				if not ignore_scale:
					next_matrix *= mathutils.Matrix.Scale(anim_scale[0], 4, mathutils.Vector([1,0,0]))
					next_matrix *= mathutils.Matrix.Scale(anim_scale[1], 4, mathutils.Vector([0,1,0]))
					next_matrix *= mathutils.Matrix.Scale(anim_scale[2], 4, mathutils.Vector([0,0,1]))
				
				motion_matrices.append(next_matrix)
			
			return motion_matrices
		else:
			return [obj.matrix_world]
