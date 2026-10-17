# TB7 新人安装测试流程

负责人：B。目标（技术文档 §8 TB7）：请一位队外人员只看 `docs/SETUP.md` 安装 ChalkBack，记下真实用时，
再按他卡住的地方修改文档。得到的数字用在 demo 0:15–0:35（B 讲）和答辩幻灯片里。

**截止：周日 13:00**（之后功能冻结）。

| 时间 | 做什么 | 谁 |
| --- | --- | --- |
| 周日 09:00 前 | 开测前检查（第 1 节），包括自己在干净环境里完整走一遍（这也是 TB6 的验收） | B |
| 约 10:00 | 正式测试，留 45 分钟（第 3、4 节） | B 主持，测试者 |
| 10:45–12:00 | 整理问题、修改 SETUP.md（第 5 节）；有时间就请第二位测试者 | B |
| 12:30 前 | 把数字发给 D（幻灯片）和 A（`docs/DEMO.md`）（第 6 节） | B |

---

## 1. 开测前检查（全部打勾才开测）

已知会卡住的地方没解决就开测，只会浪费测试者的时间，测出来的数字也不能用。

- [ ] `SETUP.md` 里没有 `TODO` 和 *to verify*：在仓库根目录运行 `grep -n "TODO\|to verify" docs/SETUP.md`，结果为空
  - [ ] 第 5 步：C 写好了老师启动控制台的方式
  - [ ] 第 4 步：实测装好后 pipe 的名字（`chalkback` 还是 `pipe`），必要时修改 SETUP，并告诉 C
  - [ ] 第 6 步：实测 pipe 的安装目录
- [ ] **B 自己预演一遍**：在干净环境里按 SETUP 从头做到 `All required checks passed`，记下自己的用时作为参照
- [ ] Hub 的公网地址能打开（D）
- [ ] D 为测试者生成了一个**专用邀请码**（角色 teacher），测试后删除
- [ ] 准备一个**测试专用的 AI key**，设好消费上限，测试后作废。不要给测试者用你个人的 key
- [ ] 测试电脑：最好用测试者**自己的电脑**；没有的话就在某台电脑上**新建一个系统用户**
  （macOS：系统设置 → 用户与群组；Windows：设置 → 账户 → 其他用户）。
  如果那台电脑已经装过 Node.js 或 Python，记录下来，第 3 步的用时会因此偏短
- [ ] 测试现场的网络能下载东西（screenpipe、Node.js、Python 安装包加起来有几百 MB）
- [ ] 计时工具：手机秒表；征得同意的话再录屏（之后也能当 demo 备用素材）
- [ ] 打印或发给测试者：本文末尾的**测试者说明卡**、`SETUP.md` 的链接、邀请码、AI key

## 2. 找测试者

- **人选**：队外、没见过这个项目、会正常用电脑的人。老师或者不写代码的人最好，最接近真实用户。
- **约时间时说清楚**：大约 40 分钟，用自己的电脑；过程中会安装 screenpipe（它会记录屏幕和麦克风），
  测试结束后我们会帮忙卸载干净。
- 测试者说明卡（文末）是英文的，可以提前发给对方。

## 3. 测试当天：主持人怎么做

### 开场（2 分钟）

照着说明卡跟测试者讲一遍，重点三句话：
1. 我们测的是**说明文档**，不是你：卡住了说明是文档写得不好。
2. 请**边做边说**你在想什么（"我在找……"，"这里我不确定……"）。
3. 我尽量不帮忙，你可以随时停止。

请测试者先关掉私人应用（邮件、聊天软件），因为装好 screenpipe 后它会开始记录屏幕。

### 计时规则

- **开始**：测试者打开 `SETUP.md` 的那一刻。
- **结束**：第 6 步 doctor 输出 `All required checks passed.`。
- 每一步结束都记一下时间，填进下面的表。第 7 步（试跑）是可选的，单独计时，不算进总时间。
- 下载等待时间很长时（超过 1 分钟）要单独记下来，汇报时可以说明"其中 X 分钟在等下载"。

### 什么时候介入

