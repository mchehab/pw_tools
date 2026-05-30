#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0
# Copyright 2026 Mauro Carvalho Chehab <mchehab+huawei@kernel.org>

"""
Patchwork Checker - Get and update patch checks on patchwork.
"""

import argparse
import os
import sys

from lib.pw_checker import PatchworkChecker

CONFIG_FILE = os.environ.get("PWCLIENTRC", os.path.expanduser("~/.pwclientrc"))

FNAME = os.path.basename(__file__)

EPILOG = f"""
Examples:
  get <message-id or patch-id>
      Show checks for a specific patch.
      Supports both patch-id and message-id (with or without angle brackets).

  set <message-id or patch-id> <context> <state> <URL> <description>
      Set check status for a specific patch.

      Example:
          {FNAME} set 12345 MyCI success https://ci.example.com "Build passed"
          {FNAME} set patch-id-12345@thread.gmane.org warning https://lint.example.com "lint warning. See link for details"
"""


def main():
    """Main code"""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=EPILOG)
    parser.add_argument("--project", "-p",
                        help=".pwclientrc project entry to use (if not specified, use default}")

    subparsers = parser.add_subparsers(dest="command", required=False)

    get_parser = subparsers.add_parser("get",
                                       help="List all checks for a specific patch")
    get_parser.add_argument("identifier",
                            help="Patch ID or Message-ID (e.g., 12345 or patch-id@domain.com)")

    set_parser = subparsers.add_parser("set",
                                       help="Set check status for a specific patch")
    set_parser.add_argument("--dry-run", action="store_true",
                            help="Simulate adding a new check")
    set_parser.add_argument("identifier", help="Patch ID or Message-ID")
    set_parser.add_argument("context",
                            help="Check context/name (e.g., CI, Lint, Build)")
    set_parser.add_argument("state",
                            help="Check state (e.g., success, fail, warning)")
    set_parser.add_argument("url", help="Target URL for the check")
    set_parser.add_argument("description", help="Description of the check")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    checker = PatchworkChecker(CONFIG_FILE, args.project)

    if args.command == "get":
        checks = checker.get_checks(args.identifier)
        if checks:
            print(f"Checks for {args.identifier}:")
            for i, check in enumerate(checks, 1):
                print(f"  {i:2d}. [{check.get('state')}] {check.get('context')}: {check.get('target_url')}")
        else:
            print("  No CI checks found.")

    elif args.command == "set":
        success = checker.set_check(args.identifier, args.context,
                                    args.state, args.url, args.description,
                                    dry_run=args.dry_run)
        if success:
            print(f"{args.context} {args.identifier} set to '{args.state}'")
        else:
            sys.exit(f"Failed to set check for {args.identifier}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
