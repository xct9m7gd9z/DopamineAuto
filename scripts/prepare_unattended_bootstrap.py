import argparse
import copy
import hashlib
import io
import os
import tarfile
import tempfile
from pathlib import Path

import zstandard


BUILD_MARKER = "preset-mobile-password-20261026-1"
ORIGINAL_PASSWORD_BLOCK = '''if [ -z "$NO_PASSWORD_PROMPT" ]; then
    PASSWORDS=""
    PASSWORD1=""
    PASSWORD2=""
    while [ -z "$PASSWORD1" ] || [ ! "$PASSWORD1" = "$PASSWORD2" ]; do
            PASSWORDS="$(/usr/bin/uialert -b "In order to use command line tools like \\"sudo\\" after jailbreaking, you will need to set a terminal passcode. (This cannot be empty)" --secure "Password" --secure "Repeat Password" -p "Set" "Set Password")"
            PASSWORD1="$(printf "%s\\n" "$PASSWORDS" | /usr/bin/sed -n '1 p')"
            PASSWORD2="$(printf "%s\\n" "$PASSWORDS" | /usr/bin/sed -n '2 p')"
    done
    printf "%s\\n" "$PASSWORD1" | /usr/sbin/pw usermod 501 -h 0
fi'''


def patch_script(script: bytes) -> bytes:
    replacement = f'''# DopamineAuto {BUILD_MARKER}
if [ -z "$NO_PASSWORD_PROMPT" ]; then
    printf "%s\\n" "123" | /usr/sbin/pw usermod 501 -h 0 || exit $?
fi'''.encode()
    if replacement in script:
        return script
    original = ORIGINAL_PASSWORD_BLOCK.encode()
    if script.count(original) != 1:
        raise ValueError("unexpected bootstrap password block; refusing to patch")
    return script.replace(original, replacement, 1)


def entry_record(member, data):
    digest = hashlib.sha256(data).hexdigest() if data is not None else None
    return (member.name, member.type, member.mode, member.uid, member.gid,
            member.uname, member.gname, member.linkname, member.mtime, digest)


def patch_archive(source: Path, destination: Path):
    expected = []
    found = 0
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".tar.zst", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with source.open("rb") as original, temporary_path.open("wb") as output:
            with zstandard.ZstdDecompressor().stream_reader(original) as decoded:
                with zstandard.ZstdCompressor(level=10).stream_writer(output) as encoded:
                    with tarfile.open(fileobj=decoded, mode="r|") as reader:
                        with tarfile.open(fileobj=encoded, mode="w|") as writer:
                            for member in reader:
                                data = reader.extractfile(member).read() if member.isfile() else None
                                updated = copy.copy(member)
                                if member.name.removeprefix("./") == "prep_bootstrap.sh" and member.isfile():
                                    data = patch_script(data)
                                    updated.size = len(data)
                                    updated.pax_headers = member.pax_headers.copy()
                                    if "size" in updated.pax_headers:
                                        updated.pax_headers["size"] = str(len(data))
                                    found += 1
                                writer.addfile(updated, io.BytesIO(data) if data is not None else None)
                                expected.append(entry_record(updated, data))
        if found != 1:
            raise ValueError("bootstrap archive must contain exactly one setup script")

        actual = []
        with temporary_path.open("rb") as compressed:
            with zstandard.ZstdDecompressor().stream_reader(compressed) as decoded:
                with tarfile.open(fileobj=decoded, mode="r|") as archive:
                    for member in archive:
                        data = archive.extractfile(member).read() if member.isfile() else None
                        actual.append(entry_record(member, data))
        if actual != expected:
            raise ValueError("bootstrap members changed unexpectedly while packaging")
        os.replace(temporary_path, destination)
        print(f"Verified {len(actual)} entries in {destination.name}; changed only prep_bootstrap.sh")
    finally:
        temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archives", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.archives:
        patch_archive(path, path)
