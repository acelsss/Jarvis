# ADR-0001: Use OpenMemory as primary memory service

- Context: 我们需要一个可持久化的记忆系统，支持搜索与回溯

- Decision: 以 OpenMemory 为主，本地 JSON 为兜底

- Consequences: 远端不可用时自动回退；后续可接向量索引

