import datetime, os, sys, zipfile

def make_addon(zip_name, zip_ver):
	try:
		print("Packing Blendigo addon to %s" % zip_name)
		
		with zipfile.ZipFile(zip_name, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
			# Write an info meta file
			zf.writestr('indigo_release.txt', ('Blendigo v%s; packaged %s' % (zip_ver, str(datetime.datetime.now()))).encode())
		
			for addon_files in os.walk('../sources', True):
				a_path, a_dirs, a_files = addon_files
				for a_file in a_files:
					if a_file[-3:].lower() == '.py':
						py_file_full = os.path.join(a_path, a_file)
						py_file = py_file_full[11:]
						print('Adding %s' % py_file_full)
						zf.write(py_file_full, arcname=py_file)
	
	except Exception as err:
		print("ERROR: %s" % err)
		sys.exit(-1)
		
if __name__ == "__main__":
	try:
		if len(sys.argv) < 3:
			raise Exception('Not enough args, need .zip file name and version number')
		
		zip_name = sys.argv[1]
		zip_ver = sys.argv[2]
		
		make_addon(zip_name, zip_ver)
	
	except Exception as err:
		print("ERROR: %s" % err)
		sys.exit(-1)