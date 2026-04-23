# openclaw 内置命令说明

`openclaw` 是 OpenClaw SPK 的命令包装器，安装后位于：

- `/var/packages/ainasclaw/target/bin/openclaw`
- （通常也会同步到 `/usr/local/bin/openclaw`）

## 它做了什么

1. 自动读取 SPK 配置并解析当前工作目录（workspace）
2. 自动设置环境变量：
   - `OPENCLAW_CONFIG_PATH`
   - `OPENCLAW_STATE_DIR`
   - `HOME`
3. 将你的命令转发到 SPK 内置 OpenClaw CLI 入口
4. 不自动切换用户；建议在服务用户下执行（`sc-openclaw`），避免权限混乱

这样你不需要每次手工写一长串 node/dist 路径。

## 默认路径与 Token

- 默认用户目录（HOME）：`/volume1/openclaw`
- 默认状态目录：`/volume1/openclaw/.openclaw`
- 默认配置文件：`/volume1/openclaw/.openclaw/openclaw.json`
- 模板默认 Token：`123456`（可在 `openclaw.json` 中修改）

查看当前 token：

```bash
openclaw token
```

## 常用命令

```bash
openclaw gateway status
openclaw gateway restart
openclaw config get
openclaw models list
openclaw plugins install @tencent-connect/openclaw-qqbot@latest
```

指定配置文件（推荐多实例/测试目录场景）：

```bash
openclaw --config /volume1/test/openclaw.json doctor --fix
```

你也可以直接导出环境变量覆盖：

```bash
OPENCLAW_CONFIG_PATH=/volume1/test/openclaw.json \
OPENCLAW_STATE_DIR=/volume1/test/.openclaw \
openclaw config get
```

## 诊断

查看 wrapper 实际解析到的路径：

```bash
openclaw env
```

输出示例：

```text
OPENCLAW_CONFIG_PATH=/volume1/openclaw/.openclaw/openclaw.json
OPENCLAW_STATE_DIR=/volume1/openclaw/.openclaw
HOME=/volume1/openclaw
```

如果命令报错，请先确认：

1. OpenClaw SPK 已安装并正在运行
2. `openclaw.json` 路径存在
3. `openclaw env` 显示的路径与你预期一致
