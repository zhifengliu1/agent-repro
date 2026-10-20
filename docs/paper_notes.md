# Paper Notes

本周读了两篇论文：**ReAct**（主线）和 **Tree of Thoughts**（前期探索）。

---

# Part 1 — ReAct

论文：ReAct: Synergizing Reasoning and Acting in Language Models（Yao et al., ICLR 2023, arXiv:2210.03629）
官方代码：https://github.com/ysymyth/ReAct（已 clone 到 `~/repos/ReAct`）

## 一、一句话回答三个问题

1. **解决什么问题**：让大模型在答题/决策时，不再「只靠脑子想」（会幻觉）或「只动手」（不会规划），而是把两者**交错**起来互相喂。
2. **核心方法是什么**：prompt 里给 few-shot 例子，教模型按 `Thought → Action → Observation` 循环输出；Thought 是纯文本推理，Action 是查 Wikipedia/操作环境，Observation 是环境返回的真实结果，拼回 prompt 驱动下一轮。
3. **凭什么说有效**：Table 1 + 消融。缺一边（Act-only / CoT）都更差；ReAct 与 CoT-SC 结合最好（34.2/35.1）。决策任务 ALFWorld/WebShop 只用 1–2 个示例就超过 RL/模仿学习（+34/+10 个百分点）。

## 二、核心模块 vs 脚手架

| 类别 | 模块 | 判断理由 |
|---|---|---|
| **核心** | thought–action–observation 循环（`webthink()`） | 删掉它，ReAct 就不存在了 |
| **核心** | 轨迹拼进 prompt（历史靠程序累加） | 模型无状态，这是「记忆」的来源 |
| **核心** | 动作空间设计（search/lookup/finish） | 三个动作是「行动」的全部 |
| **核心** | 评分函数 EM（`get_metrics`/`normalize_answer`） | 决定「对不对」的标尺 |
| 脚手架 | Wikipedia 抓取（`wikienv.search_step`） | 换个知识库方法照样成立 |
| 脚手架 | 数据加载（`wrappers` 读 json） | 纯 IO |
| 脚手架 | prompt 模板（`prompts/*.json`） | 内容可换，结构是核心 |
| 脚手架 | gym wrapper 套壳 | 只是组织方式 |

## 三、核心模块逐个（输入/输出/伪代码/代码位置）

### 模块 1：thought–action–observation 循环

- **输入**：一个问题 `Question: ...` + few-shot 示例 + 环境。
- **输出**：最终答案 + 一条完整轨迹。
- **伪代码（自己写的）**：
  ```
  prompt = instruction + examples + question
  for i in 1..7:
      text = llm(prompt + "Thought i:", stop=["\nObservation i:"])  # 只让模型写 Thought/Action
      thought, action = 按 "\nAction i:" 拆开
      obs = env.step(action)                                        # 环境执行动作
      prompt += "Thought/Action/Observation"                        # 拼回历史
      if done: break
  return 从 finish 里取答案，算 EM
  ```
- **代码位置**：`hotpotqa_deepseek.py` 的 `webthink()`（官方 `hotpotqa.ipynb` cell 4）。

### 模块 2：轨迹拼进 prompt（无状态模型 → 有记忆）

- **输入/输出**：in = 当前 prompt + 新一轮的三行；out = 更长的 prompt。
- **为什么这么设计**：模型每轮调用都是无状态的，必须把历史喂回去，它才知道「我查过什么」。
- **代码位置**：`webthink()` 里的 `prompt += step_str`。

### 模块 3：动作空间（search / lookup / finish）

- **输入**：模型吐出的字符串 `"Search[Scott Derrickson]"`。
- **输出**：环境状态变化 + 观察文本。
- **伪代码**：
  ```
  if action.startswith("search[") ...:  search_step(实体)      # 发 HTTP 抓 Wikipedia
  elif action.startswith("lookup[") ...: 在 self.page 里找含关键词的句子
  elif action.startswith("finish[") ...: self.answer = 答案; done=True
  else: obs = "Invalid action"
  ```
