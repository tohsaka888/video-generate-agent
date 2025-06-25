#!/bin/bash

# 设置错误时退出
set -e

echo "开始更新代码..."

# 检查是否在git仓库中
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "错误：当前目录不是git仓库！"
    exit 1
fi

# 更新所有SubModule
echo "正在更新子模块..."
if ! git submodule update --init --recursive; then
    echo "子模块初始化失败！"
    exit 1
fi

# 使用 --remote --merge 参数更新子模块，保持在跟踪的分支上
if ! git submodule update --remote --merge --recursive; then
    echo "子模块更新失败！"
    exit 1
fi

echo "✅ 所有更新完成！"