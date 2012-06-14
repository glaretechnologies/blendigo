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
# System Libs
import os, subprocess, threading, time, sys

# Blender Libs
import bpy, bl_ui			#@UnresolvedImport

# EF Libs
from extensions_framework import util as efutil

# Indigo Libs
from indigo import IndigoAddon, bl_info
from indigo.export import indigo_log

# Exporter Property Groups need to be imported to ensure initialisation
import indigo.properties.camera
import indigo.properties.environment
import indigo.properties.lamp
import indigo.properties.material
import indigo.properties.object
import indigo.properties.render_settings
import indigo.properties.tonemapping

# Exporter Interface Panels need to be imported to ensure initialisation
import indigo.panels.camera
#import indigo.panels.image
import indigo.panels.lamp
import indigo.panels.material
import indigo.panels.object
import indigo.panels.render
import indigo.panels.world

# Exporter Operators need to be imported to ensure initialisation
import indigo.operators

from indigo.core.util import getVersion, getGuiPath, getConsolePath, getInstallPath

# Add standard Blender Interface elements
bl_ui.properties_render.RENDER_PT_render.COMPAT_ENGINES.add(IndigoAddon.BL_IDNAME)
bl_ui.properties_render.RENDER_PT_dimensions.COMPAT_ENGINES.add(IndigoAddon.BL_IDNAME)
bl_ui.properties_render.RENDER_PT_output.COMPAT_ENGINES.add(IndigoAddon.BL_IDNAME)

bl_ui.properties_scene.SCENE_PT_scene.COMPAT_ENGINES.add(IndigoAddon.BL_IDNAME)
bl_ui.properties_scene.SCENE_PT_audio.COMPAT_ENGINES.add(IndigoAddon.BL_IDNAME)
bl_ui.properties_scene.SCENE_PT_physics.COMPAT_ENGINES.add(IndigoAddon.BL_IDNAME) #This is the gravity panel
bl_ui.properties_scene.SCENE_PT_keying_sets.COMPAT_ENGINES.add(IndigoAddon.BL_IDNAME)
bl_ui.properties_scene.SCENE_PT_keying_set_paths.COMPAT_ENGINES.add(IndigoAddon.BL_IDNAME)
bl_ui.properties_scene.SCENE_PT_unit.COMPAT_ENGINES.add(IndigoAddon.BL_IDNAME)
bl_ui.properties_scene.SCENE_PT_custom_props.COMPAT_ENGINES.add(IndigoAddon.BL_IDNAME)

bl_ui.properties_material.MATERIAL_PT_context_material.COMPAT_ENGINES.add(IndigoAddon.BL_IDNAME)
bl_ui.properties_texture.TEXTURE_PT_context_texture.COMPAT_ENGINES.add(IndigoAddon.BL_IDNAME)

def compatible(module):
	module = getattr(bl_ui, module)
	for subclass in module.__dict__.values():
		try:	subclass.COMPAT_ENGINES.add(IndigoAddon.BL_IDNAME)
		except:	pass

compatible("properties_data_mesh")
compatible("properties_data_camera")
compatible("properties_particle")

