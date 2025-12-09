require 'FileUtils'

blender_scripts_dir = "C:/Program Files/Blender Foundation/Blender 5.0/5.0/scripts"
if !File.directory?(blender_scripts_dir)
	raise "Could not find blender scripts dir at '#{blender_dir}'"
end

FileUtils.cp_r("../sources/indigo_exporter/", blender_scripts_dir + "/addons_core", :verbose => true)
