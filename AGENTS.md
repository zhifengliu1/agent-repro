# AGENTS.md

本仓库的工作约定（供协作的 Coding Agent 参考）。

## 环境

- 复现脚本 `hotpotqa_deepseek.py` 通过 `openai` 库调用 OpenAI 兼容的 chat 接口。
- API Key 一律从环境变量 `OPENAI_API_KEY`（或 `DEEPSEEK_API_KEY`）读取，禁止写死在代码或提交到仓库。
- 接口地址 / 模型名通过 `OPENAI_BASE_URL` / `OPENAI_MODEL` 覆盖，默认是 DeepSeek 官方（`https://api.deepseek.com` / `deepseek-chat`）。
- 本机直连 `en.wikipedia.org` 不可达，Wikipedia 抓取必须走代理（`HTTP_PROXY`/`HTTPS_PROXY`，端口见 README）。

## 怎么装

```bash
pip install --break-system-packages numpy gym requests beautifulsoup4 openai
```

（系统 Python 受 PEP 668 保护，需 `--break-system-packages`。）

## 怎么跑

```bash
export OPENAI_API_KEY='你的key'
export OPENAI_BASE_URL='https://www.dmxapi.cn/v1'   # 或 https://api.deepseek.com
export OPENAI_MODEL='kimi-k2.5'                     # 或 deepseek-chat
python3 hotpotqa_deepseek.py 10                     # 样本数，默认 3
```

## 怎么测

- 单样本冒烟：`python3 hotpotqa_deepseek.py 1`，应打印完整 `Thought/Action/Observation` 轨迹 + 一个 EM。
- 网络：`curl -m 8 -o /dev/null -w "%{http_code}\n" https://en.wikipedia.org/wiki/Earth`（需先设代理）。

## 结构

- `hotpotqa_deepseek.py`：ReAct HotpotQA 复现脚本（核心，唯一要跑的文件）。
- `setup_tot.sh` + `patches/tot/`：ToT 一键搭建脚本 + DeepSeek 适配补丁（见下方「ToT 怎么跑」）。
- `docs/paper_notes.md`：论文精读（ReAct + ToT 两篇的核心模块 vs 脚手架）。
- `README.md`：复现哪个数字、一条命令跑通。
- `REPORT.md`：结果、归因、「我仍然不知道的」（Part 1 ReAct / Part 2 ToT）。
- `agent_log.md`、`debug_log.md`：两个日志（覆盖两篇）。
- `logs/game24/`：论文原始实验日志（gpt-4_*）+ 我的 deepseek-chat 各次运行日志（数字的证据，json 可复算）。
- `skills/repro-official-repo/SKILL.md`：可复用 skill。
- `hello_agent.py`：Day 1 的最小示例脚本。

## ToT 怎么跑（一周命令）

```bash
bash setup_tot.sh          # clone 官方仓库到 ~/repos/tree-of-thought-llm + 建 venv + 打 DeepSeek 补丁
cd ~/repos/tree-of-thought-llm
export DEEPSEEK_API_KEY='你的key'

# ToT 冒烟（b=1、打分 1 次，1 局，约 $0.04）
.venv/bin/python run.py --task game24 --task_start_index 900 --task_end_index 901 \
  --method_generate propose --method_evaluate value --method_select greedy \
  --n_evaluate_sample 1 --n_select_sample 1

# CoT baseline（10 采样）
.venv/bin/python run.py --task game24 --task_start_index 900 --task_end_index 901 \
  --naive_run --prompt_sample cot --n_generate_sample 10
```

- 输出看 `-- new_ys -- / -- sol values -- / -- choices --`（生成→打分→选 top-b）和末尾 `cnt_avg/n`、`cnt_any/n`。
- 论文口径：CoT 4% 是 `cnt_avg`（平均），ToT 74% 是 `cnt_any`（best-of-k），别混。
- 已踩坑（详见 debug_log）：DeepSeek 不守隐式格式示范，`patches/` 里已收紧四个 prompt；日志文件会被同名运行覆盖，重跑前先备份。

## 约定

- 复现的官方代码在 `~/repos/ReAct` 和 `~/repos/tree-of-thought-llm`（本仓库只放文档、适配补丁和日志）。
- 不改评测来凑数字；跑不出来如实写进 REPORT。
