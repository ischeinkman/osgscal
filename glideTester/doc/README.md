# Description

The glideTester is a testing framework aimed at testing
network facing services by using Grid resources.
The aim is to perform the same test at different concurrency
levels in a deterministic way. To fully automate the process,
glideTester heavily leverages the glideinWMS system for this purpose.

The Condor daemons and the glideinWMS glidein
factory daemon are used unmodified, and configured and
operated as suggested by the glideinWMS manuals. All the
Condor monitoring and debugging features are thus
available.

The tester daemon instead replaces the VO frontend.
The reason for reimplementing the frontend is simple;
the frontend provided with the glideinWMS is designed to be reactive; 
its modus operandi is to monitor a Condor scheduler for 
waiting jobs and to request glideins if there are any.
What we need instead is to first create the needed glidein
pool and then submit the test jobs.

Our system does not assume anything about the test
jobs; it only submits them and saves the output. In order to
prevent data loss, a separate subdirectory is created for each
instance of the test jobs. Moreover, to keep bookkeeping
manageable, the job directories are grouped by the
concurrency level.

Analysis of the output of the tests is beyond the current
scope of the framework, although may be implemented in
the future. However, the tester daemon does provide the exit
status of the test jobs for each completed concurrency level.

# Installation and Setup

## Pre-Installation

Before installing GlideinWMS, the host must be able to accept incoming HTTP requests on port `80`, and must be able to redirect URL paths to a folder location writeable by the user that GlideTester will run as. In addition, the `glideinwms` library should be installed somewhere reachable via the default Python `import`. For example by install the glideinwms libraries RPM

```console
yum install glideinwms-libs
```

In addition, the factory must be configured to be able to accept glidein requests from
the frontend's name and identity. Currently, GlideTester uses a hard-coded security class of 0. For example, for a username of `t001` on a factory called `glidein-1.t2.ucsd.edu`, the config entry might be:

```xml
<frontend name="t001" identity="t001@glidein-1.t2.ucsd.edu">
    <security_classes>
        <security_class name="0" username="t001"/>
    </security_classes>
</frontend>
```

## Frontend Setup

Before running GlideTester the user must create both a Frontend Configuration folder and Frontend WebStruct folder, accomplished via the `createTesterWebStruct.py` file.
In greater detail, the webstruct creation script creates a standard Frontend `workDir` and `webStageDir` and the specified paths to be used by both the `glideinwms` library and the factory. After the `webStageDir` is created, the user must add a URL redirect so that the configured `webURL` resolves to the `webStageDir`.

For example, if the glidetester host is running `httpd` with a hostname of `glidetester.example.org` the `glidetester.cfg` file contains the lines

```
webstruct.webStageDir = /etc/glidetester/webStageDir
webstruct.webURL = http://glidetester.example.org/weburl
```

Create a config file named `glidetester.conf` and place in `/etc/httpd/conf.d`:

```xml
Alias /weburl /etc/glidetester/webStageDir
<Directory /etc/glidetester/webStageDir>
        # Apache 2.2
        Order allow,deny
        Allow from all
</Directory>
```

This will correctly redirect `GET` calls to the appropriate files. Note that GlideTester
does **not** require the directory index feature of many http serves to be enabled; the
webstruct creator automatically generates an empty `index.html` file at the root of the `webStageDir`.

# Configuration

The GlideTester program is configured via one or more configuration files. These files are a series of key-value pairs, one pair per line, of the format `KEY=VALUE`. An example is included in the `etc` folder.

## File Locations and Priorities

The GlideTester program allows for configuration to be split between multiple specific locations. These locations are checked in a set priority, with options in lower priority files only being check if they do not exist in higher priority locations.

The priority list, from highest priority to lowest priority, is as follows:

1. The path specified via the `-cfg` or `--config` path, if it exists.

2. `~/.config/glideTester/glideTester.cfg`, if it exists.

3. `/etc/glideTester/glideTester.cfg`.

4. `os.path.join(sys.path[0], '../etc')` **NOTE: For development purposes only. Normal installs should instead rely on the default configuration at `/etc/glideTester/glideTester.cfg`.**

## Option List

### General Options

| Key | Description | Example | Optional? | Default Value |
| -- | -- | -- | -- | -- |
| `configDir` | The path to the generated frontend configuration directory, generally the same as `webstruct.workDir` | `~/workDir` | No | None |
| `collectorNode` | The hostname and port range of the collector node to use for collecting glideins. | `test-001.t2.ucsd.edu:9620-9630` | No | None |
| `glideinWMSDir` | The path to the `glideinwms` library code to use. **NOTE: For development purposes only. Normal users should instead install `glideinwms` normally and rely on Python's regular library importing.** | `~/glideinwms` | Yes | None |

### Proxy Options