- **不主动帮忙**，不指屏幕，也不说"往下看"。
- 只有两种情况才介入：**卡住超过 3 分钟**，或者测试者**正要做有害的操作**（比如删错文件）。
- 介入时只给最小提示（例如"再看一下第 3 步最后一段"），并且**记一次求助**：写下当时的时间、步骤和你说了什么。
- 测试过程中**不要改文档**，先记下来。

### 记录表

每一步的用时（分钟）：

| 第 1 步 screenpipe | 第 2 步 AI key | 第 3 步 Node/Python | 第 4 步 装 pipe | 第 5 步 向导 | 第 6 步 自检 | 总计 | 求助次数 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | |

观察记录（犹豫、出错、求助、长时间等待都记下来，测试者的原话尤其有用）：

| 时间 | 步骤 | 发生了什么 | 类型：犹豫 / 出错 / 求助 / 等待 | 测试者原话 |
| --- | --- | --- | --- | --- |
| | | | | |

## 4. 测试后访谈（5 分钟，用英文问）

1. *Which step was the hardest, and why?*
2. *Was anything in the instructions unclear or in the wrong order?*
3. **隐私理解检查**：*In your own words, what does ChalkBack record, and what does it share with the school?*
   如果答不出"录音和截图不离开电脑，只有批准后的覆盖数据会共享"，就说明 SETUP 开头那张表需要改。
4. *From 1 to 5, how confident are you that you could do this again alone? Could a colleague teacher do it?*

然后帮测试者**卸载**：照 SETUP 里的 *Uninstall* 做，再退出并卸载 screenpipe，删除 `~/.screenpipe` 和 `~/.chalkback`。
最后作废测试用的 AI key，请 D 删除测试邀请码和测试老师账号。

## 5. 整理问题、修改文档

把观察记录里的每一条归到下面一类：

| 类别 | 例子 | 谁来改 |
| --- | --- | --- |
| 文档写得不清楚 | 看不懂某句话、找不到按钮在哪 | B，马上改 |
| 缺步骤或顺序不对 | 少了"重新打开终端"，或者要先做 B 才能做 A | B，马上改 |
| 产品问题 | 向导报错、doctor 误报、pipe 装不上 | 对应负责人：控制台找 C、pipe 权限和数据找 A、Hub 找 D。在群里报，附上时间和截图 |
| 环境问题 | 网速慢、公司电脑没有管理员权限 | 在常见问题里补一条说明 |

优先改**导致求助或卡住超过 3 分钟**的问题。改完后：
1. 把这次的结果填进 `SETUP.md` 末尾的 *New-user test log* 表；
2. 有时间的话，请第二位测试者再测一次，或者至少自己把改过的步骤重走一遍；
3. 提交：`git commit -m "TB7: newcomer test results, SETUP fixes"`。

## 6. 给 demo 和答辩用的数字

**如实汇报**，用实测的总时间，有求助就要说出来。评委可能会问细节，数字经得起追问比好看更重要。

可以用的说法：

- 没有求助：*"A first-time user who had never seen ChalkBack installed it in **X minutes** using only our SETUP guide."*
- 有求助：*"... in **X minutes** with **N** hint(s) — we fixed those steps in the guide afterwards."*
- 中文：**"一位从没见过项目的队外新人，只看安装文档，X 分钟装好（期间求助 N 次，之后已据此修改文档）。"**

发给：
- **D**：答辩幻灯片；
- **A**：`docs/DEMO.md` 和彩排；
- **B 自己**：demo 0:15–0:35 的讲稿。

---

## Tester card (print or send this part)

**Thank you for helping us!**

We are testing our **installation guide**, not you. If something is confusing, that is exactly what we need to find out.

**What to do**

1. Open the guide: `docs/SETUP.md` in <https://github.com/wangunuxe/Chalkback>.
2. Follow it from the top, on your own, until step 6 says **All required checks passed**.
3. Please **think aloud** — say what you are looking for and what you are unsure about.
4. We will stay quiet and only step in if you are stuck for several minutes. You can stop at any time.

**You will receive:** an invite code and an AI key for this test (both are deleted afterwards).

**Privacy:** the guide installs *screenpipe*, which records your screen and microphone **on your laptop only**.
Please close private apps (mail, chat) before starting. Nothing is sent to us, and we will help you uninstall
everything at the end.

**Time:** about 30–40 minutes, plus a few questions at the end.
