#ifndef TSH_AUTO_REFRESH_GATE_H
#define TSH_AUTO_REFRESH_GATE_H

#include <stdbool.h>

typedef struct {
    bool started;
} TSHAutoRefreshGate;

static inline bool TSHTryStartAutoRefresh(TSHAutoRefreshGate *gate, bool active, bool visible)
{
    (void)gate;
    (void)active;
    (void)visible;
    return false;
}

#endif
