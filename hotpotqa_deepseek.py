"""ReAct (HotpotQA) 复现 —— DeepSeek 版。

基于官方 hotpotqa.ipynb 改造：把 OpenAI 的 text-davinci-002 Completion 接口
替换成 DeepSeek 的 deepseek-chat Chat 接口，其余逻辑（few-shot prompt、
Thought/Action/Observation 循环、Wikipedia 环境）保持原样。

用法:
    export DEEPSEEK_API_KEY='...'
    python3 hotpotqa_deepseek.py [样本数]     # 默认跑 3 个样本

依赖: numpy, gym, requests, beautifulsoup4（均已安装）。
"""

import os
import sys
import time

import requests
from openai import OpenAI

import wikienv
import wrappers

# ---------------------------------------------------------------- API
api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
if not api_key:
    raise SystemExit(
        "错误: 未找到 API Key（OPENAI_API_KEY 或 DEEPSEEK_API_KEY）。\n"
        "请先设置后再运行，例如:\n"
        "  export OPENAI_API_KEY='你的 key'"
    )

# base_url / model 支持环境变量覆盖，换中转站或模型时无需改代码
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
MODEL = os.environ.get("OPENAI_MODEL", "deepseek-chat")

client = OpenAI(api_key=api_key, base_url=BASE_URL)


def llm(prompt, stop=["\n"]):
    """OpenAI 兼容 chat 接口：整段 prompt 作为单条 user 消息。"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=150,
        stop=stop,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------- 环境
env = wikienv.WikiEnv()
env = wrappers.HotPotQAWrapper(env, split="dev")
env = wrappers.LoggingWrapper(env)


def step(env, action):
    attempts = 0
    while attempts < 10:
        try:
            return env.step(action)
        except requests.exceptions.Timeout:
            attempts += 1


# ---------------------------------------------------------------- prompt
with open("./prompts/prompts_naive.json", "r") as f:
    prompt_dict = __import__("json").load(f)

webthink_examples = prompt_dict["webthink_simple6"]

instruction = """Solve a question answering task with interleaving Thought, Action, Observation steps. Thought can reason about the current situation, and Action can be three types: 
(1) Search[entity], which searches the exact entity on Wikipedia and returns the first paragraph if it exists. If not, it will return some similar entities to search.
(2) Lookup[keyword], which returns the next sentence containing keyword in the current passage.
(3) Finish[answer], which returns the answer and finishes the task.
Here are some examples.
"""

webthink_prompt = instruction + webthink_examples


# ---------------------------------------------------------------- 主循环
def webthink(idx=None, prompt=webthink_prompt, to_print=True):
    question = env.reset(idx=idx)
    if to_print:
        print(idx, question)
    prompt += question + "\n"
    n_calls, n_badcalls = 0, 0
    for i in range(1, 8):
        n_calls += 1
        thought_action = llm(prompt + f"Thought {i}:", stop=[f"\nObservation {i}:"])
        try:
            thought, action = thought_action.strip().split(f"\nAction {i}: ")
        except Exception:
            if to_print:
                print("ohh...", thought_action)
            n_badcalls += 1
            n_calls += 1
            thought = thought_action.strip().split("\n")[0]
            action = llm(prompt + f"Thought {i}: {thought}\nAction {i}:", stop=["\n"]).strip()
        obs, r, done, info = step(env, action[0].lower() + action[1:])
        obs = obs.replace("\\n", "")
        step_str = f"Thought {i}: {thought}\nAction {i}: {action}\nObservation {i}: {obs}\n"
        prompt += step_str
        if to_print:
            print(step_str)
        if done:
            break
    if not done:
        obs, r, done, info = step(env, "finish[]")
    if to_print:
        print(info, "\n")
    info.update({"n_calls": n_calls, "n_badcalls": n_badcalls, "traj": prompt})
    return r, info


if __name__ == "__main__":
    import json

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    rs = []
    old_time = time.time()
    for i in range(n):
        r, info = webthink(i, to_print=True)
        rs.append(info["em"])
        print(sum(rs), len(rs), sum(rs) / len(rs), (time.time() - old_time) / len(rs))
        print("-----------\n")
