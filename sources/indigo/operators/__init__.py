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
import os, time
import xml.etree.cElementTree as ET
import xml.dom.minidom as MD

import bpy			#@UnresolvedImport

from extensions_framework import util as efutil

from indigo import IndigoAddon
import indigo.export
from indigo.export import (
	indigo_log, geometry, include, xml_multichild, xml_builder, indigo_visible,
	SceneIterator, ExportCache
)
from indigo.export.igmesh import igmesh_writer

class _Impl_operator(object):
	
	def __init__(self, **kwargs):
		"""
		Set member vars via keyword arguments
		"""
		for k,v in kwargs.items():
			setattr(self,k,v)
	
	def __getattr__(self, a):
		"""
		If using the _Impl* object directly and not as operator,
		allow access to member vars via self.properties the same
		as Operator does.
		"""
		if a == 'properties' and a not in self.__dict__.keys():
			return self
		return self.__dict__[a]
	
	def set_report(self, report_func):
		indigo.export.REPORTER = report_func
		return self

class _Impl_OT_igmesh(_Impl_operator):
	'''Export an Indigo format binary mesh file (.igmesh)'''
	
	bl_idname = "export.igmesh"
	bl_label = "Export IGMESH"
	
	objectname = bpy.props.StringProperty(options={'HIDDEN'}, name="Object Name", default='')
	
	filename = bpy.props.StringProperty(name="File Name", description="File name used for exporting the IGMESH file", maxlen= 1024, default= "")
	directory = bpy.props.StringProperty(name="Directory", description="", maxlen= 1024, default= "")
	filepath = bpy.props.StringProperty(name="File Path", description="File path used for exporting the IGMESH file", maxlen= 1024, default= "")
	
	def execute(self, context):
		#print("Selected: " + context.active_object.name)
		#print("Filename: %s"%self.properties.filepath)
		
		if not self.properties.filepath:
			indigo_log('Filename not set', message_type='ERROR')
			return {'CANCELLED'}
		
		if self.properties.objectname == '':
			self.properties.objectname = context.active_object.name
		
		try:
			obj = bpy.data.objects[self.properties.objectname]
		except:
			indigo_log('Cannot find mesh data in context', message_type='ERROR')
			return {'CANCELLED'}
		
		igmesh_writer.factory(context.scene, obj, self.properties.filepath, debug=False, stream=True)
		
		return {'FINISHED'}
	
	def invoke(self, context, event):
		if self.properties.objectname == '':
			self.properties.objectname = context.active_object.name
		wm = context.window_manager
		wm.fileselect_add(self)
		return {'RUNNING_MODAL'}

@IndigoAddon.addon_register_class
class EXPORT_OT_igmesh(_Impl_OT_igmesh, bpy.types.Operator):
	def execute(self, context):
		self.set_report(self.report)
		return super().execute(context)

# add igmesh operator into file->export menu
menu_func = lambda self, context: self.layout.operator("export.igmesh", text="Export Indigo Mesh...")
bpy.types.INFO_MT_file_export.append(menu_func)