| Key | Description | Example | Optional? | Default Value |
| -- | -- | -- | -- | -- |
| `proxyFile` | The path to the file containing proxy information. | `~/.globus/fe_proxy` | Yes | None |
| `pilotFile` | The path to the file containing proxy pilot information. | `~/.globus/pilot_proxy` | Yes | None |
| `delegateProxy` | Whether or not GlideTester should use a delegated proxy; can be either `True` or `False`. | `True` | Yes | `True` if either `pilotFile` or `proxyFile` are set; `False` otherwise. |

### Factory Options

| Key | Description | Example | Optional? | Default Value |
| -- | -- | -- | -- | -- |
| `gfactoryNode` | The hostname of the factory to request glideins from. | `glidein-1.t2.ucsd.edu` | No | None |
| `gfactoryConstraint` | The constraint to query possible factories against. | `(FactoryType=?="sleeper")` | No | None |
| `gfactoryClassadID` | The ID of the factory's classad to query for. | `t001@glidein-1.t2.ucsd.edu` | No | None |

### Classad Options

| Key | Description | Example | Optional? | Default Value |
| -- | -- | -- | -- | -- |
| `myClassadID` | The ID of the classad on the factory to authenticate with. | `t001@glidein-1.t2.ucsd.edu` | No | None |
| `mySecurityName` | The name of the user to use when authenticating with the factory. | `t001` | No | None |

### Logging Optionspassed

| Key | Description | Example | Optional? | Default Value |
| -- | -- | -- | -- | -- |
|`logger.directory`| The directory to store **the GlideTester program's** logs to (IE **not** the logs of the actual runs themselves). |`~/log` | Yes | `/var/log/glideTester` |
|`logger.extension`| The file name extension to use for the glidetester log files. |`log.txt`| Yes | `log.txt` |
|`logger.levels`| A comma-separated list of log levels to output to the logger. The valid levels are `WARN`, `ERR`, `INFO`, and `DEBUG`. | `WARN,ERR` | Yes | `WARN,ERR,INFO,DEBUG` |
|`logger.maxDays`| The maximum number of days to store in a single log file before starting a new one. | `365` | Yes | `10` |
|`logger.minDays`| The minimum number of days to store in a log file before starting a new one. | `10` | Yes | `1` |
|`logger.maxSize`| The maximum size, in megabytes, a log can reach before starting a new one. | `1024` | Yes | `10` |

### Web Structure Options

| Key | Description | Example | Optional? | Default Value |
| -- | -- | -- | -- | -- |
| `webstruct.workDir` | The path to use for creating GlideTester's fake frontend configuration information. | `~/workDir` | No | None |
| `webstruct.webStageDir` | The path to use for creating GlideTester's web-accessible frontend configuration files. Should be accessable from the value of `webstruct.webURL`. See the [Frontend Setup](#Frontend-Setup) section for more information. | `~/webStageDir` | No | None |
| `webstruct.shouldClean` | Whether or not the webstruct creation script should overwrite the `workDir` and `webStageDir` folders if they already exist; if this is `False` then the script will throw an error instead. | `True` | Yes | `False` |
| `webstruct.webURL` | The URL that the factory will use to look for the frontend's configuration files. | `http://test-001.t2.ucsd.edu/weburl` | No | None |
| `webstruct.gridmapFile` | The file containing the map information for the grid to use.  | `~/test-gridmapfile` | No | None |
| `webstruct.glideinWMSDir` | The path to the `glideinwms` library code for the web struct creation script to use. **NOTE: For development purposes only. Normal users should instead install `glideinwms` normally and rely on Python's regular library importing.** | `~/glideinwms` | Yes | None |

# Running

Like the general configuration, a GlideTester "job" is represented and passed as a `parameters.cfg` file containing `KEY=VALUE` pair lines. The file follows the exact same priority list as the main `glidetester.cfg` file; note that therefore if a key is missing from a passed `parameters.cfg` file, **GlideTester will first look for corresponding keys in lower priority `parameters.cfg` files before loading the stated defaults!** For this reason the included example `parameters.cfg` file will have all options commented out.

The options are:

| Key | Description | Example | Optional? | Default Value |
| -- | -- | -- | -- | -- |
| `executable` | The path to the executable to run file to run in each of the glideins' shells. |`/home/ilan/osgscal/glideTester/bin/timed_loop.sh` | No | None |
| `concurrency` | A space-separated list of parallel "concurrency levels" to run the executable at, IE the number of Glideins to collect before running the executable on them. Note that glideins will be re-used between concurrency levels. |`5 10 100 1000` | No | None |
| `runs` | The number of times to run each concurrency level. |`1` | No | None |
| `arguments` | The command-line arguments to pass ot the executable. |`--flag flagval  --cluster $(Cluster) arg2` | Yes | None |
| `gfactoryAdditionalConstraint` | Additional constraints on the factory to add to the ClassAd. | ` FactoryName=?='TestName' ` | Yes | None |

In addition, the following `condor_submit` parameters are supported and will be added unaltered to generated condor jobs:

* `should_transfer_files`
* `transfer_input_files`
* `transfer_output_files`
* `environment`
* `getenv`
* `x509userproxy`
