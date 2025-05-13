# Ben Build

Helper tool for building, running and deploying cmake applications and plugins.

## Usage

```shell
usage: bb [-h] [--version] [--build-jobs BUILD_JOBS] [--build] [--clean] [--codesign] [--codesign-identity ID] [--run] [--deploy] [target]

positional arguments:
  target

options:
  -h, --help            show this help message and exit
  --version, -v         show program's version number and exit
  --build-jobs, -j BUILD_JOBS
  --build, -b
  --clean               Clean build directory (implies --build) (default: False)
  --codesign, -s
  --codesign-identity ID
                        The identity to be used in the codesign command, or set the CODESIGN_KEY env variable (default: None)
  --run, -r
  --deploy, -d
```
