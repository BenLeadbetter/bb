import bb

import argparse
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
    result = subprocess.run(
        ["ninja", "-t", "query", args.target],
        capture_output=True,
        text=True,
    )
    lines = result.stdout.split("\n")
    for i, line in enumerate(lines):
        if "input: phony" in line and i + 1 < len(lines):
            cmd = lines[i + 1].strip()
            if not is_executable(cmd):
                eprint(f"{cmd} is not executable")
                sys.exit(1)
            subprocess.run([cmd] + unknown_args)


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
