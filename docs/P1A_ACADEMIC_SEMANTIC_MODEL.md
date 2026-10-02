# P1A：Academic Semantic Model

## 概念、能力与任务条件

Concept 表示“是什么”，例如 Mean、Standard deviation。Competency 表示学生能展示的动作，例如 Calculate the mean、Calculate standard deviation。Mean 不会因为是名词就被当成一个技能。

Task Condition 表示这次如何要求学生展示能力，例如 From summary statistics。Q2(a) 和 Q2(b) 共享这一条件，而不创建两种“from summary statistics”专属能力。能力 ID 和名称不包含课程、考试局、题号或教练场景。

Curriculum Scope 则回答课程要求的范围。即使考纲和题目都提到 summary statistics，课程范围与当前任务条件仍是两个对象，具有独立版本和审核记录。

## 复用与最小扩展

已检查 v0.2 prototype、v0.3 domain schema、P0/Q2 服务、CLI、迁移、测试、文档、历史验收文件和真实 SQLite 数据。v0.2 区分 canonical identity 与课程 scope，但其 question mapping 还是整题级；v0.3 已有 Concept、Concept–Competency Link 和 question-part mapping。因此 P1A 复用 v0.3 的 `CanonicalConcept` 与 `CompetencyConceptLink`，将它们注册到现有 P0 对象存储，不重新定义审批系统。

- `concept`：复用 v0.3 Concept，含 ID、领域、名称、定义、provenance 和候选审核字段。
- `concept_link`：复用 v0.3 关系 `applies_concept`。每条关系引用一个 competency 和一个 concept，多条关系自然支持双向多对多。
- `task_condition`：新增小型可复用任务形式定义，继承现有 Reviewable，仅增加 ID、name、description、kind。它没有 question_id，也没有 curriculum context。
- 原有 `condition` 保留为题目具体给定条件：Q2 跑者人数、数据、教练场景仍在这里。原有 v0.3 TaskCondition 要求 question_id，不能直接用来跨题复用；P1A 的可复用定义与具体题目条件通过同一 mapping 的依赖闭包同时参与审核。
- `part_mapping`：继续使用现有映射对象和 evidence、confidence、provenance、review 字段，仅增加可选 `semantics`，包含 `role=primary|secondary`、parsed_part_id、concept_link_ids、task_condition_ids。原有 `role=assessed|supporting` 表示评估关系，语义主次放在 semantics.role，避免把两个维度混为一谈。

没有添加 `question_part.skill_id`。一题可以映射多个能力，同一能力也可被多个题目引用。primary/secondary 是显式候选数据，不从每个推理步骤自动生成 secondary。Q2(a/b) 没有新增 secondary。

## Q2 Gold Standard

Gold Standard 是用户定义的架构验收 fixture，不是生产审批。

- Q2(a)：Mean → primary Calculate the mean；条件 From summary statistics。
- Q2(b)：Standard deviation → primary Calculate standard deviation；复用同一个 From summary statistics。
- Q2(c)：Standard deviation、Variation / spread、Extreme values → primary Interpret measures of variation；secondary 候选 Make contextual inferences using statistical evidence；条件 Compare variation using standard deviation。

Variation / spread 表示一般离散概念，Extreme values 表示分布两端的值，与具体度量 Standard deviation 分开。这是 Q2 所需的四个概念，不是完整统计学本体。

保留现有四个 competency ID，只更新通用名称/定义；不创建 Interpret standard deviation、Compare coaches 等额外身份。Q2(c) 两个 competency 分别通过显式关系关联这三个概念。共新增 4 个 concept、8 条 concept_link、2 个可复用 task_condition，更新 4 个 competency 和 4 条 mapping。

复用三个已存在的 parsed records、八条证据、原有 locator/source 和条件。没有重打、修复或替换题干文本。公式抽取缺陷与评分 notes 保持原样。具体考纲关联不足之处仍未断言；没有新增 syllabus objective。

## 版本、审核与发布

全部候选通过 `Service.stage` 写入。source/locator 核验与学术批准仍独立。所有新语义对象都使用原有 append-only 审核 journal、CAS、幂等键及 `Service.review`。

映射的现有依赖图现在自动包含：question part、parsed part、competency、concept relationship、concept、task condition，以及原有 evidence、scope、context、具体题目条件和来源。修改任一相关内容会改变依赖摘要，使旧映射审批 stale。跨能力概念关系、不存在的引用、重复语义引用和不匹配的 parsed part 都被拒绝。

候选自填 approved/verified 仍无效。全部必要依赖批准后才能发布；Q2(c) secondary 及其依赖未批准时，完整 Q2 发布仍阻断。撤回记录使后续发布和旧快照读取失败，不改快照历史。trusted read 只能走 `Service.snapshot`，语义报告和 inspect 是候选调试视图，不是可信学术内容接口。