- **代码位置**：`wikienv.py:128` `WikiEnv.step()`；抓取在 `wikienv.py:98` `search_step()`。

### 模块 4：评分（EM + normalize）

- **输入**：模型答案 + 标准答案（都是字符串）。
- **输出**：em ∈ {0,1}。
- **伪代码**：
  ```
  a = normalize(模型答案)   # 小写、去标点、去 a/an/the
  b = normalize(标准答案)
  em = (a == b)
  ```
- **代码位置**：`wrappers.py:42` `normalize_answer`、`wrappers.py:117` `get_metrics`。

## 四、我做的验证（预测→验证）

- **预测**：去掉 `stop` 参数，模型会自己编 Observation。
- **验证**：实测中转站推理型模型（deepseek-v4-pro）不守格式时，果然直接吐答案、不写 Thought/Action，导致 `split` 解析崩 → 触发一堆 `ohh...`。→ 与「无状态+格式依赖」的理解一致。

## 五、我还不懂的（ReAct）

1. CoT-SC 的 21 采样投票、以及最后两行组合方法的切换启发式，代码里没有完整实现，只看了论文描述。
2. `lookup` 的「result N / M」分页返回细节，对最终准确率的影响有多大。

---

# Part 2 — Tree of Thoughts (ToT)

论文：Tree of Thoughts: Deliberate Problem Solving with Large Language Models（Yao et al., NeurIPS 2023, arXiv:2305.10601）
官方代码：https://github.com/princeton-nlp/tree-of-thought-llm（复用副本在 `~/repos/tree-of-thought-llm`）

## 一、一句话回答三个问题

1. **解决什么问题**：CoT 是一条「线」走到黑，一步错步步错；ToT 让模型在**多条思路的树**上搜索，走岔了能回头。
2. **核心方法是什么**：把问题求解变成「思维树搜索」——每个节点是一个「部分解答」状态，用 `propose` 生成候选下一步、用 `value` 给每个候选打分、用 BFS/DFS 选择最有希望的分支继续展开。
3. **凭什么说有效**：Game of 24 上 CoT 4% → ToT 74%（GPT-4）；在创意写作、填字游戏上也显著超过 CoT。

## 二、核心模块 vs 脚手架

| 类别 | 模块 | 判断理由 |
|---|---|---|
| **核心** | BFS 搜索循环 `solve()`（生成→打分→选 top-b，循环 4 步） | 删掉树搜索就退回 CoT |
| **核心** | 状态打分（`get_value` + `value_outputs_unwrap`：sure/likely/impossible → 20/1/0.001） | 决定搜索往哪走 |
| **核心** | `propose` 生成候选下一步（`get_proposals`） | 「树枝」的来源 |
| 脚手架 | 答案抽取 + 判分（`test_output`：正则 + sympy） | 纯评测，但必须是确定性代码 |
| 脚手架 | 各任务 prompt 模板（`prompts/game24.py`） | 内容可换（但格式约定是隐式核心，见验证） |

## 三、核心模块逐个

### 模块 1：BFS 搜索循环 `solve()`

- **输入**：题目 x（如 "4 5 6 10"）+ 参数（b、打分次数）。
- **输出**：b 条完整轨迹（每条 4 行：3 步算式 + 1 行 Answer），或失败轨迹。
- **伪代码（自己写的，注意是「逐层展开」不是队列）**：
  ```
  ys = ['']                        # 当前候选轨迹，一开始一条空轨迹
  for step in 1..4:                # 4 轮：3 步算式 + 1 步答案
      new_ys = 对 ys 中每条轨迹：get_proposals(x, y)   # 每条都追加"可能的下一步"
      values = 对 new_ys 每条：get_value(x, y)         # 模型打分
      ys = 按 values 从高到低取前 b 条                   # 剪枝
  return ys
  ```
- **代码位置**：`src/tot/methods/bfs.py:49-88`（已打开核对）。DFS 版本在 `scripts/crosswords/search_crosswords-dfs.ipynb`（官方没有独立 dfs.py）。

### 模块 2：打分 `get_value` + `value_outputs_unwrap`

