


```
agent_os_system/
│
├── base_os/                  # (不可变) 真正的神明/看门狗
│   └── os_kernel.py          # 监听 Evo Agent 的退出状态码
│
├── evo_agent_active/         # (可变) 正在运行的 Evo Agent 实体
│   ├── main.py               # Agent的主循环
│   ├── memory.py             # 记忆管理核心
│   ├── reasoning.py          # 思考框架 (如 ReAct, COT)
│   └── skills/               # 工具库
│
├── staging_area/             # (可变) Evo Agent 写新代码的草稿箱
│   └── (结构同 evo_agent_active)
│
└── history_versions/         # (不可变) Base-OS 维护的快照，用于回滚
    ├── v1.0/
    ├── v1.1/
    └── ...
```
