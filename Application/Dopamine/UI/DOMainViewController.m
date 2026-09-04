//
//  DOMainViewController.m
//  Dopamine
//
//  Created by tomt000 on 08/01/2024.
//

#import "DOMainViewController.h"
#import "DOUIManager.h"
#import "DOEnvironmentManager.h"
#import "DOJailbreaker.h"
#import "DOGlobalAppearance.h"
#import "DOActionMenuButton.h"
#import "DOUpdateViewController.h"
#import "DOLogCrashViewController.h"
#import <pthread.h>
#import <sys/sysctl.h>
#import <libjailbreak/libjailbreak.h>

static NSInteger const DO_AUTO_JAILBREAK_DELAY_SECONDS = 8;
static NSInteger const DO_AUTO_RETRY_DELAY_SECONDS = 30;
static NSInteger const DO_AUTO_EXIT_DELAY_SECONDS = 3;
static NSInteger const DO_AUTO_MAX_ATTEMPTS = 2;

@interface DOMainViewController ()

@property DOJailbreakButton *jailbreakBtn;
@property NSArray<NSLayoutConstraint *> *jailbreakButtonConstraints;
@property DOActionMenuButton *updateButton;
@property DOActionMenuView *actionView;
@property DOHeaderView *headerView;
@property(nonatomic) BOOL hideStatusBar;
@property(nonatomic) BOOL hideHomeIndicator;
@property(nonatomic) NSTimer *automaticCountdownTimer;
@property(nonatomic) NSTimer *automaticRetryTimer;
@property(nonatomic) NSTimer *alreadyJailbrokenExitTimer;
@property(nonatomic) UIAlertController *automaticCountdownAlert;
@property(nonatomic) NSInteger automaticCountdownRemaining;
@property(nonatomic) NSInteger automaticAttemptCount;
@property(nonatomic) BOOL automaticJailbreakCancelled;
@property(nonatomic) BOOL jailbreakAttemptInProgress;

@end

@implementation DOMainViewController

- (void)viewDidLoad {
    [super viewDidLoad];
    [[NSNotificationCenter defaultCenter] addObserver:self selector:@selector(applicationWillResignActive:) name:UIApplicationWillResignActiveNotification object:nil];
    [self setupStack];
}

- (void)viewDidAppear:(BOOL)animated
{
    [super viewDidAppear:animated];
    [self scheduleAutomaticActionIfEligible];
}

- (void)viewWillDisappear:(BOOL)animated
{
    [super viewWillDisappear:animated];
    [self cancelAutomaticTimers];
}

- (void)dealloc
{
    [[NSNotificationCenter defaultCenter] removeObserver:self];
    [self cancelAutomaticTimers];
}

- (void)applicationWillResignActive:(NSNotification *)notification
{
    [self cancelAutomaticTimers];
}

- (void)cancelAutomaticTimers
{
    [self.automaticCountdownTimer invalidate];
    [self.automaticRetryTimer invalidate];
    [self.alreadyJailbrokenExitTimer invalidate];
    self.automaticCountdownTimer = nil;
    self.automaticRetryTimer = nil;
    self.alreadyJailbrokenExitTimer = nil;
    if (self.automaticCountdownAlert.presentingViewController) {
        [self.automaticCountdownAlert dismissViewControllerAnimated:NO completion:nil];
    }
    self.automaticCountdownAlert = nil;
}

