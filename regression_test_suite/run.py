#
# Blendigo 2.5 Regression Testing Suite
#
# INFO:
# The easiest way to run this script is in Blender's Text Editor or run runme.py in command line instead. report.html and results.txt will be created in outputs directory
# set path to Indigo Test Suite folder

import os
INDIGO_TEST_SUITE = os.path.split(__file__)[0]

import os, subprocess, shutil, time, glob
from pypng import png

import bpy
from indigo_exporter.core import getConsolePath
BLENDER_BINARY = os.path.join(bpy.utils.script_paths()[0].split(os.sep)[0]+os.sep, *bpy.utils.script_paths()[0].split(os.sep)[1:-3], 'blender.exe')
INDIGO_PATH = os.path.split(getConsolePath())[0]

def image_analysis(ref_file, tst_file):
    ref_data = ref_file.asRGBA()
    tst_data = tst_file.asRGBA()
    
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
    return sum_sqr_err/px_count

def regression_test(filter_list=None, BLENDIGO_VERSION='0.0.0'):
    output_log = []
    failure_count = 0
    regression_scenes = sorted([f for f in os.listdir(os.path.join(INDIGO_TEST_SUITE, 'scenes')) if f.endswith('.blend')])
    if filter_list!=None and len(filter_list):
        regression_scenes = [s for s in filter(lambda x: x[:-6] in filter_list, regression_scenes)]
    regression_names = [os.path.splitext(f)[0] for f in regression_scenes]
    
    # turn off verbose exporting
    if 'B25_OBJECT_ANALYSIS' in os.environ.keys():
        del os.environ['B25_OBJECT_ANALYSIS']
    
    test_sep = '*'*80
    
    test_results = {}
    test_times = {}
    
    for i in range(len(regression_scenes)):
        test_start = time.time()
        scene  = os.path.join(INDIGO_TEST_SUITE, 'scenes', '%s' % regression_scenes[i])
        name   = regression_names[i]
        
        print(test_sep)
        print('Test: %s' % name)
        
        # clean the output location
        output_path = os.path.join(INDIGO_TEST_SUITE, 'outputs', '%s' % name)
        try:
            shutil.rmtree(output_path)
        except: pass
        
        try:
            # run blender
            args = [BLENDER_BINARY, '-noaudio']
            args.extend(['-b',scene])
            args.extend(['-P', os.path.join(INDIGO_TEST_SUITE, 'scene_script.py')])
            args.append('--')
            args.append('--output-path=%s' % output_path)
            args.append('--install-path=%s' % INDIGO_PATH)
            args.append('--test-name=%s' % name)
            args.append('--blendigo-version=%s' % BLENDIGO_VERSION)
            exit_code = subprocess.call(args, env=os.environ)
            
            if exit_code < 0:
                raise Exception('process error!')
            
            #tst_file_name = os.path.join(INDIGO_TEST_SUITE, 'outputs', '%s/%s.png' % (name, name))
            tst_file_name = [f for f in os.listdir(os.path.join(INDIGO_TEST_SUITE, 'outputs')) if f.startswith(name) and f.endswith('.png')].pop()
            tst_file_path = os.path.join(INDIGO_TEST_SUITE, 'outputs', tst_file_name)
            
            if not os.path.exists(tst_file_path):
                raise Exception('no output image!')
                
            # perform image analysis!
            
            ref_file = png.Reader(os.path.join(INDIGO_TEST_SUITE, 'references', '%s.png' % name))
            tst_file = png.Reader(tst_file_path)
            MSE = image_analysis(ref_file, tst_file)
            if MSE > 1.0:
                MSE_msg = '****** HIGH VALUE ******'
                failure_count += 1
            else:
                MSE_msg = 'OK'
                
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
    
    return output_log, failure_count, test_results, test_times


