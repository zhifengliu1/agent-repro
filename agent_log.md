# Agent Log

记录这周和 Coding Agent（ZCode）协作的过程，重点是**它出错或误导我的例子**（任务书要求 ≥2 个，附 prompt、原话、我怎么发现的）。覆盖 ReAct（主线）和 ToT（前期探索）两篇。

## 一、Agent 出错/误导的例子

### 例子 1：Agent 一口咬定「跑不通是因为 DeepSeek 不支持」，没先查网络（ReAct）

- **我的 prompt**：报 `requests.exceptions.ConnectionError: Failed to establish a new connection ... en.wikipedia.org`，问「为什么跑不起来」。
- **Agent 原话（大意）**：转向怀疑 API 或代码实现，一度倾向于「换一种方式实现 Wikipedia 检索」或「用本地知识库替代」，把方向往「改代码」引。
- **我怎么发现的**：我自己在终端 `curl en.wikipedia.org` 返回超时、`curl api.deepseek.com` 返回 401、`curl google.com` 也超时——**根因是网络到不了 Wikipedia，不是代码也不是 API**。代码本身是对的。
- **教训**：Agent 遇到报错容易「就地找代码锅」，网络/环境这类最外层的原因常被跳过。先分层排除（DNS→直连→代理）再谈改代码。

### 例子 2：Agent 差点让我用「推理型模型」跑 ReAct，会静默失败（ReAct）

- **我的 prompt**：给了中转站模型列表，问「用哪个 DeepSeek 模型跑 ReAct」。
- **Agent 原话（大意）**：倾向选列表里最强的 `deepseek-v4-pro`，理由是「能力越强答案越准」。
- **我怎么发现的**：我用一段 ReAct few-shot 例子实测格式跟随，`deepseek-v4-pro` **直接吐答案、不写 Thought/Action**，会把 `webthink` 里的 `split("\nAction i:")` 解析崩、触发一串 `ohh...`。逐个模型测下来只有 `kimi-k2.5` 严格跟格式。
- **教训**：复现「靠模型守格式」的方法时，不能只看模型能力强弱，要先测「格式遵从度」。Agent 的「选最强的」是通用直觉，在这个特定约束下是错的。

### 例子 3：Agent 一开始把「ToT 解不出」往实现 bug 上归，没先想到是模型格式（ToT）

- **我的 prompt**：ToT 在 Game of 24 跑通但 `cnt_any=0`，问「是不是实现哪里错了」。
- **Agent 原话（大意）**：先怀疑 propose/value/select 的实现或 sympy 校验有 bug，建议加日志逐步排查。
- **我怎么发现的**：打印 `get_proposals` 的原始输出，发现 deepseek-chat **根本不守** `X op Y = Z (left: a b c)` 格式，回一堵废话墙，被按 `\n` 拆成 50+ 行垃圾。**实现没错，是模型不守格式**。
- **教训**：负结果排查时，「模型差异」和「实现 bug」要并列考虑，尤其当 baseline（CoT）能出数、实验组（ToT）出不了数时，先怀疑模型对格式的遵从度。

### 例子 4：Agent 随口编造「打分器 8/2 随机」的数字，且没跑实验就下结论（ToT）

- **我的 prompt**：问「是不是 temperature 的原因」。
- **Agent 原话（大意）**：「你让打分器判断 5 10 10，跑 10 次，可能 8 次说 impossible、2 次说 sure」，并据此说打分器"多步心算不稳定"。
- **我怎么发现的**：那个 8/2 **根本不是实测数字**，是它举的例子。后来受控测了 5 个用例，打分器 5/5 全对——「打分器不准」的结论是错的，Agent 自己也在报告里撤回（§2.3）。我一度被它的举例带跑，以为问题在打分器。
- **教训**：Agent 举例子时会把「示意数字」说成「观测数字」的口吻；听到任何带数字的结论都要追问"这是测出来的还是你编的"。我的正确直觉其实是"b=1 + 实验次数少"，被它的例子干扰了。

