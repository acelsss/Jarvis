#!/bin/bash
# 自动生成的下载脚本
# 在本地电脑上运行此脚本下载skill-creator

set -e

SKILL_DIR="skill-creator"
mkdir -p "$SKILL_DIR/references"

echo "开始下载skill-creator文件..."

echo "下载 LICENSE.txt..."
curl -L "https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/LICENSE.txt" -o "$SKILL_DIR/LICENSE.txt"

echo "下载 SKILL.md..."
curl -L "https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/SKILL.md" -o "$SKILL_DIR/SKILL.md"

echo "下载 references/output-patterns.md..."
curl -L "https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/references/output-patterns.md" -o "$SKILL_DIR/references/output-patterns.md"

echo "下载 references/workflows.md..."
curl -L "https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/references/workflows.md" -o "$SKILL_DIR/references/workflows.md"

echo ""
echo "下载完成！"
echo ""
echo "文件列表:"
ls -la "$SKILL_DIR"
if [ -d "$SKILL_DIR/references" ] && [ "$(ls -A $SKILL_DIR/references)" ]; then
    echo ""
    echo "References目录:"
    ls -la "$SKILL_DIR/references"
fi

echo ""
echo "=========================================="
echo "使用以下命令传输到远程服务器:"
echo "=========================================="
echo "scp -r $SKILL_DIR jetson@<远程IP>:/home/jetson/projects/Jarvis/skills_workspace/"
echo ""
echo "或使用rsync:"
echo "rsync -avz --progress $SKILL_DIR/ jetson@<远程IP>:/home/jetson/projects/Jarvis/skills_workspace/skill-creator/"
