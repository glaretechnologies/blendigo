import bpy            #@UnresolvedImport

from .. export import UnexportableObjectException
from .. export._igmesh import igmesh, igmesh_stream
from .. export import ( indigo_log )
import time
import array


### Some utility methods for writing binary data to a file. ###

def write_uint32(file, x):
    a = array.array('i', [x]) # NOTE: this is actually signed
    a.tofile(file)
    
    
def write_string(file, s):
    string_bytes = bytearray(s.encode(encoding='UTF-8'))

    # Write length of string
    write_uint32(file, len(string_bytes))
    
    # Write string bytes.
    a = array.array('b', string_bytes)
    a.tofile(file)
    
    
def write_list_of_vec2s(file, vec2_list):
    # Write length of vector
    write_uint32(file, len(vec2_list))
    
    # Convert the list of vec3s to a list of floats
    component_list = []
    for v in vec2_list:
        component_list.extend([v[0], v[1]])

    # Write the list of floats
    a = array.array('f', component_list)
    a.tofile(file)
    
    
def write_list_of_vec3s(file, vec3_list):
    # Write length of vector
    write_uint32(file, len(vec3_list))
    
    # Convert the list of vec3s to a list of floats
    component_list = []
    for v in vec3_list:
        component_list.extend([v[0], v[1], v[2]])
        
    # Write the list of floats
    a = array.array('f', component_list)
    a.tofile(file)
    
    
    

