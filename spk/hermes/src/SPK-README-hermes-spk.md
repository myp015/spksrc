# hermes 内置命令说明

`hermes` 是 Hermes Agent SPK 的命令包装器，安装后位于：

- `/var/packages/hermes/target/bin/hermes`
- （通常也会同步到 `/usr/local/bin/hermes`）

## 它做了什么

1. 自动读取 SPK 配置并解析当前工作目录（workspace）
2. 自动设置环境变量：
   - `HERMES_CONFIG_PATH`
   - `HERMES_STATE_DIR`
   - `HOME`
3. 将你的命令转发到 SPK 内置 Hermes Agent CLI 入口
4. 不自动切换用户；建议在服务用户下执行（`sc-hermes`），避免权限混乱

这样你不需要每次手工写一长串 node/dist 路径。

## 默认路径与 Token

- 默认用户目录（HOME）：`/volume1/hermes`
- 默认状态目录：`/volume1/hermes/.hermes`
- 默认配置文件：`/volume1/hermes/.hermes/hermes.json`
- 模板默认 Token：`123456`（可在 `hermes.json` 中修改）

查看当前 token：

```bash
hermes token
```

## 常用命令

```bash
hermes gateway status
hermes gateway restart
hermes config get
hermes models list
hermes plugins install @tencent-connect/hermes-qqbot@latest
```

指定配置文件（推荐多实例/测试目录场景）：

```bash
hermes --config /volume1/test/hermes.json doctor --fix
```

你也可以直接导出环境变量覆盖：

```bash
HERMES_CONFIG_PATH=/volume1/test/hermes.json \
HERMES_STATE_DIR=/volume1/test/.hermes \
hermes config get
```

## 诊断

查看 wrapper 实际解析到的路径：

```bash
hermes env
```

输出示例：

```text
HERMES_CONFIG_PATH=/volume1/hermes/.hermes/hermes.json
HERMES_STATE_DIR=/volume1/hermes/.hermes
HOME=/volume1/hermes
```

如果命令报错，请先确认：

1. Hermes Agent SPK 已安装并正在运行
2. `hermes.json` 路径存在
3. `hermes env` 显示的路径与你预期一致