- (void)scheduleAutomaticActionIfEligible
{
    if (UIApplication.sharedApplication.applicationState != UIApplicationStateActive || self.jailbreakAttemptInProgress)
        return;

    DOEnvironmentManager *environment = [DOEnvironmentManager sharedManager];
    DOPreferenceManager *preferences = [DOPreferenceManager sharedManager];
    BOOL isJailbroken = environment.isJailbroken || environment.isJailbrokenWithOtherJailbreak;
    BOOL exitEnabled = [preferences boolPreferenceValueForKey:@"exitWhenJailbroken" fallback:YES];
    if (isJailbroken) {
        if (exitEnabled)
            [self scheduleAlreadyJailbrokenExit];
        return;
    }

    BOOL autoEnabled = [preferences boolPreferenceValueForKey:@"autoJailbreakEnabled" fallback:YES];
    BOOL removeEnabled = [preferences boolPreferenceValueForKey:@"removeJailbreakEnabled" fallback:NO];
    BOOL hasPackageManager = [DOUIManager sharedInstance].enabledPackageManagerKeys.count > 0;
    if (!autoEnabled || removeEnabled || !environment.isSupported || environment.isJailbrokenWithOtherJailbreak ||
        !hasPackageManager || self.automaticJailbreakCancelled || self.automaticCountdownTimer || self.automaticRetryTimer)
        return;

    self.automaticCountdownRemaining = DO_AUTO_JAILBREAK_DELAY_SECONDS;
    self.automaticCountdownAlert = [UIAlertController alertControllerWithTitle:DOLocalizedString(@"Auto_Jailbreak_Title")
                                                                         message:[NSString stringWithFormat:DOLocalizedString(@"Auto_Jailbreak_Countdown"), (long)self.automaticCountdownRemaining]
                                                                  preferredStyle:UIAlertControllerStyleAlert];
    [self.automaticCountdownAlert addAction:[UIAlertAction actionWithTitle:DOLocalizedString(@"Auto_Jailbreak_Now") style:UIAlertActionStyleDestructive handler:^(UIAlertAction *action) {
        [self.automaticCountdownTimer invalidate];
        self.automaticCountdownTimer = nil;
        [self.automaticCountdownAlert dismissViewControllerAnimated:YES completion:^{
            self.automaticCountdownAlert = nil;
            [self beginJailbreakAutomatically:YES];
        }];
    }]];
    [self.automaticCountdownAlert addAction:[UIAlertAction actionWithTitle:DOLocalizedString(@"Auto_Jailbreak_Cancel_This_Launch") style:UIAlertActionStyleCancel handler:^(UIAlertAction *action) {
        [self.automaticCountdownTimer invalidate];
        self.automaticCountdownTimer = nil;
        self.automaticJailbreakCancelled = YES;
        self.automaticCountdownAlert = nil;
    }]];
    [self presentViewController:self.automaticCountdownAlert animated:YES completion:nil];

    __weak typeof(self) weakSelf = self;
    self.automaticCountdownTimer = [NSTimer scheduledTimerWithTimeInterval:1.0 repeats:YES block:^(NSTimer *timer) {
        __strong typeof(weakSelf) self = weakSelf;
        if (!self) return;
        self.automaticCountdownRemaining -= 1;
        if (self.automaticCountdownRemaining > 0) {
            self.automaticCountdownAlert.message = [NSString stringWithFormat:DOLocalizedString(@"Auto_Jailbreak_Countdown"), (long)self.automaticCountdownRemaining];
            return;
        }
        [timer invalidate];
        self.automaticCountdownTimer = nil;
        [self.automaticCountdownAlert dismissViewControllerAnimated:YES completion:^{
            self.automaticCountdownAlert = nil;
            [self beginJailbreakAutomatically:YES];
        }];
    }];
}

- (void)scheduleAlreadyJailbrokenExit
{
    if (self.alreadyJailbrokenExitTimer)
        return;

    self.alreadyJailbrokenExitTimer = [NSTimer scheduledTimerWithTimeInterval:DO_AUTO_EXIT_DELAY_SECONDS repeats:NO block:^(NSTimer *timer) {
        self.alreadyJailbrokenExitTimer = nil;
        DOEnvironmentManager *environment = [DOEnvironmentManager sharedManager];
        if (UIApplication.sharedApplication.applicationState == UIApplicationStateActive &&
            (environment.isJailbroken || environment.isJailbrokenWithOtherJailbreak) &&
            [[DOPreferenceManager sharedManager] boolPreferenceValueForKey:@"exitWhenJailbroken" fallback:YES]) {
            exit(0);
        }
    }];
}

