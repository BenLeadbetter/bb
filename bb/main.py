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

    generator = detect_generator()
    validate_generater(generator)

    if not args.build and not args.run:
        eprint("Must specify --build or --run")
        sys.exit(1)

    if args.build:
        build(args)
    if args.run:
        run(args, unknown_args)


def build(args):
    result = subprocess.run(
        ["ninja", "-j", args.jobs, args.target],
        text=True,
    )
    if result.returncode != 0:
        eprint("Build failed")
        sys.exit(result.returncode)


def run(args, unknown_args):
    cmd = run_cmd_from_cmake(args.target)
    if cmd is None:
        cmd = run_cmd_from_ninja(args.target)
    if cmd is None:
        eprint("Couldn't locate target executable.")
        sys.exit(1)
    if not is_executable(cmd[0]):
        eprint(f"{cmd[0]} is not executable")
        sys.exit(1)
    subprocess.run([cmd[0]] + unknown_args, cwd=cmd[1])


RunCommand = typing.Tuple[str, typing.Optional[str]]


def run_cmd_from_cmake(target) -> typing.Optional[RunCommand]:
    def handle_file(file):
        data = json.load(file)
        exec = data.get("artifacts", [{}])[0].get("path", None)
        if exec is not None:
            exec = os.getcwd() + "/" + exec
        return (
            exec,
            data.get("debugger", [{}]).get("workingDirectory", None),
        )

    target_config = get_target_cmake_config_filename(target)
    if target_config is None:
        return None
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


def run_cmd_from_ninja(target) -> typing.Optional[RunCommand]:
    result = subprocess.run(
        ["ninja", "-t", "query", target],
        capture_output=True,
        text=True,
    )
    lines = result.stdout.split("\n")
    for i, line in enumerate(lines):
        if "input: phony" in line and i + 1 < len(lines):
            return (lines[i + 1].strip(), None)
    return None


def detect_generator() -> typing.Optional[str]:
    with open("CMakeCache.txt", "r") as file:
        for line in file:
            if "CMAKE_GENERATOR:INTERNAL" in line:
                return line.split("=")[1].strip()


def validate_generater(generator: typing.Optional[str]):
    if generator is None:
        eprint("Error: Could not detect CMake generator.")
        sys.exit(1)

    match generator:
        case "Ninja":
            return
        case _:
            eprint(f"Unsupported generator {generator}")
            sys.exit(1)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    version = bb.__version__
    parser.add_argument("target")
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