class LightingChecker(SceneIterator):
	progress_thread_action = "Checking"
	
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
		
		self.valid_lighting = False
		
		self.ObjectsChecked = ExportCache("Objects")
		self.LampsChecked = ExportCache("Lamps")
		self.MaterialsChecked = ExportCache("Materials")
		self.CheckedDuplis = ExportCache("Duplis")
	
	def isValid(self):
		return self.valid_lighting
	
	def handler_Duplis_GENERIC(self, obj, *args, **kwargs):
		if self.CheckedDuplis.have(obj): return
		self.CheckedDuplis.add(obj, obj)
		
		try:
			obj.dupli_list_create(self.scene)
			if not obj.dupli_list:
				raise Exception('cannot create dupli list for object %s' % obj.name)
		except Exception as err:
			indigo_log('%s'%err)
			return
		
		for dupli_ob in obj.dupli_list:
			if dupli_ob.object.type not in self.valid_objects_callbacks:
				continue
			if not indigo_visible(self.scene, dupli_ob.object, is_dupli=True):
				continue
			
			self.handler_MESH(dupli_ob.object)
		
		obj.dupli_list_clear()
	
	def handler_MESH(self, obj, *args, **kwargs):
		if self.ObjectsChecked.have(obj): return
		
		emitting_object = False
		
		for ms in obj.material_slots:
			if self.MaterialsChecked.have(ms.material): continue
			self.MaterialsChecked.add(ms.material, ms.material)
			
			iem = ms.material.indigo_material.indigo_material_emission
			mat_test = iem.emission_enabled
			if iem.emission_enabled:
				mat_test &= self.check_spectrum(iem, 'emission')
				if iem.emission_scale:
					mat_test &= (iem.emission_scale_value > 0.0)
				else:
					mat_test &= (iem.emit_power > 0.0 and iem.emit_gain_val > 0.0)
				mat_test &= self.scene.indigo_lightlayers.is_enabled(iem.emit_layer)
				mat_test &= self.scene.indigo_lightlayers.gain_for_layer(iem.emit_layer) > 0.0
			emitting_object |= mat_test
		
		self.ObjectsChecked.add(obj, obj)
		self.valid_lighting |= emitting_object
	
	def handler_LAMP(self, obj, *args, **kwargs):
		if self.LampsChecked.have(obj): return
		
		self.valid_lighting |= obj.data.type in ('SUN', 'HEMI')
		self.LampsChecked.add(obj, obj)
		
	def check_spectrum(self, obj, prefix):
			valid_sp = False
			sp_type = getattr(obj, '%s_SP_type' % prefix)
			if sp_type == 'uniform':
				valid_sp = getattr(obj, '%s_SP_uniform_val' % prefix) > 0.0
			elif sp_type == 'rgb':
				valid_sp = getattr(obj, '%s_SP_rgb' % prefix).v > 0.0
			elif sp_type == 'blackbody':
				valid_sp = getattr(obj, '%s_SP_blackbody_gain' % prefix) > 0.0
			return valid_sp
	
	def canAbort(self):
		return self.valid_lighting

