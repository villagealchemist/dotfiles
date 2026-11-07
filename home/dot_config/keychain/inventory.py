"""Search macOS Keychain metadata without requesting password data."""

import argparse
import getpass
import re
import subprocess
import sys


ATTRIBUTES = {"svce": "service", "srvr": "server", "acct": "account",
              "labl": "label", "0x00000007": "label"}


def decode_value(value):
    value = value.strip()
    if value == "<NULL>":
        return ""
    if value.startswith("0x"):
        match = re.match(r"0x([0-9a-fA-F]+)", value)
        if match:
            try:
                return bytes.fromhex(match[1]).decode("utf-8", errors="replace")
            except ValueError:
                pass
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
        escapes = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}

        def unescape(match):
            escaped = match[1]
            if escaped.startswith("x"):
                return chr(int(escaped[1:], 16))
            if escaped[0] in "01234567":
                return chr(int(escaped, 8))
            return escapes[escaped]

        return re.sub(r'\\(x[0-9a-fA-F]{2}|[0-7]{1,3}|[nrt"\\])', unescape, value)
    return value


def parse_metadata(raw):
    items = []
    current = None
    keychain = ""
    for line in raw.splitlines():
        if line.startswith("keychain: "):
            keychain = decode_value(line[len("keychain: "):])
        elif line.startswith("class: "):
            current = {"type": decode_value(line[len("class: "):]), "keychain": keychain}
            items.append(current)
        elif current is not None:
            match = re.match(r'\s*(?:"([^"]+)"|(0x[0-9a-fA-F]+))\s*<[^>]+>\s*=\s*(.*)$', line)
            if match:
                name = ATTRIBUTES.get(match[1] or match[2])
                if name:
                    current[name] = decode_value(match[3])
    return [item for item in items if item["type"] in ("genp", "inet")]


def select_items(items, queries, account=None, generic_only=False):
    selected = []
    for item in items:
        if generic_only and item["type"] != "genp":
            continue
        if account is not None and item.get("account", "") != account:
            continue
        fields = [item.get(field, "").casefold()
                  for field in ("service", "server", "account", "label")]
        if all(any(query.casefold() in field for field in fields) for query in queries):
            selected.append(item)
    return sorted(selected, key=lambda item: (
        item.get("service", item.get("server", "")).casefold(),
        item.get("account", ""), item["keychain"], item["type"]))


def display_text(value):
    # Keep untrusted metadata from injecting terminal control sequences.
    return "".join(char if char.isprintable() else ascii(char)[1:-1] for char in value)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="include all accounts and internet items")
    parser.add_argument("--names", action="store_true", help="generic service names for completion")
    parser.add_argument("--account", help="match one exact account")
    parser.add_argument("query", nargs="*")
    args = parser.parse_args(argv)
    try:
        result = subprocess.run(["/usr/bin/security", "dump-keychain"],
                                capture_output=True, text=True, errors="replace", check=False)
    except OSError as exc:
        print(f"Cannot read Keychain metadata: {exc}", file=sys.stderr)
        return 2
    if result.returncode:
        print("Keychain metadata search failed; saved-item status is unknown.", file=sys.stderr)
        if result.stderr.strip():
            print(display_text(result.stderr.strip()), file=sys.stderr)
        return 2
    account = args.account
    if account is None and not args.all:
        account = getpass.getuser()
    items = select_items(parse_metadata(result.stdout), args.query, account,
                         generic_only=args.names or not args.all)
    if args.names:
        names = sorted({item.get("service", "") for item in items})
        for name in names:
            if name and all(char.isprintable() for char in name):
                print(name)
        return 0
    if not items:
        print("No matching items in the accessible Keychain search list.")
        return 1
    rows = [("TYPE", "SERVICE / SERVER", "ACCOUNT", "LABEL", "KEYCHAIN")]
    for item in items:
        rows.append(tuple(display_text(value) for value in (
            "generic" if item["type"] == "genp" else "internet",
            item.get("service", item.get("server", "")),
            item.get("account", ""), item.get("label", ""), item["keychain"])))
    widths = [max(len(row[column]) for row in rows) for column in range(4)]
    for row in rows:
        print("  ".join(value.ljust(widths[column]) if column < 4 else value
                        for column, value in enumerate(row)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
