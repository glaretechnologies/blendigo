#
# Blendigo 2.5 Regression Testing Suite
#
# INFO:
# The easiest way to run this script is in Blender's Text Editor or run runme.py in command line instead. report.html and results.txt will be created in outputs directory
# set path to Indigo Test Suite folder

import os
INDIGO_TEST_SUITE = os.path.split(__file__)[0]

import os, subprocess, shutil, time, glob, sys

sys.path.append(INDIGO_TEST_SUITE)
from pypng import png

import json
with open(os.path.join(INDIGO_TEST_SUITE, 'scenes', 'annotations.json'), 'r') as f:
    annotations_data = json.loads(f.read())
print(annotations_data)

import bpy
from indigo_exporter.core import getConsolePath
from indigo_exporter.core.util import getVersion
BLENDER_BINARY = bpy.app.binary_path
INDIGO_PATH = os.path.split(getConsolePath())[0]

def image_analysis(ref_file, tst_file):
    ref_data = ref_file.asRGBA()
    tst_data = tst_file.asRGBA()
    
    if ref_data[0]!=tst_data[0] or ref_data[1]!=tst_data[1]:
        raise Exception('output images size mismatch!')
    
    ref_rgb = ref_data[2]
    tst_rgb = tst_data[2]
    
    sum_err = 0
    px_count = 0
    for ref_row, tst_row in zip(ref_rgb, tst_rgb):
        for ref_col, tst_col in zip(ref_row, tst_row):
            err = tst_col - ref_col
            sum_err += abs(err)
            px_count += 1
    return sum_err/px_count

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
            print(args)
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
            ME = image_analysis(ref_file, tst_file)
            if ME > 4:
                ME_msg = '****** HIGH VALUE ******'
                failure_count += 1
            else:
                ME_msg = 'OK'
                
            test_results[name] = 'ME = %0.4f  %s' % (ME, ME_msg)
        
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
    .cap{{
        margin: 2rem;
    }}
    .text{{
        text-align: justify;
    }}
    .additional{{
        margin: 2rem 0rem;
        padding: 1rem;
        border: solid 1px gray;
        border-radius: 1rem;
    }}
</style>
</head>
<body>
<span class="cap">Blendigo: {ver}</span>
<span class="cap">Indigo: {indigo_ver}</span>
<span class="cap">Blender: {blender_ver}</span>
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
    <div class="text">{test_annotation}</div>
</div>
"""

additional_tests = set()

class NonstandardTest:
    def register(cls):
        additional_tests.add(cls)

    textcase_template="""
<div class="container faulty-{faulty}">
    <div class="caption">
        <span class="left">{test_name}</span>
        <span class="right">{test_result}</span>
    </div>
</div>
"""
    name = "NonstandardTest"

    output_log = []
    test_results = {}

    def __contains__(self, key):
        return key == self.name
    
    def __str__(self):
        # use template to produce html formatted output e.g.:
        return self.textcase_template.format(
            test_name=test_name,
            test_result=self.test_results[test_name],
            faulty=str('FAILED' in self.test_results[self.name]),
            )
    
    def execute(self, BLENDIGO_VERSION='0.0.0'):
        # return output_log and test_result
        pass

@NonstandardTest.register
class MultifileAnimation(NonstandardTest):
    name = "multifile_animation"

    textcase_template="""
<div class="additional">
    <div class="cap">{testcase}</div>
    <div class="text">{test_annotation}</div>
    {results_images}
    {results_simple}
</div>
"""

    simple_result_template="""
<div class="container faulty-{faulty}">
    <div class="caption">
        <span class="left">{test_name}</span>
        <span class="right">{test_result}</span>
    </div>
</div>
"""
    pair_template="""
<div class="container faulty-{faulty}">
    <div class="caption">
        <span class="left">{test_name}</span>
        <span class="right">{test_result}</span>
    </div>
    <img src="../references/{reference_file}"><img src="../outputs/{out_file}">
