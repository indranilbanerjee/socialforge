"""Where credential_manager.py keeps a key (1.31.0).

Before 1.31.0 `setup-wavespeed` and `setup-higgsfield` copied the key (and the secret) from the environment into
credentials.json in plain text, `setup-vertex` copied the service-account JSON next to it, `chmod 600` was the only
protection (a no-op on Windows), and `--api-key` / `--api-secret` still took a key on the command line, where it lands in
shell history and the process table. Now:

  * a key that is in the environment is never written: credentials.json records the variable NAME, and the value is read
    from the environment each time it is needed;
  * a key given through --api-key-stdin or --prompt goes to the OS keychain when the optional `keyring` package has a
    working backend, and otherwise to the file with a warning that says "plain text";
  * the service-account JSON is used where the user keeps it: its path is recorded and no copy is made (an older copy is
    left alone and reported);
  * on Windows a file that may hold a secret is limited to the current account with icacls, run as an argument list;
  * --api-key / --api-secret exit 2 before anything is read or written (tests/test_hermes_review_fixes.py runs the CLI).

No test reaches the real keychain: tests/_isolation.py selects keyring's null backend for the session, and the tests that
need a keychain hand the module a fake one. Stdlib only.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import credential_manager as cm  # noqa: E402
import install_deps  # noqa: E402

KEY = "k" * 24
HF_KEY, HF_SECRET = "a" * 24, "b" * 24
CLEAR_ENV = {"WAVESPEED_API_KEY": "", "HF_API_KEY": "", "HF_API_SECRET": ""}


class FakeKeyring:
    """Stands in for the `keyring` module: a dict, so nothing touches the user's real keychain."""

    def __init__(self, fail=False):
        self.store, self.fail = {}, fail

    def set_password(self, service, name, value):
        if self.fail:
            raise RuntimeError("locked")
        self.store[(service, name)] = value

    def get_password(self, service, name):
        return self.store.get((service, name))


