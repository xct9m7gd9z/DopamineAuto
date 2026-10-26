#ifndef TSH_AUTO_REFRESH_GATE_H
#define TSH_AUTO_REFRESH_GATE_H

#include <stdbool.h>

typedef struct {
    bool started;
} TSHAutoRefreshGate;

static inline bool TSHTryStartAutoRefresh(TSHAutoRefreshGate *gate, bool active, bool visible)
{
    if (gate->started || !active || !visible) return false;
    gate->started = true;
    return true;
}

#endif
