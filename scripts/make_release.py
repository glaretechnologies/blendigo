import os, subprocess, sys, time

# Sign the windows installer with the Glare tech code signing key
def signProgram(app_name, exe_path):
	
	max_retries = 3
	
	# v7.0A does not come with vs 2008
	#signtool_path = 'C:/Program Files (x86)/Microsoft SDKs/Windows/v7.0A/Bin/signtool.exe'
	signtool_path = "C:/Program Files (x86)/Microsoft SDKs/Windows/v7.1A/Bin/signtool.exe"
	#signtool_path = 'C:/Program Files/Microsoft SDKs/Windows/v6.0A/Bin/signtool.exe'
	command = "\"" + signtool_path + "\" sign /f " + os.environ['INDIGO_TRUNK_DIR'] + "/code_signing/Glare-Technologies-Limited-Glare.p12 /p " + os.environ['GLARE_CODE_SIGNING_PASSWORD'] + " /d \"" + app_name + "\" /du http://www.indigorenderer.com /t http://tsa.starfieldtech.com \"" + exe_path + "\""

	num_retries = 0
	while(num_retries < max_retries):
		print(command)
		if(subprocess.call(command) == 0):
			break

		num_retries += 1
		time.sleep(1.0)

	if(num_retries >= max_retries):
		print("Signing failed after some attempts, giving up")
		exit(1) # Fail


if __name__ == '__main__':
	
	try:
		if len(sys.argv) < 2:
			raise Exception('Not enough args, need server upload username')
		
		SERVER_USER = sys.argv[1]
		
		addon_path = os.path.realpath( os.getcwd()+r'\..\sources')
		sys.path.append(addon_path)
		os.environ['BLENDIGO_RELEASE'] = 'TRUE'
		
		# Import blender module init.py to get version.
		# Since it depends on pby, we loat the script and execute it,
		# ignoring all errors, to get the bl_info obj.
		try:
			exec(open("../sources/indigo_exporter/__init__.py").read())
		except ImportError: pass
		
		TAG			= '.'.join(['%i'%i for i in bl_info['version']])
		BL_VERSION	= '.'.join(['%i'%i for i in bl_info['blender']])
		print("BL_VERSION: " + BL_VERSION);
		
		proc = subprocess.Popen('git log --pretty=format:%h -n 1 ..', stdout=subprocess.PIPE)
		HASH, errs = proc.communicate()
		print("HASH: " + HASH);

		BRANCH = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).strip()
		print("BRANCH: " + BRANCH);
		
		ZIP_NAME = "blendigo-%s-%s-%s.zip" % (TAG, HASH, BRANCH)
		
		cwd = os.getcwd()
		
		# package the tagged version
		from make_addon import make_addon
		make_addon(ZIP_NAME, TAG)
		
		# Make windows installer
		os.environ['BLENDIGO_VERSION'] = TAG
		os.environ['BLENDIGO_COMMIT_HASH'] = HASH
		os.environ['BLENDIGO_BRANCH'] = BRANCH

		# Make a Blender version string string like "2.68"
		# This controls where the installed indigo files go in the blender program files dir.
		os.environ['BLENDER_VERSION'] = str(bl_info['blender'][0]) + "." + str(bl_info['blender'][1]) + str(bl_info['blender'][2])
		INSTALLER_NAME = "blendigo-%s-%s-%s-installer.exe" % (TAG, HASH, BRANCH)

		print("Making Windows installer ./installer_windows/" + INSTALLER_NAME + "...");

		os.chdir('./installer_windows')
		subprocess.call("makensis /V2 blendigo-25.nsi")
		os.chdir(cwd)
		del os.environ['BLENDIGO_VERSION']
		del os.environ['BLENDER_VERSION']
		del os.environ['BLENDIGO_COMMIT_HASH']
		del os.environ['BLENDIGO_BRANCH']

		signProgram("Blendigo " + TAG, './installer_windows/' + INSTALLER_NAME)
		
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