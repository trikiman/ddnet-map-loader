# DDNet Map Loader v2（便携版）

一个小工具：让你双击任何`.map`文件即可在本地 DDNet 服务器热重载，同时自动备份并记录日志。

## 📋 系统要求
- Windows 10/11（无需管理员权限）
- 已安装 DDNet 客户端/服务器，并可连接到本地服务器

## 🤔 这是什么/有什么用
- 将`.map`文件与本程序关联。
- 双击地图后会：
  - 校验地图文件
  - 备份当前正在使用的地图
  - 替换工作用地图并发送`hot_reload`
  - 将过程写入`%APPDATA%\DDNet\maps\ddnet_control.log`
- 适合制图时进行快速本地测试。

## 🚀 快速使用
1) 检查/移动 `myServerconfig.cfg`
   - 找到 DDNet 的 `data` 文件夹（见下文），将 `myServerconfig.cfg` 复制进去（推荐）。
2) 将`.map`文件与本程序关联（推荐）
   - 右键任意 `.map` → 打开方式 → 选择其他应用 → 更多应用 → 在这台电脑上查找其他应用
   - 选择本文件夹中的 `ddnet_control.exe`
   - 勾选“始终使用此应用打开 .map 文件”并确认
   - 确认`.map`图标已改变；若未改变，请见“故障排查”。
   - 进阶（可选）：也可运行 `registry\setup_map_association_current_user.bat` 自动为当前用户注册，然后重启资源管理器。
3) 双击任意 `.map`
   - 例如：`%APPDATA%\DDNet\maps\mapsfortest\anymap.map`
   - 文件图标应为新的加载器图标（若是快捷方式可能带小箭头）。
4) 查看日志
   - `%APPDATA%\DDNet\maps\ddnet_control.log`（包含校验/备份/重载状态）

## 📁 myServerconfig.cfg 放在哪里
- 快速找到 DDNet `data` 文件夹的方法：
  1) 在任务栏/开始菜单/桌面上右键 DDNet 快捷方式 → 打开文件位置
  2) 在打开的文件夹中进入 `ddnet` 目录（`DDNet.exe` 所在处）
  3) 打开 `data` 子文件夹 → 将 `myServerconfig.cfg` 复制进去
- 常见位置（示例，实际可能不同）：
  - Steam 默认：`C:\Program Files (x86)\Steam\steamapps\common\DDraceNetwork\ddnet\data`
  - 其他 Steam 库：`<YourSteamLibrary>\steamapps\common\DDraceNetwork\ddnet\data`
  - 非 Steam/便携版：与 `DDNet.exe` 同级的 `data` 文件夹

## 🧰 故障排查
- 窗口一闪而过
  - 多为未传入文件路径。请重新按第 2 步关联并重启资源管理器。
- “打开方式”里找不到应用
  - 按第 2 步的“在这台电脑上查找其他应用”，选择 `ddnet_control.exe`，并勾选“始终使用此应用…”。
- 图标未更新
  - 重启 Windows 资源管理器；图标缓存较顽固。
- 未热重载
  - 确保本地服务器在 `127.0.0.1:8303` 运行，RCON 设置正确。
  - 查看 `%APPDATA%\DDNet\maps\ddnet_control.log` 获取原因。
- 取消关联
  - 运行：`registry\remove_map_association_current_user.bat`

## 📂 包含内容
- `ddnet_control.exe`
- `ddnet_loader.ico`
- `myServerconfig.cfg`
- `registry/`
  - `setup_map_association_current_user.bat`
  - `remove_map_association_current_user.bat`