#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0
# Copyright 2026 Mauro Carvalho Chehab <mchehab+huawei@kernel.org>

"""
Patchwork Checker - Get and update patch checks on patchwork.
"""

import configparser
import logging
import sys

from typing import Optional, List, Dict, Any

import requests


class PatchworkChecker:
    """
    Allow get/update Patchwork checks done via CI
    """
    def __init__(self,
                 config_file: Optional[str] = None,
                 entry: Optional[str] = None,
                 url: Optional[str] = None,
                 token: Optional[str] = None,
                 logger: Optional[logging.Logger] = None,
                 timeout: int = 10, max_retries: int = 3) -> None:
        if logger:
            self.logger = logger
        else:
            logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
            self.logger = logging.getLogger(__name__)

        self.timeout = timeout

        if url:
            self.url = url
            self.token = token
        elif not config_file:
            sys.exit("At least config_file or both url and token is needed.")
        else:
            config = configparser.ConfigParser()
            try:
                config.read([config_file])
            except configparser.Error as e:
                sys.exit(f"Can't read {config_file}: {e}")

            if not entry:
                try:
                    entry = config.get("options", "default")
                except configparser.Error:
                    sys.exit(f"Default project not configured at {config_file}")

            try:
                self.url = config.get(entry, "url").removesuffix("/")
            except configparser.Error:
                sys.exit(f"Project {entry}: URL is missing at {config_file}")
            try:
                self.token = config.get(entry, "token")
            except configparser.Error:
                sys.exit(f"Project {entry}: token is missing at {config_file}")

        self.session = requests.Session()
        self.session.mount("https://",
                           requests.adapters.HTTPAdapter(max_retries=max_retries))

        # For get, token can be optional
        if self.token:
            self.session.headers.update({
                "Authorization": f"Token {self.token}",
            })

    def _resolve_patch_id(self, identifier: str) -> Optional[int]:
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
            response = self.session.get(url, params=params, timeout=self.timeout)
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

    def get_checks(self, identifier: str) -> List[Dict[str, Any]]:
        """Fetch all checks for a specific patch."""
        patch_id = self._resolve_patch_id(identifier)
        if patch_id is None:
            self.logger.warning(f"patch {patch_id} not found.")
            return []

        url = f"{self.url}/patches/{patch_id}/checks/"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            return data.get("results", data) if isinstance(data, dict) else data
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching checks for patch {patch_id}: {e}")
            return []

    def set_check(self, identifier: str, context: str,
                  state: str, target_url: str,
                  description: str, dry_run: bool = False) -> bool:
        """Set a check status for a specific patch."""
        patch_id = self._resolve_patch_id(identifier)
        if patch_id is None:
            self.logger.warning(f"patch {patch_id} not found.")
            return False

        url = f"{self.url}/patches/{patch_id}/checks/"
        data = {
            "state": state.lower(),  # Patchwork requires lowercase states
            "target_url": target_url,
            "context": context,
            "description": description,
        }

        if dry_run:
            self.logger.info(f"[dry-run] {url}: add {data}")
            return True

        try:
            response = self.session.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            self.logger.info(f"{patch_id}: {data["context"]} set to '{data["state"]}'")

            return True
        except requests.exceptions.RequestException as e:
            self.logger.error(f"{patch_id}: {data["context"]} failed to set '{data["state"]}'")
            return False
