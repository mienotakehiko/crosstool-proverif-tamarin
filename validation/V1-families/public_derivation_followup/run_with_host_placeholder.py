#!/usr/bin/env python3
"""Start an archived runner with a placeholder in place of the host name.

    python3 -B run_with_host_placeholder.py RUNNER.py [arguments of the runner]

The runners validation/common/run_set.py and run_set_monotonic.py write the
host name into results/environment.json. This wrapper makes platform.node()
return "host-redacted" and then executes the runner file unchanged. The
environment record therefore needs no later change, and it still states the
SHA-256 hash of the runner file.
"""
import platform
import runpy
import sys


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    runner = sys.argv[1]
    sys.argv = [runner] + sys.argv[2:]
    platform.node = lambda: "host-redacted"
    runpy.run_path(runner, run_name="__main__")


if __name__ == "__main__":
    main()