class _Impl_OT_indigo(_Impl_operator):
	'''Export an Indigo format scene (.igs)'''
	
	bl_idname = 'export.indigo'
	bl_label = 'Export Indigo Scene (.igs)'
	
	filename	= bpy.props.StringProperty(name='IGS filename')
	directory	= bpy.props.StringProperty(name='IGS directory')
	
	def invoke(self, context, event):
		wm = context.window_manager
		wm.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def check_write(self, directory):
		if not os.access(directory, os.W_OK):
			return False
		return True
	
	def check_lights(self, scene):
		LC = LightingChecker(scene)
		LC.iterateScene(scene)
		return LC.isValid()
	
	def check_output_path(self, path):
		efutil.export_path = efutil.filesystem_path(path)
		
		if not os.path.isdir(efutil.export_path):
			parent_dir = os.path.realpath( os.path.join(efutil.export_path, os.path.pardir) )
			if not self.check_write(parent_dir):
				indigo_log('Output path "%s" is not writable' % parent_dir)
				raise Exception('Output path is not writable')
			
			try:
				os.makedirs(efutil.export_path)
			except: 
				indigo_log('Could not create output path %s' % efutil.export_path)
				raise Exception('Could not create output path')
		
		if not self.check_write(efutil.export_path):
			indigo_log('Output path "%s" is not writable' % efutil.export_path)
			raise Exception('Output path is not writable')
		
		igs_filename = '/'.join( (efutil.export_path, self.properties.filename) )
		
		indigo_log('Writing to %s'%igs_filename)
		
		if efutil.export_path[-1] not in ('/', '\\'):
			efutil.export_path += '/'
		
		try:
			out_file = open(igs_filename, 'w')
			out_file.close()
		except:
			indigo_log('Failed to open output file "%s" for writing: check output path setting' % igs_filename)
			raise Exception('Failed to open output file for writing: check output path setting')
		
		return igs_filename
	
	def execute(self, master_scene):
		try:
			if master_scene is None:
				indigo_log('Scene context is invalid')
				raise Exception('Scene context is invalid')
			
			#------------------------------------------------------------------------------
			# Init stats
			indigo_log('Indigo export started ...')
			start_time = time.time()
			
			igs_filename = self.check_output_path(self.properties.directory)
			
			export_scenes = [master_scene.background_set, master_scene]
			
			have_illumination = False
			for ex_scene in export_scenes:
				if ex_scene is None: continue
				have_illumination |= self.check_lights(ex_scene)
				
			if not have_illumination:
				indigo_log('No light sources available!')
				raise Exception('No light sources available!')
			
			indigo_log('Export render settings')
			
			#------------------------------------------------------------------------------
			# Start with render settings, this also creates the root <scene>
			scene_xml = master_scene.indigo_engine.build_xml_element(master_scene)
			
			#------------------------------------------------------------------------------
			# Camera
			indigo_log('Export camera')
			scene_xml.append(
				master_scene.camera.data.indigo_camera.build_xml_element(master_scene)
			)
			
			#------------------------------------------------------------------------------
			# Tonemapping
			indigo_log('Export tonemapping')
			scene_xml.append(
				master_scene.camera.data.indigo_tonemapping.build_xml_element(master_scene)
			)
			
			#------------------------------------------------------------------------------
			# Materials - always export the default clay material and a null material
			from indigo.export.materials.Clay import ClayMaterial, NullMaterial
			scene_xml.append(ClayMaterial().build_xml_element(master_scene))
			scene_xml.append(NullMaterial().build_xml_element(master_scene))
			
			geometry_exporter = geometry.GeometryExporter(master_scene, master_scene.background_set)
			
			from indigo.export.light_layer import light_layer_xml
			# TODO:
			# light_layer_count was supposed to export correct indices when there
			# is a background_set with emitters on light layers -
			# however, the re-indexing at material export time is non-trivial for
			# now and probably not worth it.
			#light_layer_count = 0
			for ex_scene in export_scenes:
				if ex_scene is None: continue
				
				#------------------------------------------------------------------------------
				# Meshes and the materials assigned
				indigo_log('Parsing objects for scene %s' % ex_scene.name)
				geometry_exporter.iterateScene(ex_scene)
				
				#------------------------------------------------------------------------------
				# Light layer names
				for layer_name, idx in ex_scene.indigo_lightlayers.enumerate().items():
					indigo_log('Light layer %i: %s' % (idx, layer_name))
					scene_xml.append(
						light_layer_xml().build_xml_element(ex_scene, idx, layer_name)
					)
					# light_layer_count += 1
			
			indigo_log('Export lamps')
			
			# use special n==1 case due to bug in indigo <sum> material
			if geometry_exporter.ExportedLamps.count() == 1:
				scene_background_settings = ET.Element('background_settings')
				scene_background_settings_mat = ET.Element('background_material')
				scene_background_settings.append(scene_background_settings_mat)
				
				for ck, ci in geometry_exporter.ExportedLamps.get_all():		#@UnusedVariable
					for xml in ci:
						scene_background_settings_mat.append(xml)
				
				scene_xml.append(scene_background_settings)
			
			if geometry_exporter.ExportedLamps.count() > 1:
				
				scene_background_settings = ET.Element('background_settings')
				scene_background_settings_fmt = {
					'background_material': {
						'material': {
							'name': ['background_material'],
							'sum': { 'mat': xml_multichild() }
						}
					}
				}
				
				for ck, ci in geometry_exporter.ExportedLamps.get_all():		#@UnusedVariable
					for xml in ci:
						scene_xml.append(xml)
					
					scene_background_settings_fmt['background_material']['material']['sum']['mat'].append({
						'mat_name': [ck],
						'weight': {'constant': [1]}
					})
				scene_background_settings_obj = xml_builder()
				scene_background_settings_obj.build_subelements(None, scene_background_settings_fmt, scene_background_settings)
				scene_xml.append(scene_background_settings)
			
			for ck, ci in geometry_exporter.ExportedMaterials.get_all():	#@UnusedVariable
				for xml in ci:
					scene_xml.append(xml)
			indigo_log('Exported used materials')
			mc = 0
			for ck, ci in geometry_exporter.ExportedMeshes.get_all():		#@UnusedVariable
				mesh_name, xml = ci											#@UnusedVariable
				scene_xml.append(xml)
				mc += 1
			indigo_log('Exported %i meshes' % mc)
			
			#------------------------------------------------------------------------------
			# We write object instances to a separate file
			oc = 0
			scene_data_xml = ET.Element('scenedata')
			for ck, ci in geometry_exporter.ExportedObjects.get_all():		#@UnusedVariable
				xml = ci[0]
				scene_data_xml.append(xml)
				oc += 1
			
			objects_file_name = '%s%s/%s/%05d/objects.igs' % (
				efutil.export_path,
				efutil.scene_filename(),
				bpy.path.clean_name(master_scene.name),
				master_scene.frame_current
			)
			
			objects_file = open(objects_file_name, 'wb')
			ET.ElementTree(element=scene_data_xml).write(objects_file, encoding='utf-8')
			objects_file.close()
			indigo_log('Exported %i object instances to %s' % (oc,objects_file_name))
			scene_data_include = include.xml_include( efutil.path_relative_to_export(objects_file_name) )
			scene_xml.append( scene_data_include.build_xml_element(master_scene) )
			
			#------------------------------------------------------------------------------
			# Write formatted XML for settings, materials and meshes
			out_file = open(igs_filename, 'w')
			xml_str = ET.tostring(scene_xml, encoding='utf-8').decode()
			
			# substitute back characters protected from entity encoding in CDATA nodes
			xml_str = xml_str.replace('{_LESSTHAN_}', '<')
			xml_str = xml_str.replace('{_GREATERTHAN_}', '>')
			
			xml_dom = MD.parseString(xml_str)
			xml_dom.writexml(out_file, addindent='\t', newl='\n', encoding='utf-8')
			out_file.close()
			
			#------------------------------------------------------------------------------
			# Print stats
			end_time = time.time()
			indigo_log('Export finished; took %f seconds' % (end_time-start_time))
			
			return {'FINISHED'}
		
		except Exception as err:
			indigo_log('%s' % err, message_type='ERROR')
			if os.getenv('B25_OBJECT_ANALYSIS', False):
				raise err
			return {'CANCELLED'}

