# OpenClaw SPK（真容器版）— 在线自更新

把 **Docker 版本的 OpenClaw** 打包为 Synology（群晖）SPK。设置界面移植自 `spk/ainasclaw`，但**运行时改为 Docker 容器**，且实现了**容器内在线自更新**——不再像 ainasclaw 那样每次上游发版都要重新编译整个 SPK。

## 与 ainasclaw 的核心区别

| 维度 | ainasclaw | 本包 openclaw（容器版） |
|---|---|---|
| 运行时 | 无 Docker，node 直接跑 npm bundle | **Docker 容器**（依赖群晖 Docker/Container Manager 套件） |
| 镜像 | 无 | **固定** `openclaw/openclaw:2026.8.2`，从不更新 |
| OpenClaw 本体 | 静态打进 SPK，更新=重新编译 | 在**持久卷**里，容器内 npm **在线自更新**，重启保留 |
| 升级 | 手动装新 SPK | 套件内点「在线升级」，或 `openclaw update` |

## 工作原理

### 固定镜像，只当「种子 + Node 环境」
容器镜像 `openclaw/openclaw:2026.8.2` 固定不动。它提供：
- Node.js 运行时
- 初始 OpenClaw 应用（镜像内 `/app`）

### OpenClaw 本体放持久卷，可在线更新
容器挂载数据目录（默认 `/volume1/docker/openclaw`）：
```
data/runtime/    # OpenClaw 程序本体（首次从镜像 /app 复制种子）
data/conf/       # OpenClaw 配置/状态 → 容器内 /home/node/.openclaw
data/workspace/  # 工作区
data/scripts/    # 容器入口 + 更新脚本
```
容器启动时用覆盖后的 `entrypoint.sh`：
1. `/data/runtime` 为空 → 从镜像 `/app` 复制种子
2. 有更新标记 → 跑 `update-openclaw.sh`
3. 用 `/data/runtime/openclaw.mjs` 启动 gateway

**在线更新** = 容器内 `npm pack openclaw@<version>` → 解包到临时目录 → 保留 `node_modules` 增量替换 `/data/runtime` → 重启容器。镜像/容器本体从不改。

## 目录结构（spk/openclaw）

```
src/
  Makefile                        # SPK 构建（轻壳，无运行时）
  service-setup.sh                # 安装/升级/卸载钩子 + 容器配置
  start-stop-status               # 容器 start/stop/status（自定义，SSS_SCRIPT）
  openclaw-spk                    # 宿主侧 `openclaw` CLI 包装（docker exec）
  openclaw.json                   # OpenClaw 默认配置模板
  scripts/ui-run.sh               # root 特权辅助（web UI 经 sudo 调用）
  ui/index.cgi                    # DSM 设置界面（概览/模型/渠道/在线升级/日志）
  app/                            # DSM 应用壳（openclaw.js + config + 图标）
  container/
    entrypoint.sh                 # 容器入口（种子 + 启动）
    update-openclaw.sh            # 容器内 OpenClaw 自更新
  wizard_templates/               # 安装/升级向导（数据目录 + 端口）
```

## 构建

```sh
# 装一次构建依赖
apt-get install -y imagemagick moreutils jq ruby
gem install mustache --no-document

cd /www/project/spksrc/spk/openclaw
make arch-x64-7.2          # Intel x64
make arch-aarch64-7.2      # ARMv8（RTD1296/RTD1619B/armada37xx）
# 产物：packages/openclaw_<arch>-7.2_2026.8.2-1.spk
```

## 安装

1. 群晖安装 **Docker / Container Manager** 套件
2. 套件中心 → 手动安装 → 选择 `.spk`
3. 向导填：**数据目录**（建议空间充足的存储卷）+ **端口**（默认 58789）
4. 安装时自动 `docker pull openclaw/openclaw:2026.8.2`；首次启动容器完成种子复制

## 使用

- **设置界面**：DSM 主菜单 → OpenClaw（概览 / 模型配置 / 渠道配置 / 在线升级 / 运行日志）
- **在线升级**：设置界面「在线升级」Tab 或命令行
  ```sh
  openclaw check-update   # 已装 vs 最新
  openclaw update         # 升级到 latest
  openclaw update 2026.8.3   # 指定版本
  ```
- **OpenClaw 面板**：`http://<NAS>:58789/openclaw-web`（默认 Token: 123456）
- 通用 CLI：`openclaw status|restart|logs|doctor` 等

## 注意事项

- **依赖群晖 Docker**：未安装 Docker 套件时服务无法启动（安装向导已提示）。
- **数据目录只增不删**：升级 SPK 外壳不碰 `data/`；卸载套件会**删除数据目录**，请先备份。
- **镜像 tag 固定**：如官方基础镜像布局/入口有重大变化，需手动改 `Makefile` 的 `OPENCLAW_IMAGE_TAG` 并重新构建外壳 SPK（仅此情形才需重编译）。
