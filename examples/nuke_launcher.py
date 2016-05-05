
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
#   Path to the Nuke script.
#
script_path = '/path/to/project/comp/nuke_script_v01.nk'

#
#   A comma-separated list of Write nodes to render. "All" will render all enabled
#   write nodes in the script.
#
write_node = 'Write1,Write2'
#write_node = 'All'

#
#   Other job parameters.
#
render_params = {
    #
    #   num_instances = Number of render nodes to assign to this job.
    #
    'num_instances': 1,
    #
    #   skip_check = Whether to skip the file check / upload. Only use this if you're
    #                absolutely sure all files have already been uploaded to ZYNC.
    #
    'skip_check': 0,
    #
    #   upload_only = Whether to run an "upload-only" job. 0 will perform a full render
    #                 render job, 1 will just upload files - no rendering will take place.
    #
    'upload_only': 0,
    #
    #   priority = The job's priority. 1-100, lower numbers = more priority.
    #
    'priority': 50,
    #
    #   instance_type = The instance type to use on your job.
    #
    'instance_type': 'n1-standard-8',
    #
    #   frange = The frame range to render.
    #
    'frange': '1-10',
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
    #   proj_name = ZYNC project.
    #
    'proj_name': 'NUKE_LAUNCHER'
}

#
#   Launch the job. submit_job() returns the ID of the new job.
#
new_job = z.submit_job('nuke', script_path, write_node, render_params)

print 'Job launched.'