class igmesh_writer(object):
    
    @staticmethod
    def factory(scene, obj, filename, mesh, debug=False):
        
        debug = False
        
        if debug:
            start_time = time.time()
            print('igmesh_writer.factory was passed %s' % obj)
            indigo_log('igmesh_writer.factory was passed %s' % obj)
        
        if obj.type not in ['MESH', 'SURFACE', 'FONT', 'CURVE']:
            raise Exception("Can only export 'MESH', 'SURFACE', 'FONT', 'CURVE' objects")
        

        (used_mat_indices, use_shading_normals) = igmesh_writer.write_mesh(filename, scene, obj, mesh)

        if debug:
            end_time = time.time()
            print('Build + Save took %0.2f sec' % (end_time-start_time))
            indigo_log('Build + Save took %0.5f sec' % (end_time-start_time))
        
        return (used_mat_indices, use_shading_normals)
        
    
                
        
    ################################################################################
    @staticmethod
    def write_mesh(filename, scene, obj, mesh):
    
        profile = False
        
        exportDummyUVs = True
        
        if profile:
            total_start_time = time.time()
            
        if len(mesh.polygons) < 1:
            raise UnexportableObjectException('Object %s has no faces!' % obj.name)
        
        if len(mesh.vertices) < 1:
            raise UnexportableObjectException('Object %s has no verts!' % obj.name)

        mesh.calc_loop_triangles()
        # TODO: consecutive loop triangles corresponding to the same polygon ought to be considered as one quad
        tessfaces = mesh.loop_triangles
        
        def get_tess_idxs():
            # convert tris to quads/tris and get indexes of verts
            # TODO: step+2? WTF what have i done
            length = len(mesh.loop_triangles)
            for i in range(0, length, 2):
                if i+1 < length and mesh.loop_triangles[i].polygon_index == mesh.loop_triangles[i+1].polygon_index:
                    # quad
                    yield mesh.loop_triangles[i].loops[:] + (mesh.loop_triangles[i+1].loops[2],)
                else:
                    # tri
                    yield mesh.loop_triangles[i].loops[:]

        class Quad:
            def __init__(self, index, tri1, tri2=None):
                self.tri1 = tri1
                self.tri2 = tri2
                self.index = index

            @property
            def material_index(self):
                return self.__tri1.material_index
        
        render_uvs = [uvl for uvl in mesh.uv_layers]
        num_uv_sets = len(render_uvs)
        

        # Open file to write to
        file = open(filename, 'wb')
        
        # Write magic number
        write_uint32(file, 5456751)
        
        # Write format version
        write_uint32(file, 3)
        
        # Write num UV mappings
        if num_uv_sets == 0 and exportDummyUVs:
            write_uint32(file, 1)
        else:
            write_uint32(file, num_uv_sets)
        
        #used_mat_indices = rang(obj.material_slots)
        
        used_mat_indices = set()
        mats = []
        
        num_mats = len(obj.material_slots)
        for mi in range(num_mats):
            mats.append(obj.material_slots[mi].material)
            used_mat_indices.add(mi)
        
        
        if profile:
            indigo_log('used_mat_indices: %s' % str(used_mat_indices))
    
                
        if len(mats) == 0:
            # Write num used materials
            write_uint32(file, 1)
            
            # Write material name
            write_string(file, 'blendigo_clay')
        else:
            # Count number of actual materials.
            count = 0
            for m in mats:
                if m == None: continue
                count += 1
                
            # Write num used materials
            write_uint32(file, count)
            
            for m in mats:
                if m == None: continue
                # Write material name
                write_string(file, m.indigo_material.get_name(m))
        
        # Write num uv set expositions.  Note that in v2, these aren't actually read, so can just write zero.
        write_uint32(file, 0)
        
        start_time = time.time()

        num_smooth = 0
        for face in mesh.polygons: # for each face
            if face.use_smooth:
                num_smooth += 1
            
        #indigo_log('num smooth: %i, num flat: %i' % (num_smooth, num_flat))
        
        
        vertices = []
        normals = []
        
        for v in mesh.vertices:
            vertices.append(v.co)
            
        # If we need shading normals, write them all out
        # TODO: loops[].normal in 2.8. This does not work for flat/smooth mixed meshes (all exported as smooth). Have to use split normals.
        if num_smooth != 0:
            for v in mesh.vertices:
                normals.append(v.normal)
            
        # write vertices
        write_list_of_vec3s(file, vertices)

        # write vertex normals
        write_list_of_vec3s(file, normals)
        
        
        del vertices
        del normals
        
        if profile:
            indigo_log('Writing vertices and vertex normals: %0.5f sec' % (time.time() - start_time))
        
        if profile:
            indigo_log('num_uv_sets : %i' % num_uv_sets)
            indigo_log('len(mesh.loop_triangles) : %i' % len(mesh.loop_triangles))
            #indigo_log('4*len(mesh.tessfaces)*num_uv_sets : %i sec' % (4*len(mesh.tessfaces)*num_uv_sets))
            #indigo_log('8*4*len(mesh.tessfaces)*num_uv_sets : %i sec' % (8*4*len(mesh.tessfaces)*num_uv_sets))
        
        start_time = time.time()
        uv_start_time = time.time()
        
        uv_data = []

        if num_uv_sets > 0:
            for layer_uv in render_uvs: # For each UV set
                for tri in mesh.loop_triangles: # For each tri
                    uv_data.extend([layer_uv.data[tri.loops[0]].uv, layer_uv.data[tri.loops[1]].uv, layer_uv.data[tri.loops[2]].uv, (0,0)])
                    # TODO: Only tris for now. Need quads
        elif exportDummyUVs:
            uv_data.extend([(0,0)])

        '''
        if num_uv_sets > 0:
            for uv_index in range(num_uv_sets): # For each UV set
                layer_uvs = render_uvs[uv_index]
                for face in tessfaces: # For each face
                    face_uvs = layer_uvs.data[face.index]
                    if len(face.vertices) == 3:
                        uv_data.extend([face_uvs.uv[0], face_uvs.uv[1], face_uvs.uv[2], (0,0)])
                    else:
                        uv_data.extend([face_uvs.uv[0], face_uvs.uv[1], face_uvs.uv[2], face_uvs.uv[3]])
        elif exportDummyUVs:
            uv_data.extend([(0,0)])
        '''

        if profile:
            indigo_log('    Making UV list time : %0.5f sec' % (time.time() - start_time))
        start_time = time.time()
        
        
        # Write UV layout
        write_uint32(file, 1) # UV_LAYOUT_LAYER_VERTEX = 1;

        # Write UV data
        write_list_of_vec2s(file, uv_data)
        
        del uv_data # Free uv_data mem
        

        if profile:
            indigo_log('    Writing UVs: %0.5f sec' % (time.time() - start_time))
            indigo_log('Total UV time: %0.5f sec' % (time.time() - uv_start_time))

        
        # Write triangles
        start_time = time.time()
        
        tri_data = [] # A list of integers
        quad_data = [] # A list of integers
        

        if num_uv_sets > 0:
            # TODO: Quads
            for tri in mesh.loop_triangles:
                uv_idx = tri.index * 4
                fv = tri.vertices
                
                if len(tri.vertices) == 3: # if this is a triangle
                    tri_data.extend([fv[0], fv[1], fv[2], uv_idx, uv_idx + 1, uv_idx + 2, tri.material_index])
                else: # Else if this is a quad
                    quad_data.extend([fv[0], fv[1], fv[2], fv[3], uv_idx, uv_idx + 1, uv_idx + 2, uv_idx + 3, face.material_index])
        else:
            # TODO: Quads
            for tri in mesh.loop_triangles:
                fv = tri.vertices
                if len(tri.vertices) == 3: # if this is a triangle
                    tri_data.extend([fv[0], fv[1], fv[2], 0, 0, 0, tri.material_index])
                else: # Else if this is a quad
                    quad_data.extend([fv[0], fv[1], fv[2], fv[3], 0, 0, 0, 0, face.material_index])
        '''
        if num_uv_sets > 0:
            for face in tessfaces:
                uv_idx = face.index * 4
                fv = face.vertices
                
                if len(face.vertices) == 3: # if this is a triangle
                    tri_data.extend([fv[0], fv[1], fv[2], uv_idx, uv_idx + 1, uv_idx + 2, face.material_index])
                else: # Else if this is a quad
                    quad_data.extend([fv[0], fv[1], fv[2], fv[3], uv_idx, uv_idx + 1, uv_idx + 2, uv_idx + 3, face.material_index])
        else:
            for face in tessfaces:
                fv = face.vertices
                if len(face.vertices) == 3: # if this is a triangle
                    tri_data.extend([fv[0], fv[1], fv[2], 0, 0, 0, face.material_index])
                else: # Else if this is a quad
                    quad_data.extend([fv[0], fv[1], fv[2], fv[3], 0, 0, 0, 0, face.material_index])
        '''
        
    
        ####### Write triangles #######        
        # Write num triangles
        
        num_tris = len(tri_data) // 7  # NOTE: // is integer division, which we want.  There are 7 uints per triangle.
        write_uint32(file, num_tris)
                    
        tri_array = array.array('i', tri_data)
        tri_array.tofile(file)
        
        del tri_data # Free tri data
        
        if profile:
            indigo_log('Writing triangle time: %0.5f sec' % (time.time() - start_time))
        
        ####### Write quads #######        
        # Write num quads
        num_quads = len(quad_data) // 9  # NOTE: // is integer division, which we want.  There are 9 uints per quad.
        write_uint32(file, num_quads)

        quad_array = array.array('i', quad_data)
        quad_array.tofile(file)
        
        # Close the file we have been writing to.
        file.close()
        
        use_shading_normals = num_smooth > 0
        
        if profile:
            total_time = time.time() - total_start_time
            indigo_log('Total mesh writing time: %0.5f sec' % (total_time))
        
        return (used_mat_indices, use_shading_normals)