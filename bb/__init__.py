from importlib.metadata import PackageNotFoundError, version

def get_version() -> str:
    try:
        return version('bb')
    except PackageNotFoundError:
        return "dev"

__version__ = get_version()
