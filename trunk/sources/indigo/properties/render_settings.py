# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 Indigo Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond, Tom Svilans, Yves Collé
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
import time, os

import bpy
from bpy.app.handlers import persistent

from extensions_framework import declarative_property_group
from extensions_framework import util as efutil
from extensions_framework.validate import Logic_OR as O

from indigo import bl_info, IndigoAddon
from indigo.core.util import PlatformInformation, getInstallPath
import indigo.export

def find_indigo():
    rp = getInstallPath()
    if rp != "": return getInstallPath()

    return efutil.find_config_value('indigo', 'defaults', 'install_path', '')

@persistent
def indigo_scene_load_render_settings(context):
    ''' Prevent using the Indigo install dir from blend files if it doesn't exist on the local machine,
    also reset the output path if it doesn't exist on the local machine
    '''

    for s in bpy.data.scenes:
        # If the Indigo path in the scene doesn't exist.
        if not os.path.exists(s.indigo_engine.install_path):
            # Find Indigo.
            indigo_path = find_indigo()

            # If Indigo was found.
            if indigo_path != '' and os.path.exists(indigo_path):
                indigo.export.indigo_log("Scene '%s' Indigo install path was adjusted for local machine" % s.name)
                s.indigo_engine.install_path = indigo_path
            else:
                indigo.export.indigo_log("Failed %s to find Indigo installation" % s.name)

        # Get the output path for frame 1. s.render.filepath will return the raw
        # output path, potentially including # characters. s.render.frame_path(1)
        # handles # characters correctly. Not handling them correctly will result
        # in false positives for the output path adjusting.
        output_dir = os.path.dirname(s.render.frame_path(1))

        if not os.path.exists(output_dir):
            indigo.export.indigo_log("Scene '%s' output path was adjusted for local machine" % s.name)
            s.render.filepath = bpy.app.tempdir

if hasattr(bpy.app, 'handlers') and hasattr(bpy.app.handlers, 'load_post'):
    bpy.app.handlers.load_post.append(indigo_scene_load_render_settings)

def set_render_mode(self, context):
    if self.render_mode == 'bidir':
        self.bidir = True
        self.metro = False
        self.alpha_mask = False
        self.material_id = False
        self.gpu = False
        self.shadow = False
    if self.render_mode == 'bidir_mlt':
        self.bidir = True
        self.metro = True
        self.alpha_mask = False
        self.material_id = False
        self.gpu = False
        self.shadow = False
    if self.render_mode == 'path_cpu':
        self.bidir = False
        self.metro = False
        self.alpha_mask = False
        self.material_id = False
        self.gpu = False
        self.shadow = False
    if self.render_mode == 'path_gpu':
        self.bidir = False
        self.metro = False
        self.alpha_mask = False
        self.material_id = False
        self.gpu = True
        self.shadow = False
    if self.render_mode == 'alpha':
        self.bidir = False
        self.metro = False
        self.alpha_mask = True
        self.material_id = False
        self.gpu = False
        self.shadow = False
    if self.render_mode == 'material_id':
        self.bidir = False
        self.metro = False
        self.alpha_mask = False
        self.material_id = True
        self.gpu = False
        self.shadow = False
    if self.render_mode == 'shadow':
        self.bidir = False
        self.metro = False
        self.alpha_mask = False
        self.material_id = False
        self.gpu = False
        self.shadow = True

def set_filter_preset(self, context):
    if self.filter_preset == 'default':
        self.splat_filter = 'fastbox'
        self.ds_filter = 'mitchell'
        self.ds_filter_blur = 1.0
        self.ds_filter_ring = 0.0
        self.ds_filter_radius = 1.65
    if self.filter_preset == 'crisp':
        self.splat_filter = 'fastbox'
        self.ds_filter = 'mitchell'
        self.ds_filter_blur = 1/3
        self.ds_filter_ring = 1/3
        self.ds_filter_radius = 2.0
    if self.filter_preset == 'strong':
        self.splat_filter = 'radial'
        self.ds_filter = 'sharp'

