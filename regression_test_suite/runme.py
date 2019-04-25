#
# Blendigo 2.5 Regression Testing Suite
#
# INFO:
# Run this script in command line to start testing suite. report.html and results.txt will be created in outputs directory

INDIGO_TEST_SUITE = r'E:\Blender\myaddons\blendigo_fork\regression_test_suite'
BLENDER_BINARY = r'E:\Blender\blender-2.79b-windows64\blender.exe'
filter_scenes = []

import os, subprocess

# run blender
args = [BLENDER_BINARY, '-noaudio']
args.append('-b')
args.extend(['-P', os.path.join(INDIGO_TEST_SUITE, 'run.py')])
args.append('--')
args.append('--INDIGO_TEST_SUITE=%s' % INDIGO_TEST_SUITE)
args.extend(filter_scenes)

exit_code = subprocess.call(args, env=os.environ)

if exit_code < 0:
    raise Exception('process error!')