-(void)setupStack
{
    UIStackView *stackView = [[UIStackView alloc] init];
    [stackView setAxis:UILayoutConstraintAxisVertical];
    [stackView setAlignment:UIStackViewAlignmentTrailing];
    [stackView setDistribution:UIStackViewDistributionEqualSpacing];
    [stackView setTranslatesAutoresizingMaskIntoConstraints:NO];

    [self.view addSubview:stackView];


    int statusBarHeight = fmax(15, [[UIApplication sharedApplication] keyWindow].safeAreaInsets.top - 20);

    [NSLayoutConstraint activateConstraints:@[
        [stackView.centerYAnchor constraintEqualToAnchor:self.view.centerYAnchor constant:statusBarHeight],//-35
        [stackView.heightAnchor constraintEqualToAnchor:self.view.heightAnchor multiplier:[DOGlobalAppearance isHomeButtonDevice] ? 0.78 : 0.73]
    ]];

    if ([[UIDevice currentDevice] userInterfaceIdiom] == UIUserInterfaceIdiomPad)
    {
        NSLayoutConstraint *relativeWidthConstraint = [stackView.widthAnchor constraintEqualToAnchor:self.view.widthAnchor multiplier:0.8];
        relativeWidthConstraint.priority = UILayoutPriorityDefaultHigh;
        NSLayoutConstraint *maxWidthConstraint = [stackView.widthAnchor constraintLessThanOrEqualToConstant:UI_IPAD_MAX_WIDTH];
        maxWidthConstraint.priority = UILayoutPriorityRequired;

        [NSLayoutConstraint activateConstraints:@[
            relativeWidthConstraint,
            maxWidthConstraint,
            [stackView.centerXAnchor constraintEqualToAnchor:self.view.centerXAnchor]
        ]];
    }
    else
    {
        [NSLayoutConstraint activateConstraints:@[
            [stackView.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor constant:UI_PADDING],
            [stackView.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor constant:-UI_PADDING],
        ]];
    }

    //Header
    DOHeaderView *headerView = [[DOHeaderView alloc] initWithImage: [UIImage imageNamed:@"Dopamine"] subtitles: @[
        [DOGlobalAppearance mainSubtitleString:[[DOEnvironmentManager sharedManager] versionSupportString]],
        [DOGlobalAppearance secondarySubtitleString:DOLocalizedString(@"Credits_Made_By")],
    ]];
    self.headerView = headerView;
    
    [stackView addArrangedSubview:headerView];

    [NSLayoutConstraint activateConstraints:@[
        [headerView.leadingAnchor constraintEqualToAnchor:stackView.leadingAnchor constant:5],
        [headerView.trailingAnchor constraintEqualToAnchor:stackView.trailingAnchor]
    ]];
    
    //Action Menu
    DOActionMenuView *actionView = [[DOActionMenuView alloc] initWithActions:@[
        [UIAction actionWithTitle:DOLocalizedString(@"Menu_Settings_Title") image:[UIImage systemImageNamed:@"gearshape" withConfiguration:[DOGlobalAppearance smallIconImageConfiguration]] identifier:@"settings" handler:^(__kindof UIAction * _Nonnull action) {
            [self.navigationController pushViewController:[[DOSettingsController alloc] init] animated:YES];
        }],
        [UIAction actionWithTitle:DOLocalizedString(@"Menu_Restart_SpringBoard_Title") image:[UIImage systemImageNamed:@"arrow.clockwise" withConfiguration:[DOGlobalAppearance smallIconImageConfiguration]] identifier:@"respring" handler:^(__kindof UIAction * _Nonnull action) {
            [self fadeToBlack:^{
                [[DOEnvironmentManager sharedManager] respring];
            }];
        }],
        [UIAction actionWithTitle:DOLocalizedString(@"Menu_Reboot_Userspace_Title") image:[UIImage systemImageNamed:@"arrow.clockwise.circle" withConfiguration:[DOGlobalAppearance smallIconImageConfiguration]] identifier:@"reboot-userspace" handler:^(__kindof UIAction * _Nonnull action) {
            [self fadeToBlack:^{
                [[DOEnvironmentManager sharedManager] rebootUserspace];
            }];
        }],
        [UIAction actionWithTitle:DOLocalizedString(@"Menu_Credits_Title") image:[UIImage systemImageNamed:@"info.circle" withConfiguration:[DOGlobalAppearance smallIconImageConfiguration]] identifier:@"credits" handler:^(__kindof UIAction * _Nonnull action) {
            [self.navigationController pushViewController:[[DOCreditsViewController alloc] init] animated:YES];
        }]
    ] delegate:self];
    self.actionView = actionView;
    
    [stackView addArrangedSubview: actionView];

    [NSLayoutConstraint activateConstraints:@[
        [actionView.leadingAnchor constraintEqualToAnchor:stackView.leadingAnchor],
        [actionView.trailingAnchor constraintEqualToAnchor:stackView.trailingAnchor],
    ]];
    
    
    UIView *buttonPlaceHolder = [[UIView alloc] init];
    [buttonPlaceHolder setTranslatesAutoresizingMaskIntoConstraints:NO];
    [stackView addArrangedSubview:buttonPlaceHolder];
    [NSLayoutConstraint activateConstraints:@[
        [buttonPlaceHolder.heightAnchor constraintEqualToConstant:60]
    ]];
    
    //Jailbreak Button
    BOOL isJailbroken = [[DOEnvironmentManager sharedManager] isJailbroken] || [[DOEnvironmentManager sharedManager] isJailbrokenWithOtherJailbreak];
    BOOL isSupported = [[DOEnvironmentManager sharedManager] isSupported];

    NSString *jailbreakButtonTitle = [self jailbreakButtonTitle];
        
    UIImage *jailbreakButtonImage;
    if (isSupported)
        jailbreakButtonImage = [UIImage systemImageNamed:@"lock.open" withConfiguration:[DOGlobalAppearance smallIconImageConfiguration]];
    else
        jailbreakButtonImage = [UIImage systemImageNamed:@"lock.slash" withConfiguration:[DOGlobalAppearance smallIconImageConfiguration]];
    
    self.jailbreakBtn = [[DOJailbreakButton alloc] initWithAction: [UIAction actionWithTitle:jailbreakButtonTitle image:jailbreakButtonImage identifier:@"jailbreak" handler:^(__kindof UIAction * _Nonnull action) {
        [self beginJailbreakAutomatically:NO];
    }]];
    self.jailbreakBtn.enabled = !isJailbroken && isSupported;

    [self.view addSubview:self.jailbreakBtn];

    [NSLayoutConstraint activateConstraints:(self.jailbreakButtonConstraints = @[
        [self.jailbreakBtn.leadingAnchor constraintEqualToAnchor:stackView.leadingAnchor],
        [self.jailbreakBtn.trailingAnchor constraintEqualToAnchor:stackView.trailingAnchor],
        [self.jailbreakBtn.heightAnchor constraintEqualToAnchor:buttonPlaceHolder.heightAnchor],
        [self.jailbreakBtn.centerYAnchor constraintEqualToAnchor:buttonPlaceHolder.centerYAnchor]
    ])];

    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 0.1 * NSEC_PER_SEC), dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_LOW, 0), ^{
        if ([[DOUIManager sharedInstance] environmentUpdateAvailable])
        {
            dispatch_async(dispatch_get_main_queue(), ^{
                [self setupUpdateAvailable:YES];
            });
        }
        else if ([[DOUIManager sharedInstance] isUpdateAvailable])
        {
            dispatch_async(dispatch_get_main_queue(), ^{
                [self setupUpdateAvailable:NO];
            });
        }
    });
}

