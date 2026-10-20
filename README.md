# Agent 复现周记

本周复现了两篇 Agent 论文：**ReAct**（主线）和 **Tree of Thoughts / ToT**（前期探索）。结论先放最前面：

- **ReAct（HotpotQA EM）**：论文 27.4/30.4（PaLM/GPT-3，500 题），我得到 **50.0%**（kimi-k2.5，10 题）。模型代差，见 [REPORT.md](./REPORT.md) Part 1。
- **ToT（Game of 24）**：论文 CoT 4% → ToT 74%（GPT-4）。用 deepseek-chat 时结论**不迁移**：原版 prompt 下 ToT 解不出（0%），根因是「模型不守 propose 的严格格式」；收紧 prompt 后 ToT 能解题了（1 局解出 `(5*6)-(10-4)=24`），但 b=1 + 小样本下成功率不稳定，属「当前预算下不可判定」，见 [REPORT.md](./REPORT.md) Part 2。

---

# Part A — ToT 复现（一周命令）

## 复现哪个数字

Tree of Thoughts（Yao et al., NeurIPS 2023, arXiv:2305.10601）在 **Game of 24** 上「CoT vs ToT 成功率」：

| 口径 | 论文（GPT-4，100 局） | 官方仓库日志复算 | 我（deepseek-chat） |
|---|---|---|---|
| CoT 平均成功率（`cnt_avg/n`） | 4.0% | 4.0%（100 局） | 21%（10 局×10 采样） |
| CoT best-of-k（`cnt_any/n`） | 49%（best-of-100） | 49% | 80%（best-of-10） |
| ToT（`cnt_any/n`） | 74%（b=5） | 69% | 0%（原版 prompt）；收紧后 1 局解出（b=1） |

> 证据：官方仓库自带的论文原始实验日志已复制到本仓库 `logs/game24/gpt-4_*.json`（复算数字与论文表 2 / README 完全一致）。我自己的 deepseek-chat 各次运行日志同在 `logs/game24/deepseek-chat_*.json`。

## 一条命令跑通

```bash
# 0. 前置：本仓库自带官方日志和 DeepSeek 适配补丁，脚本负责 clone+装依赖+打补丁
bash setup_tot.sh                          # 默认装到 ~/repos/tree-of-thought-llm

# 1. 冒烟（ToT b=1，1 局，约 $0.04，2 分钟内）
cd ~/repos/tree-of-thought-llm
export DEEPSEEK_API_KEY='你的key'
.venv/bin/python run.py --task game24 --task_start_index 900 --task_end_index 901 \
  --method_generate propose --method_evaluate value --method_select greedy \
  --n_evaluate_sample 1 --n_select_sample 1

# 2. CoT baseline（10 采样，约 $0.01）
.venv/bin/python run.py --task game24 --task_start_index 900 --task_end_index 901 \
  --naive_run --prompt_sample cot --n_generate_sample 10

# 3. 论文原配置 ToT（b=5、打分 3 次，约 $0.7/局；想验证论文请从这里开始）
.venv/bin/python run.py --task game24 --task_start_index 900 --task_end_index 902 \
  --method_generate propose --method_evaluate value --method_select greedy \
  --n_evaluate_sample 3 --n_select_sample 5
```

**输出怎么看**：`-- new_ys -- / -- sol values -- / -- choices --` 三轮 = 生成→打分→选 top-b；每局一行 `sum(accs)`；最终 `cnt_avg/n` 和 `cnt_any/n` 就是两个成功率（论文 CoT=4% 是前者、ToT=74% 是后者）。

## 一个结论的完整证据链（负结果 → 反转）

1. **原版 prompt + deepseek-chat**：propose 输出是一堵 Markdown/废话墙（证据：`logs/game24/deepseek-chat_0.7_propose1_value1_greedy1_start900_end901.json` 的 `steps[].new_ys`），按 `\n` 拆成 50+ 行垃圾，ToT = 0%。
2. **杠杆1（temperature=0）**：无效。输出仍话痨（证据：`..._0.0_..._start900_end902.json`）。
3. **杠杆3（收紧 4 个 prompt，明说格式）**：有效。propose 变 24 个干净候选；1 局解出正确轨迹 `10-4=6 → 5*6=30 → 30-6=24`。
4. **但 b=1 + 2 局样本**：成功率 1/2 → 0/2 漂移，最终状态「当前预算下不可判定」。

---

# Part B — ReAct 复现（主线）

复现 **ReAct: Synergizing Reasoning and Acting in Language Models**（Yao et al., ICLR 2023, arXiv:2210.03629）在 **HotpotQA** 上的一个数字。

- **我复现的数字**：HotpotQA 的 Exact Match（EM）准确率，ReAct 方法。
- **论文值**：27.4%（PaLM-540B）／ 30.4%（GPT-3 davinci-002），500 题 dev 集。
- **我得到**：**50.0%**（10 题，模型 `kimi-k2.5`，经第三方中转 `www.dmxapi.cn`）。
- **差在哪 / 为什么**：见 [REPORT.md](./REPORT.md) Part 1。一句话：模型代差（2025 年的 kimi-k2.5 远强于 2022 年的 PaLM/GPT-3），加上样本只有 10 题。

### 一条命令跑通

```bash
git clone https://github.com/ysymyth/ReAct.git ~/repos/ReAct
pip install --break-system-packages numpy gym requests beautifulsoup4 openai
cp hotpotqa_deepseek.py ~/repos/ReAct/
cd ~/repos/ReAct
export OPENAI_API_KEY='你的key'
export OPENAI_BASE_URL='https://www.dmxapi.cn/v1'   # 或 https://api.deepseek.com
export OPENAI_MODEL='kimi-k2.5'                     # 或 deepseek-chat
export HTTP_PROXY='http://172.18.112.1:10793'       # 你的梯子端口，见下
export HTTPS_PROXY='http://172.18.112.1:10793'
export NO_PROXY='dmxapi.cn,api.deepseek.com,127.0.0.1,localhost'
python3 hotpotqa_deepseek.py 10     # 10 题约 2~3 分钟
```

> **Wikipedia 必须走代理**：本机直连 `en.wikipedia.org` 不可达。梯子要开「Allow LAN」，端口用
> `powershell.exe -NoProfile -Command "(Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings').ProxyServer"` 查。

## 目录

- `hotpotqa_deepseek.py` —— ReAct HotpotQA 复现脚本（DeepSeek/OpenAI 兼容 chat 接口）。
- `setup_tot.sh` + `patches/tot/` —— ToT 一键搭建脚本 + DeepSeek 适配补丁（别人 clone 一条命令能跑）。
- `logs/game24/` —— 论文原始实验日志（gpt-4_*）+ 我的 deepseek-chat 各次运行日志（数字的证据）。
- `docs/paper_notes.md` —— 论文精读：ReAct + ToT 两篇的核心模块 vs 脚手架、每个核心模块的算法逻辑。
- `REPORT.md` —— 结果、归因、「我仍然不知道的」（Part 1 ReAct / Part 2 ToT）。
- `agent_log.md` / `debug_log.md` —— 两个日志（Agent 出错记录 + bug 根因记录）。
- `skills/repro-official-repo/SKILL.md` —— 本周沉淀的 skill。
- `hello_agent.py` —— Day 1 的最小示例脚本。

## 花费

- ReAct：约 ¥2 以内（10 题）。
- ToT：约 ¥5（含中间作废的跑批）。ToT 贵在「模型话痨 + 每局打分次数多」，单局约 2.9 万 completion token。
- 未超预算。
