import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "manage-config"
BASE = "CONFIG_NET=y\nCONFIG_DEBUG_INFO=y\nCONFIG_DEBUG_INFO_DWARF5=y\n"


class ManageConfigTests(unittest.TestCase):
    def run_config(self, root, arch, debug="n", mode="no_sign", cert=""):
        subprocess.run(
            ["bash", str(SCRIPT), arch, mode, cert], cwd=root,
            env={**os.environ, "SONIC_DEBUGGING_ON": debug},
            check=True, capture_output=True, text=True,
        )

    def test_production_and_debug_configurations(self):
        for arch in ("amd64", "arm64", "armhf"):
            for debug in ("n", "y"):
                with self.subTest(arch=arch, debug=debug), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    directory = root / "debian/config.local" / arch
                    directory.mkdir(parents=True)
                    config = directory / "config.sonic"
                    config.write_text(BASE)
                    self.run_config(root, arch, debug)
                    if debug == "y":
                        self.assertEqual(config.read_text(), BASE)
                    else:
                        result = config.read_text()
                        self.assertIn("CONFIG_NET=y\n", result)
                        self.assertIn("CONFIG_DEBUG_INFO_NONE=y\n", result)
                        self.assertNotIn("CONFIG_DEBUG_INFO=y\n", result)
                        self.assertNotIn("CONFIG_DEBUG_INFO_DWARF5=y\n", result)
                        self.run_config(root, arch, debug)
                        self.assertEqual(config.read_text().count("CONFIG_DEBUG_INFO_NONE=y"), 1)

    def test_secure_boot_certificate_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "debian/config.local/amd64"
            directory.mkdir(parents=True)
            config = directory / "config.sonic"
            config.write_text(BASE)
            (directory / "config.sonic-secureboot").write_text('CONFIG_SYSTEM_TRUSTED_KEYS="old"\n')
            cert = root / "signing.crt"
            cert.touch()
            self.run_config(root, "amd64", mode="dev", cert=str(cert))
            self.assertIn(f'CONFIG_SYSTEM_TRUSTED_KEYS="{cert}"', config.read_text())
            self.assertIn("CONFIG_DEBUG_INFO_NONE=y", config.read_text())


if __name__ == "__main__":
    unittest.main()
