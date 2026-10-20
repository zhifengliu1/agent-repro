#!/usr/bin/env bash
# 一键搭建 ToT（Game of 24）复现环境：clone 官方仓库 → 装依赖 → 打 DeepSeek 适配补丁。
# 用法: bash setup_tot.sh [目标目录，默认 ~/repos/tree-of-thought-llm]
set -euo pipefail

DEST="${1:-$HOME/repos/tree-of-thought-llm}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. clone 官方仓库（已存在则跳过；网络不稳可改用 --depth 1）
if [ ! -d "$DEST/.git" ]; then
    mkdir -p "$(dirname "$DEST")"
    git clone --depth 1 https://github.com/princeton-nlp/tree-of-thought-llm.git "$DEST"
fi

cd "$DEST"

# 2. 建 venv 并装依赖（官方 requirements.txt 钉死 openai==0.27.7 已过时，装新版）
if [ ! -x .venv/bin/python ]; then
    uv venv .venv
    uv pip install --python .venv/bin/python openai sympy pandas numpy
    uv pip install --python .venv/bin/python -e . --no-deps
fi

# 3. 打 DeepSeek 适配补丁（幂等：--check 通过才 apply）
PATCH_DIR="$SCRIPT_DIR/patches/tot"
if git apply --check "$PATCH_DIR"/*.patch 2>/dev/null; then
    git apply "$PATCH_DIR"/*.patch
else
    echo "补丁已应用或与工作区冲突，跳过（若冲突请先 git checkout 官方文件）。"
fi

echo
echo "搭建完成。运行方式（记得先 export DEEPSEEK_API_KEY）："
echo "  cd $DEST"
echo "  # ToT 快速冒烟（b=1、打分 1 次，1 局，约 \$0.04）"
echo "  .venv/bin/python run.py --task game24 --task_start_index 900 --task_end_index 901 \\"
echo "      --method_generate propose --method_evaluate value --method_select greedy \\"
echo "      --n_evaluate_sample 1 --n_select_sample 1"
echo "  # CoT baseline（10 采样）"
echo "  .venv/bin/python run.py --task game24 --task_start_index 900 --task_end_index 901 \\"
echo "      --naive_run --prompt_sample cot --n_generate_sample 10"