- (NSString *)jailbreakButtonTitle
{
    BOOL isJailbroken = [[DOEnvironmentManager sharedManager] isJailbroken];
    BOOL isSupported = [[DOEnvironmentManager sharedManager] isSupported];
    BOOL removeJailbreakEnabled = [[DOPreferenceManager sharedManager] boolPreferenceValueForKey:@"removeJailbreakEnabled" fallback:NO];

    NSString *jailbreakButtonTitle = DOLocalizedString(@"Button_Jailbreak_Title");
    if (!isSupported)
        jailbreakButtonTitle = DOLocalizedString(@"Unsupported");
    else if (isJailbroken)
        jailbreakButtonTitle = DOLocalizedString(@"Status_Title_Jailbroken");
    else if (removeJailbreakEnabled)
        jailbreakButtonTitle = DOLocalizedString(@"Button_Remove_Jailbreak");
    
    return jailbreakButtonTitle;
}

- (void)viewWillAppear:(BOOL)animated
{
    [super viewWillAppear:animated];
    [self.jailbreakBtn.button setTitle:[self jailbreakButtonTitle] forState:UIControlStateNormal];
}

- (void)beginJailbreakAutomatically:(BOOL)automatic
{
    [self cancelAutomaticTimers];
    self.automaticJailbreakCancelled = YES;
    if (self.jailbreakAttemptInProgress)
        return;

    [self.actionView hide];
    [self.jailbreakBtn expandButton:self.jailbreakButtonConstraints];
    self.jailbreakBtn.button.userInteractionEnabled = NO;
    self.updateButton.userInteractionEnabled = NO;
    [UIView animateWithDuration:0.75 delay:0 usingSpringWithDamping:0.9 initialSpringVelocity:2.0 options:UIViewAnimationOptionCurveEaseInOut animations:^{
        [self.headerView setTransform:CGAffineTransformMakeTranslation(0, -25)];
        self.updateButton.alpha = 0;
    } completion:nil];
    self.jailbreakAttemptInProgress = YES;
    [self startJailbreakAutomatically:automatic];
}

