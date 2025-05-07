import bb

import argparse
import glob
import json
import os
import pathlib
import subprocess
import sys
import typing
import signal

ALL_TARGETS = "ALL"


def handle_interrupt(_signum, _frame):
    eprint("Interrupted")
    sys.exit(1)


signal.signal(signal.SIGINT, handle_interrupt)


def main():
    args, unknown_args = make_parser().parse_known_args()

    if not args.build and not args.run and not args.codesign:
        args.build = True
    if args.clean:
        args.build = True

    if args.build:
        build(args)
    if args.codesign:
        codesign(args)
    if args.deploy:
        deploy(args)
    if args.run:
        run(args, unknown_args)


def deploy(args):
    print("todo")
    sys.exit(1)


def codesign(args):
    if sys.platform != "darwin":
        eprint("Code signing is only supported on macOS")
        return
    target = signing_target(args.target)

    def codesign(path: str):
        result = subprocess.run(
            [
                "codesign",
                "-s",
                args.codesign,
                target,
            ],
            text=True,
            stderr=subprocess.PIPE,
        )
        if "already signed" in result.stderr:
            print(f"{path} is already signed")
            return
        if result.returncode != 0:
            eprint(f"Code signing failed for {path}")
            sys.exit(result.returncode)
        print(f"Codesigned {path}")

    if pathlib.Path(target).is_dir():
        for file in pathlib.Path(target).rglob("*.framework"):
            codesign(str(file))
        for file in pathlib.Path(target).rglob("*.dylib"):
            codesign(str(file))
    codesign(target)


def build(args):
    env = os.environ.copy()
    env["CMAKE_BUILD_PARALLEL_LEVEL"] = str(args.jobs)
    cmd = ["cmake", "--build", "."]
    if args.target != ALL_TARGETS:
        cmd.extend(["--target", args.target])
    if args.clean:
        cmd.append("--clean-first")
    result = subprocess.run(
        cmd,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        eprint("Build failed")
        sys.exit(result.returncode)


def run(args, unknown_args):
    if args.target == ALL_TARGETS:
        eprint("No target specified to run")
        exit(1)
    cmd, cwd = run_cmd_from_cmake(args.target)
    if not is_executable(cmd):
        eprint(f"{cmd} is not executable")
        sys.exit(1)
    subprocess.run([cmd] + unknown_args, cwd=cwd)


RunCommand = typing.Tuple[str, typing.Optional[str]]


def signing_target(target) -> str:
    def handle_file(file):
        exec = get_executable_from_target_cmake_config_file(file)
        if exec is None:
            eprint(f"Could not find executable for {target}")
            sys.exit(1)
        bundle = pathlib.Path(exec).parent.parent
        if bundle.suffix not in [".app", ".vst3", ".component", ".aax"]:
            return exec
        return str(bundle)

    target_config = get_target_cmake_config_filename(target)
    if target_config is None:
        eprint(f"Could not find target config file for {target}")
        sys.exit(1)
    return with_file(target_config, handle_file)


def run_cmd_from_cmake(target) -> RunCommand:
    def handle_file(file):
        exec = get_executable_from_target_cmake_config_file(file)
        if exec is None:
            eprint(f"Could not find executable for {target}")
            sys.exit(1)
        return (
            exec,
            get_executable_working_directory_from_target_cmake_config_file(file),
        )

    target_config = get_target_cmake_config_filename(target)
    if target_config is None:
        eprint(f"Could not find target config file for {target}")
        sys.exit(1)
    return with_file(target_config, handle_file)


def get_executable_from_target_cmake_config_file(file):
    data = json.load(file)
    exec = data.get("artifacts", [{}])[0].get("path", None)
    return os.getcwd() + "/" + exec


def get_executable_working_directory_from_target_cmake_config_file(file):
    data = json.load(file)
    return data.get("debugger", {}).get("workingDirectory", None)


def get_target_cmake_config_filename(target_name: str) -> typing.Optional[str]:
    def handle_file(file):
        data = json.load(file)
        targets = data.get("configurations", [{}])[0].get("targets", [{}])
        for target in targets:
            if target.get("name") == target_name:
                filename = target.get("jsonFile", None)
                if filename is not None:
                    filename = ".cmake/api/v1/reply/" + filename
                return filename
        return None

    config = glob.glob("codemodel-v2-*", root_dir=".cmake/api/v1/reply/")
    if not config:
        return None
    # use the first match
    return with_file(".cmake/api/v1/reply/" + config[0], handle_file)


def with_file(
    filename: str, fn: typing.Callable[[typing.TextIO], typing.Any]
) -> typing.Any:
    try:
        with open(filename, "r") as file:
            return fn(file)
    except FileNotFoundError:
        eprint(f"File '{filename}' not found.")
        exit(1)
    except PermissionError:
        eprint(f"Permission denied for file '{filename}'.")
        exit(1)
    except OSError as e:
        eprint(f"An OS error occurred: {e}")
        exit(1)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    version = bb.__version__
    parser.add_argument(
        "target",
        nargs="?",
        default=ALL_TARGETS,
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"{os.path.basename(sys.argv[0])} {version}",
    )
    parser.add_argument(
        "--jobs",
        "-j",
        default="6",
    )
    parser.add_argument(
        "--build",
        "-b",
        action="store_true",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build directory (implies --build)",
    )
    parser.add_argument(
        "--codesign",
        "-s",
        type=str,
        default=None,
        metavar="ID",
    )
    parser.add_argument(
        "--run",
        "-r",
        action="store_true",
    )
    parser.add_argument(
        "--deploy",
        "-d",
        action="store_true",
    )
    return parser


def is_executable(file_path: str) -> bool:
    return os.path.isfile(file_path) and os.access(file_path, os.X_OK)


def eprint(text: str):
    print(f"\033[91mError: {text}\033[0m", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