class StoreTest(unittest.TestCase):
    """Each test gets its own credentials folder, an environment with no provider keys, and no keychain unless it asks."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sf-cred-"))
        patches = [
            mock.patch.object(cm, "CRED_DIR", self.tmp),
            mock.patch.object(cm, "CRED_FILE", self.tmp / "credentials.json"),
            mock.patch.object(cm, "GCP_KEY_FILE", self.tmp / "gcp-credentials.json"),
            mock.patch.object(cm, "_restrict_secret_file", return_value=None),
            mock.patch.object(cm, "_keyring", return_value=None),
            mock.patch.dict(os.environ, CLEAR_ENV),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        for name in CLEAR_ENV:
            os.environ.pop(name, None)

    def stored_text(self) -> str:
        return cm.CRED_FILE.read_text(encoding="utf-8") if cm.CRED_FILE.exists() else ""


class TestKeysFromTheEnvironmentAreNeverWritten(StoreTest):

    def test_wavespeed_records_the_variable_name_only(self):
        with mock.patch.dict(os.environ, {"WAVESPEED_API_KEY": KEY}):
            result = cm.setup_wavespeed(KEY, from_env=True)
            self.assertEqual((result["status"], result["source"]), ("success", "env"))
            self.assertNotIn(KEY, self.stored_text())
            self.assertEqual(json.loads(self.stored_text())["wavespeed"],
                             {"source": "env", "env_vars": ["WAVESPEED_API_KEY"]})
            self.assertEqual(cm.get_wavespeed_key(), KEY, "the value is read from the environment at call time")
            self.assertEqual(cm.validate_wavespeed(), {"configured": True, "source": "env_var"})
        # The variable gone: nothing was stored, so nothing is configured, and the error says why.
        self.assertIsNone(cm.get_wavespeed_key())
        self.assertFalse(cm.validate_wavespeed()["configured"])
        self.assertIn("does not see it", cm.validate_wavespeed()["error"])

    def test_higgsfield_records_both_names_only(self):
        with mock.patch.dict(os.environ, {"HF_API_KEY": HF_KEY, "HF_API_SECRET": HF_SECRET}):
            cm.setup_higgsfield(HF_KEY, HF_SECRET, from_env=True)
            self.assertEqual(cm.get_higgsfield_auth(), (HF_KEY, HF_SECRET))
        text = self.stored_text()
        self.assertNotIn(HF_KEY, text)
        self.assertNotIn(HF_SECRET, text)
        self.assertEqual(json.loads(text)["higgsfield"]["env_vars"], ["HF_API_KEY", "HF_API_SECRET"])

    def test_the_environment_wins_over_an_old_plaintext_key(self):
        cm.CRED_FILE.write_text(json.dumps({"wavespeed": {"api_key": "old" * 8}}), encoding="utf-8")
        with mock.patch.dict(os.environ, {"WAVESPEED_API_KEY": KEY}):
            self.assertEqual(cm.get_wavespeed_key(), KEY)
        self.assertEqual(cm.get_wavespeed_key(), "old" * 8, "an old plaintext key still works until setup replaces it")
        self.assertTrue(any("plain text" in w for w in cm.get_status().get("warnings", [])),
                        "status must say an old key sits in plain text")


class TestKeysGivenOnStdinGoToTheKeychain(StoreTest):

    def test_with_a_keychain_the_file_holds_no_value(self):
        fake = FakeKeyring()
        with mock.patch.object(cm, "_keyring", return_value=fake):
            result = cm.setup_wavespeed(KEY)
            self.assertEqual(result["source"], "keyring")
            self.assertNotIn("warnings", result)
            self.assertEqual(fake.store[(cm.KEYRING_SERVICE, "wavespeed_api_key")], KEY)
            self.assertNotIn(KEY, self.stored_text())
            self.assertEqual(cm.get_wavespeed_key(), KEY)
            self.assertEqual(cm.validate_wavespeed(), {"configured": True, "source": "keyring"})
            cm.setup_higgsfield(HF_KEY, HF_SECRET)
            self.assertEqual(cm.get_higgsfield_auth(), (HF_KEY, HF_SECRET))
            self.assertNotIn(HF_SECRET, self.stored_text())

    def test_without_a_keychain_the_file_fallback_warns_in_plain_words(self):
        with mock.patch("sys.stderr"):
            result = cm.setup_wavespeed(KEY)
        self.assertEqual(result["source"], "file")
        self.assertTrue(any("plain text" in w and "--groups keyring" in w for w in result["warnings"]), result)
        self.assertIn(KEY, self.stored_text(), "the fallback really is the file, and the warning says so")
        self.assertEqual(cm.validate_wavespeed()["source"], "plugin_data_file")

    def test_a_keychain_that_refuses_falls_back_and_says_why(self):
        with mock.patch.object(cm, "_keyring", return_value=FakeKeyring(fail=True)), mock.patch("sys.stderr"):
            result = cm.setup_wavespeed(KEY)
        self.assertEqual(result["source"], "file")
        self.assertIn("keychain refused", result["warnings"][0])

    def test_the_null_backend_counts_as_no_keychain(self):
        """tests/_isolation.py relies on this: keyring's null backend (priority -1) must never be used to 'store' a key."""
        for priority in (-1, 0, None):
            with self.subTest(priority=priority):
                fake_module = mock.MagicMock()
                fake_module.get_keyring.return_value = mock.Mock(priority=priority)
                with mock.patch.dict(sys.modules, {"keyring": fake_module}):
                    self.assertIsNone(SHIPPED_KEYRING())
        working = mock.MagicMock()
        working.get_keyring.return_value = mock.Mock(priority=5)
        with mock.patch.dict(sys.modules, {"keyring": working}):
            self.assertIs(SHIPPED_KEYRING(), working)
        with mock.patch.dict(sys.modules, {"keyring": None}):   # not installed
            self.assertIsNone(SHIPPED_KEYRING())

    def test_the_test_session_uses_the_null_backend(self):
        self.assertEqual(os.environ.get("PYTHON_KEYRING_BACKEND"), "keyring.backends.null.Keyring")


SHIPPED_KEYRING = cm._keyring   # captured before StoreTest patches the module attribute


class TestTheServiceAccountFileIsNotCopied(StoreTest):

    def write_sa(self, folder: Path) -> Path:
        path = folder / "my-sa.json"
        path.write_text(json.dumps({"type": "service_account", "project_id": "demo-project",
                                    "client_email": "sf@demo-project.iam.gserviceaccount.com"}), encoding="utf-8")
        return path

    def test_setup_records_the_path_and_makes_no_copy(self):
        with tempfile.TemporaryDirectory() as user_dir:
            sa = self.write_sa(Path(user_dir))
            result = cm.setup_vertex_ai(str(sa))
            self.assertEqual(result["status"], "success", result)
            self.assertFalse(cm.GCP_KEY_FILE.exists(), "setup must not copy the key file any more")
            record = json.loads(self.stored_text())["vertex_ai"]
            self.assertEqual(Path(record["credentials_file"]), sa.resolve())
            self.assertNotIn("private_key", self.stored_text())
            self.assertNotIn("warnings", result)

    def test_an_older_copy_is_left_in_place_and_reported(self):
        cm.GCP_KEY_FILE.write_text("{}", encoding="utf-8")
        with tempfile.TemporaryDirectory() as user_dir:
            result = cm.setup_vertex_ai(str(self.write_sa(Path(user_dir))))
        self.assertTrue(cm.GCP_KEY_FILE.exists(), "the old copy is the user's to delete")
        self.assertTrue(any("older SocialForge copy" in w for w in result.get("warnings", [])), result)
        self.assertTrue(any("older SocialForge copy" in w for w in cm.get_status().get("warnings", [])))


