#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0
# Copyright 2026 Mauro Carvalho Chehab <mchehab+huawei@kernel.org>

import email
import email.utils
import logging
import os

from typing import Optional

from .pw_checker import PatchworkChecker

BOTS = {
    "lkp@intel.com": "LDP",
    "syzbot@syzkaller.appspotmail.com": "syzbot",
    "sashiko-bot@kernel.org": "sashiko",
}

LORE_BASE_URL = "https://lore.kernel.org/all"


class BotEmailProcessor:
    def __init__(self, patchwork_checker: PatchworkChecker,
                 logger: Optional[logging.Logger]=None,
                 dry_run: Optional[bool]=False):
        if logger:
            self.logger = logger
        else:
            logging.basicConfig(level=logging.INFO,
                                format="%(levelname)s: %(message)s")
            self.logger = logging.getLogger(__name__)

        self.dry_run = dry_run
        self.patchwork_checker = patchwork_checker

    @staticmethod
    def _extract_email(header_value: str) -> Optional[str]:
        """Sanitize e-mail, picking only its address"""
        header_value = header_value.strip("<>").strip()

        if not header_value:
            return None

        _, addr = email.utils.parseaddr(header_value)

        username, _, url = addr.partition("@")
        if not url:
            return None

        username = username.split("+", 1)[0]

        return f"{username}@{url}"

    def process_file(self, fname: str) -> bool:
        fname = os.path.expanduser(fname)
        if not os.path.isfile(fname):
            sys.exit(f"Error: File not found: {fname}")

        try:
            with open(fname, 'rb') as f:
                msg = email.message_from_binary_file(f)

            msgid = msg.get("Message-ID").strip("<>").strip()
            if not msgid:
                return False

            reply_id = msg.get("In-Reply-To")
            if not reply_id:
                reply_id = msg.get("References")

            reply_id = reply_id.strip("<>").strip()

            if not reply_id:
                return False

            addr = self._extract_email(msg.get("From"))
            if not addr or addr not in BOTS:
                return False

            url = f"{LORE_BASE_URL}/{msgid}"

            return self.patchwork_checker.set_check(identifier=reply_id,
                                                    context=BOTS[addr],
                                                    state="warning",
                                                    target_url=url,
                                                    description="Link",
                                                    dry_run=self.dry_run)
        except Exception as e:
            self.logger.error(f"Failed to process {fname}: {repr(e)}")
            return False


class MaildirProcessor:
    def __init__(self, maildir: str,
                 patchwork_checker: PatchworkChecker,
                 logger: Optional[logging.Logger]=None,
                 dry_run: Optional[bool]=False):
        if not maildir.is_dir():
            raise FileNotFoundError(f"Maildir directory not found: {self.maildir}")

        self.maildir = os.path.expanduser(maildir)
        self.bot_processor = BotEmailProcessor(patchwork_checker,
                                               logger=logger,
                                               dry_run=dry_run)


    def process_all(self) -> int:
        """Iterate through cur/ new and process each email."""
        count = 0
        for folder in ["cur", "new"]:
            folder_path = os.path.join(self.maildir, folder)
            if not os.path.isdir(folder_path.is_dir):
                continue

            for fname in os.listdir(folder_path):
                fpath = os.path.join(folder_path, fname)
                if fpath.is_file():
                    if self.bot_processor.process_file(fpath):
                        count += 1

        return count
