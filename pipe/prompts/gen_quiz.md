<!-- 负责人：B（TB3）。由 pipe.md 引用。 -->

# gen_quiz

## 目标

按覆盖时长和权重分配题量，只考讲过的知识点，每题带 source；按老师风格写题。

## 输入

coverage.json、segments.json、state/weights.json、state/style_profile.json

## 输出

quiz（status=pending，通过 validate.py quiz；每题 source.quote 必须能在 segments 的 speech 里找到原文）

## 步骤

<!-- TODO(TB3) -->

## 规则

- 不要发明契约之外的字段；格式见 contracts/ 与技术文档 §5。
- 原文和 screenpipe id 只能出现在本机文件里。