@IndigoAddon.addon_register_class
class RENDERENGINE_indigo(bpy.types.RenderEngine):
	bl_idname = IndigoAddon.BL_IDNAME
	bl_label = 'Indigo'
	bl_use_preview = False
	
	render_lock = threading.Lock()
	
	def render(self, context):
		
		with RENDERENGINE_indigo.render_lock:	# just render one thing at a time
			
			self.renderer				= None
			self.message_thread			= None
			self.stats_thread			= None
			self.framebuffer_thread		= None
			self.render_update_timer	= None
			self.rendering				= False
			
			# force scene update to current rendering frame
			context.frame_set(context.frame_current)
			
			#------------------------------------------------------------------------------
			# Export the Scene
			
			# Don't make stupid /tmp/ folders on windows; replace the /tmp
			# segment with the real %tmp% folder
			# OSX also has a special temp location that we should use
			output_path_split = list(os.path.split(context.render.filepath))
			if sys.platform in ('win32', 'darwin') and output_path_split[0] == '/tmp':
				output_path_split[0] = efutil.temp_directory()
				fp = '/'.join(output_path_split)
			else:
				fp = context.render.filepath
			output_path = efutil.filesystem_path( fp )
			
			# Allow specifying custom output filename
			output_path_nameext = os.path.splitext(output_path)
			if output_path_nameext[1] == '.igs':
				output_filepath = output_path_nameext[0]
				
				# Fill out frame number template
				output_path_parts = os.path.split(output_filepath)
				
				output_path = '/'.join(output_path_parts[:-1])
				output_file_prefix = output_path_parts[-1]
				
				hash_count = output_file_prefix.count('#')
				if hash_count > 0:
					output_file_prefix = output_path_parts[-1].replace('#'*hash_count, ('%%0%0ii'%hash_count)%context.frame_current)
				
			else:
				output_file_prefix = '%s.%s.%05i' % (efutil.scene_filename(), bpy.path.clean_name(context.name), context.frame_current)
			
			output_filename = '%s.igs' % output_file_prefix
			
			exported_file = '/'.join([
				output_path,
				output_filename
			])
			
			if output_path[-1] not in ('/', '\\'):
				output_path = '%s/'%output_path
			
			png_filename = '%s%s.png' % (output_path, output_file_prefix)
			
			if self.is_animation:
				igq_filename = '%s/%s.%s.igq'%(output_path, efutil.scene_filename(), bpy.path.clean_name(context.name))
				if context.frame_current == context.frame_start:
					# start a new igq file
					igq_file = open(igq_filename, 'w')
					igq_file.write('<?xml version="1.0" encoding="utf-8" standalone="no" ?>\n')
					igq_file.write('<render_queue>\n')
				else:
					# append to existing
					igq_file = open(igq_filename, 'a')
				
				igq_file.write('\t<item>\n')
				igq_file.write('\t\t<scene_path>%s</scene_path>\n' % exported_file)
				igq_file.write('\t\t<halt_time>%d</halt_time>\n' % context.indigo_engine.halttime)
				igq_file.write('\t\t<halt_spp>%d</halt_spp>\n' % context.indigo_engine.haltspp)
				igq_file.write('\t\t<output_path>%s</output_path>\n' % png_filename[:-4])
				igq_file.write('\t</item>\n')
				
				if context.frame_current == context.frame_end:
					igq_file.write('</render_queue>\n')
				
				igq_file.close()
				
				fr = context.frame_end - context.frame_start
				fo = context.frame_current - context.frame_start
				self.update_progress(fo/fr)
			
			scene_writer = indigo.operators._Impl_OT_indigo(
				directory = output_path,
				filename = output_filename
			).set_report(self.report)
			
			export_result = scene_writer.execute(context)
			
			if not 'FINISHED' in export_result:
				return
			
			#------------------------------------------------------------------------------
			# Update indigo defaults config file 
			config_updates = {
				'auto_start': context.indigo_engine.auto_start,
				'console_output': context.indigo_engine.console_output
			}
			
			if context.indigo_engine.use_console:
				indigo_path = getConsolePath(context)
			else:
				indigo_path = getGuiPath(context)
			
			if os.path.exists(indigo_path):
				config_updates['install_path'] = getInstallPath(context)
			
			try:
				for k,v in config_updates.items():
					efutil.write_config_value('indigo', 'defaults', k, v)
			except Exception as err:
				indigo_log('Saving indigo config failed: %s' % err, message_type='ERROR')
			
			#------------------------------------------------------------------------------
			# Conditionally Spawn Indigo
			
			exe_path = efutil.filesystem_path( indigo_path )
			
			# Make sure that the Indigo we are going to launch is at least as
			# new as the exporter version
			version_ok = True
			if not context.indigo_engine.skip_version_check:
				iv = getVersion(context)
				for i in range(3):
					version_ok &= iv[i]>=bl_info['version'][i]
			
			if context.indigo_engine.auto_start and os.path.exists(exe_path):
				#if not version_ok:
					#indigo_log("Unsupported version v%s; Cannot start Indigo with this scene" % ('.'.join(['%s'%i for i in iv])), message_type='ERROR')
					#return
				
				if self.is_animation and context.frame_current != context.frame_end:
					# if it's an animation, don't execute until final frame
					return
				
				if self.is_animation and context.frame_current == context.frame_end:
					# if animation and final frame, launch queue instead of single frame
					exported_file = igq_filename
					indigo_args = [
						exe_path,
						exported_file
					]
				else:
					indigo_args = [
						exe_path,
						exported_file,
						'-o',
						png_filename
					]
				
				if context.indigo_engine.network_mode == 'master':
					indigo_args.extend(['-n', 'm'])
				
				if context.indigo_engine.network_mode == 'working_master':
					indigo_args.extend(['-n', 'wm'])
				
				if context.indigo_engine.network_mode in ['master', 'working_master']:
					indigo_args.extend([
						'-p',
						'%i' % context.indigo_engine.network_port
					])
				
				if context.indigo_engine.network_mode == 'manual':
					indigo_args.extend([
						'-h',
						'%s:%i' % (context.indigo_engine.network_host, context.indigo_engine.network_port)
				])
				
				indigo_log("Starting indigo: %s" % indigo_args)
				
				if context.indigo_engine.use_console or context.indigo_engine.wait_for_process:
					f_stdout = subprocess.PIPE
				else:
					f_stdout = None
				
				indigo_proc = subprocess.Popen(indigo_args, stdout=f_stdout)
				indigo_pid = indigo_proc.pid
				indigo_log('Started Indigo process, PID: %i' % indigo_pid)
				
				if context.indigo_engine.use_console or context.indigo_engine.wait_for_process:
					while indigo_proc.poll() == None:
						indigo_proc.communicate()
						time.sleep(2)
					
					indigo_proc.wait()
					if not indigo_proc.stdout.closed:
						indigo_proc.communicate()
					if indigo_proc.returncode == -1:
						sys.exit(-1)
			
			else:
				indigo_log("Scene was exported to %s" % exported_file)
			
			#------------------------------------------------------------------------------
			# Finished
			return
	
	def stats_timer(self):
		'''
		Update the displayed rendering statistics and detect end of rendering
		
		Returns None
		'''
		
		self.update_stats('', 'Indigo Renderer: Rendering %s' % self.stats_thread.stats_string)
		if self.test_break() or not self.message_thread.isAlive():
			self.renderer.terminate_rendering()
			self.stats_thread.stop()
			self.stats_thread.join()
			self.message_thread.stop()
			self.message_thread.join()
			self.framebuffer_thread.stop()
			self.framebuffer_thread.join()
			# self.framebuffer_thread.kick() # Force get final image
			self.update_stats('', '')
			self.rendering = False
			self.renderer = None # destroy/unload the renderer instance
