# Q2 原文解析与 mapping 候选

本轮在现有 P0 流程上增加有界解析器，不调用模型、不自动审核。`academic_os/parsing.py` 从已登记 locator 的受控原文中提取 Q2(a/b/c)；`academic_os/mapping.py` 使用显式规则匹配题干与评分段，生成标准 `Service.stage` 输入。它不是通用题库解析器，也不会凭 filename 推断身份。

## 实际变化

- 新增 `parsed_part` 域对象：题干、共享题干、比较条件、评分段、评分说明，每段保存 locator ID、locator 内容版本、原始字符区间 `[start,end)` 及逐字文本；保存分值和 parser version。
- Q2 分值从试卷和评分方案分别抽取，要求一致，当前为 a=1、b=2、c=2。
- Q2(c) 保留完整评分 notes，其中包括对 (b) 的依赖和 follow-through 条件；不把“标准差更大”简化为必然存在更快个体的结论。
- 映射规则检查 a 的 mean、b 的 standard deviation、c 的 contextual reasoning 指令及对应评分段。仅关联现有四个 competency ID，不新增或自动批准定义。无法匹配时明确报 unresolved 并停止整批计划生成。
- 生成 15 个候选：3 个新 parsed_part、4 个 mapping 新版本、8 个 evidence 新版本。复用旧 context、conditions、competency、scope 和来源，旧内容版本不被覆盖。
- mapping 与 evidence 的 `judgment_refs` 绑定解析记录；解析内容变化会令审批 stale，解析记录自身也须人工 approve。撤回解析审核同样阻断快照读取。
- graph 校验拒绝伪造文本、越界位置、过期 locator 版本、跨题/跨小题定位和来源类型不符。该结构校验不代替人工判断语义与真实性。

## 可复现命令

从项目目录运行。以下使用独立数据库，避免改动已有操作员审核；如果路径已存在，应继续使用已有计划或选择一个新的输出文件名，`parse-q2` 不覆盖文件。

```powershell
python -X utf8 -m academic_os --db var/q2_parser_demo.sqlite3 import-q2 --request-id q2-seed-v1
python -X utf8 -m academic_os --db var/q2_parser_demo.sqlite3 parse-q2 --output output/q2_parser_demo/plan.json
python -X utf8 -m academic_os --db var/q2_parser_demo.sqlite3 stage --file output/q2_parser_demo/plan.json --request-id q2-parsed-v1
python -X utf8 -m academic_os --db var/q2_parser_demo.sqlite3 inspect parsed_part:PARSED-Q2-c
python -X utf8 -m academic_os --db var/q2_parser_demo.sqlite3 check
```

最后一步预期退出 2：没有人工审核，必须阻断。`parse-q2` 只生成计划，不写审核或候选数据库；`stage` 才事务性入库。重复提交同一个计划与 request ID 幂等。计划生成后如有人修改 mapping，旧计划 CAS 失败；需要重新查看和生成新计划，不能强行覆盖。

本轮已实际在 `var/p0_q2.sqlite3` 完成候选升级，真实审批数仍为 0。`output/q2_parsing/candidates.json` 是该次计划，其 expected_heads 指向升级前版本；重复提交须使用原请求 ID `real-q2-parsing-v1`。不要将这份带旧版本 CAS 的计划当作任何数据库都能导入的模板。

## 边界与待确认

此适配器依赖现有 Q2 来源/定位和候选 registry seed，只支持 June 2025 9MA0/31 Q2 的当前受控文本版式。缺段、重复标记、顺序错误、分值不符或未知指令会失败；失败不会写入半批候选。规则匹配仅为候选建议，不证明 competency 定义或课程关联正确。

共享题干保留公式乱码，尚不把 `sum x`、`sum x²` 解析为可计算公式 AST，也不重新推导原有人工配置的条件。公式解释、条件、评分 notes、competency 和具体考纲关联仍需审核；CONTEXT-INFER 的具体考纲对应仍未断言。解析器代码行为变化时必须更新 `PARSER_VERSION`。

后续通用 parsing 适配器可输出同一 `ParsedQuestionPart` 和标准 stage envelope；前端/API 复用 `Service.plan_q2`、`stage`、`inspect`、`review`、`check` 和 `snapshot`。数据库仍使用 P0 migration 1，无需覆盖迁移或重置任何审核。

测试：`python -X utf8 -m unittest discover -p 'test_*.py'`。成功发布测试使用临时 TEST-ONLY 来源与审核者；真实 Q2 流程始终保持待审核。
