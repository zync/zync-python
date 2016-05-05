
#
#   Go two levels up and add that directory to the PATH, so we can find zync.py.
#
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#
#   Import ZYNC Python API.
#
import zync

#
#   Connect to ZYNC. This will start the browser to perform an Oauth2
#   authorization if needed.
#
z = zync.Zync()

#
#   Path to the Maya scene.
#
scene_path = '/path/to/project/scenes/maya_scene_v01.mb'

#
#   Other job parameters.
#
params = {
    #
    #   num_instances = Number of render nodes to assign to this job.
    #
    'num_instances': 1,
    #
    #   priority = The job's priority. 1-100, lower numbers = more priority.
    #
    'priority': 50, 
    #
    #   job_subtype = The job's subtype. Will almost always be "render".
    #
    'job_subtype': 'render', 
    #
    #   upload_only = Whether to run an "upload-only" job. 0 will perform a full render
    #                 render job, 1 will just upload files - no rendering will take place.
    #
    'upload_only': 0, 
    #
    #   proj_name = ZYNC project.
    #
    'proj_name': 'MAYA_LAUNCHER', 
    #
    #   skip_check = Whether to skip the file check / upload. Only use this if you're
    #                absolutely sure all files have already been uploaded to ZYNC.
    #
    'skip_check': 0, 
    #
    #   instance_type = The instance type to use on your job.
    #
    'instance_type': 'n1-standard-16', 
    #
    #   frange = The frame range to render.
    #
    'frange': '1-24,30-40', 
    #
    #   step = The frame step, i.e. a step = 1 will render every frame, 2 will render
    #          every other frame, etc. Using step > 1 will set your Chunk Size to 1.
    #
    'step': 1, 
    #
    #   chunk_size = The number of frames to render per Task.
    #
    'chunk_size': 10, 
    #
    #   renderer = The renderer to use, e.g. "vray" or "arnold".
    #
    'renderer': 'vray', 
    #
    #   layers = The render layers you wish to render.
    #
    'layers': 'Simple_scene_exr_test', 
    #
    #   out_path = The output path for frames to be downloaded to.
    #
    'out_path': '/path/to/project/images', 
    #
    #   camera = The render camera to use.
    #
    'camera': 'camera1', 
    #
    #   xres = The output image x resolution.
    #
    'xres': 1280, 
    #
    #   yres = The output image y resolution.
    #
    'yres': 720, 
    #
    #   project = The path to your Maya project.
    #
    'project': '/path/to/project', 
    #
    #   ignore_plugin_errors = Whether to ignore missing plugin errors.
    #
    'ignore_plugin_errors': 0
    #
    #   distributed = Whether to use Distribute Rendering. Only currently available
    #                 for Vray.
    #
    'distributed': 0, 
    #
    #   use_vrscene = Whether to use Vray Standalone.
    #
    'use_vrscene': 0,
    #
    #   use_ass = Whether to use Arnold Standalone.
    #
    'use_ass': 0, 
    #
    #   use_mi = Whether to use Mental Ray Standalone.
    #
    'use_mi': 0, 
    #
    #   vray_nightly = Whether to use the latest Vray Nightly Build.
    #
    'vray_nightly': 0, 
    #
    #   scene_info = A collection of information about your Maya scene.
    #
    'scene_info': {
        #
        #   files = A list of files needed to render. Use local paths.
        #
        'files': [
            '/path/to/project/textures/abc_cube.jpg', 
            '/path/to/project/textures/wooden-floor-texture.jpg'
        ], 
        #
        #   arnold_version = The Arnold version in use in your scene. Only needed
        #                    for Arnold renders.
        #
        'arnold_version': '', 
        #
        #   plugins = A list of plugins in use in your scene.
        #
        'plugins': ['Mayatomr', 'vrayformaya'], 
        #
        #   file_prefix = The global file prefix, followed by a dict of each render
        #                 layer specific prefix.
        #
        'file_prefix': ['', {
            'Simple_scene_exr_test': ''
        }], 
        #
        #   padding = The frame padding.
        #
        'padding': 3, 
        #
        #   version_version = The Vray version in use in your scene. Only needed for
        #                     Vray renders.
        #
        'vray_version': '2.40.01', 
        #
        #   references = A list of references used by your scene. Use local, absolute paths.
        #
        'references': [], 
        #
        #   unresolved_references = A list of unresolved references in your scene. Use
        #                           local, absolute paths. Probably not needed if all
        #                           of your reference paths above are correct.
        #
        'unresolved_references': [], 
        #
        #   render_layers = A list of ALL render layers in your scene.
        #
        'render_layers': [
            'Simple_scene_NB_test', 
            'Simple_scene_exr_test', 
            'Simple_scene_jpg_test', 
            'Simple_scene_png_test', 
            'Simple_scene_vs_exr_test', 
            'defaultRenderLayer'
        ], 
        #
        #   render_passes = A dict of each render layer's render passes.
        #
        'render_passes': {}, 
        #
        #   extension = The scene's output file extension.
        #
        'extension': 'exr', 
        #
        #   version = The Maya version in use.
        #
        'version': '2014'
    }
}

#
#   Launch the job. submit_job() returns the ID of the new job.
#
new_job_id = z.submit_job('maya', scene_path, params=params)

print 'Job Launched! New Job ID: %d' % (str(new_job_id),)
