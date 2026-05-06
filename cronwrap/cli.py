"""Command-line interface for cronwrap."""

import argparse
import sys

from cronwrap.lock import JobLock, LockAcquisitionError, LockConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap",
        description="Lightweight wrapper for cron jobs with logging, alerting, and retry logic.",
    )
    parser.add_argument("job_name", help="Unique name for the cron job")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to execute")
    parser.add_argument(
        "--timeout", type=int, default=0, metavar="SECONDS",
        help="Kill job after SECONDS (0 = disabled)",
    )
    parser.add_argument(
        "--retries", type=int, default=0, metavar="N",
        help="Number of retry attempts on failure",
    )
    parser.add_argument(
        "--retry-delay", type=float, default=5.0, metavar="SECONDS",
        help="Delay between retries in seconds",
    )
    parser.add_argument(
        "--log-file", default=None, metavar="PATH",
        help="Path to log file (defaults to stderr)",
    )
    parser.add_argument(
        "--lock", action="store_true",
        help="Prevent overlapping executions using a lock file",
    )
    parser.add_argument(
        "--lock-dir", default="/tmp/cronwrap/locks", metavar="DIR",
        help="Directory for lock files (default: /tmp/cronwrap/locks)",
    )
    parser.add_argument(
        "--stale-lock-after", type=int, default=3600, metavar="SECONDS",
        help="Consider lock stale after SECONDS (default: 3600)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.error("A command to execute is required.")

    if args.lock:
        lock_cfg = LockConfig(
            lock_dir=args.lock_dir,
            stale_after_seconds=args.stale_lock_after,
        )
        lock = JobLock(args.job_name, lock_cfg)
        try:
            lock.acquire()
        except LockAcquisitionError as exc:
            print(f"cronwrap: {exc}", file=sys.stderr)
            return 1
    else:
        lock = None

    try:
        from cronwrap.core import CronJob
        from cronwrap.retry import RetryPolicy
        from cronwrap.timeout import TimeoutConfig

        timeout_cfg = TimeoutConfig(seconds=args.timeout)
        retry_policy = RetryPolicy(
            max_attempts=args.retries + 1,
            delay=args.retry_delay,
        )
        job = CronJob(
            name=args.job_name,
            command=args.command,
            timeout=timeout_cfg,
            retry_policy=retry_policy,
        )
        result = job.run()
        return 0 if result.succeeded else 1
    finally:
        if lock is not None:
            lock.release()


if __name__ == "__main__":
    sys.exit(main())
