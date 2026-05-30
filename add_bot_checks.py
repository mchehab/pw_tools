#!/usr/bin/env python3

"""
Process CI bot emails and update Patchwork checks.
"""

import sys
import os
import argparse
import logging
from lib.pw_checker import PatchworkChecker
from lib.bot_check import BotEmailProcessor, MaildirProcessor


CONFIG_FILE = os.environ.get("PWCLIENTRC", os.path.expanduser("~/.pwclientrc"))

EPILOG = """
Examples:
  %(prog)s --file message.eml --dry-run
  %(prog)s --maildir /var/mail/ci --move-processed --dry-run
"""

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=EPILOG)

    parser.add_argument("--project", "-p",
                        help=".pwclientrc project entry to use (if not specified, use default}")
    parser.add_argument("--config", "-c",
                        help="config file to use (optional)")
    parser.add_argument("--url", "-u",
                        help="Patchwork's REST API base URL")
    parser.add_argument("--token", "-t",
                        help="Patchwork's REST API token")

    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate without updating patchwork status")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=str,
                       help="Path to a single email .eml file")
    group.add_argument("--maildir", type=str,
                       help="Path to a Maildir directory")


    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger(__name__)

    if not args.url and not args.config:
        args.config = CONFIG_FILE

    checker = PatchworkChecker(config_file=args.config, entry=args.project,
                               url=args.url, token=args.token)

    if args.file:
        proc = BotEmailProcessor(checker, logger, dry_run=args.dry_run)
        if not  proc.process_file(args.file):
            sys.exit("Failed to add checker")

    elif args.maildir:
        maildir_proc = MaildirProcessor(args.maildir, checker,
                                        logger, dry_run=args.dry_run)
        count = maildir_proc.process_all()
        logger.info(f"Finished. Successfully added {count} check results.")

if __name__ == "__main__":
    main()