- (void)startJailbreakAutomatically:(BOOL)automatic
{
    DOJailbreaker *jailbreaker = [[DOJailbreaker alloc] init];

    if (automatic)
        self.automaticAttemptCount += 1;

    [[DOUIManager sharedInstance] startLogCapture];
    
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_HIGH, 0), ^{
        if ([jailbreaker contiguousMappingWorkaroundNeeded]) {
            
            cpu_subtype_t cpuFamily = 0;
            size_t cpuFamilySize = sizeof(cpuFamily);
            sysctlbyname("hw.cpufamily", &cpuFamily, &cpuFamilySize, NULL, 0);
            NSString *workaroundMessage = DOLocalizedString(@"Respring_Required_Message");
            if (cpuFamily == CPUFAMILY_ARM_TYPHOON) {
                workaroundMessage = [workaroundMessage stringByAppendingString:[NSString stringWithFormat:@"\n\n%@", DOLocalizedString(@"Respring_Required_Notice_A8")]];
            }

            UIAlertController *contiguousMappingWorkaroundAlertController = [UIAlertController alertControllerWithTitle:DOLocalizedString(@"Respring_Required") message:workaroundMessage preferredStyle:UIAlertControllerStyleAlert];
            
            UIAlertAction *cancelAction = [UIAlertAction actionWithTitle:DOLocalizedString(@"Respring_Cancel") style:UIAlertActionStyleCancel handler:^(UIAlertAction * _Nonnull action) {
                exit(0);
            }];
            
            UIAlertAction *workaroundAction = [UIAlertAction actionWithTitle:DOLocalizedString(@"Apply_Workaround") style:UIAlertActionStyleDefault handler:^(UIAlertAction * _Nonnull action) {
                [jailbreaker applyContiguousMappingWorkaround];
            }];
            
            [contiguousMappingWorkaroundAlertController addAction:cancelAction];
            [contiguousMappingWorkaroundAlertController addAction:workaroundAction];
            contiguousMappingWorkaroundAlertController.preferredAction = workaroundAction;

            dispatch_async(dispatch_get_main_queue(), ^{
                [self presentViewController:contiguousMappingWorkaroundAlertController animated:YES completion:nil];
            });
            return;
        }

        //We need to get the preconfig mutex to start the jailbreak (self.jailbreakBtn.canStartJailbreak)
        [self.jailbreakBtn lockMutex];
        dispatch_async(dispatch_get_main_queue(), ^{
            self.hideHomeIndicator = YES;
        });

        NSError *error;
        BOOL didRemove = NO;
        BOOL showLogs = YES;
        [jailbreaker runWithError:&error didRemoveJailbreak:&didRemove showLogs:&showLogs];
        dispatch_async(dispatch_get_main_queue(), ^{
            if (error && showLogs) {
                [[DOUIManager sharedInstance] sendLog:[NSString stringWithFormat:@"Jailbreak failed with error: %@", error] debug:NO];
                self.jailbreakAttemptInProgress = NO;
                if (automatic && self.automaticAttemptCount < DO_AUTO_MAX_ATTEMPTS) {
                    [[DOUIManager sharedInstance] sendLog:DOLocalizedString(@"Auto_Jailbreak_Retry") debug:NO];
                    self.automaticRetryTimer = [NSTimer scheduledTimerWithTimeInterval:DO_AUTO_RETRY_DELAY_SECONDS repeats:NO block:^(NSTimer *timer) {
                        self.automaticRetryTimer = nil;
                        if (UIApplication.sharedApplication.applicationState == UIApplicationStateActive &&
                            ![DOEnvironmentManager sharedManager].isJailbroken &&
                            [DOEnvironmentManager sharedManager].isSupported &&
                            ![[DOPreferenceManager sharedManager] boolPreferenceValueForKey:@"removeJailbreakEnabled" fallback:NO]) {
                            self.jailbreakAttemptInProgress = YES;
                            [self startJailbreakAutomatically:YES];
                        }
                    }];
                }
                else {
                    [self.navigationController pushViewController:[[DOLogCrashViewController alloc] initWithTitle:[error localizedDescription]] animated:YES];
                }
            }
            else if (error && !showLogs) {
                self.jailbreakAttemptInProgress = NO;
                // Used when there is an error that is explainable in such detail that additional logs are not needed
                UIAlertController *alertController = [UIAlertController alertControllerWithTitle:DOLocalizedString(@"Log_Error") message:[error localizedDescription] preferredStyle:UIAlertControllerStyleAlert];
                UIAlertAction *rebootAction = [UIAlertAction actionWithTitle:DOLocalizedString(@"Button_Reboot") style:UIAlertActionStyleDefault handler:^(UIAlertAction * _Nonnull action) {
                    exec_cmd_trusted(JBROOT_PATH("/sbin/reboot"), NULL);
                }];
                [alertController addAction:rebootAction];
                [self presentViewController:alertController animated:YES completion:nil];
            }
            else if (didRemove) {
                self.jailbreakAttemptInProgress = NO;
                UIAlertController *alertController = [UIAlertController alertControllerWithTitle:DOLocalizedString(@"Removed_Jailbreak_Alert_Title") message:DOLocalizedString(@"Removed_Jailbreak_Alert_Message") preferredStyle:UIAlertControllerStyleAlert];
                UIAlertAction *rebootAction = [UIAlertAction actionWithTitle:DOLocalizedString(@"Button_Close") style:UIAlertActionStyleDefault handler:^(UIAlertAction * _Nonnull action) {
                    exit(0);
                }];
                [alertController addAction:rebootAction];
                [self presentViewController:alertController animated:YES completion:nil];
            }
            else {
                // No errors
                self.jailbreakAttemptInProgress = NO;
                [[DOUIManager sharedInstance] completeJailbreak];
                [self fadeToBlack: ^{
                    [jailbreaker finalize];
                }];
            }
        });
        [self.jailbreakBtn unlockMutex];
    });
}

