import io
import plistlib
import struct
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts.package_update import BUILD_MARKER, build_update


class PackageUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / "official.tar"
        self.helper = self.root / "PersistenceHelper"
        self.output = self.root / "TrollStoreAutoRefresh.tar"
        self.original_files = {
            "TrollStore.app/Info.plist": plistlib.dumps({
                "CFBundleIdentifier": "com.opa334.TrollStore",
                "CFBundleVersion": "2.1.1",
            }),
            "TrollStore.app/TrollStore": b"official-app",
            "TrollStore.app/trollstorehelper": b"official-root-helper",
            "TrollStore.app/PersistenceHelper": b"official-persistence-helper",
            "TrollStore.app/ldid": b"official-ldid",
        }
        self.write_base()
        self.helper.write_bytes(
            struct.pack("<IIIIIIII", 0xFEEDFACF, 0x100000C, 0, 2, 0, 0, 0, 0)
            + BUILD_MARKER.encode("ascii")
        )

    def write_base(self):
        with tarfile.open(self.base, "w:gz") as archive:
            for name, data in self.original_files.items():
                member = tarfile.TarInfo(name)
                member.mode = 0o755 if name.endswith("Helper") else 0o644
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))

    def test_preserves_every_official_file_except_persistence_helper(self):
        build_update(self.base, self.helper, self.output)
        with tarfile.open(self.output) as archive:
            self.assertEqual(set(archive.getnames()), set(self.original_files))
            for name, data in self.original_files.items():
                if name.endswith("/PersistenceHelper"):
                    data = self.helper.read_bytes()
                    self.assertEqual(archive.getmember(name).mode, 0o755)
                self.assertEqual(archive.extractfile(name).read(), data)

    def test_rejects_helper_without_custom_build_marker(self):
        self.helper.write_bytes(self.helper.read_bytes()[:32])
        with self.assertRaisesRegex(ValueError, "build marker"):
            build_update(self.base, self.helper, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_non_arm64_executable(self):
        self.helper.write_bytes(b"not a Mach-O" + BUILD_MARKER.encode("ascii"))
        with self.assertRaisesRegex(ValueError, "arm64"):
            build_update(self.base, self.helper, self.output)

    def test_rejects_wrong_base_app(self):
        self.original_files["TrollStore.app/Info.plist"] = plistlib.dumps({
            "CFBundleIdentifier": "com.example.OtherApp", "CFBundleVersion": "2.1.1"
        })
        self.write_base()
        with self.assertRaisesRegex(ValueError, "identity"):
            build_update(self.base, self.helper, self.output)

    def test_rejects_missing_official_helper(self):
        del self.original_files["TrollStore.app/PersistenceHelper"]
        self.write_base()
        with self.assertRaisesRegex(ValueError, "PersistenceHelper"):
            build_update(self.base, self.helper, self.output)


if __name__ == "__main__":
    unittest.main()
