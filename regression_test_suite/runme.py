#
# Blendigo 2.5 Regression Testing Suite
#
# INFO:
# Run this script in command line to start testing suite. report.html and results.txt will be created in outputs directory
# Copy pypng to blender's python/lib

BLENDER_BINARY = r'F:\Blender\blender-2.80-windows64\blender.exe'
filter_scenes = [
# 'AbsoluteTexturePath',
# 'Animation',
# 'BackgroundSet',
# 'CoatingMaterial',
# 'ComplexUVMap',
# 'CurveObject',
# 'DoubleSidedThin',
# 'DupliGroup_Instances',
# 'EXREnvironment',
# 'EmittingParticles',
# 'ExternalMaterial',
# 'FindCRF',
# 'Focus_CurveAnim',
# 'HighSubdiv',
# 'ISL_01',
# 'InstanceMaterials',
# 'InvisibleToCameraObject',
# 'LinkedBackgroundSet',
# 'ModifiedCurve',
# 'MotionBlur',
# 'MultipleUVSets',
# 'NestedGroups',
# 'PackedImage',
# 'ParentObjectTransforms',
# 'ParticleSystem_01',
# 'ParticleSystem_02',
# 'ParticleSystem_03',
# 'ParticleSystem_04',
# 'RelativeTexturePath',
# 'ShadowCatcher',
# 'SpherePrimitive',
'SunAndEnvMap',
# 'TexturedEmission',
# 'TriangleMesh',
# 'dupligroup-error',
# 'glossy_roughness_transparent_nk',
# 'hemi_blackbody',
# 'hemi_rgb',
# 'hemi_uniform',
# 'ies_dupli',
# 'light_color',
# 'lightlayers',
# 'motion_blur_dupli_instances',
# 'motion_blur_particles_simple',
# 'null_fastsss',
# 'proxy'
# 'external_mat_ies_scale'
]

filter_additional = [
# "multifile_animation",
]

filter_scenes.extend(filter_additional)

import os, subprocess

# run blender
INDIGO_TEST_SUITE = os.path.split(__file__)[0]
args = [BLENDER_BINARY, '-noaudio']
args.append('-b')
args.extend(['-P', os.path.join(INDIGO_TEST_SUITE, 'run.py')])
args.append('--')
args.append('--INDIGO_TEST_SUITE=%s' % INDIGO_TEST_SUITE)
args.extend(filter_scenes)

exit_code = subprocess.call(args, env=os.environ)

if exit_code < 0:
    raise Exception('process error!')