html_template="""
<html>
<head>
<title>
    Blendigo Test Suite Report
</title>
<style>
    body{{
        width: 1000px;
        margin: auto;
    }}
    .container{{
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        padding: 20px;
    }}
    .container.faulty-True{{
        background-color: orangered;
    }}
    .caption{{
        width: 100%;
    }}
    .left{{
        float: left;
    }}
    .right{{
        float: right;
    }}
    .hide{{
        display: none;
    }}
    label{{
        margin: 1rem;
    }}
</style>
</head>
<body>
<span>Blendigo Version: {ver}</span>
<div>
<label><input id="check" type="checkbox" checked onclick="
if(this.checked){{
    for(const val of document.getElementsByClassName('faulty-False'))
        val.classList.remove('hide');
}}else{{
    for(const val of document.getElementsByClassName('faulty-False'))
        val.classList.add('hide');
}}
">Passed</label>

<label><input id="check" type="checkbox" checked onclick="
if(this.checked){{
    for(const val of document.getElementsByClassName('faulty-True'))
        val.classList.remove('hide');
}}else{{
    for(const val of document.getElementsByClassName('faulty-True'))
        val.classList.add('hide');
}}
">Faulty</label>
</div>
{pairs}
</body>
</html>
"""

pair_template="""
<div class="container faulty-{faulty}">
    <div class="caption">
        <span class="left">{test_name}</span>
        <span class="right">{test_result}</span>
    </div>
    <img src="../references/{reference_file}"><img src="{out_file}">
</div>
"""

textcase_template="""
<div class="container faulty-{faulty}">
    <div class="caption">
        <span class="left">{test_name}</span>
        <span class="right">{test_result}</span>
    </div>
</div>
"""

def additional_tests():
    test_dict = {
        "multifile_animation": test_multifile_animation
    }
    output_log=[]
    test_results={}
    for t in test_dict.items():
        if not filter_list or t[0] in filter_list:
            output_log1, test_results1 = t[1]()
            output_log.extend(output_log1)
            test_results.update(test_results1)

    return output_log, test_results

def test_multifile_animation(BLENDIGO_VERSION='0.0.0'):
    # additional non-standardized tests

    # use one of the test scenes to check multi-file export options
    output_log = []
    
    # turn off verbose exporting
    if 'B25_OBJECT_ANALYSIS' in os.environ.keys():
        del os.environ['B25_OBJECT_ANALYSIS']
    
    test_sep = '*'*80
    
    test_results = {}

    scene  = os.path.join(INDIGO_TEST_SUITE, 'scenes', 'multifile', 'multifile.blend')
    name   = "multifile_export"
    
    print(test_sep)
    print('Additional tests')
    print('Test: multi-file export')
    
    # clean the output location
    output_path = os.path.join(INDIGO_TEST_SUITE, 'outputs', 'multifile', 'multifile')
    try:
        shutil.rmtree(output_path)
    except: pass
    
    try:
        # run blender
        args = [BLENDER_BINARY, '-noaudio']
        args.extend(['-b',scene])
        args.extend(['-P', os.path.join(INDIGO_TEST_SUITE, 'scene_multifile.py')])
        args.append('--')
        args.append('--output-path=%s' % output_path)
        args.append('--install-path=%s' % INDIGO_PATH)
        args.append('--test-name=%s' % name)
        args.append('--blendigo-version=%s' % BLENDIGO_VERSION)
        exit_code = subprocess.call(args, env=os.environ)
        
        if exit_code < 0:
            raise Exception('process error!')

        ####
        tst_file_names = [f for f in os.listdir(os.path.join(INDIGO_TEST_SUITE, 'outputs', 'multifile'))]
        # tst_file_name = glob.glob(os.path.join(INDIGO_TEST_SUITE, 'outputs', 'multifile', test_name+"*"))

        reference_filenames = [
        # 'multifile.Scene.00189.igs',
        # 'multifile.Scene.00190.igs',
        # 'multifile0189.igi',
        'multifile0189.png',
        'multifile0189_channels.exr',
        'multifile0189_tonemapped.exr',
        'multifile0189_untonemapped.exr',
        # 'multifile0190.igi',
        'multifile0190.png',
        'multifile0190_channels.exr',
        'multifile0190_tonemapped.exr',
        'multifile0190_untonemapped.exr',
        ]

        for name in reference_filenames:
            if name in tst_file_names:
                test_results[name] = "OK"
            else:
                test_results[name] = "FAILED"
        
        # check igi files exported with timestamp in filename
        import re
        refstr = ' '.join(reference_filenames)
        if re.search('multifile0189_\d+\.igi', refstr):
            test_results[r'multifile0189_\d+\.igi'] = "OK"
        else:
            test_results[r'multifile0189_\d+\.igi'] = "FAILED"

        if re.search('multifile0190_\d+\.igi', refstr):
            test_results[r'multifile0190_\d+\.igi'] = "OK"
        else:
            test_results[r'multifile0190_\d+\.igi'] = "FAILED"
    
    except Exception as err:
        test_results[name] = 'FAILED: %s' % err
    
    print('Test: %s completed' % name)
    print(test_sep)
    print('\n')
    
    
    output_log.append('All Tests complete!\n')
    output_log.append(test_sep)
    for test_name in sorted(test_results.keys()):
        output_log.append('%-30s %s' % (test_name, test_results[test_name]))
    output_log.append(test_sep)
    
    return output_log, test_results


