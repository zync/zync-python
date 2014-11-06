# ZYNC Python API

## Install / Setup

Clone this repository to a centrally available location at your facility. This library will be used by both the Maya and Nuke plugins, so it must be easily accessible.

Once cloned, create a new file zync-python/config.py. This file should contain one line:

```
ZYNC_URL = "https://<site>.zyncio.com"
```

This address will match the address you use to access your ZYNC Web Console.

A sample configuration file "config.py.sample" is included in this repository.

## Usage

```python
import zync

# set up a ZYNC object
z = zync.Zync('script_name', 'api_key')

# authenticate with ZYNC
z.login(username='bcipriano', password='password')

# supply some non-default rendering paramters
job_params = dict( frange = '1-100',
               chunk_size = 2 )

# submit the job to ZYNC
z.submit_job('nuke', '/path/to/nuke_script.nk', 'write_node', job_params)
```

## Dependencies

This library uses [httplib2](http://code.google.com/p/httplib2/).

It is included with this API for convenience, though you can also install it with `pip` or `easy_install`:

```
easy_install httplib2
```

The license for httplib2 is available [here](https://github.com/jcgregorio/httplib2/blob/master/LICENSE).
