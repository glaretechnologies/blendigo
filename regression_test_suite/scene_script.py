import bpy, datetime, optparse, sys

def terminate(code=-1):
	#sys.exit(code)
	bpy.ops.wm.quit_blender()

# Parse the command line options sent from run.py
parser = optparse.OptionParser()
parser.add_option(
	'--output-path',
	metavar = 'PATH', type = str,
	dest = 'output_path'
)
parser.add_option(
	'--install-path',
	metavar = 'PATH', type = str,
	dest = 'install_path'
)
parser.add_option(
	'--test-name',
	metavar = 'NAME', type = str,
	dest = 'test_name'
)
parser.add_option(
	'--blendigo-version',
	metavar = 'VER', type = str,
	dest = 'blendigo_version'
)
# Skip argv prior to and including '--'
parse_args = sys.argv[sys.argv.index('--')+1:]
options, args = parser.parse_args(parse_args)

if not options.output_path:
	print('Error: No output path specified!')
	terminate(-1)
if not options.install_path:
	print('Error: No console binary specified!')
	terminate(-1)
if not options.test_name:
	print('Error: No test name specified!')
	terminate(-1)
if not options.blendigo_version:
	print('Error: No blendigo version specified!')
	terminate(-1)

# Set up to use console rendering
bpy.context.scene.render.engine = 'indigo_renderer' #'blendigo-%s' % options.blendigo_version
bpy.context.scene.indigo_engine.install_path = options.install_path
bpy.context.scene.indigo_engine.use_console = True
bpy.context.scene.indigo_engine.console_output = True
bpy.context.scene.indigo_engine.skip_version_check = True

# don't switch to gpu in incompatible scenes 
if not bpy.context.scene.indigo_engine.render_mode in ('custom', 'shadow'):
	# speed up testing with gpu
	bpy.context.scene.indigo_engine.render_mode = 'path_gpu'
	# bpy.context.scene.indigo_engine.render_mode = 'path_cpu' # temporary... i don't have sufficient gpu right now

# Set up halt condition and behaviour
bpy.context.scene.indigo_engine.halttime = -1
bpy.context.scene.indigo_engine.haltspp = 2048

# Set up output dimensions
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
bpy.context.scene.render.resolution_percentage = 15

# Set up output format
bpy.context.scene.render.image_settings.file_format = 'PNG'
bpy.context.scene.render.filepath = options.output_path

try:
	# Render!
	render_result = bpy.ops.render.render()
	if not 'FINISHED' in render_result:
		raise Exception('Rendering %s failed!' % options.test_name)
		
except Exception as err:
	print('ERROR: %s' % err)
	terminate(-1)
