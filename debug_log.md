# Debug Log

记录调试日志。根因归到五类之一：**环境/依赖、数据、实现、评测、理解错误**。覆盖 ReAct（主线）和 ToT（前期探索）两篇。

## 2026-10-16～17 — ToT 阶段

| 现象 | 根因类别 | 怎么发现 | 修法 | 怎么防止再犯 |
|---|---|---|---|---|
| `uv pip install` 挂起 8+ 分钟无输出，之后所有安装（含 `-v six` 这种小包）也全部超时 | 环境/依赖 | `ps aux` 看到多个 `uv pip install` 进程同时存活但 CPU 几乎为 0；用 `curl` 直连 pypi.org 和清华源都返回 200（<1s），排除"网络全断" | `pkill` 掉全部 uv 进程 + 删 `~/.cache/uv/.lock` 和 `.tmp*`，改用清华源单进程重装，4 秒完成 | 不并发起多个 uv/pip 安装（会抢 `~/.cache/uv/.lock` 全局锁）；网络慢先换镜像再重试 |
| `import tot.models` 直接报 `openai.OpenAIError: Missing credentials`；官方代码里是 `openai.ChatCompletion.create` / `openai.api_base` 旧接口 | 环境/依赖 | 官方 `requirements.txt` 钉死 `openai==0.27.7`，而我装的 `openai==3.33.0` 已移除 `ChatCompletion.create`，且空 key 会在构造 client 时直接 raise | 重写 `models.py`：换新版 `openai.OpenAI(base_url=...)`、client 懒加载、空 key 时清晰报错；`n` 参数改成循环 `n=1` 调用（DeepSeek 只支持 `n=1`） | 跑老仓库先看 `requirements.txt` 里 openai 的版本，判断新旧接口；换模型前先确认目标 API 对 `n` 参数的限制 |
| `git clone` 报 `error: RPC failed; curl 56 GnuTLS recv error` | 环境/依赖 | 第一次 `--depth 1` clone 成功、第二次全量 clone TLS 断连 | 用已 clone 好的副本 `cp -a` 到 `~/repos/tree-of-thought-llm`（origin 仍指向官方仓库） | 网络不稳时用 `--depth 1` 或复用已有副本，别在同一件事上耗太久 |
| ToT 在 Game of 24 上「跑通但解不出」：index 900 一局 `cnt_any=0`，且比 CoT（1/10 解出）还差；单局烧 2.9 万 completion token（$0.041） | 理解错误（模型差异） | 打印 propose 的原始输出：deepseek-chat **不守** `X op Y = Z (left: a b c)` 一行一算式格式，回一堵 Markdown/LaTeX/代码块/废话墙（"If you want I can continue…"），还把剩余数写成 `left: 4, 10, 30`（逗号+把结果算进剩余）。代码 `get_proposals` 按 `\n` 拆行 → 拆出 50+ 行垃圾当「想法」，搜索锁死在错误第一步 `6*5=30` | 先如实记录为负结果（论文 74% 是 GPT-4 的数字，不迁移到 deepseek-chat）；可选：收紧 prompt / 限 `max_tokens` 逼它简洁，但要记为方法改动 | 复现「靠模型守格式」的方法前，先花几毛钱看目标模型对格式的遵从度；换模型必然带来格式漂移，别默认原数字能迁移 |

## 2026-10-18～19 — ReAct 环境与网络

| 现象 | 根因类别 | 怎么发现 | 修法 | 怎么防止再犯 |
|---|---|---|---|---|
| `pip install numpy gym ...` 报 `externally-managed-environment`，`--user` 也被拒 | 环境/依赖 | 直接报错信息提示 PEP 668 | `pip install --break-system-packages` | 系统 Python 受 PEP 668 保护时，先确认能否 venv，不行再用 `--break-system-packages`（dev 环境可接受） |
| `requests.get(en.wikipedia.org)` 抛 `ConnectionError: Network is unreachable` | 环境/依赖（网络） | `curl en.wikipedia.org` 超时、`curl google.com` 也超时，但 `api.deepseek.com`/`github.com` 通 | 走 Windows 梯子系统代理 `http://172.18.112.1:10793`（Allow LAN 后） | 先分层测连通性（DNS→直连→代理→各目标域名），再谈代码；WSL2 要用宿主机 IP 而非 127.0.0.1 |
| Wikipedia 搜索返回 403，Observation 恒为空 | 环境/依赖（反爬） | `requests.get` 无 User-Agent，Wikipedia 拒绝 `python-requests/...`，正文仅 126 字节 | `wikienv.py` 加浏览器 User-Agent + timeout | 抓公开网页时带上合法 User-Agent；空 Observation 先看 HTTP 状态码，别急着调 prompt |

