import bb

import argparse
import glob
import json
import os
import subprocess
import sys
import typing
import signal


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
    if args.run:
        run(args, unknown_args)


def codesign(args):
    eprint("todo")
    sys.exit(1)


def build(args):
    env = os.environ.copy()
    env["CMAKE_BUILD_PARALLEL_LEVEL"] = str(args.jobs)
    cmd = ["cmake", "--build", "."]
    if args.target != "ALL":
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
    if args.target == "All":
        eprint("No target specified to run")
        exit(1)
    cmd, cwd = run_cmd_from_cmake(args.target)
    if not is_executable(cmd):
        eprint(f"{cmd} is not executable")
        sys.exit(1)
    subprocess.run([cmd] + unknown_args, cwd=cwd)


RunCommand = typing.Tuple[str, typing.Optional[str]]


def run_cmd_from_cmake(target) -> RunCommand:
    def handle_file(file):
        data = json.load(file)
        exec = data.get("artifacts", [{}])[0].get("path", None)
        if exec is None:
            eprint(f"Could not find executable for {target}")
            sys.exit(1)
        exec = os.getcwd() + "/" + exec
        return (
            exec,
            data.get("debugger", {}).get("workingDirectory", None),
        )

    target_config = get_target_cmake_config_filename(target)
    if target_config is None:
        eprint(f"Could not find target config file for {target}")
        sys.exit(1)
    return with_file(target_config, handle_file)


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
        default="ALL",
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
    # parser.add_argument(
    #     "--deploy-au",
    #     "--au",
    #     action="store_true",
    # )
    # parser.add_argument(
    #     "--deploy-vst3",
    #     "--vst3",
    #     action="store_true",
    # )
    return parser


def is_executable(file_path: str) -> bool:
    return os.path.isfile(file_path) and os.access(file_path, os.X_OK)


def eprint(text: str):
    print(f"\033[91mError: {text}\033[0m", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