-(void)setupUpdateAvailable:(BOOL)environmentUpdate
{
    if (self.jailbreakBtn.didExpand)
        return;

    NSString *title = environmentUpdate ? DOLocalizedString(@"Button_Update_Environment") : DOLocalizedString(@"Button_Update_Available");
    
    NSString *releaseFrom = [[DOUIManager sharedInstance] getLaunchedReleaseTag];
    NSString *releaseTo = [[DOUIManager sharedInstance] getLatestReleaseTag];

    if (environmentUpdate)
    {
        releaseFrom = [[DOEnvironmentManager sharedManager] jailbrokenVersion];
        releaseTo = [[DOUIManager sharedInstance] getLaunchedReleaseTag];
    }

    self.updateButton = [DOActionMenuButton buttonWithAction:[UIAction actionWithTitle:title image:[UIImage systemImageNamed:@"arrow.down.circle" withConfiguration:[DOGlobalAppearance smallIconImageConfiguration]] identifier:@"update-available" handler:^(__kindof UIAction * _Nonnull action) {
        [self.navigationController pushViewController:[[DOUpdateViewController alloc] initFromTag:releaseFrom toTag:releaseTo] animated:YES];
    }] chevron:NO];

    self.updateButton.translatesAutoresizingMaskIntoConstraints = NO;
    [self.view addSubview:self.updateButton];

    [NSLayoutConstraint activateConstraints:@[
        [self.updateButton.centerXAnchor constraintEqualToAnchor:self.view.centerXAnchor],
        [self.updateButton.heightAnchor constraintEqualToConstant:30],
        [self.updateButton.bottomAnchor constraintEqualToAnchor:self.jailbreakBtn.topAnchor constant:[DOGlobalAppearance isHomeButtonDevice] ? -10 : -20]
    ]];

    [self.updateButton setTransform:CGAffineTransformMakeTranslation(0, 25)];
    [self.updateButton setAlpha:0];
    [UIView animateWithDuration:0.5 delay:0 usingSpringWithDamping:0.9 initialSpringVelocity:2.0  options: UIViewAnimationOptionCurveEaseInOut animations:^{
        [self.updateButton setTransform:CGAffineTransformIdentity];
        [self.updateButton setAlpha:1];
    } completion:nil];
}