</div>
"""

    def __str__(self):
        simple_str = ""
        for name, result in self.test_results.items():
            simple_str += self.simple_result_template.format(
                test_name=name,
                test_result=result,
                faulty=str('FAILED' in result),
                )
        
        images_str = ""
        # First image
        ref_path = os.path.join(INDIGO_TEST_SUITE, 'references', 'multifile', 'multifile0189.png')
        tst_path = os.path.join(INDIGO_TEST_SUITE, 'outputs', 'multifile', 'multifile0189.png')
        ref_file = png.Reader(ref_path)
        tst_file = png.Reader(tst_path)
        ME = image_analysis(ref_file, tst_file)
        if ME > 4:
            ME_msg = f'ME = {ME:0.4f}  ****** HIGH VALUE ******'
        else:
            ME_msg = 'OK'
        
        images_str += self.pair_template.format(
            faulty = ME > 4,
            test_name = "multifile0189.png Image",
            test_result = ME_msg,
            reference_file = 'multifile/multifile0189.png',
            out_file = 'multifile/multifile0189.png',
        )

        # Second image
        ref_path = os.path.join(INDIGO_TEST_SUITE, 'references', 'multifile', 'multifile0190.png')
        tst_path = os.path.join(INDIGO_TEST_SUITE, 'outputs', 'multifile', 'multifile0190.png')
        ref_file = png.Reader(ref_path)
        tst_file = png.Reader(tst_path)
        ME = image_analysis(ref_file, tst_file)
        if ME > 4:
            ME_msg = f'ME = {ME:0.4f}  ****** HIGH VALUE ******'
        else:
            ME_msg = 'OK'
        
        images_str += self.pair_template.format(
            faulty = ME > 4,
            test_name = "multifile0190.png Image",
            test_result = ME_msg,
            reference_file = 'multifile/multifile0190.png',
            out_file = 'multifile/multifile0190.png',
        )
        
        outstr = self.textcase_template.format(
            testcase = self.name,
            test_annotation = annotations_data[self.name] if self.name in annotations_data else "",
            results_images = images_str,
            results_simple = simple_str,
        )
        return outstr

    def execute(self, BLENDIGO_VERSION='0.0.0'):
        # additional non-standardized tests

        # use one of the test scenes to check multi-file export options
        
        # turn off verbose exporting
        if 'B25_OBJECT_ANALYSIS' in os.environ.keys():
            del os.environ['B25_OBJECT_ANALYSIS']
        
        test_sep = '*'*80

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
                    self.test_results[name] = "OK"
                else:
                    self.test_results[name] = "FAILED"
            
            # check igi files exported with timestamp in filename
            import re
            refstr = ' '.join(tst_file_names)
            if re.search('multifile0189_\d+\.igi', refstr):
                self.test_results[r'multifile0189_\d+\.igi'] = "FAILED"
            else:
                self.test_results[r'multifile0189_\d+\.igi'] = "OK"

            if re.search('multifile0190_\d+\.igi', refstr):
                self.test_results[r'multifile0190_\d+\.igi'] = "FAILED"
            else:
                self.test_results[r'multifile0190_\d+\.igi'] = "OK"
        
        except Exception as err:
            self.test_results[name] = 'FAILED: %s' % err
        
        print('Test: %s completed' % name)
        print(test_sep)
        print('\n')
        
        
        self.output_log.append('All Tests complete!\n')
        self.output_log.append(test_sep)
        for test_name in sorted(self.test_results.keys()):
            self.output_log.append('%-30s %s' % (test_name, self.test_results[test_name]))
        self.output_log.append(test_sep)




@NonstandardTest.register
class MultifileStill(NonstandardTest):
    name = "multifile_still"

    textcase_template="""
<div class="additional">
    <div class="cap">{testcase}</div>
    <div class="text">{test_annotation}</div>
    {results_images}
    {results_simple}
</div>
"""

    simple_result_template="""
<div class="container faulty-{faulty}">
    <div class="caption">
        <span class="left">{test_name}</span>
        <span class="right">{test_result}</span>
    </div>
</div>
"""
    pair_template="""
<div class="container faulty-{faulty}">
    <div class="caption">
        <span class="left">{test_name}</span>
        <span class="right">{test_result}</span>
    </div>
    <img src="../references/{reference_file}"><img src="../outputs/{out_file}">
