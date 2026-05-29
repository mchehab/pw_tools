# Patchwork tools

This repository contains some tools meant to be used with Patchwork.

Currently, it has one one tool: pw-checks.py.

## pw-checks.py

This small tool allows get/set CI checks for a patchwork patch. It
works with pwclient's configuration file (`~/.pwclientrc`). Only rest
API mode (version 1.3) is supported, and requires a token to be set.

An example of a `~/.pwclientrc` file is this one:

```ini
[options]
default = kernel-org

[kernel]
backend = rest
url = https://patchwork.kernel.org/api/
token = some_token

[linuxtv]
backend = rest
url = https://patchwork.linuxtv.org/api/
token = some_other_token
```

The location of the configuration file can be overriden using
an ENV var:

```bash
set PWCLIENTRC=/some/other/config/file
```

The script has two commands:

### Get checks

Usage:

```bash
get <message-id or patch-id>
```

Show checks for a specific patch.

### Get checks

Usage:

```bash
  set <message-id or patch-id> <context> <state> <URL> <description>
```

Set check status for a specific patch.

Examples:

Set success:

At default project:

```bash
pw-checks.py set 12345 MyCI success https://ci.example.com "Build passed"
```

On another project:

```bash
pw-checks.py -p project2 set 12345 MyCI success https://ci.example.com "Build passed"
```

Set warning:

```bash
pw-checks.py set patch-id-12345@example.com warning https://lint.example.com "See link for details"
```
