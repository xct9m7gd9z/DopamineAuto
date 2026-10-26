#import <Foundation/Foundation.h>
#include <assert.h>
#include <stdbool.h>

static NSArray *availableManagers;
static BOOL otherJailbreak;
static BOOL otherJailbreakActived(bool unused) { return otherJailbreak; }

@interface DOPreferenceManager : NSObject
@property NSMutableDictionary *values;
@property NSInteger writes;
+ (instancetype)sharedManager;
- (id)preferenceValueForKey:(NSString *)key;
- (BOOL)boolPreferenceValueForKey:(NSString *)key fallback:(BOOL)fallback;
- (void)setPreferenceValue:(NSObject *)value forKey:(NSString *)key;
@end

@implementation DOPreferenceManager
+ (instancetype)sharedManager
{
    static DOPreferenceManager *instance;
    if (!instance) {
        instance = [DOPreferenceManager new];
        instance.values = [NSMutableDictionary new];
    }
    return instance;
}
- (id)preferenceValueForKey:(NSString *)key { return self.values[key]; }
- (BOOL)boolPreferenceValueForKey:(NSString *)key fallback:(BOOL)fallback
{
    NSNumber *value = self.values[key];
    return value ? value.boolValue : fallback;
}
- (void)setPreferenceValue:(NSObject *)value forKey:(NSString *)key
{
    self.values[key] = value;
    self.writes++;
}
@end

@interface DOEnvironmentManager : NSObject
@property BOOL isInstalledThroughTrollStore;
@property BOOL isBootstrapped;
@property BOOL isSupported;
+ (instancetype)sharedManager;
@end

@implementation DOEnvironmentManager
+ (instancetype)sharedManager
{
    static DOEnvironmentManager *instance;
    if (!instance) instance = [DOEnvironmentManager new];
    return instance;
}
@end

@interface DOUIManager : NSObject
{
    NSString *_bootlogoPath;
    DOPreferenceManager *_preferenceManager;
    NSMutableArray *_logRecord;
    NSLock *_logLock;
}
+ (instancetype)sharedInstance;
- (NSArray *)availablePackageManagers;
- (NSArray *)enabledPackageManagerKeys;
- (void)setPackageManager:(NSString *)key enabled:(BOOL)enabled;
@end

@implementation DOUIManager
+ (instancetype)sharedInstance
{
    static DOUIManager *instance;
    if (!instance) instance = [DOUIManager new];
    return instance;
}
- (NSArray *)availablePackageManagers { return availableManagers; }
__UI_METHODS__
@end

@interface DOMainViewController : NSObject
- (BOOL)automaticEnvironmentReady;
@end

@implementation DOMainViewController
__READY_METHOD__
@end

int main(int argc, char **argv)
{
    @autoreleasepool {
        assert(argc == 3);
        availableManagers = [NSArray arrayWithContentsOfFile:@(argv[2])];
        assert(availableManagers.count == 2);
        NSString *test = @(argv[1]);
        DOPreferenceManager *preferences = [DOPreferenceManager sharedManager];
        NSString *sileo = @"org.coolstar.SileoStore";
        NSString *zebra = @"xyz.willy.Zebra";

        if ([test isEqualToString:@"empty"]) preferences.values[@"enabledPkgManagers"] = @[];
        if ([test isEqualToString:@"obsolete"]) preferences.values[@"enabledPkgManagers"] = @[@"obsolete.manager"];
        if ([test isEqualToString:@"zebra"]) preferences.values[@"enabledPkgManagers"] = @[zebra];
        if ([test isEqualToString:@"both"]) preferences.values[@"enabledPkgManagers"] = @[sileo, zebra];
        if ([test isEqualToString:@"ready"] || [test isEqualToString:@"exclusions"])
            preferences.values[@"enabledPkgManagers"] = @[sileo];

        DOUIManager *manager = [DOUIManager sharedInstance];
        if ([test isEqualToString:@"fresh"] || [test isEqualToString:@"empty"] ||
            [test isEqualToString:@"obsolete"] || [test isEqualToString:@"relaunch"] ||
            [test isEqualToString:@"manual"])
        {
            assert([[manager enabledPackageManagerKeys] isEqualToArray:@[sileo]]);
            assert([preferences.values[@"enabledPkgManagers"] isEqualToArray:@[sileo]]);
            assert(preferences.writes == 1);
        }
        if ([test isEqualToString:@"zebra"]) {
            assert([[manager enabledPackageManagerKeys] isEqualToArray:@[zebra]]);
            assert(preferences.writes == 0);
        }
        if ([test isEqualToString:@"both"]) {
            assert([[manager enabledPackageManagerKeys] isEqualToArray:(@[sileo, zebra])]);
            assert(preferences.writes == 0);
        }
        if ([test isEqualToString:@"relaunch"]) {
            DOUIManager *nextLaunch = [DOUIManager new];
            assert([[nextLaunch enabledPackageManagerKeys] isEqualToArray:@[sileo]]);
            assert(preferences.writes == 1);
        }
        if ([test isEqualToString:@"manual"]) {
            [manager setPackageManager:sileo enabled:NO];
            assert(manager.enabledPackageManagerKeys.count == 0);
            [manager setPackageManager:zebra enabled:YES];
            assert([[manager enabledPackageManagerKeys] isEqualToArray:@[zebra]]);
        }

        DOEnvironmentManager *environment = [DOEnvironmentManager sharedManager];
        environment.isSupported = YES;
        environment.isInstalledThroughTrollStore = YES;
        DOMainViewController *controller = [DOMainViewController new];
        if ([test isEqualToString:@"ready"]) {
            environment.isBootstrapped = NO;
            assert([controller automaticEnvironmentReady]);
            environment.isBootstrapped = YES;
            assert([controller automaticEnvironmentReady]);
        }
        if ([test isEqualToString:@"exclusions"]) {
            environment.isBootstrapped = YES;
            assert([controller automaticEnvironmentReady]);
            environment.isSupported = NO;
            assert(![controller automaticEnvironmentReady]);
            environment.isSupported = YES;
            environment.isInstalledThroughTrollStore = NO;
            assert(![controller automaticEnvironmentReady]);
            environment.isInstalledThroughTrollStore = YES;
            otherJailbreak = YES;
            assert(![controller automaticEnvironmentReady]);
            otherJailbreak = NO;
            preferences.values[@"autoJailbreakEnabled"] = @NO;
            assert(![controller automaticEnvironmentReady]);
            preferences.values[@"autoJailbreakEnabled"] = @YES;
            preferences.values[@"removeJailbreakEnabled"] = @YES;
            assert(![controller automaticEnvironmentReady]);
        }
        printf("PASS: %s\n", argv[1]);
    }
}
