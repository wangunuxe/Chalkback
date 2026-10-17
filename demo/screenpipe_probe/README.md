# screenpipe /search 实测记录（TA1）

<!-- 每种 content_type 贴一份真实返回（删掉敏感内容），记录字段名、权限规则实测结果。 -->

## 环境

- 机器 / 系统：
- screenpipe 版本：

## audio（device_type = input）

## ocr

## accessibility

## 权限规则实测

| 规则 | 预期 | 实测 |
| --- | --- | --- |
| `Content(audio, ocr, accessibility)` | 放行 | |
| `/raw_sql` | 拒绝 | |
| `App(1Password)` | 拒绝 | |
