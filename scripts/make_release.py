if __name__ == '__main__':
	
	try:
		import os, subprocess, sys
		
		if len(sys.argv) < 2:
			raise Exception('Not enough args, need server upload username')
		
		SERVER_USER = sys.argv[1]
		
		addon_path = os.path.realpath( os.getcwd()+r'\..\sources')
		sys.path.append(addon_path)
		os.environ['BLENDIGO_RELEASE'] = 'TRUE'
		
		from indigo import bl_info
		
		TAG			= '.'.join(['%i'%i for i in bl_info['version']])
		BL_VERSION	= '.'.join(['%i'%i for i in bl_info['blender']])
		
		ZIP_NAME = "blendigo-2.6-%s.zip" % TAG
		
		cwd = os.getcwd()
		
		# package the tagged version
		from make_addon import make_addon
		make_addon(ZIP_NAME, TAG)
		
		# Make windows installer
		os.environ['BLENDIGO_VERSION'] = TAG

		# Make a Blender version string string like "2.68"
		# This controls where the installed indigo files go in the blender program files dir.
		os.environ['BLENDER_VERSION'] = str(bl_info['blender'][0]) + "." + str(bl_info['blender'][1]) + str(bl_info['blender'][2])
		INSTALLER_NAME = "blendigo-2.6-%s-installer.exe" % TAG
		os.chdir('./installer_windows')
		subprocess.call("makensis /V2 blendigo-25.nsi")
		os.chdir(cwd)
		del os.environ['BLENDIGO_VERSION']
		del os.environ['BLENDER_VERSION']
		
		if os.path.exists(ZIP_NAME):
			server = "downloads.indigorenderer.com"
			
			subprocess.call("pscp %(ZN)s %(UN)s@%(server)s:/var/www/dl-indigorenderer.com/dist/exporters/blendigo" % {'ZN':ZIP_NAME, 'UN':SERVER_USER, 'UP': os.environ['USERPROFILE'], 'server' : server})
			subprocess.call("pscp installer_windows\%(IN)s %(UN)s@%(server)s:/var/www/dl-indigorenderer.com/dist/exporters/blendigo" % {'IN': INSTALLER_NAME, 'UN':SERVER_USER, 'UP': os.environ['USERPROFILE'], 'server' : server})
			
			#from send_release_email import send_release_email
			#DIST_URL = "http://www.indigorenderer.com/dist/exporters/blendigo/"
			#send_release_email(
			#	TAG,
			#	"%(DU)s%(ZN)s\n%(DU)s%(IN)s" % { 'DU': DIST_URL, 'ZN': ZIP_NAME, 'IN': INSTALLER_NAME},
			#	BL_VERSION,
			#	rt_log
			#)
		else:
			print("%s was not created, cannot upload!" % ZIP_NAME)
	
	except Exception as err:
		print('Release aborted: %s' % err)