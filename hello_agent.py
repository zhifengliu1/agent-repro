import os

from openai import OpenAI

# 从环境变量读取 API Key，绝不写死在代码里
api_key = os.environ.get("DEEPSEEK_API_KEY")
if not api_key:
    raise SystemExit(
        "错误: 未找到环境变量 DEEPSEEK_API_KEY。\n"
        "请先设置后再运行，例如:\n"
        "  export DEEPSEEK_API_KEY='你的 key'"
    )

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "你好！请用一句话介绍你自己。"},
    ],
)

print(response.choices[0].message.content)
