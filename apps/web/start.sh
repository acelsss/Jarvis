#!/bin/bash
# Jarvis Web 服务器启动脚本

cd "$(dirname "$0")/../.."

echo "启动 Jarvis Web 服务器..."
echo "访问地址: http://localhost:8000"
echo ""

python -m apps.web.api_server
