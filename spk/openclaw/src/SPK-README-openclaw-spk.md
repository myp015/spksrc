# openclaw-spk 内置命令说明

`openclaw-spk` 是 OpenClaw SPK 的命令包装器，安装后位于：

- `/var/packages/openclaw/target/bin/openclaw-spk`

## 它做了什么

1. 自动读取 SPK 配置并解析当前工作目录（workspace）
2. 自动设置环境变量：
   - `OPENCLAW_CONFIG_PATH`
   - `OPENCLAW_STATE_DIR`
   - `HOME`
3. 将你的命令转发到 SPK 内置 OpenClaw CLI 入口

这样你不需要每次手工写一长串 node/dist 路径。

## 默认路径与 Token

- 默认配置目录：`/volume1/docker/openclaw`
- 默认配置文件：`/volume1/docker/openclaw/openclaw.json`
- 模板默认 Token：`123456`（可在 `openclaw.json` 中修改）

查看当前 token：

```bash
openclaw-spk token
```

## 常用命令

```bash
openclaw-spk gateway status
openclaw-spk gateway restart
openclaw-spk config get
openclaw-spk models list
openclaw-spk plugins install @tencent-connect/openclaw-qqbot@latest
```

指定配置文件（推荐多实例/测试目录场景）：

```bash
openclaw-spk --config /volume1/docker/test/openclaw.json doctor --fix
```

你也可以直接导出环境变量覆盖：

```bash
OPENCLAW_CONFIG_PATH=/volume1/docker/test/openclaw.json \
OPENCLAW_STATE_DIR=/volume1/docker/test \
openclaw-spk config get
```

## 诊断

查看 wrapper 实际解析到的路径：

```bash
openclaw-spk env
```

输出示例：

```text
OPENCLAW_CONFIG_PATH=/volume1/docker/openclaw/openclaw.json
OPENCLAW_STATE_DIR=/volume1/docker/openclaw
HOME=/volume1/docker/openclaw
```

如果命令报错，请先确认：

1. OpenClaw SPK 已安装并正在运行
2. `openclaw.json` 路径存在
3. `openclaw-spk env` 显示的路径与你预期一致
