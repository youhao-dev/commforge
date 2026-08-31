# 构建与发布

CommForge 使用 PyInstaller 的 one-folder 模式生成原生桌面目录，再统一压缩为 ZIP。PyInstaller 不支持从一个系统交叉编译另一个系统，因此 GitHub Actions 会在目标系统和目标 CPU 上分别执行原生构建。

## 支持矩阵

| 产物标识 | GitHub runner | Python | 说明 |
| --- | --- | --- | --- |
| `windows-x64` | `windows-2025` | 3.12 | Windows Server 2025 x64 原生构建 |
| `windows-arm64` | `windows-11-arm` | 3.12 | Windows 11 ARM64 原生构建 |
| `linux-x64` | `ubuntu-24.04` | 3.12 | Ubuntu 24.04 x64 原生构建 |
| `linux-arm64` | `ubuntu-24.04-arm` | 3.12 | Ubuntu 24.04 ARM64 原生构建 |
| `macos-x64` | `macos-15-intel` | 3.12 | macOS 15 Intel 原生构建 |
| `macos-arm64` | `macos-15` | 3.12 | macOS 15 Apple Silicon 原生构建 |

这里的“各 CPU 架构”指 PySide6、Python 3.12 与 GitHub 标准托管运行器共同支持的主流桌面架构 x64 和 ARM64。由于上游没有完整的 32 位 PySide6/Python 3.12 构建链，本项目不生成 x86/ARM32 桌面包。

## 本地构建

先安装运行依赖和 PyInstaller：

```bash
python -m pip install -r requirements.txt
python -m pip install "pyinstaller>=6.0,<7"
```

执行测试并构建：

```bash
python -m pytest -q -p no:cacheprovider
python -m PyInstaller --noconfirm --clean CommForge.spec
```

输出位于 `dist/CommForge/`。`CommForge.spec` 会将主 README 和用户指南复制到运行目录，Qt 插件、SQLAlchemy 和串口依赖由 PyInstaller hooks 收集。

压缩并生成 SHA-256：

```bash
python scripts/package_release.py --platform windows --arch x64 --version 1.0.0
```

产物位于 `artifacts/`：

```text
CommForge-v1.0.0-windows-x64.zip
CommForge-v1.0.0-windows-x64.zip.sha256
```

压缩包始终包含一个 `CommForge/` 顶层目录，用户解压时不会把大量 Qt 文件散落到当前目录。

## GitHub Actions 行为

工作流文件：`.github/workflows/build-release.yml`。

- 推送到 `master` 或 `main`：六种环境运行测试、打包并上传 Artifacts。
- Pull Request：执行同样的六环境验证，但不创建 Release。
- 手动运行：可以从 Actions 页面选择 **Build and release** 后执行。
- 推送 `v*` 标签：等待全部环境成功后创建 GitHub Release，并上传 6 个 ZIP 与 6 个 SHA-256 文件。

发布示例：

```bash
git tag v1.0.0
git push origin v1.0.0
```

版本号由 `pyproject.toml` 读取。发布标签建议与项目版本保持一致；修改版本时也应同步更新 `commforge/__init__.py`。

## 产物验证

Windows PowerShell：

```powershell
Get-FileHash .\CommForge-v1.0.0-windows-x64.zip -Algorithm SHA256
```

Linux / macOS：

```bash
shasum -a 256 CommForge-v1.0.0-linux-x64.zip
```

输出应与相邻 `.sha256` 文件中的摘要一致。

## 代码签名

当前仓库不包含 Windows Authenticode 或 Apple Developer 证书，也不会在 CI 中上传私钥。因此自动产物是未签名版本。若用于面向公众的正式分发，应通过 GitHub Environments/Secrets 注入签名材料，并在压缩步骤之前完成签名和 macOS 公证。

## 运行时数据位置

源码模式使用仓库根目录的 `data/` 和 `logs/`；PyInstaller 冻结模式使用可执行文件旁的同名目录。此差异由 `commforge.app.paths.resolve_project_root()` 统一处理，避免将数据库写入 PyInstaller 的 `_internal` 目录。
