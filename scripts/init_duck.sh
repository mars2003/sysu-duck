#!/bin/bash

# 初始化鸭鸭环境脚本
# 使用方法：./init_duck.sh <user_id>

if [ $# -eq 0 ]; then
    echo "请提供用户ID"
    echo "例如：./init_duck.sh your_user_id"
    exit 1
fi

USER_ID=$1

echo "设置环境变量..."
export DUCK_USER_ID=$USER_ID
echo "DUCK_USER_ID=$DUCK_USER_ID"

echo "创建数据目录..."
mkdir -p ../data

echo "初始化完成！"
echo "现在可以使用 ./start_duck.sh 命令来操作鸭鸭"
