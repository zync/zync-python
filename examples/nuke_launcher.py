
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
#   Connect to ZYNC. Set up a script & API token via the Admin page in the ZYNC
#   Web Console.
#
z = zync.Zync('nuke_launcher', '**********************')

#
#   Login with your ZYNC username & password. This will allow you to launch jobs.
#
z.login(username='zync_user', password='********')

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
    #   start_new_slots = Whether the job is allowed to start new slots. 0 = will only
    #                     use already-running slots, 1 = will start new ones as needed.
    #
    'start_new_slots': 1,
    #
    #   skip_check = Whether to skip the file check / upload. Only use this if you're
    #                absolutely sure all files have already been uploaded to ZYNC.
    #
    'skip_check': 0,
    #
    #   notify_complete = Whether to send out a notification when the job completes.
    #
    'notify_complete': 0,
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
    'instance_type': 'ZYNC8',
    #
    #   frange = The frame range to render.
    #
    'frange': '0-10',
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
new_job_id = z.submit_job('nuke', script_path, write_node, render_params)

print 'Job Launched! New Job ID: %d' % (str(new_job_id),)

