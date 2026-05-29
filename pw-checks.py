#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0
# Copyright 2026 Mauro Carvalho Chehab <mchehab+huawei@kernel.org>

"""
Patchwork Checker - Get and update patch checks on patchwork.
"""

import argparse
import configparser
import logging
import os
import sys

import requests

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


class PatchWorkChecker:
    def __init__(self, entry=None, logger=None):
        config = configparser.ConfigParser()
        try:
            config.read([CONFIG_FILE])
        except configparser.Error as e:
            sys.exit(f"Can't read {CONFIG_FILE}")

        if logger:
            self.logger = logger
        else:
            logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
            self.logger = logging.getLogger(__name__)

        if not entry:
            try:
                entry = config.get("options", "default")
            except configparser.Error as e:
                sys.exit(f"Default project not configured at {CONFIG_FILE}")

        try:
            self.url = config.get(entry, "url").removesuffix("/")
        except configparser.Error as e:
            sys.exit(f"Project {entry}: URL is missing at {CONFIG_FILE}")
        try:
            self.token = config.get(entry, "token")
        except configparser.Error as e:
            sys.exit(f"Project {entry}: token is missing at {CONFIG_FILE}")

        self.session = requests.Session()
        self.session.mount("https://",
                           requests.adapters.HTTPAdapter(max_retries=3))
        self.session.headers.update({
            "Authorization": f"Token {self.token}",
        })

    def _resolve_patch_id(self, identifier):
        """
        Resolve a patch ID from either a numeric patch-id or a message-id.
        Uses the official API /patches/ endpoint with the msgid filter.
        """
        # Strip optional angle brackets and surrounding whitespace
        identifier = identifier.strip("<>").strip()

        # If already a valid integer, return it directly
        if identifier.isdigit():
            return int(identifier)

        # Query Patchwork API to resolve message-id to patch ID
        url = f"{self.url}/patches/"
        params = {"msgid": identifier, "per_page": 1}

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict):
                patches = data.get("results", data)
            else:
                patches = data

            if not patches:
                self.logger.error(f"No patch found for message-id: {identifier}")
                return None

            return patches[0]["id"]
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to resolve message-id {identifier}: {e}")
            return None

    def get_checks(self, identifier):
        """Fetch all checks for a specific patch."""
        patch_id = self._resolve_patch_id(identifier)
        if patch_id is None:
            return []

        url = f"{self.url}/patches/{patch_id}/checks/"
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("results", data) if isinstance(data, dict) else data
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching checks for patch {patch_id}: {e}")
            return []

    def set_check(self, identifier, context, state, target_url, description):
        """Set a check status for a specific patch."""
        patch_id = self._resolve_patch_id(identifier)
        if patch_id is None:
            return False

        url = f"{self.url}/patches/{patch_id}/checks/"
        check_data = {
            "state": state.lower(),  # Patchwork requires lowercase states
            "target_url": target_url,
            "context": context,
            "description": description,
        }

        try:
            response = self.session.post(url, json=check_data, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error setting check for patch {patch_id}: {e}")
            return False


def main():
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

    checker = PatchWorkChecker(args.project)

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
                                    args.state, args.url, args.description)
        if success:
            print(f"{args.context} {args.identifier} set to '{args.state}'")
        else:
            sys.exit(f"Failed to set check for {args.identifier}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
