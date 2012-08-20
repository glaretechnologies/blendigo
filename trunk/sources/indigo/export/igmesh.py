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
import bpy			#@UnresolvedImport

from indigo.export import UnexportableObjectException
from indigo.export._igmesh import igmesh, igmesh_stream

class igmesh_writer(object):
	
	@staticmethod
	def factory(scene, obj, filename, debug=False, stream=True):
		
		'''
		We need to decide here which igmesh type to use.
		
		igmesh() = marginally quicker, but uses lots of RAM
		igmesh_stream() = marginally slower but uses much less RAM
		
		For a mesh with 1007616 tris:
		igmesh()
			317mb peak usage, exported in 21.1 sec
		
		igmesh_stream()
			67mb peak usage, exported in 25.5 sec
			
		As a contrast:
		 - writing to <embedded> takes 341mb / 12.54 sec (though this does not yet write UVs)
		 - Blendigo 2.0.10/Blender 2.48 wrote to <embedded_2> in 40mb / 16.9 sec 
		
		By default we should prefer speed over memory (igmesh). There
		should be an option to prefer memory over speed (igmesh_stream)
		in case users have difficulty exporting large objects.
		
		UPDATE: A large portion of the time used on large meshes is
		in Blender's create_render_mesh() method - NOT in mesh export!!
		This has more influence if the modifiers create tris (subdiv).
		For faster export you should apply all modifiers beforehand.
		'''
		
		if debug:
			import time
			start_time = time.time()
			print('igmesh_writer.factory was passed %s' % obj)
		
		if obj.type not in ['MESH', 'SURFACE', 'FONT', 'CURVE']:
			raise Exception("Can only export 'MESH', 'SURFACE', 'FONT', 'CURVE' objects")
		
		if stream:
			igo = igmesh_stream(filename)
		else:
			igo = igmesh()
		
		if debug:
			igo.debug = True
		
		if stream:
			used_mat_indices = igmesh_writer.build_mesh_stream(scene, igo, obj)
		else:
			used_mat_indices = igmesh_writer.build_mesh(scene, igo, obj)
		
		if debug:
			build_time = time.time()
			print('Build took %0.2f sec' % (build_time-start_time))
		
		if not stream:
			try:
				igo.save(filename)
				if debug:
					save_time = time.time()
					print('Save took %0.2f sec' % (save_time-build_time))
			except:
				print(igo)
				print(igo.triangles)
				raise
		
		if debug:
			end_time = time.time()
			print('Build + Save took %0.2f sec' % (end_time-start_time))
		
		return used_mat_indices
	
	@staticmethod
	def build_mesh_stream(scene, igo, obj):
		
		# Create mesh with applied modifiers
		if len(obj.modifiers) > 0 or obj.type in ['SURFACE', 'FONT', 'CURVE']:
			mesh = obj.to_mesh(scene, True, 'RENDER')
		else:
			mesh = obj.data

		mesh.update(calc_tessface=True) # Update the mesh, this ensures that the triangle tesselations are available
			
		if len(mesh.tessfaces) < 1:
			raise UnexportableObjectException('Object %s has no faces!' % obj.name)
		
		if len(mesh.vertices) < 1:
			raise UnexportableObjectException('Object %s has no verts!' % obj.name)

		render_uvs = [uvt for uvt in mesh.tessface_uv_textures]
		num_uv_sets = len(render_uvs)

		igo.add_num_uv_mappings(num_uv_sets)

		total_tris = 0
		used_mat_indices = set()
		for face in mesh.tessfaces:
			total_tris += len(face.vertices) - 2
			used_mat_indices.add(face.material_index)

		mats = []
		if len(obj.material_slots) > 0:
			# need to attach all mats up to max used index
			for mi in range(max(used_mat_indices) + 1): #sorted([mi for mi in used_mat_indices]):
				mat = obj.material_slots[mi].material
				if mat == None: continue
				mats.append(mat)
		
		num_mats = len(mats)
		if num_mats == 0:
			igo.add_num_used_materials(1)
			igo.add_used_material('blendigo_clay')
		else:
			#um = []
			#mn = 0
			#for m in mesh.materials:
			#	if m is not None:
			#		um.append(m)
			#		mn+=1
			#if mn == 0:
			#	igo.add_num_used_materials(1)
			#	igo.add_used_material('blendigo_clay')
			#else:
			igo.add_num_used_materials(num_mats)
			for m in mats:
				igo.add_used_material(m.indigo_material.get_name(m))
		
		igo.add_num_uv_set_expositions(num_uv_sets)
		for i,uvt in enumerate(render_uvs):
			igo.add_uv_set_exposition(uvt.name, i)

		vert_cache = []
		normal_cache = []

		# Write vertices and normals, and collate face indices against
		# verts using vert normal or face normal

		face_vert_indices = {}		# mapping of face index to list of exported vert indices for that face
		vert_vno_indices = {}		# mapping of vert index to exported vert index for verts with vert normals
		vert_use_vno = set()		# Set of vert indices that use vert normals

		vert_index = 0				# exported vert index
		for face in mesh.tessfaces:
			face_vert_indices[face.index] = []

			for vertex in face.vertices:
				v = mesh.vertices[vertex]

				if face.use_smooth:

					if vertex not in vert_use_vno:
						vert_use_vno.add(vertex)

						vert_cache.append(v.co)
						normal_cache.append(v.normal)
						vert_vno_indices[vertex] = vert_index
						face_vert_indices[face.index].append(vert_index)

						vert_index += 1
					else:
						face_vert_indices[face.index].append(vert_vno_indices[vertex])

				else:

					# face-vert-co-no are all unique, no caching
					# possible
					vert_cache.append(v.co)
					normal_cache.append(face.normal)
					face_vert_indices[face.index].append(vert_index)
					vert_index += 1

		del vert_vno_indices
		del vert_use_vno


		igo.add_num_vert_positions(len(vert_cache))
		for v in vert_cache:
			igo.add_vert_position_fast(v)

		igo.SEQ += 1

		igo.add_num_vert_normals(len(normal_cache))
		for n in normal_cache:
			igo.add_vert_normal_fast(n)

		igo.SEQ += 1


		del vert_cache
		del normal_cache

		igo.add_num_uv_pairs(4*len(mesh.tessfaces)*num_uv_sets)

		if num_uv_sets > 0:
			# UVs are interleaved thus -
			# face[0].uv[0].co[0]
			# face[0].uv[1].co[0]
			# ..
			# face[0].uv[*].co[1]
			# ..
			# face[1].uv[*].co[*]
			for face in mesh.tessfaces:
				add_blank_uv4 = len(face.vertices) == 3
				for uv_coord_idx in range(4):
					for uv_index in range(num_uv_sets):
						if add_blank_uv4 and uv_coord_idx == 3:
							igo.add_uv_pair_fast(tuple([0,0]))
						else:
							igo.add_uv_pair_fast(tuple(render_uvs[uv_index].data[face.index].uv[uv_coord_idx]))

			igo.SEQ += 1


		igo.add_num_triangles(total_tris)

		
		# Write triangles

		if num_uv_sets > 0:
			for face in mesh.tessfaces:
				uv_idx = face.index * 4
				igo.add_triangle_fast(
					face_vert_indices[face.index][0:3],
					(uv_idx, uv_idx + 1, uv_idx + 2),
					face.material_index
				)
				if len(face.vertices) > 3:
					igo.add_triangle_fast(
						(face_vert_indices[face.index][0], face_vert_indices[face.index][2], face_vert_indices[face.index][3]),
						(uv_idx, uv_idx + 2, uv_idx + 3),
						face.material_index
					)
		else:
			for face in mesh.tessfaces:
				igo.add_triangle_fast(
					face_vert_indices[face.index][0:3],
					(0, 0, 0),
					face.material_index
				)
				if len(face.vertices) > 3:
					igo.add_triangle_fast(
						(face_vert_indices[face.index][0], face_vert_indices[face.index][2], face_vert_indices[face.index][3]),
						(0, 0, 0),
						face.material_index
					)

		igo.SEQ += 1

		igo.finish()


		if len(obj.modifiers) > 0 or obj.type in ['SURFACE', 'FONT', 'CURVE']:
			# Remove mesh with applied modifiers
			bpy.data.meshes.remove(mesh)
		
		return used_mat_indices
	
	@staticmethod
	def build_mesh(scene, igo, obj):
		
		# Create mesh with applied modifiers
		if len(obj.modifiers) > 0 or obj.type in ['SURFACE', 'FONT', 'CURVE']:
			mesh = obj.to_mesh(scene, True, 'RENDER')
		else:
			mesh = obj.data
			
		if len(mesh.faces) < 1:
			raise UnexportableObjectException('Object %s has no faces!' % obj.name)
		
		if len(mesh.vertices) < 1:
			raise UnexportableObjectException('Object %s has no verts!' % obj.name)
		
		render_uvs = [uvt for uvt in mesh.uv_textures]
		num_uv_sets = len(render_uvs)
		
		igo.num_uv_mappings = num_uv_sets
		
		used_mat_indices = set()
		for face in mesh.faces:
			used_mat_indices.add(face.material_index)
		
		mats = []
		if len(obj.material_slots) > 0:
			# need to attach all mats up to max used index
			for mi in range(max(used_mat_indices)+1): #sorted([mi for mi in used_mat_indices]):
				mat = obj.material_slots[mi].material
				if mat == None: continue
				mats.append( mat )
		
		num_mats = len(mats)
		if num_mats == 0:
			igo.used_materials = ['blendigo_clay']
		else:
			igo.used_materials = [ m.indigo_material.get_name(m) for m in mats ]
		
		igo.uv_set_expositions = { i: uvt.name for i,uvt in enumerate(render_uvs) }
		
		# Write vertices and normals, and collate face indices against
		# verts using vert normal or face normal
		
		face_vert_indices = {}		# mapping of face index to list of exported vert indices for that face
		vert_vno_indices = {}		# mapping of vert index to exported vert index for verts with vert normals
		vert_use_vno = set()		# Set of vert indices that use vert normals
		
		vert_index = 0				# exported vert index
		for face in mesh.faces:
			fvi = []
			for vertex in face.vertices:
				v = mesh.vertices[vertex]
				
				if face.use_smooth:
					
					if vertex not in vert_use_vno:
						vert_use_vno.add(vertex)
						
						igo.vert_positions.append(v.co)
						igo.vert_normals.append(v.normal)
						vert_vno_indices[vertex] = vert_index
						fvi.append(vert_index)
						
						vert_index += 1
					else:
						fvi.append(vert_vno_indices[vertex])
					
				else:
					
					# face-vert-co-no are all unique, no caching
					# possible
					igo.vert_positions.append(v.co)
					igo.vert_normals.append(face.normal)
					fvi.append(vert_index)
					vert_index += 1
			
			face_vert_indices[face.index] = fvi
		
		del vert_vno_indices
		del vert_use_vno
		
		if num_uv_sets > 0:
			# UVs are interleaved thus -
			# face[0].uv[0].co[0]
			# face[0].uv[1].co[0]
			# ..
			# face[0].uv[*].co[1]
			# ..
			# face[1].uv[*].co[*]
			for face in mesh.faces:
				add_blank_uv4 = len(face.vertices)==3
				for uv_coord_idx in range(4):
					for uv_index in range(num_uv_sets):
						if add_blank_uv4 and uv_coord_idx==3:
							igo.uv_pairs.append( tuple([0,0]) )
						else:
							igo.uv_pairs.append( tuple(render_uvs[uv_index].data[face.index].uv[uv_coord_idx]) )
		
		# Write triangles
		
		if num_uv_sets > 0:
			for face in mesh.faces:
				igo.triangles.append({
					'vertex_indices': face_vert_indices[face.index][0:3],
					'uv_indices': face_vert_indices[face.index][0:3],
					'tri_mat_index': face.material_index
				})
				if len(face.vertices) > 3:
					igo.triangles.append({
						'vertex_indices': (face_vert_indices[face.index][0], face_vert_indices[face.index][2], face_vert_indices[face.index][3]),
						'uv_indices': (face_vert_indices[face.index][0], face_vert_indices[face.index][2], face_vert_indices[face.index][3]),
						'tri_mat_index': face.material_index
					})
		else:
			for face in mesh.faces:
				igo.triangles.append({
					'vertex_indices': face_vert_indices[face.index][0:3],
					'uv_indices': (0,0,0),
					'tri_mat_index': face.material_index
				})
				if len(face.vertices) > 3:
					igo.triangles.append({
						'vertex_indices': (face_vert_indices[face.index][0], face_vert_indices[face.index][2], face_vert_indices[face.index][3]),
						'uv_indices': (0,0,0),
						'tri_mat_index': face.material_index
					})
		
		if len(obj.modifiers) > 0 or obj.type in ['SURFACE', 'FONT', 'CURVE']:
			# Remove mesh with applied modifiers
			bpy.data.meshes.remove(mesh)
		
		return used_mat_indices