if __name__ == "__main__":
    import sys
    # Skip argv prior to and including '--'
    filter_list = None
    parse_args = sys.argv[sys.argv.index('--')+1:]
    if len(parse_args) > 0:
        INDIGO_TEST_SUITE = parse_args[0].split('=')[1]
        filter_list = parse_args[1:]
        print(filter_list)
    
    addon_path = os.path.join(INDIGO_TEST_SUITE, '..', 'sources')
    sys.path.append(addon_path)
    os.environ['BLENDIGO_RELEASE'] = 'TRUE'
    
    from indigo_exporter import bl_info
    TAG = '.'.join(['%i'%i for i in bl_info['version']])
    
    del os.environ['BLENDIGO_RELEASE']
    
    print('\n\n\n* Test Started *\n\n\n')
    log_lines, failure_count, test_results, test_times = regression_test(filter_list, TAG)
        
    additional_output_log, additional_test_results = additional_tests()

    with open(os.path.join(INDIGO_TEST_SUITE, 'outputs','results.txt'), 'w') as file:
        for log_line in log_lines:
            print(log_line)
            file.write('\n'+log_line)
        file.write('\n'*2 + '\nFailures: '+str(failure_count))

        for log_line in additional_output_log:
            print(log_line)
            file.write('\n'+log_line)

        file.write('\nBlendigo Version: '+TAG)
        
        
    with open(os.path.join(INDIGO_TEST_SUITE, 'outputs','report.html'), 'w') as file:
        cases = []
        for test_name in test_results.keys():
            reference_file = test_name+".png"
            gr = glob.glob(os.path.join(INDIGO_TEST_SUITE, 'outputs', test_name+"*.png"))
            out_file = gr[0] if len(gr) else 'not_found.png'
            
            cases.append(pair_template.format(
                test_name=test_name,
                reference_file=reference_file,
                out_file=out_file,
                test_result='%0.2f sec'%test_times[test_name]+' '+test_results[test_name],
                faulty=str('HIGH VALUE' in test_results[test_name] or 'FAILED' in test_results[test_name]),
                ))

        for test_name in additional_test_results.keys():
            cases.append(textcase_template.format(
                test_name=test_name,
                test_result=additional_test_results[test_name],
                faulty=str('FAILED' in additional_test_results[test_name]),
                ))

        file.write(html_template.format(pairs='\n'.join(cases), ver=TAG))