## 2026-10-20 — ReAct 模型选择

| 现象 | 根因类别 | 怎么发现 | 修法 | 怎么防止再犯 |
|---|---|---|---|---|
| 中转站 `deepseek-chat` 报 `model_not_found` | 环境/依赖 | 调 `/v1/models` 发现列表里没有 `deepseek-chat` | 换可用模型名 | 换第三方中转先 `GET /v1/models` 拉真实模型列表，别假设模型名一致 |
| 用 `deepseek-v4-pro`/`deepseek-v3.1` 跑，ReAct 轨迹崩（一堆 `ohh...`，`Invalid action`） | 理解错误（模型不守格式） | 用一段 ReAct few-shot 例子实测：推理型 DeepSeek 直接吐答案、不写 `Thought/Action`，`split("\nAction i:")` 解析失败 | 换 `kimi-k2.5`（严格跟格式） | 复现「靠模型守格式」的方法前，先花几毛钱测目标模型的格式遵从度；推理型模型 ≠ 适合 ReAct |

## 2026-10-20 — ReAct 评测现象（非 bug，理解记录）

| 现象 | 根因类别 | 说明 |
|---|---|---|
| 模型答 `Chief of Protocol of the United States`，标准答案 `Chief of Protocol`，被判 EM=0（但 F1=0.67） | 理解错误（对评测的预期） | EM 是逐字精确匹配，`normalize_answer` 只去标点/冠词/大小写，**不处理「多答几个词」**。内容对也会被判错。这是论文评测的固有严格度，不是实现 bug |

## 2026-10-20 — ToT 后续实验（收紧 prompt、temperature、打分器探测）

| 现象 | 根因类别 | 怎么发现 | 修法 | 怎么防止再犯 |
|---|---|---|---|---|
| temperature=0 后 propose 输出**仍然**是 Markdown/废话墙 | 理解错误（根因是"格式没被告知"，不是采样随机性） | 跑 `--temperature 0` 的 2 局，第一步 propose 原始输出仍是 `**Step 1 – Try addition:**`、`Let's solve this step by step`、`left: 6, 9, 10`（逗号） | 无效修法（temperature）；有效修法是收紧 prompt：propose/value/value_last_step/cot 都加显式格式死命令（"只输出 `a op b = c (left: x y z)`、用 `*`/`/`、空格、不要 Markdown/逗号/解释"）——之后 propose 从 50 行废话变成 24 个干净候选 | 格式不守先分清两种可能：a) 采样随机导致偶发散（降 temperature 有效）；b) 模型根本不知道格式要求（必须改 prompt 明说）。先跑 1 局看原始输出再选修法 |
| 收紧 prompt 后 ToT 成功率在 1/2 ↔ 0/2 之间漂移 | 未定位（候选：b=1 单点押注 / 打分只取 1 次 / 样本仅 2 局） | 两次同配置运行结果不同（一次解出 900、一次 0/2）；受控探测 5 个打分用例 5/5 全对，**排除"打分器坏"** | 未修——按任务书 §6.4 记为「当前预算下不可判定」；正确下一步是论文原配置 b=5 + 打分 3 次跑 10 局 | 归因前先隔离变量做受控探测；小样本（≤2 局）的组间差异不构成结论 |
| 唯一一次「收紧 prompt 后解出 900」的运行日志丢失 | 实现（流程失误） | 两次运行参数相同 → run.py 生成同名日志文件 → 后一次覆盖前一次，成功轨迹只剩对话里的转述 | 教训性记录：本仓库已把日志复制进 `logs/game24/`，但那次成功已被覆盖、不可恢复 | 重跑实验前先 `cp` 备份旧日志，或给日志文件名加时间戳 |

## 根因归类小结

两篇论文共同的最高频根因是 **理解错误（模型不守格式）**——ToT 的 deepseek-chat 和 ReAct 的推理型 DeepSeek 都是同一类问题；且这个根因本身也分两层：**a) 模型不知道格式要求（改 prompt 明说有效）** 与 **b) 模型能力/训练决定的遵从度（换模型才有效）**。其次是 **环境/依赖**（网络、PEP 668、User-Agent、旧 openai 接口）。数据、实现、评测三类在两篇里都排查过并排除。
