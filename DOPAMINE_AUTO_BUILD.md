# DopamineAuto 构建与安装

本分支基于官方 Dopamine 3.x，仅增加启动自动越狱、一次失败重试和已越狱自动退出。电源控制、重启检测和向日葵远控不包含在包内。

## 1. 创建 GitHub 仓库

1. 登录 GitHub，创建一个新的个人仓库，例如 `DopamineAuto`。
2. 选择 Public 或 Private 均可；不要勾选初始化 README、License 或 `.gitignore`。
3. 在本地 Dopamine 源码目录执行：

   ```powershell
   git remote add origin https://github.com/<你的用户名>/DopamineAuto.git
   git push -u origin dopamine-auto-source
   ```

4. 打开仓库的 Actions 页面，确认工作流已被识别。

## 2. 触发 macOS 构建

1. 选择 `Dopamine: build and upload` 工作流。
2. 点击 `Run workflow`，分支选择 `dopamine-auto-source`。
3. 等待 `Test DopamineAuto source contracts`、Procursus、THEOS 和 Xcode 构建全部完成。
4. 在成功的运行页面底部下载 `DopamineAuto-<commit>` artifact。

GitHub Actions 使用 macOS runner 编译；Windows 本机不能替代 Xcode/iPhoneOS SDK。工作流会在上传前把上游生成的 `Dopamine.tipa` 重命名为 `DopamineAuto.tipa`。

## 3. 安装到 TrollStore

1. 解压下载的 artifact，得到 `DopamineAuto.tipa`。
2. 将文件传到 iPhone（AirDrop、文件共享或网盘均可）。
3. 在文件 App 中点击 `.tipa`，选择 TrollStore 安装。
4. 因为包标识仍为 `com.opa334.Dopamine`，它会替换当前标准 Dopamine；安装前应确认自己保留了官方 IPA 作为回滚副本。
5. 打开 DopamineAuto → Settings，确认：
   - `Automatic Jailbreak` 已开启；
   - `Exit When Already Jailbroken` 已开启；
   - 至少一个 Package Manager 已配置；
   - `Remove Jailbreak` 未开启。

## 4. 配合快捷指令

将现有的“充电器已连接 → 打开 Dopamine”动作改为打开 `DopamineAuto`。DopamineAuto 在主界面出现后显示 8 秒倒计时；倒计时结束后自动运行原始越狱流程。第一次详细日志失败时，30 秒后自动再试一次；第二次失败保留日志并停止。

如果设备已经处于越狱状态，`Exit When Already Jailbroken` 会在 3 秒后关闭 App，避免充电器自动化重复打开它。

## 5. 回滚

出现异常时，在 TrollStore 卸载 DopamineAuto，重新安装官方 Dopamine。不要在越狱进行中强制终止 App；成功路径需要先完成原有 `finalize` 和用户空间转换。

## 6. 验证边界

本地 Windows 测试只能验证源代码契约。以下项目必须在你的 iPhone 12 / iOS 15.0 上验证：快捷指令拉起、倒计时取消、自动越狱、一次重试、成功 finalize、已越狱自动退出。漏洞利用失败或设备异常重启时，应保留官方 Dopamine 的恢复方式。
