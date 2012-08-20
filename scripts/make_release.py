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
		
		# update code to tagged version
		#subprocess.call("hg update -r %s" % TAG)
		
		# run regression test
		# del os.environ['BLENDIGO_RELEASE']
		# rt_path = os.path.realpath( os.getcwd()+r'\..\..\blendigo-2.5-regressiontest')
		# sys.path.append(rt_path)
		cwd = os.getcwd()
		# os.chdir(rt_path)
		# from run import regression_test
		# output_log, failure_count = regression_test(None, TAG)
		# os.chdir(cwd)
		# rt_log = '\n'.join(output_log)
		# print(rt_log)
		# if failure_count > 0:
			# raise Exception('%i regression tests failed, or had high MSE values' % failure_count)
		
		# package the tagged version
		from make_addon import make_addon
		make_addon(ZIP_NAME, TAG)
		
		# Make windows installer
		os.environ['BLENDIGO_VERSION'] = TAG
		os.environ['BLENDER_VERSION'] = '%i.%i%i' % bl_info['blender']
		INSTALLER_NAME = "blendigo-2.6-%s-installer.exe" % TAG
		os.chdir('./installer_windows')
		subprocess.call("makensis blendigo-25.nsi")
		os.chdir(cwd)
		del os.environ['BLENDIGO_VERSION']
		del os.environ['BLENDER_VERSION']
		
		if os.path.exists(ZIP_NAME):
			# use 3rd argument as debug switch; prevents upload and emails
			# upload the release and notify via email
			#subprocess.call("pscp -i \"%(UP)s/.ssh/id_rsa.ppk\" %(ZN)s %(UN)s@indigorenderer.com:/home/%(UN)s/blendigo" % {'ZN':ZIP_NAME, 'UN':SERVER_USER, 'UP': os.environ['USERPROFILE']})
			#subprocess.call("pscp -i \"%(UP)s/.ssh/id_rsa.ppk\" installer_windows\%(IN)s %(UN)s@indigorenderer.com:/home/%(UN)s/blendigo" % {'IN': INSTALLER_NAME, 'UN':SERVER_USER, 'UP': os.environ['USERPROFILE']})
			#subprocess.call("pscp %(ZN)s %(UN)s@indigorenderer.com:/home/%(UN)s/blendigo" % {'ZN':ZIP_NAME, 'UN':SERVER_USER, 'UP': os.environ['USERPROFILE']})
			#subprocess.call("pscp installer_windows\%(IN)s %(UN)s@indigorenderer.com:/home/%(UN)s/blendigo" % {'IN': INSTALLER_NAME, 'UN':SERVER_USER, 'UP': os.environ['USERPROFILE']})
			
			subprocess.call("pscp %(ZN)s %(UN)s@indigorenderer.com:/var/www/indigorenderer.com/dist/exporters/blendigo" % {'ZN':ZIP_NAME, 'UN':SERVER_USER, 'UP': os.environ['USERPROFILE']})
			subprocess.call("pscp installer_windows\%(IN)s %(UN)s@indigorenderer.com:/var/www/indigorenderer.com/dist/exporters/blendigo" % {'IN': INSTALLER_NAME, 'UN':SERVER_USER, 'UP': os.environ['USERPROFILE']})
			
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
	
	#finally:
		# update to current revision
		#subprocess.call("hg update")
