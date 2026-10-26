#import <TSListControllerShared.h>
#include "TSHAutoRefreshGate.h"

@interface TSHRootViewController : TSListControllerShared
{
    NSString* _newerVersion;
    TSHAutoRefreshGate _autoRefreshGate;
}
@end
