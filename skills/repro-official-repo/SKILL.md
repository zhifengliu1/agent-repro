---
name: repro-official-repo
description: 拿到一个有官方代码的论文仓库，用最小代价跑到第一个结果。当需要复现某篇论文、或跑通一个陌生仓库时使用。
---

# 复现一个官方 repo 的最小路径

## 什么时候用

- 你 clone 了一个论文的官方仓库，想尽快跑到「第一个可复现的数字」。
- 你面对一个陌生仓库，不知道从哪下手。

## 步骤（可以直接复制的命令）

1. **先读 README 的 install / test / example 三节，别急着装环境。** 很多仓库在 `examples/` 或 `tests/` 里藏着最便宜的一次运行。
2. **先跑最便宜的那个 demo。** 目标：1 分钟内结束、端到端走通（数据 → 模型 → 输出）。用最小规模：1 条样本、1 个 batch、最小模型。
3. **确认 API 形态后再写适配。** 老仓库常写死旧接口（`openai.Completion.create` / `openai.api_base`），新环境要换 chat 接口；先 `pip show openai` 看版本，再决定改不改、怎么改。
4. **环境问题先分层排查**（顺序固定）：DNS → 直连 → 代理 → 各目标域名。别一上来改代码。
5. **把最小跑通固化成一个独立脚本**（不要留在 notebook 里），加一个命令行参数控制样本数。

```bash
# 复现 ReAct 这个仓库时的最小命令（示例，换你的仓库后改路径/模型）
git clone https://github.com/ysymyth/ReAct.git
cd ReAct
pip install --break-system-packages numpy gym requests beautifulsoup4 openai
export OPENAI_API_KEY='你的key'
export OPENAI_BASE_URL='https://www.dmxapi.cn/v1'   # 换你实际的
export OPENAI_MODEL='kimi-k2.5'                     # 换你实际的
python3 hotpotqa_deepseek.py 3                      # 先 3 题，通了再放大到 50/500
```

## 检查点：每一步怎么确认成功了

- **网络/代理**：`curl -m 8 -o /dev/null -w "%{http_code}\n" https://目标域名` 返回 200（不是 403/000）。
- **API**：最小调用返回非空 `choices[0].message.content`。
- **格式遵从**（对 ReAct 这类方法）：喂一段 few-shot 例子，看模型是否严格输出你要求的分隔符。
- **端到端**：脚本打印出完整的 `Thought/Action/Observation` 轨迹 + 一个数字。

## 常见失败与处理

| 现象 | 处理 |
|---|---|
| `externally-managed-environment` | 系统 Python 受 PEP 668 保护，用 `pip install --break-system-packages`（dev 环境可接受），或建 venv |
| `ConnectionError: Network is unreachable` | 先测直连，再走代理；WSL2 里代理要用宿主机 IP（`ip route` 的默认网关），不是 127.0.0.1 |
| 目标网站 403 / 空返回 | 加浏览器 User-Agent；先看 HTTP 状态码，别急着调 prompt |
| 模型不按格式输出、解析崩 | 换一个「非推理型」模型；推理型模型（r1/v3-pro 等）倾向直接吐答案 |
| `model_not_found` | `GET /v1/models` 拉真实模型列表，别假设模型名一致 |

## 不要做什么

- 不要一上来就装全部依赖（`requirements.txt` 里一堆用不上的）。
- 不要改官方代码的核心逻辑；只加 User-Agent、超时、API 适配这些「环境层」的东西。
- 不要在 500 条数据上 debug，先在 3 条上 debug。
- 不要把 API key 写进代码或提交。
