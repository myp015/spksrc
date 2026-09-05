# DSM 7 套件面板 root 授权方法（OpenClaw SPK 实战记录）

> 目标读者：以后要在别的 SynoCommunity SPK 面板里做「管理员输密码 → 写入 sudoers →
> 解锁面板操作」的开发者。这份文档把 OpenClaw SPK 里踩通的全流程、关键坑、以及可复用的
> 判定逻辑写下来，避免重新踩坑。

## 1. 最重要的事实：面板 CGI 以 root 运行

DSM 7 的 webman 3rdparty 套件 UI（`/webman/3rdparty/<app>/index.cgi`）不是由 nginx worker
（`http` 用户）直接执行的——nginx 里 `.cgi` 走 `scgi_pass synoscgi`，由 **`synoscgi` 进程**
执行。实测 OpenClaw 面板 CGI 的 `os.getuid()` **恒为 `0`（root）**。

推论：

- 在 CGI 里做 `sudo -n docker version` 探测**恒为真**（root 不需要 sudoers 就能任意 sudo）。
  用它判断「授权与否」是无效的——面板永远显示已授权。
- 因此 sudoers 文件约束的不是面板自身，而是**非 root 组件**：套件服务用户 `sc-openclaw`
  的 docker/终端入口、以及（若面板曾以 http 运行时的）http 用户。

### 怎么确认你的面板 CGI 以谁运行

在 status 端点里输出运行身份（OpenClaw 已内置，概览页显示「面板运行用户」）：

```python
import os, pwd
_u = os.getuid()
_un = pwd.getpwuid(_u).pw_name   # 'root' / 'http' / 'sc-openclaw' 等
```

## 2. 授权判定：以 sudoers 文件为准

OpenClaw 的授权状态 = `/etc/sudoers.d/openclaw-ui` 存在 **且** `sc-openclaw` 能 `sudo -n docker`。
因为 CGI 是 root，用嵌套 sudo 直接以 sc-openclaw 身份探测（root 用 `sudo -n -u` 转过去不需要密码）：

```python
def auth_ok():
    try:
        if not os.path.exists('/etc/sudoers.d/openclaw-ui'):
            return False
        p = subprocess.run(['sudo', '-n', '-u', 'sc-openclaw', 'sudo', '-n',
                            '/usr/local/bin/docker', 'version'],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=8)
        return p.returncode == 0
    except Exception:
        return False
```

`index.cgi` 中此判定统一用于：status 的 `_auth_check`、`authorize` 的 `auth_check`、
`install_run` / `logs` / `install` 的 `auth_ok`。

## 3. sudoers 内容（authorize-root.sh 写入）

`/etc/sudoers.d/openclaw-ui`（`chmod 440`，写入前用 `visudo -c -f` 校验）：

```
http ALL=(root) NOPASSWD: /usr/syno/bin/synopkg, /usr/local/bin/docker, /usr/bin/docker, /bin/systemctl, /usr/sbin/nginx, /usr/bin/nginx, /bin/ln, /var/packages/openclaw/target/scripts/ui-run.sh
sc-openclaw ALL=(root) NOPASSWD: /usr/local/bin/docker, /usr/bin/docker, /usr/syno/bin/synopkg, /var/packages/openclaw/target/scripts/openclaw-terminal-entry.sh
```

- `http` 规则：面板若以 http 运行时的 docker/nginx 修复命令。
- `sc-openclaw` 规则：套件服务用户的 docker 助手 + 终端入口（web 终端变 root shell 的关键）。

payload 脚本：`spk/openclaw/src/scripts/authorize-root.sh`（写入 → `visudo -c` 校验 → mv → chmod 440，
日志到 `/var/packages/openclaw/var/authorize-root.log`）。

## 4. 授权流程（SimplePermissionManager 式，DSM 7.2 v4 API）

浏览器端 `doAuthorizePanel()`（index.cgi）：

1. **验证管理员密码**，拿一次性 `SynoConfirmPWToken`：
   `SYNO.Core.User.PasswordConfirm auth v2 {password}`。
2. **取任务骨架**（后端认可的 schedule/extra/real_owner 模板）：
   `SYNO.Core.TaskScheduler get v4 {id:-1, type:"script"}`。
3. **创建一次性 root 脚本任务**：
   `SYNO.Core.TaskScheduler.Root create v4`
   `{name, owner:"root", enable:true, type:"script", extra:{script: payload}, schedule, SynoConfirmPWToken}`；
   若骨架返回 `real_owner` 则一并带上。
4. **查任务 id + real_owner**（run/delete 必需，从后端返回拿，不猜用户名）：
   `SYNO.Core.TaskScheduler list v3 {offset:0, limit:100}`（刚创建可能未入列表，需重试）。
5. **运行**：`SYNO.Core.TaskScheduler run v2 {tasks:[{id, real_owner}]}`（无密码）。
6. **轮询授权生效**（run 是异步的，不能只查一次）→ **删除**：`delete v2 {tasks:[{id, real_owner}]}`。

### 4800 根因：requestFormat=JSON（必读）

`SYNO.Core.TaskScheduler` 继承 entry.cgi 默认模板 `/usr/syno/synoman/webapi/lib.def` 的
`"requestFormat": "JSON"`（TaskScheduler.lib 没覆盖它）。所以官方任务计划 UI 会把**每个顶层
参数值 `JSON.stringify` 后**放进 form 字段再发：

- 正确：`schedule={"date_type":0,...,"monthly_week":[],...}`、`tasks=[{"id":5,"real_owner":"admin"}]`、
  `extra={"script":"..."}`。
- 错误：普通表单 bracket 序列化 `schedule[monthly_week]=`（空数组变空字符串）→ 后端逐字段
  JSON.parse 后类型不合法 → **`4800 monthly_week expected for v4`**。

`dsmApiFetch` 的 `jsonMode` 就是为此加的：每个顶层值 `encodeURIComponent(JSON.stringify(v))`。

### 为什么不用旧版 EventScheduler

`SYNO.Core.EventScheduler.Root v1` 在 DSM 7.x 即使收到 `owner[0]=root` 也读不到 owner
（报 117）。必须用 `SYNO.Core.TaskScheduler.Root v4`（owner 是平铺字符串 `"root"`）。

### SynoToken 要求

DSM 7.2 开启 SynoToken 后，敏感 webapi 必须带当前会话 token，否则返回 `119`（会话已过期）。
面板复用 `SYNO.SDS.UpdateSynoToken` 机制：嵌入桌面时读框架缓存的
`parent.SYNO.SDS.Session.SynoToken`；独立打开时 `GET /webman/login.cgi` 取；请求同时带
`X-SYNO-TOKEN` 头 + `SynoToken` 查询参数。

## 5. 复用清单（给其他 SPK）

- [ ] 面板 CGI 以 root 运行是 DSM 默认，别用自身 sudo 探测授权。
- [ ] 授权状态 = sudoers 文件存在 + 套件服务用户能 `sudo -n docker`（嵌套 sudo 探测）。
- [ ] 授权流程用 `SYNO.Core.TaskScheduler.Root` v4 + `SynoConfirmPWToken`，TaskScheduler 调用一律 `jsonMode`。
- [ ] payload 脚本 `visudo -c` 校验后再 `mv`，`chmod 440`。
- [ ] run 后轮询生效再返回成功（run 是异步的）。
- [ ] 参考实现：`spk/openclaw/src/scripts/authorize-root.sh`、
  `spk/openclaw/src/ui/index.cgi`（`doAuthorizePanel` / `dsmApiFetch` / `findTaskRefByName` / `fetchCreateSkeleton`）。