- **输入**：一个部分轨迹 y（字符串，累积到当前步的所有算式）。
- **输出**：数字分数（20/1/0.001 的加权和）。
- **伪代码**：
  ```
  prompt = value_prompt.format(input=当前剩余数字)     # 或最后一步用 value_last_step_prompt
  outs = [llm(prompt) 重复 n_evaluate_sample 次]        # 采样多次抗噪
  verdicts = [每条输出的最后一行]                       # 模型解释完、最后才落一个词
  score = 20×(sure 次数) + 1×(likely 次数) + 0.001×(impossible 次数)
  ```
- **代码位置**：`src/tot/methods/bfs.py:6-14`（`get_value`）、`src/tot/tasks/game24.py:85-92`（`value_outputs_unwrap`，含 `value_map = {'impossible':0.001,'likely':1,'sure':20}`）。

### 模块 3：`propose` 生成候选（`get_proposals`）

- **输入**：当前轨迹 y；解析出「剩余数字」。
- **输出**：多个候选轨迹（每条 = y + 一行新算式）。
- **伪代码**：
  ```
  current = get_current_numbers(y)                     # 从 y 最后一行抠 "left: " 后面的剩余数
  prompt = propose_prompt.format(input=current)
  lines = llm(prompt).split('\n')                      # ★ 按换行拆：强依赖模型守格式
  return [y + line + '\n' for line in lines]           # 追加到原轨迹
  ```
- **代码位置**：`src/tot/methods/bfs.py:34-37`、`src/tot/tasks/game24.py:65-73`（拼 prompt）、`game24.py:9-11`（解析剩余数字）。

## 四、我做的验证（负结果 → 部分反转的关键，按实验顺序）

1. **预测**：deepseek-chat 会守 propose 的隐式格式示范（`X op Y = Z (left: a b c)`）。
   **验证**：❌ 不守。回一堵 Markdown/LaTeX/废话墙，`get_proposals` 按 `\n` 拆行后得到 50+ 行垃圾当「想法」→ ToT 0%。**ToT 对「模型守格式」的强依赖是核心脆弱点。**

2. **预测**：temperature 降到 0 能治格式发散。
   **验证**：❌ 无效。输出还是话痨（只是从"随机话痨"变成"确定性话痨"）。说明根因不是采样随机性，而是"模型没被告知格式"。

3. **预测**：把格式要求**明说**（杠杆3：propose/value/cot 三个 prompt 都加"只输出严格格式、不要 Markdown/逗号/解释"的死命令）后，DeepSeek 会守格式。
   **验证**：✅ 成立。propose 从"50 行废话墙"变成"24 个干净候选"；1 局解出正确轨迹 `10-4=6 → 5*6=30 → 30-6=24 → Answer: (5*6)-(10-4)=24`。**结论：deepseek-chat 需要显式格式指令，GPT-4 能从示范中自己领悟——这是两者对同一 prompt 的行为差异。**

4. **探针**：打分器（value prompt）准不准？直接喂 5 个用例：`5 6 6`(可解)、`5 10 10`(不可)、`4 6`(可)、`2 12`(可)、`1 2 3`(不可)。
   **验证**：✅ 5/5 全对（`5 10 10` 甚至穷举 30+ 行组合后才判 impossible）。**打分器大致可靠**；之前的失败更可能来自 b=1 单点押注 + 2 局小样本，而非打分器坏。

## 五、我还不懂的（ToT）

1. 「守隐式格式示范 vs 需要显式格式指令」到底是模型规模、训练数据还是 RLHF 造成的，没有系统证据。
2. b=5 + 打分 3 次（论文原配置）下 deepseek-chat 的 ToT 成功率到底是多少——这是唯一还没跑的、能一锤定音的实验。
3. 步骤 4→5 的波动（1/2 → 0/2）里，b=1、打分只取 1 次、样本量各自贡献多大。

---

> 判断标准回顾：把这块删掉，论文的方法就不成立了——那它就是核心。两篇里我都按这个标准把「循环/搜索 + 打分 + 生成候选」标为核心，把「数据加载/评测脚本/prompt 模板」标为脚手架。
