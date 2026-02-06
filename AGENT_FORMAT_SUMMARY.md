# Agent Output Format Summary

## 观察到的所有格式

### 格式 1: 标准格式 (期望格式，兼容 v5.0-5.3)
```json
{
  "score_breakdown": {
    "A1_code_volume": 3,
    "A2_subsystem_criticality": 8,
    "A3_cross_subsystem": 0,
    "B1_category_base": 13,
    "B2_stable_significance": 4,
    "B3_user_impact": 4,
    "B4_novelty": 1,
    "C1_review_chain": 3,
    "C2_commit_message": 4,
    "C3_testing": 0,
    "C4_atomicity": 2,
    "D1_cross_org": 1,
    "D2_maintainer_endorsement": 2,
    "D3_community_response": 0
  }
}
```

### 格式 2: 嵌套对象格式
```json
{
  "score_technical": {...},
  "score_impact": {...},
  "score_quality": {...},
  "score_community": {...}
}
```

### 格式 3: *_breakdown 格式
```json
{
  "technical_breakdown": {...},
  "impact_breakdown": {...},
  "quality_breakdown": {...},
  "community_breakdown": {...}
}
```

### 格式 4: score_* 前缀格式
```json
{
  "score_a1_technical_complexity": 3,
  "score_a2_subsystem_criticality": 8,
  "score_a3_cross_subsystem": 0,
  ...
  "total_score": 45
}
```

### 格式 5: a1_, a2_ 前缀格式
```json
{
  "a1_code_volume": 3,
  "a2_category_base": 13,
  ...
}
```

### 格式 6: B2_stable_lts 等变体
字段名称的其他变体：
- `B2_stable_lts` 而不是 `B2_stable_significance`
- `C2_message_quality` 而不是 `C2_commit_message`
- `D2_maintainer_role` 而不是 `D2_maintainer_endorsement`
- `D3_responsiveness` 而不是 `D3_community_response`

## 当前代码状态

linux_kernel_analyzer.py 中的转换代码已经支持格式 1-5，但可能还有遗漏的变体。

## 建议

1. 固定 agent prompt，明确要求返回格式 1 (标准格式)
2. 或者完全重写 agent prompt，使其更严格
3. 在 Python 代码中添加更完整的格式检测和转换逻辑
