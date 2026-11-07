"""Offline regression checks for Keychain discovery and zsh helpers.

All Keychain and clipboard commands are replaced with test functions. Only
synthetic metadata and credentials are used.
"""

import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest import mock


HELPER_DIR = Path(os.environ.get("KEYCHAIN_HELPER_DIR", Path(__file__).resolve().parents[1] / "home/dot_config/keychain"))
SPEC = importlib.util.spec_from_file_location("keychain_inventory", HELPER_DIR / "inventory.py")
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


def metadata_item(service, account="tester", label="", kind="genp", keychain="/test/login.keychain-db"):
    field = "srvr" if kind == "inet" else "svce"
    return (
        f'keychain: "{keychain}"\n'
        'version: 512\n'
        f'class: "{kind}"\n'
        'attributes:\n'
        f'    "{field}"<blob>="{service}"\n'
        f'    "acct"<blob>="{account}"\n'
        f'    0x00000007 <blob>="{label}"\n'
    )


FIXTURE = "".join([
    metadata_item("ORCHID_API_KEY", label="Flower service"),
    metadata_item("ORCHID_API_KEY", account="other", label="Alternate account"),
    metadata_item("ORCHID_API_KEY", label="Second keychain", keychain="/test/other.keychain-db"),
    metadata_item("service[prod].*", label="Literal symbols"),
    metadata_item("serviceprodXX", label="Different service"),
    metadata_item("orchid.example", account="web-user", kind="inet", label="Website login"),
    metadata_item("Not a password", kind="cert"),
])


class InventoryTests(unittest.TestCase):
    def run_main(self, argv, *, raw=FIXTURE, rc=0, error=""):
        output, errors = io.StringIO(), io.StringIO()
        result = subprocess.CompletedProcess(["mock"], rc, stdout=raw, stderr=error)
        with mock.patch.object(inventory.subprocess, "run", return_value=result) as run:
            with mock.patch.object(inventory.getpass, "getuser", return_value="tester"):
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                    code = inventory.main(argv)
        self.assertEqual(run.call_args.args[0], ["/usr/bin/security", "dump-keychain"])
        self.assertFalse(set(run.call_args.args[0]) & {"-w", "-g", "-d", "-r", "-a", "-i"})
        return code, output.getvalue(), errors.getvalue()

    def test_numeric_label_with_space_and_password_classes(self):
        items = inventory.parse_metadata(FIXTURE)
        self.assertEqual(len(items), 6)
        self.assertEqual(items[0]["label"], "Flower service")
        self.assertEqual(items[0]["keychain"], "/test/login.keychain-db")
        self.assertEqual(items[-1]["server"], "orchid.example")

    def test_hex_utf8_null_and_escaped_values(self):
        self.assertEqual(inventory.decode_value('0x436166c3a9 "ignored rendering"'), "Café")
        self.assertEqual(inventory.decode_value("<NULL>"), "")
        self.assertEqual(inventory.decode_value(r'"quote\" and slash\\ and tab\t and octal\101"'),
                         'quote" and slash\\ and tab\t and octalA')
        raw = metadata_item("placeholder").replace('"placeholder"', '0x436166c3a9')
        self.assertEqual(inventory.parse_metadata(raw)[0]["service"], "Café")

    def test_search_is_case_insensitive_and_literal(self):
        items = inventory.parse_metadata(FIXTURE)
        self.assertEqual(len(inventory.select_items(items, ["oRcHiD"])), 4)
        matches = inventory.select_items(items, ["[prod].*"])
        self.assertEqual([item["service"] for item in matches], ["service[prod].*"])
        matches = inventory.select_items(items, ["ORCHID", "other"])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["account"], "other")

    def test_default_own_account_and_all_accounts(self):
        own = inventory.select_items(inventory.parse_metadata(FIXTURE), [], "tester", True)
        self.assertEqual(len(own), 4)
        self.assertTrue(all(item["type"] == "genp" for item in own))
        code, output, errors = self.run_main([])
        self.assertEqual(code, 0)
        self.assertNotIn("web-user", output)
        self.assertNotIn("Alternate account", output)
        self.assertEqual(errors, "")
        code, output, errors = self.run_main(["--all", "orchid"])
        self.assertEqual(code, 0)
        self.assertIn("web-user", output)
        self.assertIn("Alternate account", output)
        self.assertIn("internet", output)

    def test_names_are_unique_generic_services_and_allow_explicit_account(self):
        code, output, errors = self.run_main(["--names"])
        self.assertEqual(code, 0)
        self.assertEqual(output.splitlines().count("ORCHID_API_KEY"), 1)
        self.assertNotIn("orchid.example", output)
        code, output, errors = self.run_main(["--names", "--account", "other"])
        self.assertEqual(output, "ORCHID_API_KEY\n")
        code, output, errors = self.run_main(["--all", "--names"])
        self.assertNotIn("orchid.example", output)

    def test_no_match_differs_from_scan_failure_even_with_partial_output(self):
        code, output, errors = self.run_main(["unknown-service"])
        self.assertEqual(code, 1)
        self.assertIn("No matching items", output)
        self.assertEqual(errors, "")
        code, output, errors = self.run_main([], rc=1, error="Permission denied")
        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertIn("status is unknown", errors)
        self.assertIn("Permission denied", errors)

    def test_missing_security_binary_is_an_error(self):
        errors = io.StringIO()
        with mock.patch.object(inventory.subprocess, "run", side_effect=OSError("test unavailable")):
            with contextlib.redirect_stderr(errors):
                code = inventory.main([])
        self.assertEqual(code, 2)
        self.assertIn("Cannot read Keychain metadata", errors.getvalue())

    def test_control_characters_cannot_reach_table_or_completion(self):
        raw = metadata_item(r"bad\x1b[31m", label=r"line\nbreak")
        code, output, errors = self.run_main([], raw=raw)
        self.assertEqual(code, 0)
        self.assertNotIn("\x1b", output)
        self.assertIn(r"\x1b", output)
        self.assertIn(r"line\nbreak", output)
        code, output, errors = self.run_main(["--names"], raw=raw)
        self.assertEqual(output, "")


class ShellTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="keychain-offline-tests-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        helper = (HELPER_DIR / "helpers.zsh").read_text()
        self.assertIn("/usr/bin/security", helper)
        self.assertIn("/usr/bin/pbcopy", helper)
        helper = helper.replace("/usr/bin/security", "test-security")
        helper = helper.replace("/usr/bin/pbcopy", "test-pbcopy")
        helper = helper.replace('command python3 "$HOME/.config/keychain/inventory.py" "$@"', 'test-inventory "$@"')
        self.assertNotIn("/usr/bin/security", helper)
        self.assertNotIn("/usr/bin/pbcopy", helper)
        self.helper = self.directory / "helpers.zsh"
        self.helper.write_text(helper)
        self.security_log = self.directory / "security-args"
        self.clipboard_log = self.directory / "clipboard"
        self.inventory_log = self.directory / "inventory-args"

    def run_shell(self, body, *, rc=0, stderr="", stdin=""):
        script = self.directory / "check.zsh"
        script.write_text(r'''
test-security() {
  printf '%s\0' "$@" >> "$TEST_SECURITY_LOG"
  local result=$TEST_SECURITY_RC arg previous='' service=''
  for arg in "$@"; do
    [[ "$previous" == -s ]] && service="$arg"
    previous="$arg"
  done
  if [[ "$TEST_RC_BY_SERVICE" == yes ]]; then
    case "$service" in
      missing) result=44 ;;
      failed) result=36 ;;
      *) result=0 ;;
    esac
  fi
  [[ -n "$TEST_SECURITY_ERROR" ]] && print -ru2 -- "$TEST_SECURITY_ERROR"
  if (( result == 0 )) && [[ " $* " == *" -w "* ]]; then
    print -r -- 'synthetic-secret-only'
  fi
  return "$result"
}
test-pbcopy() {
  cat > "$TEST_CLIPBOARD_LOG"
}
''' + "\nsource " + shlex.quote(str(self.helper)) + "\n" + r'''
keychain-inventory() {
  printf '%s\0' "$@" >> "$TEST_INVENTORY_LOG"
  print -r -- 'ORCHID_API_KEY'
  print -r -- 'Service with spaces'
}
''' + "\n" + body + "\n")
        environment = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(self.directory),
            "USER": "tester",
            "TEST_SECURITY_LOG": str(self.security_log),
            "TEST_CLIPBOARD_LOG": str(self.clipboard_log),
            "TEST_INVENTORY_LOG": str(self.inventory_log),
            "TEST_SECURITY_RC": str(rc),
            "TEST_SECURITY_ERROR": stderr,
        }
        return subprocess.run(["/bin/zsh", "-f", str(script)], input=stdin,
                              capture_output=True, text=True, env=environment, timeout=10)

    def security_args(self):
        if not self.security_log.exists():
            return []
        return self.security_log.read_bytes().decode().split("\0")[:-1]

    def test_source_never_queries_keychain_or_clipboard(self):
        result = self.run_shell(":")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.security_args(), [])
        self.assertFalse(self.clipboard_log.exists())
        self.assertFalse(self.inventory_log.exists())

    def test_get_preserves_exact_arguments_and_stdout_only_secret(self):
        result = self.run_shell("keychain-get 'Service [prod]' 'other account' '/test/custom keychain'")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "synthetic-secret-only\n")
        self.assertEqual(result.stderr, "")
        self.assertEqual(self.security_args(), ["find-generic-password", "-a", "other account",
                                              "-s", "Service [prod]", "-w", "/test/custom keychain"])

    def test_get_defaults_to_current_user_and_propagates_failure(self):
        result = self.run_shell("keychain-get ORCHID_API_KEY", rc=44, stderr="synthetic missing")
        self.assertEqual(result.returncode, 44)
        self.assertEqual(result.stdout, "")
        self.assertIn("synthetic missing", result.stderr)
        self.assertEqual(self.security_args(), ["find-generic-password", "-a", "tester",
                                              "-s", "ORCHID_API_KEY", "-w"])

    def test_has_is_metadata_only_and_distinguishes_failure(self):
        result = self.run_shell("keychain-has Orchid 'other account' '/test/keychain'")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "Orchid: present\n")
        self.assertEqual(self.security_args(), ["find-generic-password", "-a", "other account",
                                              "-s", "Orchid", "/test/keychain"])
        result = self.run_shell("keychain-has Orchid", rc=44)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "Orchid: missing\n")
        result = self.run_shell("keychain-has Orchid", rc=36)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("status unknown", result.stderr)

    def test_audit_propagates_most_severe_failure(self):
        result = self.run_shell("TEST_RC_BY_SERVICE=yes\nkeychain-audit failed present missing")
        self.assertEqual(result.returncode, 2)
        self.assertIn("present: present", result.stdout)
        self.assertIn("missing: missing", result.stdout)
        self.assertIn("failed: Keychain lookup failed", result.stderr)
        result = self.run_shell("TEST_RC_BY_SERVICE=yes\nkeychain-audit present missing")
        self.assertEqual(result.returncode, 1)

    def test_failed_copy_does_not_touch_clipboard(self):
        result = self.run_shell("keychain-copy Orchid", rc=44)
        self.assertEqual(result.returncode, 44)
        self.assertFalse(self.clipboard_log.exists())
        self.assertEqual(result.stdout, "")

    def test_successful_copy_only_reports_status(self):
        result = self.run_shell("keychain-copy Orchid")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("synthetic-secret-only", result.stderr)
        self.assertEqual(self.clipboard_log.read_text(), "synthetic-secret-only")

    def test_set_and_delete_refuse_nonterminal(self):
        for command in ("keychain-set Orchid", "keychain-delete Orchid"):
            with self.subTest(command=command):
                result = self.run_shell(command, stdin="yes\nsynthetic-secret\n")
                self.assertEqual(result.returncode, 2)
                self.assertIn("terminal", result.stderr)
                self.assertEqual(self.security_args(), [])

    def test_discovery_dispatch_is_literal_and_never_reads_password(self):
        result = self.run_shell("kc 'orchid[prod]'")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.security_args(), [])
        self.assertEqual(self.inventory_log.read_bytes().split(b"\0")[:-1],
                         [b"--all", b"--", b"orchid[prod]"])

    def test_completion_is_lazy_and_preserves_spaced_names(self):
        result = self.run_shell("compadd() { printf '<%s>\\n' \"$@\"; }\n"
                                "CURRENT=2\nwords=(kc '')\nkeychain-completion")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("<search>", result.stdout)
        self.assertFalse(self.inventory_log.exists())
        result = self.run_shell("compadd() { printf '<%s>\\n' \"$@\"; }\n"
                                "CURRENT=3\nwords=(kc get '')\nkeychain-completion")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("<ORCHID_API_KEY>", result.stdout)
        self.assertIn("<Service with spaces>", result.stdout)
        self.assertEqual(self.security_args(), [])
        self.assertEqual(self.inventory_log.read_bytes(), b"--names\0")


if __name__ == "__main__":
    unittest.main()
