"""Minimal CLI entry-point for cronwrap."""

import argparse
import sys
from typing import List, Optional

from cronwrap.timeout import TimeoutConfig
from cronwrap.retry import RetryPolicy
from cronwrap.core import CronJob


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap",
        description="Wrap a shell command with logging, retries, and timeouts.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run")
    parser.add_argument(
        "--timeout", type=int, default=0, metavar="SECONDS",
        help="Kill job after N seconds (0 = disabled)",
    )
    parser.add_argument(
        "--retries", type=int, default=0, metavar="N",
        help="Retry failed jobs up to N times",
    )
    parser.add_argument(
        "--retry-delay", type=float, default=1.0, metavar="SECONDS",
        help="Seconds to wait between retries",
    )
    parser.add_argument(
        "--job-name", default=None,
        help="Human-readable job name used in logs",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    command = args.command
    # argparse REMAINDER may include a leading '--'
    if command and command[0] == "--":
        command = command[1:]

    if not command:
        parser.error("No command specified.")

    job_name = args.job_name or command[0]

    timeout_cfg = TimeoutConfig(seconds=args.timeout)
    retry_policy = RetryPolicy(
        max_attempts=args.retries + 1,
        delay=args.retry_delay,
    )

    job = CronJob(
        name=job_name,
        command=command,
        timeout=timeout_cfg,
        retry_policy=retry_policy,
    )

    result = job.run()
    print(result.summary())
    return result.exit_code if result.exit_code is not None else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
