# Excel 数据匹配工具

千万级 Excel/CSV 数据自动匹配，输出匹配成功和失败的结果。

## 快速开始

```bash
# 第一次使用：安装环境
bash setup.sh        # Mac
# setup.bat          # Windows

# 每次使用
bash run.sh          # Mac（双击即可）
# run.bat            # Windows（双击即可）
```

## 文档

| 文档 | 说明 | 面向 |
|------|------|------|
| [使用手册.md](./使用手册.md) | 完整操作指南，含配置编写、场景示例、常见问题 | 财务人员 |
| [架构设计.md](./架构设计.md) | 技术架构、模块说明、性能数据 | 技术人员 |

## 目录结构

```
excelUtils/
├── README.md                  # 本文件
├── 使用手册.md                 # 用户操作手册
├── 架构设计.md                 # 技术架构文档
├── setup.sh / setup.bat       # 一键安装
├── run.sh / run.bat           # 一键运行
├── config.yaml                # 匹配规则配置
├── config.example.yaml        # 配置模板
├── data/
│   ├── input/                 # ← 数据文件放这里
│   └── output/
│       ├── matched/           # 匹配成功输出
│       └── unmatched/         # 匹配失败输出
└── src/                       # 源代码
```

## 依赖

- Python 3.9+
- duckdb, pyyaml, pandas, openpyxl
