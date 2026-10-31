import re
import operator
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
        r"static volatile uint64_t \*badRecoveryMapThreadField\([^\n]+\)\s*\{.*?^\}",
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


class PACFieldMappingIntegrationTests(unittest.TestCase):
    def test_kcall_accepts_success_and_rejects_negative_failure(self):
        source = (PAC / "badRecovery.m").read_text(encoding="utf-8")
        comparison = re.search(r"if \(kcallResult (==|!=) (-?\d+)\)", source)
        self.assertIsNotNone(comparison)
        operation = operator.eq if comparison[1] == "==" else operator.ne
        failure_check = lambda result: operation(result, int(comparison[2]))
        self.assertFalse(failure_check(1), "Fugu14 initialization returns 1 on success")
        self.assertTrue(failure_check(-1), "Fugu14 initialization returns -1 on failure")
        self.assertTrue(failure_check(0), "an uninitialized result must not count as success")

    def test_all_four_fields_are_mapped_before_the_interrupt_stack_changes(self):
        source = (PAC / "badRecovery.m").read_text(encoding="utf-8")
        setup = source.split("bool breakCFI(void)", 1)[1].split("uint64_t signedFaultHandler", 1)[0]
        for field, offset in (("recoverField", "recover"), ("cpuDataField", "machine_CpuDatap"),
                              ("kstackptrField", "machine_kstackptr"), ("contextDataField", "machine_contextData")):
            self.assertIn(f"*{field} = badRecoveryMapThreadField(chThreadPtr, koffsetof(thread, {offset}));", setup)
        self.assertIn("guard (recoverField && cpuDataField && kstackptrField && contextDataField)", setup)
        self.assertNotIn("mapAddr + koffsetof", source)

    def test_c_and_assembly_use_the_same_direct_field_pointers(self):
        source = (PAC / "badRecovery.m").read_text(encoding="utf-8")
        assembly = (PAC / "badRecovery.s").read_text(encoding="utf-8")
        for register, field in ((11, "cpuDataField"), (26, "kstackptrField"), (27, "contextDataField")):
            self.assertIn(f".__x[{register}] = (uint64_t)(uintptr_t){field};", source)
        self.assertEqual(assembly.count("ldr x24, [x11]"), 2)
        self.assertIn("str x19, [x26]", assembly)
        self.assertIn("str x18, [x27]", assembly)
        self.assertNotRegex(assembly, r"\[x11, x2[567]\]")