@IndigoAddon.addon_register_class
class indigo_engine(declarative_property_group, indigo.export.xml_builder):
    ef_attach_to = ['Scene']

    # declarative_property_group members

    controls = [

        # Process options
        'use_output_path',
        'export_path',
        'install_path',
        'auto_start',
        ['threads_auto', 'threads'],

        # Output options

        ['save_igi', 'save_exr_tm', 'save_exr_utm'],
        ['ov_info', 'ov_watermark', 'logging'],
        ['halttime', 'haltspp'],
        'skip_existing_meshes',

        'period_save',

        # Render settings

        'motionblur',
        'glass_acceleration',

        'render_mode',

        'alpha_mask',
        'material_id',
        'metro',
        'bidir',
        #'hybrid'
        'gpu',
        'shadow',

        # Filtering

        'filter_preset',

        'splat_filter',
        ['splat_filter_blur', 'splat_filter_ring'],
        'ds_filter',
        ['ds_filter_blur', 'ds_filter_ring', 'ds_filter_radius'],
        ['supersample', 'bih_tri_threshold'],

        # Networking
        'network_mode',
        'network_host',
        'network_port',

        'console_output'
    ]

    visibility = {
        'alpha_mask':          { 'render_mode': 'custom' },
        'material_id':         { 'render_mode': 'custom' },
        'metro':               { 'render_mode': 'custom' },
        'bidir':               { 'render_mode': 'custom' },
        'gpu':                 { 'render_mode': 'custom' },
        'shadow':              { 'render_mode': 'custom' },

        'splat_filter':        { 'filter_preset': 'custom' },
        'ds_filter':           { 'filter_preset': 'custom' },
        'splat_filter_blur':   { 'filter_preset': 'custom', 'splat_filter': 'mitchell' },
        'splat_filter_ring':   { 'filter_preset': 'custom', 'splat_filter': 'mitchell' },
        'ds_filter_blur':      { 'filter_preset': 'custom', 'ds_filter': 'mitchell' },
        'ds_filter_ring':      { 'filter_preset': 'custom', 'ds_filter': 'mitchell' },
        'ds_filter_radius':    { 'filter_preset': 'custom', 'ds_filter': 'mitchell' },
        'supersample':         { 'filter_preset': 'custom' },
        'bih_tri_threshold':   { 'filter_preset': 'custom' },

        'network_host':        { 'network_mode': 'manual' },
        'network_port':        { 'network_mode': O(['master', 'working_master', 'manual']) },
    }

    enabled = {
        'threads':             { 'threads_auto': False },
        'export_path':         { 'use_output_path': False },
    }

    def set_export_console_output(self, context):
        indigo.export.PRINT_CONSOLE = self.console_output
        efutil.write_config_value('indigo', 'defaults', 'console_output', self.console_output)

    properties = [
        {
            'type': 'bool',
            'attr': 'use_output_path',
            'name': 'Use output directory for .igs files',
            'description': 'Use the directory specified under Output to write the scene files to. When disabled the .igs export path can be customised below',
            'default': True
        },
        {
            'type': 'string',
            'subtype': 'FILE_PATH',
            'attr': 'export_path',
            'name': 'Scene (.igs) export path',
            'description': 'Directory/name to save Indigo scene files. # characters define location and length of frame numbers',
            'default': bpy.app.tempdir
        },
        {
            'type': 'string',
            'subtype': 'DIR_PATH',
            'attr': 'install_path',
            'name': 'Path to Indigo installation',
            'description': 'Location of Indigo',
            'default': find_indigo()
        },
        {
            # Internal var use for regression testing
            'type': 'bool',
            'attr': 'wait_for_process',
            'default': False
        },
        {
            # Internal var use for regression testing
            'type': 'bool',
            'attr': 'use_console',
            'default': False
        },
        {
            # Internal var use for regression testing
            'type': 'bool',
            'attr': 'skip_version_check',
            'default': False
        },
        {
            'type': 'bool',
            'attr': 'auto_start',
            'name': 'Auto Start',
            'description': 'Auto start Indigo after export',
            'default': efutil.find_config_value('indigo', 'defaults', 'auto_start', True)
        },

        {
            'type': 'enum',
            'attr': 'render_mode',
            'name': 'Rendering Mode',
            'description': 'Choose the rendering mode to use',
            'items': [
                ('bidir', 'BiDir (CPU)', 'Bidirectional Path Tracing on the CPU'),
                ('bidir_mlt', 'BiDir MLT (CPU)', 'Bidirectional Path Tracing with Metropolis Light Transport on the CPU'),
                ('path_cpu', 'Path (CPU)', 'Path Tracing on the CPU'),
                ('path_gpu', 'Path (GPU)', 'GPU accelerated Path Tracing'),
                ('alpha', 'Alpha Mask', 'Render an alpha mask for compositing'),
                ('material_id', 'Material ID', 'Render materials as unique flat colours for compositing'),
                ('shadow', 'Shadow Pass', 'Render shadow pass for compositing'),
                ('custom', 'Custom', 'Choose your own settings')
            ],
            'default': 'bidir',
            'update': set_render_mode
        },

        {
            'type': 'bool',
            'attr': 'gpu',
            'name': 'GPU rendering',
            'description': 'Use the GPU to accelerate rendering',
            'default': False
        },
        {
            'type': 'bool',
            'attr': 'alpha_mask',
            'name': 'Alpha Mask',
            'description': 'Enable Alpha Mask Rendering',
            'default': False,
        },
        {
            'type': 'bool',
            'attr': 'material_id',
            'name': 'Material ID',
            'description': 'Enable Material ID Rendering',
            'default': False,
        },
        {
            'type': 'bool',
            'attr': 'metro',
            'name': 'Metropolis',
            'description': 'Enable Metropolis Light Transport',
            'default': False
        },
        {
            'type': 'bool',
            'attr': 'shadow',
            'name': 'Shadow Pass',
            'description': 'Enable Shadow Pass Rendering',
            'default': False
        },
        {
            'type': 'bool',
            'attr': 'bidir',
            'name': 'Bi-Directional',
            'description': 'Enable Bi-Directional Tracing',
            'default': True
        },
        {
            'type': 'bool',
            'attr': 'hybrid',
            'name': 'Hybrid',
            'description': 'Enable Hybrid Metropolis/Path',
            'default': False
        },
        {
            'type': 'bool',
            'attr': 'motionblur',
            'name': 'Motion Blur',
            'description': 'Enable Motion Blur',
            'default': False
        },
        {
            'type': 'bool',
            'attr': 'logging',
            'name': 'Logging',
            'description': 'Enable Logging to Text File',
            'default': False
        },
        {
            'type': 'bool',
            'attr': 'ov_info',
            'name': 'Info Overlay',
            'description': 'Enable Info Overlay on Render',
            'default': False
        },
        {
            'type': 'bool',
            'attr': 'ov_watermark',
            'name': 'Watermark',
            'description': 'Enable Indigo watermark on Render',
            'default': False
        },
        {
            'type': 'bool',
            'attr': 'threads_auto',
            'name': 'Auto Threads',
            'description': 'Let Indigo decide how many threads to use',
            'default': True
        },
        {
            'type': 'int',
            'attr': 'threads',
            'name': 'Render Threads',
            'description': 'Number of threads to use',
            'default': 1,
            'min': 1,
            'soft_min': 1,
            'max': 64,
            'soft_max': 64
        },
        {
            'type': 'bool',
            'attr': 'save_exr_utm',
            'name': 'Save Raw EXR',
            'description': 'Save Raw (un-tonemapped) EXR format',
            'default': False
        },
        {
            'type': 'bool',
            'attr': 'save_exr_tm',
            'name': 'Save EXR',
            'description': 'Save (tonemapped) EXR format',
            'default': False
        },
        {
            'type': 'bool',
            'attr': 'save_igi',
            'name': 'Save IGI',
            'description': 'Save native IGI format',
            'default': False
        },
        {
            'type': 'int',
            'attr': 'halttime',
            'name': 'Halt Time',
            'description': 'Number of seconds to run rendering (-1 == disable)',
            'default': -1,
            'min': -1,
            'soft_min': -1,
            'max': 86400,
            'soft_max': 86400
        },
        {
            'type': 'int',
            'attr': 'haltspp',
            'name': 'Halt Samples/px',
            'description': 'Number of samples/px to run rendering (-1 == disable)',
            'default': -1,
            'min': -1,
            'soft_min': -1,
            'max': 64000,
            'soft_max': 64000
        },
        {
            'type': 'bool',
            'attr': 'skip_existing_meshes',
            'name': 'Skip writing existing meshes',
            'default': False,
        },
        {
            'type': 'int',
            'attr': 'period_save',
            'name': 'Save interval',
            'description': 'Number of seconds to save output',
            'default': 60,
            'min': 20,
            'soft_min': 20,
            'max': 86400,
            'soft_max': 86400
        },
        {
            'type': 'bool',
            'attr': 'glass_acceleration',
            'name': 'Glass Acceleration',
            'default': False,
        },
        {
            'type': 'enum',
            'attr': 'filter_preset',
            'name': 'Filtering',
            'description': 'Filtering methods to use; affects image sharpness',
            'items': [
                ('default', 'Default', 'Prevents black edges, good overall performance - Splat: fastbox; Downsize: mn_cubic'),
                ('crisp', 'Crisp', 'Splat: fastbox; Downsize: mn_cubic'),
                ('strong', 'Strong', 'Splat: radial; Downsize: sharp'),
                ('custom', 'Custom', 'Choose your own settings')
            ],
            'default': 'default',
            'update': set_filter_preset
        },
        {
            'type': 'enum',
            'attr': 'splat_filter',
            'name': 'Splat',
            'description': 'Splat Filter Type',
            'default': 'fastbox',
            'items': [
                ('mitchell', 'Mitchell-Netraveli', 'mitchell'),
                ('gaussian', 'Gaussian', 'gaussian'),
                ('box', 'Box', 'box'),
                ('fastbox', 'Fast Box', 'fastbox'),
                ('radial', 'Radial', 'radial'),
                # ('sharp', 'Sharp', 'sharp')
            ]
        },
        {
            'type': 'float',
            'attr': 'splat_filter_blur',
            'name': 'Splat Blur',
            'description': 'Splat Mitchell Filter Blur Amount',
            'default': 1.0,
            'min': 0,
            'soft_min': 0,
            'max': 1,
            'soft_max': 1,
        },
        {
            'type': 'float',
            'attr': 'splat_filter_ring',
            'name': 'Splat Ring',
            'description': 'Splat Mitchell Filter Ring Amount',
            'default': 0.0,
            'min': 0,
            'soft_min': 0,
            'max': 1,
            'soft_max': 1,
        },
        {
            'type': 'enum',
            'attr': 'ds_filter',
            'name': 'Downsize',
            'description': 'Downsize Filter Type',
            'default': 'mitchell',
            'items': [
                ('mitchell', 'Mitchell-Netraveli', 'mitchell'),
                ('gaussian', 'Gaussian', 'gaussian'),
                ('box', 'Box', 'box'),
                ('radial', 'Radial', 'radial'),
                ('sharp', 'Sharp', 'sharp')
            ]
        },
        {
            'type': 'float',
            'attr': 'ds_filter_blur',
            'name': 'Downsize Blur',
            'description': 'Downsize Mitchell Filter Blur Amount',
            'default': 1.0,
            'min': 0,
            'soft_min': 0,
            'max': 1,
            'soft_max': 1,
        },
        {
            'type': 'float',
            'attr': 'ds_filter_ring',
            'name': 'Downsize Ring',
            'description': 'Downsize Mitchell Filter Ring Amount',
            'default': 0.0,
            'min': 0,
            'soft_min': 0,
            'max': 1,
            'soft_max': 1,
        },
        {
            'type': 'float',
            'attr': 'ds_filter_radius',
            'name': 'Downsize Radius',
            'description': 'Downsize Mitchell Filter Radius Amount',
            'default': 1.65,
            'min': 1,
            'soft_min': 1,
            'max': 3,
            'soft_max': 3,
        },
        {
            'type': 'int',
            'attr': 'supersample',
            'name': 'Supersamples',
            'description': 'x Oversampling',
            'default': 2,
            'min': 1,
            'soft_min': 1,
            'max': 4,
            'soft_max': 4,
        },
        {
            'type': 'int',
            'attr': 'bih_tri_threshold',
            'name': 'BIH Tri Threshold',
            'description': 'BIH Tri Threshold',
            'default': 1100000,
            'min': 1,
            'soft_min': 1,
            'max': 10000000,
            'soft_max': 10000000,
        },
        {
            'type': 'enum',
            'attr': 'network_mode',
            'name': 'Network mode',
            'default': 'off',
            'items': [
                ('off', 'Off', 'Do not use networking'),
                ('master', 'Master', 'Start Indigo as a Master node (doesn\'t render)'),
                ('working_master', 'Working Master', 'Start Indigo as a Working Master node'),
                # ('manual', 'Manual', 'Connect manually to a running slave')
            ]
        },
        {
            'type': 'string',
            'attr': 'network_host',
            'name': 'Slave IP/hostname',
            'description': 'IP address or hostname of running slave'
        },
        {
            'type': 'int',
            'attr': 'network_port',
            'name': 'Network port',
            'description': 'Network render port use',
            'default': 7100,
            'min': 1025,
            'soft_min': 1025,
            'max': 32768,
            'soft_max': 32768
        },
        {
            'type': 'bool',
            'attr': 'console_output',
            'name': 'Print export progress to console',
            'default': efutil.find_config_value('indigo', 'defaults', 'console_output', False),
            'update': set_export_console_output
        },
    ]

    # xml_builder members

    def build_xml_element(self, scene):
        xml = self.Element('scene')
        xres = scene.render.resolution_x * scene.render.resolution_percentage // 100
        yres = scene.render.resolution_y * scene.render.resolution_percentage // 100
        xml_format = {
            'metadata' : {
                'created_date':    [time.strftime('%Y-%m-%d %H:%M:%S GMT', time.gmtime())],
                'exporter':        ['Blendigo ' + '.'.join(['%i'%v for v in bl_info['version']])],
                'platform':        ['%s - %s - Python %s' % (PlatformInformation.platform_id, PlatformInformation.uname, PlatformInformation.python)],
                'author':        [PlatformInformation.user],
            },
            'renderer_settings': {
                'width':  [xres],
                'height': [yres],
                'bih_tri_threshold': 'bih_tri_threshold',
                'metropolis': 'metro',

                'logging': 'logging',
                'bidirectional': 'bidir',
                'save_untonemapped_exr': 'save_exr_utm',
                'save_tonemapped_exr': 'save_exr_tm',
                'save_igi': 'save_igi',
                'image_save_period': 'period_save',
                'halt_time': 'halttime',
                'halt_samples_per_pixel': 'haltspp',
                'hybrid': 'hybrid',

                'super_sample_factor': 'supersample',
                'watermark': 'ov_watermark',
                'info_overlay': 'ov_info',

                'aperture_diffraction': [str(scene.camera.data.indigo_camera.ad).lower()],
                'vignetting': [str(scene.camera.data.indigo_camera.vignetting).lower()],
                'post_process_diffraction': [str(scene.camera.data.indigo_camera.ad_post).lower()],
                'render_foreground_alpha': 'alpha_mask',
                'material_id_tracer': 'material_id',
                'shadow_pass': 'shadow',

                'gpu': 'gpu'
            },
        }

        # Auto threads setting
        xml_format['renderer_settings']['auto_choose_num_threads'] = 'threads_auto'
        if not self.threads_auto:
            xml_format['renderer_settings']['num_threads'] = 'threads'

        if self.bidir and self.glass_acceleration:
            xml_format['renderer_settings']['glass_acceleration'] = ['true']

        # Make splat filter element
        if self.splat_filter in ['box', 'gaussian', 'fastbox']:
            xml_format['renderer_settings']['splat_filter'] = { self.splat_filter: '' } # generate an empty element
        elif self.splat_filter == 'mitchell':
            xml_format['renderer_settings']['splat_filter'] = {
                'mn_cubic': {
                    'blur': 'splat_filter_blur',
                    'ring': 'splat_filter_ring'
                }
            }

        # Make downsize filter element
        if self.ds_filter in ['box', 'gaussian']:
            xml_format['renderer_settings']['downsize_filter'] = { self.ds_filter: '' } # generate an empty element
        elif self.ds_filter == 'mitchell':
            xml_format['renderer_settings']['downsize_filter'] = {
                'mn_cubic': {
                    'blur': 'ds_filter_blur',
                    'ring': 'ds_filter_ring',
                    'radius': 'ds_filter_radius'
                }
            }

        # Region rendering
        if scene.render.use_border:
            x1 = int(xres*scene.render.border_min_x)
            y1 = int(yres-(yres*scene.render.border_max_y))
            x2 = int(xres*scene.render.border_max_x)
            y2 = int(yres-(yres*scene.render.border_min_y))
            xml_format['renderer_settings']['render_region'] = {
                'x1': [x1],
                'x2': [x2],
                'y1': [y1],
                'y2': [y2]
            }

        self.build_subelements(scene, xml_format, xml)

        return xml