</div>
"""

    def __str__(self):
        simple_str = ""
        for name, result in self.test_results.items():
            simple_str += self.simple_result_template.format(
                test_name=name,
                test_result=result,
                faulty=str('FAILED' in result),
                )
        
        images_str = ""
        # Only image
        ref_path = os.path.join(INDIGO_TEST_SUITE, 'references', 'multifile', 'multifile0189.png')
        tst_path = os.path.join(INDIGO_TEST_SUITE, 'outputs', 'multifile', 'multifile0189.png')
        ref_file = png.Reader(ref_path)
        tst_file = png.Reader(tst_path)
        ME = image_analysis(ref_file, tst_file)
        if ME > 4:
            ME_msg = f'ME = {ME:0.4f}  ****** HIGH VALUE ******'
        else:
            ME_msg = 'OK'
        
        images_str += self.pair_template.format(
            faulty = ME > 4,
            test_name = "multifile0189.png Image",
            test_result = ME_msg,
            reference_file = 'multifile_still/multifile0189.png',
            out_file = 'multifile_still/multifile0189.png',
        )
        
        outstr = self.textcase_template.format(
            testcase = self.name,
            test_annotation = annotations_data[self.name] if self.name in annotations_data else "",
            results_images = images_str,
            results_simple = simple_str,
        )
        return outstr

    def execute(self, BLENDIGO_VERSION='0.0.0'):
        # additional non-standardized tests

        # use one of the test scenes to check multi-file export options
        
        # turn off verbose exporting
        if 'B25_OBJECT_ANALYSIS' in os.environ.keys():
            del os.environ['B25_OBJECT_ANALYSIS']
        
        test_sep = '*'*80

        scene  = os.path.join(INDIGO_TEST_SUITE, 'scenes', 'multifile_still', 'multifile.blend')
        name   = "multifile_export"
        
        print(test_sep)
        print('Additional tests')
        print('Test: multi-file export')
        
        # clean the output location
        output_path = os.path.join(INDIGO_TEST_SUITE, 'outputs', 'multifile_still', 'multifile')
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

            ####
            tst_file_names = [f for f in os.listdir(os.path.join(INDIGO_TEST_SUITE, 'outputs', 'multifile_still'))]
            # tst_file_name = glob.glob(os.path.join(INDIGO_TEST_SUITE, 'outputs', 'multifile', test_name+"*"))

            reference_filenames = [
            # 'multifile.Scene.00189.igs',
            # 'multifile.Scene.00190.igs',
            # 'multifile0189.igi',
            'multifile0189.png',
            'multifile0189_channels.exr',
            'multifile0189_tonemapped.exr',
            'multifile0189_untonemapped.exr',
            ]

            for name in reference_filenames:
                if name in tst_file_names:
                    self.test_results[name] = "OK"
                else:
                    self.test_results[name] = "FAILED"
            
            # check igi files exported with timestamp in filename
            import re
            refstr = ' '.join(tst_file_names)
            print(refstr)
            if re.search('multifile0189_\d+\.igi', refstr):
                self.test_results[r'multifile0189_\d+\.igi'] = "OK"
            else:
                self.test_results[r'multifile0189_\d+\.igi'] = "FAILED"
        
        except Exception as err:
            self.test_results[name] = 'FAILED: %s' % err
        
        print('Test: %s completed' % name)
        print(test_sep)
        print('\n')
        
        
        self.output_log.append('All Tests complete!\n')
        self.output_log.append(test_sep)
        for test_name in sorted(self.test_results.keys()):
            self.output_log.append('%-30s %s' % (test_name, self.test_results[test_name]))
        self.output_log.append(test_sep)

def run_additional_tests():
    tests = filter(lambda t: t.name in filter_list, additional_tests) if filter_list else additional_tests
    tests = [t() for t in tests]
    for test in tests:
        test.execute()

    return tests


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
    blendigo_version = '.'.join(['%i'%i for i in bl_info['version']])
    indigo_version = '.'.join(['%i'%i for i in getVersion()])
    blender_version = bpy.app.version_string
    
    del os.environ['BLENDIGO_RELEASE']
    
    print('\n\n\n* Test Started *\n\n\n')
    log_lines, failure_count, test_results, test_times = regression_test(filter_list, blendigo_version)
        
    executed_additional_tests = run_additional_tests()

    with open(os.path.join(INDIGO_TEST_SUITE, 'outputs','results.txt'), 'w') as file:
        for log_line in log_lines:
            print(log_line)
            file.write('\n'+log_line)
        file.write('\n'*2 + '\nFailures: '+str(failure_count))

        for test in executed_additional_tests:
            for log_line in test.output_log:
                print(log_line)
                file.write('\n'+log_line)

        file.write('\nBlendigo Version: '+blendigo_version)
        file.write('\nIndigo Version: '+indigo_version)
        file.write('\nBlender Version: '+blender_version)
        
        
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
                test_annotation=annotations_data[test_name] if test_name in annotations_data else "",
                ))

        for test in executed_additional_tests:
            cases.append(str(test))

        file.write(html_template.format(pairs='\n'.join(cases), ver=blendigo_version, indigo_ver=indigo_version, blender_ver=blender_version))