### 例子 5：Agent 跑批时没备份日志，把唯一一次成功轨迹覆盖了（ToT）

- **我的 prompt**：先跑「收紧 prompt 后的 ToT 2 局」（解出 1 局，成功轨迹 `10-4=6 → 5*6=30 → 30-6=24`），之后又让它"把 cot_prompt 也收紧再跑 2 局"。
- **Agent 原话（大意）**：直接重跑，输出重定向到**同名**日志文件。
- **我怎么发现的**：回看日志时发现那次成功的 json 没了——run.py 的日志文件名由参数决定，参数没变所以同名覆盖，现在磁盘上只剩 0 分的记录。
- **教训**：每次跑批前先备份/改名留存日志；让 Agent 重跑时明确要求"日志文件加时间戳或改名，不许覆盖"。

## 二、运行记录（时间线）

### 2026-10-16 — ToT 阶段（Day 1 前后）

- `hello_agent.py` 首次运行成功（DeepSeek `deepseek-chat`）。
- clone ToT 官方仓库，复现 Game of 24 的 CoT/ToT。CoT 21%（10 局），ToT 0%（1 局）——负结果。

### 2026-10-18 — ReAct 环境搭建

- clone 官方仓库 `ysymyth/ReAct` 到 `~/repos/ReAct`，成功。
- 装依赖：系统 Python 3.14 受 PEP 668 保护，`pip install` / `--user` / venv 均被拒，最终 `pip install --break-system-packages` 装 numpy/gym/requests/beautifulsoup4，成功。
- gym 0.26.2 + numpy 2.5.4 有「Gym unmaintained」弃用警告，但不影响运行。

### 2026-10-18 — ReAct 首次跑通

- 官方 `hotpotqa.ipynb` 用 OpenAI `text-davinci-002`（已下线），我改写成 `hotpotqa_deepseek.py`（chat 接口）。
- 用官方 DeepSeek `deepseek-chat` 跑通 3 题，EM 2/3，轨迹正常。

### 2026-10-19 — ReAct 网络打通

- 定位 Wikipedia 不可达（地区网络限制），找到 Windows 梯子系统代理 `http://127.0.0.1:10793`，开 Allow LAN 后从 WSL 走 `http://172.18.112.1:10793` 翻出，Wikipedia 返回 200。
- 修复 Wikipedia 403（缺 User-Agent）。

### 2026-10-20 — ReAct 换 key 换模型，正式复现

- 换成第三方中转 `www.dmxapi.cn` + `kimi-k2.5`，跑 10 题，EM = **50.0%**（5/10）。

### 2026-10-20 — ToT 复现全过程（与 ZCode 新会话协作）

- 官方原版 prompt + deepseek-chat：ToT 0 分（格式不守，根因见 debug_log）。
- CoT 10 局×10 采样：平均 21%、best-of-10 80%。
- 杠杆1 temperature=0：无效（仍话痨）。杠杆3 收紧 prompt：propose 变 24 个干净候选，**1 局解出** `(5*6)-(10-4)=24`（但该次日志被后续同名运行覆盖，见例子 5）。
- 再收紧 cot_prompt 后：0/2。成功率在 b=1+2 局下漂移 → 结论「当前预算下不可判定」。
- 打分器 5 用例离线探测：5/5 全对（撤回"打分器不准"的说法）。
- 落盘：README/REPORT/paper_notes/agent_log/debug_log 全部重写，官方论文原始实验日志（gpt-4_*）与我的 deepseek-chat 日志复制进 `logs/game24/`，DeepSeek 适配做成 `patches/tot/*.patch` + `setup_tot.sh` 一键脚本。

## 三、Agent 帮到我的地方（如实记录）

1. 读论文、读代码时用「一句话/伪代码/逐行」三种粒度讲，帮我把 `webthink`、wrapper 洋葱、step 调用链彻底捋清。
2. 反向出题考我，暴露了我「同名 step 分属不同类」这个盲点。
3. 落盘文档：把我口述的结果/归因整理成 REPORT、paper_notes 的初稿（本文件除外——这些例子是我自己核对的）。
