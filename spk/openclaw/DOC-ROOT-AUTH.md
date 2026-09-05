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

## 4. 授权流程（EventScheduler v1 做管理员凭证 + 面板 CGI 同步直写 —— 秒级生效）

浏览器端 `doAuthorizePanel()`（index.cgi）：

1. **验证管理员密码**，拿一次性 `SynoConfirmPWToken`：
   `SYNO.Core.User.PasswordConfirm auth v2 {password}`。
2. **创建一次性 root 脚本任务**（`event:"bootup"`，只作**管理员身份 + CSRF 凭证**，
   **不运行**）：
   `SYNO.Core.EventScheduler.Root create v1`
   `{task_name, owner:{0:"root"}, event:"bootup", enable:true, depend_on_task:"",
   notify_enable:false, notify_mail:"", notify_if_error:false,
   operation_type:"script", operation:"<root 脚本完整路径>", SynoConfirmPWToken:token}`
   —— script 任务的 `operation` 就是**要执行的命令本身**（完整路径即可，
   esynoscheduler 存的是命令：系统自带 shutdown 任务就是
   `operation=/usr/bin/loader-reboot.sh`），**不需要**任何符号链接。
3. **同步直写**：POST 面板后端 action `authorize_write {task_name}`。后端先核对
   任务真实存在（create 需要管理员密码 token，任务存在 = 管理员验证 + CSRF 防护
   已通过），然后**由面板 CGI（root）直接执行 `authorize-root.sh`** 写 sudoers，
   秒级返回。
4. **删除**：`SYNO.Core.EventScheduler delete v1 {task_name}`（任务只是凭证）。

### 为什么「建任务却不 run」：这台 NAS 上两个调度器的 run 都是异步的

- `SYNO.Core.TaskScheduler.Root create v4` + `run v2` 是**官方推荐**的新接口，但它的
  `run` 是**异步排队**的：root 脚本要等 `synoscheduled` 守护进程下一轮扫描才执行，
  实测滞后 **5~10 分钟**。面板 60s 轮询必然超时，于是反复出现「密码正确却提示
  授权未生效」的假失败。
- **EventScheduler 的 `run v1` 在这台 NAS 上同样异步**：`run` 返回后脚本实际运行
  晚了约 **1 分钟**（`authorize-root.log` 的写入时间比 run 请求晚 ~60-100s），面板
  60s 轮询照样超时。它的「秒级」名声来自 webapi 能直接调它的 API，但**脚本执行
  本身并不跟 run 同步**。
- 结论：**任何「run + 轮询」方案都不稳**。既然面板 CGI 恒以 root 运行（见 §1），
  sudoers 的写入就直接由 CGI 执行，create 任务只充当不可绕过的管理员凭证
  （token 只能在输对管理员密码时拿到，且 create 本身是管理员级的 webapi）。
  这是 OpenClaw 现在的实现（`authorize_write`），彻底没有时序竞态。
- 早期本仓库以为「EventScheduler v1 读不到 owner（117）」是 API 限制，其实那是
  **编码错误**：没用 jsonMode 发 `owner={"0":"root"}`。v1 完全可用（本仓库只用它
  建凭证，已验证）。

### 4800 根因：requestFormat=JSON（必读）

`SYNO.Core.EventScheduler` / `TaskScheduler` 都继承 entry.cgi 默认模板
`/usr/syno/synoman/webapi/lib.def` 的 `"requestFormat": "JSON"`。所以官方 UI 会把
**每个顶层参数值 `JSON.stringify` 后**放进 form 字段再发：

- 正确：`owner={"0":"root"}`、`tasks=[{"id":5,"real_owner":"admin"}]`、
  `schedule={"date_type":0,...,"monthly_week":[],...}`、`extra={"script":"..."}`。
- 错误：普通表单 bracket 序列化 `owner[0]=root` / `schedule[monthly_week]=`
  （空数组变空字符串）→ 后端逐字段 JSON.parse 后类型不合法 → **`4800 ... expected/type invalid`**
  （bracket 发 owner 还可能导致读不到 owner）。

`dsmApiFetch` 的 `jsonMode` 就是为此加的：每个顶层值 `encodeURIComponent(JSON.stringify(v))`。

### SynoToken 要求

DSM 7.2 开启 SynoToken 后，敏感 webapi 必须带当前会话 token，否则返回 `119`（会话已过期）。
面板复用 `SYNO.SDS.UpdateSynoToken` 机制：嵌入桌面时读框架缓存的
`parent.SYNO.SDS.Session.SynoToken`；独立打开时 `GET /webman/login.cgi` 取；请求同时带
`X-SYNO-TOKEN` 头 + `SynoToken` 查询参数。

## 5. 复用清单（给其他 SPK）

- [ ] 面板 CGI 以 root 运行是 DSM 默认，别用自身 sudo 探测授权。
- [ ] 授权状态 = sudoers 文件存在 + 套件服务用户能 `sudo -n docker`（嵌套 sudo 探测）。
- [ ] 授权流程：`SYNO.Core.User.PasswordConfirm auth v2` 拿 `SynoConfirmPWToken` →
      `SYNO.Core.EventScheduler.Root create v1` 建一次性 root 任务（**管理员凭证 + CSRF
      防护**）→ 面板 CGI（root）直接执行授权脚本**同步写 sudoers** → `delete v1`。
      **别用** `TaskScheduler.Root v4 + run v2`（run 异步排队 5~10 分钟）；**也别指望**
      `EventScheduler run` 同步执行（本 NAS 实测 run 后脚本滞后 ~1 分钟）——凡
      「run + 轮询」都不稳，直接让 root CGI 同步写。
- [ ] 调用一律 `jsonMode`（lib.def 默认 requestFormat=JSON，owner 发 `owner={"0":"root"}`）。
- [ ] script 任务的 `operation` 填 root 脚本**完整路径**，无需符号链接。
- [ ] payload 脚本 `visudo -c` 校验后再 `mv`，`chmod 440`（visudo 缺失时跳过校验，直接 mv）。
- [ ] 后端同步写前核对一次性任务真实存在（`esynoscheduler.db` 只读查询 operation 含
      `authorize-root.sh`），任务不存在则拒绝——这是服务端对「管理员已验证」的独立证据。
- [ ] 参考实现：`spk/openclaw/src/scripts/authorize-root.sh`、
  `spk/openclaw/src/ui/index.cgi`（`doAuthorizePanel` / `dsmApiFetch` / 后端 `authorize_write`）。
