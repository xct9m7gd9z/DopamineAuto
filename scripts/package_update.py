import argparse
import copy
import io
import plistlib
import struct
import tarfile
from pathlib import Path


BUILD_MARKER = "auto-refresh-20261026-1"
HELPER_MEMBER = "TrollStore.app/PersistenceHelper"


def build_update(base: Path, helper: Path, output: Path):
    helper_data = helper.read_bytes()
    if len(helper_data) < 32 or struct.unpack_from("<II", helper_data) != (0xFEEDFACF, 0x100000C):
        raise ValueError("replacement must be a thin arm64 Mach-O executable")
    if BUILD_MARKER.encode("ascii") not in helper_data:
        raise ValueError("replacement helper is missing the custom build marker")

    with tarfile.open(base, "r:*") as official:
        members = official.getmembers()
        names = [member.name for member in members]
        if HELPER_MEMBER not in names:
            raise ValueError("official archive is missing PersistenceHelper")
        info = plistlib.loads(official.extractfile("TrollStore.app/Info.plist").read())
        if (info.get("CFBundleIdentifier"), info.get("CFBundleVersion")) != ("com.opa334.TrollStore", "2.1.1"):
            raise ValueError("unexpected official TrollStore identity or version")

        originals = {}
        output.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(output, "w:gz") as packaged:
            for member in members:
                data = official.extractfile(member).read() if member.isfile() else None
                originals[member.name] = data
                updated = copy.copy(member)
                if member.name == HELPER_MEMBER:
                    data = helper_data
                    updated.size = len(data)
                    updated.mode = 0o755
                packaged.addfile(updated, io.BytesIO(data) if data is not None else None)

    with tarfile.open(output, "r:*") as packaged:
        if packaged.getnames() != names:
            raise ValueError("packaged archive members changed unexpectedly")
        for member in members:
            expected = helper_data if member.name == HELPER_MEMBER else originals[member.name]
            result = packaged.extractfile(member.name).read() if member.isfile() else None
            if result != expected:
                raise ValueError(f"packaged member verification failed: {member.name}")
    print(f"Verified {len(members)} archive members; replaced only PersistenceHelper")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("helper", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build_update(args.base, args.helper, args.output)