class TestWindowsFilePermissions(unittest.TestCase):
    """chmod 600 does nothing on Windows; icacls does, and it must run as an argument list."""

    def test_icacls_runs_as_a_list_with_inheritance_removed(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "credentials.json"
            path.write_text("{}", encoding="utf-8")
            done = mock.Mock(returncode=0)
            with mock.patch.object(cm.subprocess, "run", return_value=done) as run, \
                    mock.patch.dict(os.environ, {"USERNAME": "alice", "USERDOMAIN": "PC1"}):
                self.assertIsNone(cm._restrict_secret_file(path, windows=True))
            args, kwargs = run.call_args
            self.assertEqual(args[0], ["icacls", str(path), "/inheritance:r", "/grant:r", "PC1\\alice:F"])
            self.assertIsInstance(args[0], list)
            self.assertNotIn("shell", kwargs)

    def test_a_failed_icacls_is_reported_not_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "credentials.json"
            path.write_text("{}", encoding="utf-8")
            with mock.patch.object(cm.subprocess, "run", return_value=mock.Mock(returncode=5)):
                self.assertIn("other accounts", cm._restrict_secret_file(path, windows=True))
            with mock.patch.object(cm.subprocess, "run", side_effect=FileNotFoundError("icacls")):
                self.assertIn("other accounts", cm._restrict_secret_file(path, windows=True))

    def test_posix_runs_no_icacls(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "credentials.json"
            path.write_text("{}", encoding="utf-8")
            with mock.patch.object(cm.subprocess, "run") as run:
                self.assertIsNone(cm._restrict_secret_file(path, windows=False))
            run.assert_not_called()

    def test_every_credentials_write_goes_through_the_restriction(self):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(cm, "CRED_DIR", Path(d)), mock.patch.object(cm, "CRED_FILE", Path(d) / "credentials.json"), \
                mock.patch.object(cm, "_restrict_secret_file", return_value=None) as restrict:
            cm._save_creds({})
            restrict.assert_called_once_with(Path(d) / "credentials.json")


class TestKeyringIsAnOptionalPinnedGroup(unittest.TestCase):

    def test_the_group_the_messages_name_exists_and_is_not_a_default(self):
        self.assertIn("--groups keyring", cm.PLAINTEXT_WARNING)
        self.assertEqual(install_deps.ALL_GROUPS.get("keyring"), ["keyring"])
        self.assertNotIn("keyring", install_deps.DEFAULT_GROUPS)
        self.assertRegex(install_deps.PINNED["keyring"], r"^\d+(\.\d+)+$")


class TestDocsAreHonestAboutStorage(unittest.TestCase):
    SETUP = (REPO / "skills" / "setup" / "SKILL.md").read_text(encoding="utf-8")
    SECURITY = (REPO / "SECURITY.md").read_text(encoding="utf-8")
    PRIVACY = (REPO / "PRIVACY.md").read_text(encoding="utf-8")

    def test_no_doc_still_says_the_key_or_the_json_is_copied(self):
        for name, text in (("setup", self.SETUP), ("SECURITY.md", self.SECURITY), ("PRIVACY.md", self.PRIVACY)):
            with self.subTest(doc=name):
                self.assertNotIn("copied (not linked)", text)
                self.assertNotIn("API key is stored in credentials.json", text)
                self.assertNotIn("with owner-only file permissions", text)

    def test_the_docs_say_what_happens_on_windows(self):
        for name, text in (("setup", self.SETUP), ("SECURITY.md", self.SECURITY)):
            with self.subTest(doc=name):
                self.assertIn("icacls", text)
                self.assertRegex(text, r"(?i)chmod[^.\n]*(no-op|does nothing)[^.\n]*Windows|Windows[^.\n]*chmod[^.\n]*(no-op|does nothing)")

    def test_the_docs_name_the_keychain_and_the_variable_names(self):
        for name, text in (("setup", self.SETUP), ("SECURITY.md", self.SECURITY), ("PRIVACY.md", self.PRIVACY)):
            with self.subTest(doc=name):
                self.assertRegex(text, r"(?i)keychain")
                self.assertRegex(text, r"(?i)variable name")


if __name__ == "__main__":
    unittest.main()
