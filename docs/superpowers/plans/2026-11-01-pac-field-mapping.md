# PAC Thread Field Mapping Fix

The user approved fixing the crash in `Dopamine-2026-11-01-020746.ips` and
delivering a new local TIPA. The installed app and framework UUIDs match the
previous `599e54c` package. `breakCFI +1204` loads `thread.recover` at
`0x108688030`, beyond the single mapping ending at `0x108688000`.

## Implementation

- [ ] Add native regression tests that reproduce the thread offset `0x3c50`
  plus field offset `0x3e0`. Give the two kernel pages separate userspace
  mappings separated by a guard page, then verify the actual production
  mapping expression selects the correct page. Capture the old test failure.
- [ ] In `badRecovery.m`, add a checked field mapper that passes the complete
  field address to `mapKernelPage`, rejects overflow, unaligned words, and
  failed mappings. Map recover, CpuDatap, kstackptr and contextData separately
  before changing the interrupt stack. Read through the resulting pointers.
- [ ] Pass CpuDatap, kstackptr and contextData userspace pointers directly in
  registers x11, x26 and x27. In `badRecovery.s`, dereference those pointers
  without adding offsets to the thread's original page mapping.
- [ ] Test every aligned thread placement in a 16 KB page with all four field
  offsets, plus mapping failures and address overflow. Verify C and assembly
  register agreement. Run the existing startup and unattended bootstrap tests.
- [ ] Assign a PAC-fix build marker, compile using the pinned existing CI,
  upload symbols for any subsequent device crash, and download the verified
  ZIP/TIPA/build manifest into the workspace outputs directory.

## Boundaries

Keep the default Sileo, first-bootstrap terminal password and automatic exit
settings. Do not assume adjacent kernel virtual pages are physically adjacent,
and do not solve the problem by mapping a larger contiguous physical region.
The new build must be tested on the affected phone before calling its actual
jailbreak workflow fixed.