-(void)simulateJailbreak
{
    // Let's simulate a "jailbreak" using grand central dispatch

    DOUIManager *uiManager = [DOUIManager sharedInstance];

    static BOOL didFinish = NO; //not thread safe lol
    

    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 3 * NSEC_PER_SEC), dispatch_get_main_queue(), ^{
        [uiManager completeJailbreak];
        [uiManager sendLog:@"Rebooting Userspace" debug: NO];
        didFinish = YES;
        [self fadeToBlack: ^{

        }];
    });

    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
        [NSThread sleepForTimeInterval:0.2];
        [uiManager sendLog:@"Launching kexploitd" debug: NO];
        [NSThread sleepForTimeInterval:0.5];
        [uiManager sendLog:@"Launching oobPCI" debug: NO];
        [NSThread sleepForTimeInterval:0.15];
        [uiManager sendLog:@"Gaining r/w" debug: NO];
        [NSThread sleepForTimeInterval:0.8];
        [uiManager sendLog:@"Patchfinding" debug: NO];
        NSArray *types = @[@"AMFI", @"PAC", @"KTRR", @"KPP", @"PPL", @"KPF", @"APRR", @"AMCC", @"PAN", @"PXN", @"ASLR", @"OPA"]; //Ever heard of the legendary opa bypass
        while (true)
        {
            [NSThread sleepForTimeInterval:0.6 * rand() / RAND_MAX];
            if (didFinish) break;
            NSString *type = types[arc4random_uniform((uint32_t)types.count)];
            [uiManager sendLog:[NSString stringWithFormat:@"Bypassing %@", type] debug: NO];
        }
    });
}

- (void)fadeToBlack:(void (^)(void))completion
{
    static bool didFade = false;
    if (didFade)
        return;
    didFade = true;
    UIView *mainView = self.parentViewController.view;
    float deviceCornerRadius = [[[UIScreen mainScreen] valueForKey:@"_displayCornerRadius"] floatValue];

    mainView.layer.cornerRadius = deviceCornerRadius;
    mainView.layer.cornerCurve = kCACornerCurveContinuous;
    mainView.layer.masksToBounds = YES;
    
    self.hideStatusBar = YES;

    [UIView animateWithDuration:0.5 delay:0 usingSpringWithDamping:0.9 initialSpringVelocity:2.0 options: UIViewAnimationOptionCurveEaseInOut animations:^{
        mainView.transform = CGAffineTransformMakeScale(0.9, 0.9);
        mainView.alpha = 0.0;
    } completion:^(BOOL success) {
        completion();
    }];
}

#pragma mark - Action Menu Delegate

- (BOOL)actionMenuShowsChevronForAction:(UIAction *)action
{
    if ([action.identifier isEqualToString:@"settings"] || [action.identifier isEqualToString:@"credits"]) return YES;
    return NO;
}

- (BOOL)actionMenuActionIsEnabled:(UIAction *)action
{
    if ([action.identifier isEqualToString:@"respring"] || [action.identifier isEqualToString:@"reboot-userspace"]) {
        return [[DOEnvironmentManager sharedManager] isJailbroken];
    }
    return YES;
}

#pragma mark - Status Bar

- (UIStatusBarStyle)preferredStatusBarStyle
{
    return UIStatusBarStyleLightContent;
}

- (BOOL)prefersStatusBarHidden
{
    return self.hideStatusBar;
}

- (BOOL)prefersHomeIndicatorAutoHidden
{
    return self.hideHomeIndicator;
}

- (void)setHideStatusBar:(BOOL)hideStatusBar
{
    _hideStatusBar = hideStatusBar;
    [self setNeedsStatusBarAppearanceUpdate];
}

- (void)setHideHomeIndicator:(BOOL)hideHomeIndicator
{
    _hideHomeIndicator = hideHomeIndicator;
    [self setNeedsUpdateOfHomeIndicatorAutoHidden];
}

@end
