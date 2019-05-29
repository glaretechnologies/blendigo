#
# Blendigo 2.5 Regression Testing Suite
#
# INFO:
# Run this script in command line to start testing suite. report.html and results.txt will be created in outputs directory
# Copy pypng to blender's python/lib

BLENDER_BINARY = r'E:\Blender\blender-2.79b-windows64\blender.exe'
filter_scenes = [
"DupliGroup_Instances",
"Focus_CurveAnim",
"motion_blur_particles_simple",
"ies_dupli",
"proxy",
"glossy_roughness_transparent_nk",
"null_fastsss",
"motion_blur_dupli_instances",
"lightlayers",
"light_color",
"hemi_uniform",
"hemi_rgb",
"hemi_blackbody",
]

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