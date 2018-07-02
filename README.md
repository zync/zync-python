# Zync Python API

# Warning

Note that the simplest and recommended way to install Zync plugins is through the Zync Client Application (see [instructions](https://docs.zyncrender.com/install-and-setup#option-1-the-plugins-tab-in-the-zync-client-app-simple-recommended-for-most-users)). The steps described below are for advanced users and we recommend to proceed with them only if you need to modify the plugin code for your custom needs.

## Install / Setup

Clone this repository to a centrally available location at your facility. This library will be used by both the Maya and Nuke plugins, so it must be easily accessible.

Once cloned, create a new file zync-python/zync_config.py. This file should contain one line:

```
ZYNC_URL = "https://<site>.zync.io"
```

This address will match the address you use to access your Zync Web Console.

A sample configuration file "zync_config.py.sample" is included in this repository.

## Usage

See [examples](/examples) for sample scripts demonstrating usage.

## Dependencies

This library uses [httplib2](http://code.google.com/p/httplib2/).

It is included with this API for convenience, though you can also install it with `pip` or `easy_install`:

```
pip install httplib2
```

The license for httplib2 is available [here](https://github.com/jcgregorio/httplib2/blob/master/LICENSE).
