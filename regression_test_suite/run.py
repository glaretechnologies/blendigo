#
# Blendigo 2.5 Regression Testing Suite
#
import os, subprocess, shutil, time
from pypng import png

BLENDER_BINARY = r'C:\Program Files\Blender Foundation\Blender\blender.exe'
INDIGO_PATH = r'C:\programming\indigo_installs\Indigo Renderer 3.4.4\\'

def regression_test(filter_list=None, BLENDIGO_VERSION='0.0.0'):
	output_log = []
	failure_count = 0
	
	regression_scenes  = sorted([f for f in os.listdir('./scenes/') if f.endswith('.blend')])
	
	if filter_list!=None:
		regression_scenes = [s for s in filter(lambda x: x[:-6] in filter_list, regression_scenes)]
	
	regression_names   = [os.path.splitext(f)[0] for f in regression_scenes]
	
	# turn off verbose exporting
	if 'B25_OBJECT_ANALYSIS' in os.environ.keys():
		del os.environ['B25_OBJECT_ANALYSIS']
	
	test_sep = '*'*80
	
	test_results = {}
	test_times = {}
	
	for i in range(len(regression_scenes)):
		test_start = time.time()
		scene  = './scenes/%s' % regression_scenes[i]
		name   = regression_names[i]
		
		print(test_sep)
		print('Test: %s' % name)
		
		# clean the output location
		output_path = os.path.realpath('./outputs/%s/' % name)
		try:
			shutil.rmtree(output_path)
		except: pass
		
		try:
			# run blender
			args = [BLENDER_BINARY, '-noaudio']
			args.extend(['-b',scene])
			args.extend(['-P', 'scene_script.py'])
			args.append('--')
			args.append('--output-path=%s' % output_path)
			args.append('--install-path=%s' % INDIGO_PATH)
			args.append('--test-name=%s' % name)
			args.append('--blendigo-version=%s' % BLENDIGO_VERSION)
			
			exit_code = subprocess.call(args, env=os.environ)
			
			if exit_code < 0:
				raise Exception('process error!')
			
			tst_file_name = './outputs/%s/%s.png' % (name, name)
			
			if not os.path.exists(tst_file_name):
				raise Exception('no output image!')
				
			# perform image analysis!
			
			ref_file = png.Reader('./references/%s.png' % name)
			tst_file = png.Reader(tst_file_name)
			
			ref_data = ref_file.asRGB()
			tst_data = tst_file.asRGB()
			
			if ref_data[0]!=tst_data[0] or ref_data[1]!=tst_data[1]:
				raise Exception('output images size mismatch!')
			
			ref_rgb = ref_data[2]
			tst_rgb = tst_data[2]
			
			sum_sqr_err = 0
			px_count = 0
			for ref_row, tst_row in zip(ref_rgb, tst_rgb):
				for col in range(ref_file.width):
					err = tst_row[col] - ref_row[col]
					sum_sqr_err += (err*err)
					px_count += 1
			MSE = sum_sqr_err/px_count
			if MSE > 1.0:
				MSE_msg = '****** HIGH VALUE ******'
				failure_count += 1
			else:
				MSE_msg = ''
				
			test_results[name] = 'MSE = %0.4f  %s' % (MSE, MSE_msg)
		
		except Exception as err:
			test_results[name] = 'FAILED: %s' % err
			failure_count += 1
		
		print('Test: %s completed' % name)
		print(test_sep)
		print('\n')
		
		test_end = time.time()
		test_times[name] = test_end-test_start
	
	output_log.append('All Tests complete!\n')
	output_log.append('\n%-30s %-12s %s' % ('Test', 'Time', 'Result'))
	output_log.append(test_sep)
	for test_name in sorted(test_results.keys()):
		output_log.append('%-30s %-12s %s' % (test_name, '%0.2f sec'%test_times[test_name], test_results[test_name]))
	output_log.append(test_sep)
	
	return output_log, failure_count

if __name__ == "__main__":
	import sys
	filter_list = None
	if len(sys.argv) > 1:
		filter_list = sys.argv[1:]
	
	addon_path = os.path.realpath( os.getcwd()+r'\..\sources')
	sys.path.append(addon_path)
	os.environ['BLENDIGO_RELEASE'] = 'TRUE'
	
	from indigo import bl_info
	TAG = '.'.join(['%i'%i for i in bl_info['version']])
	
	del os.environ['BLENDIGO_RELEASE']
	
	log_lines, failure_count = regression_test(filter_list, TAG)
	for log_line in log_lines:
		print(log_line)