@IndigoAddon.addon_register_class
class EXPORT_OT_indigo(_Impl_OT_indigo, bpy.types.Operator):
	def execute(self, context):
		self.set_report(self.report)
		return super().execute(context.scene)

menu_func = lambda self, context: self.layout.operator("export.indigo", text="Export Indigo Scene...")
bpy.types.INFO_MT_file_export.append(menu_func)

@IndigoAddon.addon_register_class
class INDIGO_OT_lightlayer_add(bpy.types.Operator):
	'''Add a new light layer definition to the scene'''
	
	bl_idname = "indigo.lightlayer_add"
	bl_label = "Add Indigo Light Layer"
	
	new_lightlayer_name = bpy.props.StringProperty(default='New Light Layer')
	
	def invoke(self, context, event):
		lg = context.scene.indigo_lightlayers.lightlayers
		lg.add()
		new_lg = lg[len(lg)-1]
		new_lg.name = self.properties.new_lightlayer_name
		return {'FINISHED'}

@IndigoAddon.addon_register_class
class INDIGO_OT_lightlayer_remove(bpy.types.Operator):
	'''Remove the selected lightlayer definition'''
	
	bl_idname = "indigo.lightlayer_remove"
	bl_label = "Remove Indigo Light Layer"
	
	lg_index = bpy.props.IntProperty(default=-1)
	
	def invoke(self, context, event):
		w = context.scene.indigo_lightlayers
		if self.properties.lg_index == -1:
			w.lightlayers.remove(w.lightlayers_index)
		else:
			w.lightlayers.remove( self.properties.lg_index )
		w.lightlayers_index = len(w.lightlayers)-1
		return {'FINISHED'}
