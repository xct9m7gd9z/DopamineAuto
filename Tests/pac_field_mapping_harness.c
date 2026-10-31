#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>

#define TEST_PAGE_SIZE 0x4000ULL
#define KERNEL_BASE 0xffffffe000000000ULL

static uint8_t *pages;
static uint64_t lastMappedAddress;
static uint64_t forcedFailure;

static uint64_t mapKernelPage(uint64_t address)
{
    lastMappedAddress = address;
    if (forcedFailure) return forcedFailure == 1 ? 0 : UINT64_MAX;
    uint64_t page = (address - KERNEL_BASE) / TEST_PAGE_SIZE;
    assert(page <= 1);
    return (uint64_t)(uintptr_t)(pages + page * TEST_PAGE_SIZE * 2 +
                                (address & (TEST_PAGE_SIZE - 1)));
}

__PRODUCTION_FIELD_MAPPER__

static void checkField(uint64_t threadOffset, uint64_t fieldOffset)
{
    uint64_t address = KERNEL_BASE + threadOffset + fieldOffset;
    uint64_t page = (address - KERNEL_BASE) / TEST_PAGE_SIZE;
    volatile uint64_t *expected = (volatile uint64_t *)(pages +
        page * TEST_PAGE_SIZE * 2 + (address & (TEST_PAGE_SIZE - 1)));
    *expected = 0xcafef00dbad0beefULL;
    volatile uint64_t *result = badRecoveryMapThreadField(KERNEL_BASE + threadOffset, fieldOffset);
    assert(result == expected);
    assert(lastMappedAddress == address);
    assert(*result == 0xcafef00dbad0beefULL);
}

int main(int argc, char **argv)
{
    assert(argc == 2);
    pages = mmap(NULL, TEST_PAGE_SIZE * 4, PROT_NONE, MAP_PRIVATE | MAP_ANON, -1, 0);
    assert(pages != MAP_FAILED);
    assert(mprotect(pages, TEST_PAGE_SIZE, PROT_READ | PROT_WRITE) == 0);
    assert(mprotect(pages + TEST_PAGE_SIZE * 2, TEST_PAGE_SIZE, PROT_READ | PROT_WRITE) == 0);

    if (!strcmp(argv[1], "reported-crash")) {
        checkField(0x3c50, 0x3e0);
    }
    else if (!strcmp(argv[1], "all-placements")) {
        uint64_t offsets[] = {0xa8, 0xf0, 0x150, 0x3e0};
        for (uint64_t thread = 0; thread < TEST_PAGE_SIZE; thread += 8) {
            for (unsigned field = 0; field < 4; field++) checkField(thread, offsets[field]);
        }
    }
    else if (!strcmp(argv[1], "zero-map")) {
        forcedFailure = 1;
        assert(badRecoveryMapThreadField(KERNEL_BASE + 0x3c50, 0x3e0) == NULL);
    }
    else if (!strcmp(argv[1], "failed-map")) {
        forcedFailure = 2;
        assert(badRecoveryMapThreadField(KERNEL_BASE + 0x3c50, 0x3e0) == NULL);
    }
    else if (!strcmp(argv[1], "invalid-addresses")) {
        assert(badRecoveryMapThreadField(0, 0x3e0) == NULL);
        assert(badRecoveryMapThreadField(UINT64_MAX - 7, 8) == NULL);
        assert(badRecoveryMapThreadField(KERNEL_BASE + 0x3fff, 0) == NULL);
        assert(badRecoveryMapThreadField(KERNEL_BASE, 3) == NULL);
        assert(lastMappedAddress == 0);
    }
    else {
        assert(!"unknown test case");
    }

    assert(munmap(pages, TEST_PAGE_SIZE * 4) == 0);
    printf("PASS: %s\n", argv[1]);
    return 0;
}
