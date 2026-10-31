import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAC = ROOT / "Application/Dopamine/Exploits/badRecovery"


def production_mapper():
    source = (PAC / "badRecovery.m").read_text(encoding="utf-8")
    mapped = re.search(
        r"static volatile uint64_t \*badRecoveryMapThreadField\([^;]+?^\}",
        source, re.MULTILINE | re.DOTALL,
    )
    if mapped:
        return mapped.group()

    # Compile the old production address expression to prove the reported boundary fails.
    initialization = re.search(r"uint64_t mapAddr = mapKernelPage\(chThreadPtr\);", source)
    access = re.search(r"signedFaultHandler = \*\(volatile uint64_t\*\)\((.+)\);", source)
    if not initialization or not access:
        raise ValueError("cannot locate the production thread mapping")
    setup = initialization.group().replace("chThreadPtr", "threadAddress")
    expression = access.group(1).replace("koffsetof(thread, recover)", "fieldOffset")
    return (
        "static volatile uint64_t *badRecoveryMapThreadField(uint64_t threadAddress, uint64_t fieldOffset)\n"
        "{\n" + setup + "\nreturn (volatile uint64_t *)(" + expression + ");\n}"
    )


@unittest.skipUnless(sys.platform == "darwin", "guard-page native tests run on the macOS builder")
class NativePACFieldMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        folder = Path(cls.temp.name)
        harness = (ROOT / "Tests/pac_field_mapping_harness.c").read_text(encoding="utf-8")
        source = folder / "pac-field-mapping.c"
        source.write_text(harness.replace("__PRODUCTION_FIELD_MAPPER__", production_mapper()), encoding="utf-8")
        cls.executable = folder / "pac-field-mapping"
        subprocess.run(["clang", "-std=c11", "-Wall", "-Wextra", "-Werror",
                        str(source), "-o", str(cls.executable)], check=True)

    def run_case(self, case):
        subprocess.run([str(self.executable), case], check=True, timeout=20)

    def test_reported_recover_field_in_next_page(self): self.run_case("reported-crash")
    def test_all_8192_aligned_thread_field_placements(self): self.run_case("all-placements")
    def test_null_mapping_is_rejected(self): self.run_case("zero-map")
    def test_minus_one_mapping_is_rejected(self): self.run_case("failed-map")
    def test_invalid_field_addresses_never_reach_mapper(self): self.run_case("invalid-addresses")