真实数据库仍无任何审核记录或正式快照。本轮没有将用户给出的 fixture 当作某个操作员签名。临时测试数据库使用 TEST-ONLY PDF、审核者和理由，测试成功发布、撤回和修订。

## 兼容与 SQLite

SQLite migration 仍为 1：现有 versions/heads/reviews 等通用 JSON 对象表无需 DDL 变化。没有清库或覆盖历史。

旧 mapping 没有 semantics 时，normalise 不插入 null 默认字段，保证旧内容摘要不变。扩展字段只存在于新的显式候选版本。v0.3 validator 继续校验原始域字段，P0 graph 校验新语义引用并执行相同发布门。v0.1/v0.2/v0.3 示例、旧输出和 pinned hashes 不修改。

旧版应用遇到新的对象 kind 会在 graph 校验处拒绝，不会当作可信内容忽略；读取新数据库应使用本版本。数据库管理员仍处于本机信任边界，未添加生产认证。

## 操作与复现

已升级数据库的只读候选检查：

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 semantic-q2
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 inspect concept:CON-STAT-SD
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 inspect concept_link:LINK-SD-CALC-SD
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 inspect task_condition:TC-SUMMARY-STATISTICS
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 inspect part_mapping:MAP-Q2-c-CONTEXT-INFER
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 check
```

`semantic-q2` 的 architecture_valid 仅表示 fixture 和结构符合约定：成功返回 0，即使 publishable=false。`check` 在未获审核时退出 2。报告明确分别提供 candidate_status、approval_status、competency_approval、全部依赖审批状态和发布阻断原因。

独立新数据库从已有原件复现，以下输出文件必须尚不存在：

```powershell
python -X utf8 -m academic_os --db var/p1a_demo.sqlite3 import-q2 --request-id p1a-seed
python -X utf8 -m academic_os --db var/p1a_demo.sqlite3 parse-q2 --output output/p1a_demo/parsing.json
python -X utf8 -m academic_os --db var/p1a_demo.sqlite3 stage --file output/p1a_demo/parsing.json --request-id p1a-parsing
python -X utf8 -m academic_os --db var/p1a_demo.sqlite3 semantic-q2 --plan-output output/p1a_demo/semantics.json
python -X utf8 -m academic_os --db var/p1a_demo.sqlite3 stage --file output/p1a_demo/semantics.json --request-id p1a-semantics
python -X utf8 -m academic_os --db var/p1a_demo.sqlite3 semantic-q2
python -X utf8 -m academic_os --db var/p1a_demo.sqlite3 check
```

plan-output 仅生成标准 stage envelope，带 expected_heads。Service.stage 事务性追加新版本；同一请求重试幂等，过期计划报冲突。真实库本轮使用计划 `output/p1a_semantics/plan.json` 和请求 ID `real-q2-p1a-v1`，不要把其旧 expected_heads 用于别的数据库。

## 验收与已知基线问题

```powershell
python -X utf8 -m unittest tests_p0.test_semantics
python -X utf8 -m unittest discover -p 'test_*.py'
```

修改前实际运行 179 项，已有 1 个错误：历史保护测试找不到项目根目录的 `AI_Academic_Operating_System_Brainstorm_CN.pptx`。未用其他演示 PPT 替代，未重置 hash，也未跳过该检查。最终测试数量和结果见 `output/p1a_semantics/acceptance.json` 与 `tests.log`；真实语义报告见 `gold-standard-report.json`。

新增测试覆盖语义区分、概念/能力多对多、任务条件复用、主次角色、Gold Standard、canonical identity、引用完整性、审批前阻断、临时数据成功发布、上游改版失效、撤回、幂等和并发冲突。

## 后续边界

未来 parsing/mapping 适配器仍只输出候选，使用相同 Service API。Learning Specification 可另行引用 concept/competency 的版本，不改变 canonical identity。本轮不实现 LearningRequirement、MasteryCriterion、学生掌握度、难度、生成式教学内容、Q4 或 ContextResource；resource 条件仍是显式未支持范围。frontend/ 未修改，无模型调用。


## 后续 P1B.2 人工边界修正

上文“三个概念、8 条 link”为初始 P1A 历史状态。P1B.2 人工审核将 Q2(c) primary 的 canonical 概念缩为 Standard deviation 与 Variation / spread；Extreme values 只保留于该题的推理/证据及未批准的 secondary 候选。新候选生成器创建 7 条 link；真实库仍保留原第 8 条关系的历史记录。没有新增 schema 类型。详见 `P1B_HUMAN_REVIEW_AND_PUBLICATION.md` 的 P1B.2 节。
