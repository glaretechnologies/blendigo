# Copies Windows installer file to office.glaretechnologies.com (buildbox) so it can be bundled with windows build.
#
# Copyright Glare Technologies Limited 2017 -

import os, subprocess, sys, time


if(len(sys.argv) >= 2):
	SERVER_USER = sys.argv[1]
else:
	SERVER_USER = os.environ['USERNAME']


addon_path = os.path.realpath( os.getcwd()+r'\..\sources')
sys.path.append(addon_path)
os.environ['BLENDIGO_RELEASE'] = 'TRUE'
		
from indigo import bl_info
		
TAG			= '.'.join(['%i'%i for i in bl_info['version']])
BL_VERSION	= '.'.join(['%i'%i for i in bl_info['blender']])

ZIP_NAME = "blendigo-%s.zip" % TAG

INSTALLER_NAME = "blendigo-%s-installer.exe" % TAG

server = "office.glaretechnologies.com"
port = os.environ['OFFICE_GLARE_TECH_SSH_PORT']
command = "pscp -P %(PORT)s ./installer_windows/%(IN)s %(UN)s@%(server)s:/var/indigo_exporters/blender" % {'PORT': port, 'IN': INSTALLER_NAME, 'UN':SERVER_USER, 'server' : server}
print(command)
subprocess.call(command)
