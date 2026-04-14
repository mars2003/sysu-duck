#!/bin/bash

# 启动鸭鸭脚本
# 使用方法：./start_duck.sh <命令> [参数]

# 检查是否设置了用户ID
if [ -z "$DUCK_USER_ID" ]; then
    echo "请设置DUCK_USER_ID环境变量"
    echo "例如：export DUCK_USER_ID=your_user_id"
    exit 1
fi

# 执行duck.py命令
python3 ../src/duck.py "$@"
