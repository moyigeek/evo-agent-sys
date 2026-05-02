# Evo Agent System

递归自我改进（Recursive Self-Improvement, RSI）Agent 系统。

**核心理念：「克隆 → 测试 → 换脑 → 重启」**

Evo Agent 不能直接边运行边覆盖自己的主程序代码，必须遵循严格的进化协议。

## 架构

```
evo-agent-sys/
├── base_os/                       # （不可变）看门狗
│   └── os_kernel.py               # 监听退出码，执行换脑/回滚
├── evo_agent_active.py/           # （可变）Evo Agent 代码本体
│   ├── main.py                    # 入口 + 进化协议 + ReAct 循环
│   ├── memory.py                  # 状态持久化（JSON）
│   ├── reasoning.py               # ReAct 推理框架
│   ├── system_prompt.py           # 系统提示词（架构护栏）
│   ├── llm.py                     # LLM 客户端（零外部依赖）
│   └── skills/
│       └── __init__.py            # 工具注册中心
├── staging_area/                  # 暂存区（运行时生成）
├── history_versions/              # 版本快照（运行时生成）
├── .evo_state.json                # 状态持久化文件
└── .evo_recovery_message.json     # 回滚恢复消息（Base-OS 写入）
```

## 进化协议

```
Evo Agent         Base-OS          文件系统
  │                  │                │
  │  1.暂存新代码   │                │  staging_area/
  │  2.语法检查     │                │
  │  3.隔离进程测试 │                │
  │  4.保存状态     │                │  .evo_state.json
  │                  │                │
  │──exit(42)──────→│                │
  │                  │  5.备份旧代码  │  history_versions/v{version}/
  │                  │  6.部署新代码  │  evo_agent_active.py/
  │                  │  7.重启 Agent  │
  │←─────────────────│                │
  │  8.load_state()  │                │
```

| 退出码 | 含义 | Base-OS 行为 |
|--------|------|-------------|
| 0 | 正常关机 | 退出主循环 |
| 42 | 升级请求 | 备份 → 替换 → 重启 |
| 其他非零 | 崩溃 | 记录时间戳；10分钟内≥3次则回滚 |

## 快速开始

```bash
# Echo 模式（无 LLM，仅回显输入）
python base_os/os_kernel.py

# ReAct 模式（配置 LLM）
python evo_agent_active.py/main.py --llm-url https://api.deepseek.com \
                                    --llm-key sk-your-key \
                                    --llm-model deepseek-chat
```

### LLM 配置

三种方式配置 LLM，优先级：**CLI 参数 > 环境变量 > 默认值**。

| CLI 参数 | 环境变量 | 默认值 | 说明 |
|---------|---------|--------|------|
| `--llm-url` | `EVO_LLM_API_BASE` | `https://api.openai.com` | API 地址（兼容 OpenAI 接口） |
| `--llm-key` | `EVO_LLM_API_KEY` | `""` | API Key（不设时进入 echo 模式） |
| `--llm-model` | `EVO_LLM_MODEL` | `gpt-4o` | 模型名称 |

未配置 API Key 时，Agent 运行在 echo 模式，仅回显输入内容。

## 核心机制

### 状态持久化

重启前 Agent 将对话历史、长期记忆、当前任务序列化到 `.evo_state.json`。新版本启动时自动调用 `load_state()` 恢复，用户感知不到 Agent 重启过。

### 死亡螺旋防护

Base-OS 记录每次崩溃的时间戳。若 **10 分钟内崩溃 ≥ 3 次**：

1. 从 `history_versions/` 拷贝最新备份覆盖当前代码
2. 向 `.evo_recovery_message.json` 注入恢复消息
3. Agent 启动时读取恢复消息，注入对话历史，分析并修复问题

### 自我测试

升级前执行两级测试：

1. **语法检查**：对所有 `.py` 文件运行 `py_compile`
2. **隔离进程测试**：启动新代码的子进程，发送测试 prompt，校验响应和退出码，10 秒超时防死循环

### 必留接口

重写核心代码时必须保留以下接口，否则系统无法引导：

| 接口 | 位置 | 说明 |
|------|------|------|
| `EvoAgent.__init__()` | main.py | 必须调用 `load_state()` |
| `EvoAgent.run()` | main.py | 主循环入口 |
| `evaluate_and_rewrite_core()` | main.py | 进化协议入口 |
| `save_state()` / `load_state()` | memory.py | 状态序列化/反序列化 |
| `load_recovery_message()` | memory.py | 检查回滚恢复消息 |

### 工具库

`skills/__init__.py` 提供 `SkillRegistry` 和内置工具：

| 工具 | 功能 |
|------|------|
| `read_file` | 读取文件 |
| `write_file` | 写入文件 |
| `run_command` | 执行 shell 命令（30s 超时） |

## 运行测试

```bash
python test_e2e.py
```

## 安全警告

- 该 Agent 可**修改自身核心代码**，相当于在飞行中拆装引擎
- System Prompt 中已声明架构约束和必留接口，但 LLM 可能不遵守
- 死亡螺旋回滚机制提供最后防线，但不能保证万无一失
- 生产环境建议在沙箱/容器中运行
