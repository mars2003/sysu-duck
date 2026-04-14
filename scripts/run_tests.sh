#!/bin/bash

# 运行所有测试脚本
# 使用方法：./run_tests.sh

echo "开始运行鸭鸭测试..."
python3 -m unittest discover -s ../tests -v
