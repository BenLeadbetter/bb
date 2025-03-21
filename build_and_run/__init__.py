from importlib.metadata import PackageNotFoundError, version

def get_version() -> str:
    try:
        return version('build-and-run')
    except PackageNotFoundError:
        return "dev"

__version__ = get_version()
