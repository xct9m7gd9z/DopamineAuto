#include <assert.h>
#include <stdio.h>
#include "../TrollHelper/TSHAutoRefreshGate.h"

int main(void)
{
    TSHAutoRefreshGate gate = {0};
    assert(!TSHTryStartAutoRefresh(&gate, false, false));
    assert(!TSHTryStartAutoRefresh(&gate, false, true));
    assert(!TSHTryStartAutoRefresh(&gate, true, false));
    assert(!gate.started);

    assert(TSHTryStartAutoRefresh(&gate, true, true));
    assert(gate.started);
    assert(!TSHTryStartAutoRefresh(&gate, true, true));
    assert(!TSHTryStartAutoRefresh(&gate, false, true));
    assert(!TSHTryStartAutoRefresh(&gate, true, true));

    TSHAutoRefreshGate nextLaunch = {0};
    assert(TSHTryStartAutoRefresh(&nextLaunch, true, true));
    puts("PASS: deferred cold launch, duplicate callbacks, new launch");
    return 0;
}
