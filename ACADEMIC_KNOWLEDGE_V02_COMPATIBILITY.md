# Academic Knowledge Model v0.2 — Schema Prototype

本次为并行架构原型，不替换 v0.1，不执行迁移，也不产生新的正式学术批准。

## 文件与运行方式

- `academic_knowledge_schema_v02.py`：独立 Pydantic schema；不导入 v0.1 模型。
- `build_academic_knowledge_v02_prototype.py`：只读指定 v0.1 JSON，生成真实引用与明确标记的 synthetic fixtures。
- `validate_academic_knowledge_v02.py`：schema、引用一致性、已登记真实来源、证据与排除语义校验。
- `test_academic_knowledge_v02.py`：语义测试、错误路径测试及 52 个既有文件的 SHA-256 回归基线。
- `output/academic_knowledge_v02_prototype.json`：可重复生成的 prototype，不是 approved graph 或新 audit history。

在项目根目录运行，无需新增依赖或 API key：

```powershell
python -m py_compile academic_knowledge_schema_v02.py build_academic_knowledge_v02_prototype.py validate_academic_knowledge_v02.py test_academic_knowledge_v02.py
python -X utf8 build_academic_knowledge_v02_prototype.py
python -X utf8 validate_academic_knowledge_v02.py
python -X utf8 -m unittest -v test_academic_knowledge_v02
```

Builder 固定只写新的 v0.2 JSON。Validator 可以通过 `--input` 检查其他 v0.2 文件；不会根据输入中的 source reference 任意打开文件。真实来源采用固定 allowlist，后续导入其他课程须先登记、验证来源。

## 五个概念的边界

**CanonicalCompetency：学生会做什么。** 保留 `canonical_id`、`subject_domain`、`skill_name`、`description`、`status`。没有 exam board、qualification、stage、tier、pathway、curriculum version 或 difficulty 字段。`provenance` 记录数据从何处复制/构造，不参与技能 identity。不加入尚无用途的 parent graph。

**CurriculumContext：要求出现在哪里。** Board、qualification、subject、specification code、version、educational stage、tier、pathway 均属于这里。Tier/pathway 可空，开放字符串不限制为 Edexcel 枚举。真实 parsed JSON 未记录 version、stage、pathway，所以输出为 null。`4MA1` 是 specification code，不冒充 curriculum version。

**CurriculumScope：在该 context 下要求做到什么范围。** 每条记录关联 objective/context/competency，拥有稳定 scope ID、description、constraints、included applications、excluded applications 和 unresolved scope。不存 universal difficulty。未决候选 scope 可以没有 approved mapping；矩阵 inverse 正是这种情形，并不表示该技能已列入 syllabus。

**CurriculumEvidence：为什么作出某种解释。** 关联 objective/context，可进一步指向 competency/scope。保存 source type、authority、observation、evidence role、observation status、confidence、review status 和 provenance。`evidence_role` 的 supports/clarifies/contradicts 与 `observation_status` 的 observed/ambiguous/insufficient_evidence/not_observed 分开；“未观察到”不是排除状态。

**QuestionDifficulty：一道具体 task 的测量。** 通过 question ID 独立关联，允许仅有预测，也允许后续观察值。示例使用 0–1、越大越难的任务层数值，绝不把 Foundation/Higher/IGCSE/A-Level 当作难度值；这不是跨课程通用标定尺度。

附属对象：`OfficialObjectiveReference` 保留原 source ID 与 context 关联；`OfficialCompetencyMapping` 表示多对多关系；`QuestionReference` 与 `QuestionCompetencyMapping` 只证明 task 可引用 competency，不实现 Question Bank。

## Identity、引用与 provenance

- Context ID 是显式登记的稳定标识，不由运行时间、列表顺序或难度推导。本次真实 context 为 `CTX-EDX-4MA1-F-LOCAL-BASELINE`、`CTX-EDX-4MA1-H-LOCAL-BASELINE`。它们指当前本地已解析快照，不宣称代表全部历史版本。
- Official wording 的唯一正式来源仍是现有 parsed JSON。Prototype 的 `wording_excerpt` 只是可读性副本；真实记录必须逐字与源数据一致。
- 每条有独立内容的记录保存 `provenance.origin` 与 `source_reference`；synthetic 记录还必须保存完整标记：**SYNTHETIC ARCHITECTURE TEST DATA — NOT OFFICIAL CURRICULUM DATA**。
- Synthetic context/objective/question 使用 `SYN-` ID，来源必须为 `synthetic://...`。Canonical ID 保留题目要求的 `CAN-MATH-...`，其 provenance 明确为 synthetic。Question–competency 纯关联记录通过 question 继承 synthetic 身份。
- 真实 objective 必须在固定读取的 parsed 文件中存在，context 必须匹配它的来源和 tier；真实 canonical、mapping、scope 与当前 v0.1 记录核对。不能通过声明 `origin=real` 将未知 fixture 变成官方数据。
- Context/canonical/scope/evidence/question ID 分别唯一；objective/context 对、mapping 三元组、question/competency 对和 question difficulty 记录也禁止重复。一个 objective 可映射多个不同 canonical IDs。
- 同时检查 evidence 是否真正指向该 objective、context、competency、scope，而不只检查某个 ID 是否存在。
- Schema 禁止额外字段，避免把旧 difficulty 或 curriculum identity 字段静默混入新对象。

## Evidence authority 与排除语义

Authority 是来源分类，不是分数，也不执行自动排序覆盖：

- official syllabus / specification note → `official_requirement`
- official teacher guide → `official_clarification`
- official past paper / mark scheme → `official_assessment`
- official or endorsed textbook → `official_or_endorsed_textbook`
- third-party textbook → `third_party_material`
- other → `unclassified`

Validator 检查 source type 与 authority 相符；不能给 third-party textbook 换上 official requirement 标签。Synthetic evidence 的这些分类只是模拟相应来源类别，它的 provenance 始终保留 synthetic 标记。

`excluded_applications` 不接受裸字符串。每条排除声明必须有 application、rationale、evidence IDs 和 approved review status。保守原型规则要求至少一个相同 objective/context/competency/scope/application 的证据满足：

1. `explicit_exclusion=true`，表示来源明确作出了排除声明；
2. `observation_status=observed` 且 `evidence_role=supports`；
3. evidence 已 reviewed/approved；
4. 来源为 official syllabus、specification note 或 teacher guide。

仅有过去试题未出现、textbook 未收录或支持性例题，都不能通过这个规则。明确排除仍可在有充分独立证据时与一条 not_observed 记录共存；规则禁止的是从“未观察到”推出排除，而不是禁止保存有依据的排除。

该规则是最低形式校验，不是学术真实性认证。程序不能判断自由文本是否准确概括了原文，也不能用一个 approved 字段证明真实人员已授权。真实生产中必须由可信的人审流程提供批准。支持/矛盾/含糊的证据可以同时存在，v0.2 不实现冲突裁决或 scoring。

## 三个 prototype 案例

### 真实 Edexcel F2.8E / H2.8B

从 `topic2_foundation_parsed.json` 和 `topic2_higher_parsed.json` 读取：

- `EDX-4MA1-F-2.8-E` 属于 Foundation context；scope 保留 `Simple linear inequalities`。
- `EDX-4MA1-H-2.8-B` 属于 Higher context；scope 保留 `Harder examples`。
- 二者都引用 `CAN-ALG-INEQ-REGION-INTERPRET`，名称、description、domain 直接来自 promoted graph。
- Scope description、constraints、review status 来自已存在 scope JSON；不复制其中的旧 `difficulty_level`。
- Mapping 的既有 approved 状态仅作来源复现，并链接 `REV-4MA1-T2-INEQ-REGION-001`，不创建新的决策。
- 新加的四条 v0.2 evidence annotation 使用真实 official wording 原文，分别支持 mapping、解释 scope；它们仍为 pending，未假装得到额外人工批准。

因此 approved mapping 引用 pending evidence annotation 是有意的：mapping 的授权来自既有 human decision，新增 evidence 注解本身没有新授权。此 prototype 不是生产审批状态机。

### Synthetic 跨阶段向量案例

两个不同的 synthetic boards / qualifications / stages 共用 `CAN-MATH-VECTOR-ADD`：

- IGCSE-like context：2D、numeric components、direct calculations。
- A-Level-like context：2D/3D、algebraic components、multi-step applications。

这些不是任何真实 exam board syllabus 的声明。Tier/pathway 为空。两个 scope 和两个 pending mappings 不产生重复 canonical skills。

两条 synthetic question references 刻意处在**同一个 context、同一个技能**下，预测难度分别为 0.25 和 0.75。后者另有模拟观察值 0.6、模拟 sample size 40，用来验证字段约束；它们不是学生数据或实测结论。Question content、评分、题库、校准引擎均未实现。

### Synthetic 模糊矩阵案例

Official-like wording 为 “Understand basic operations on matrices.”，只存在于明确标记的 fixture。

- syllabus-like evidence：ambiguous。
- past-paper-like sample：addition、subtraction、scalar multiplication、matrix multiplication observed，形成四条 pending candidate mappings，relationship 为 broader（官方式 broad objective 相对单个 competency 更宽）。
- textbook-like addition example：third-party supporting evidence，不升级 authority。
- inverse：not_observed；保留候选 competency 和 unresolved scope，**没有 mapping，也没有 exclusion**。

即使四项在样本中 observed，其 official coverage 和边界仍有 unresolved 说明。出现例题不等于已经穷尽 syllabus，也不自动批准 mapping。

## v0.1 → v0.2 compatibility

**CanonicalLearningObjective → CanonicalCompetency**

ID/domain/name/description/status 的职责仍然正确，原样复用真实案例。v0.2 新增 provenance；不重新设计现有 ID，也不往 identity 塞 context。跨课程是否真是同一技能仍需人类判断，字段分离不能自动保证文字语义完全独立。

**OfficialToCanonicalMapping → OfficialCompetencyMapping**

保留 source ID、canonical ID、relationship、confidence、mapping method、review status，增加 context ID 和 evidence references。Mapping confidence 表示关联判断的信心；evidence confidence 表示观察/解释的信心，二者语义不同，不互相覆盖。Reasoning/observation 归 evidence；reviewer notes 和 approved metadata 仍在 decision history，不重复存入 mapping，仅引用 decision ID。

v0.1 已用 mapping pair 表示关系，并未从根本上禁止一个 objective 对多个 competencies；v0.2 明确通过 `(official_source_id, context_id, canonical_id)` 唯一三元组保留这一能力。

**CanonicalScopeMetadata → Context + Scope**

- `tier_source` 是要求出处：进入 context 的 tier，以及 objective 与来源 context 的关联。
- `tier_applicability` 是适用性，不是出处，更不是 difficulty。未来应将适用目标解析为 context IDs，必要时为目标 context 建立经证据与人审支持的 scope 关系。不能为每个适用 tier 伪造一个不存在的 official source ID。
- `scope_description`、`constraints` 进入 CurriculumScope。
- `review_status` 保留范围声明的审核状态；`metadata_method` 的生成方式将来应落在 evidence/provenance 或相应 review event，当前真实 prototype 通过 source reference 保留可追溯性，不新造方法字段。
- 本次两个真实 region scope 的 applicability 均仅为自身 tier，所以不需要引入额外适用关系模型。Foundation 2.4A 的跨 tier applicability 是未来迁移必须人工审查的真实例子，本次没有迁移它。

**CanonicalReviewDecision 与 Human Review Decision Log**

AI proposal 不等于批准；subject domain 必须来自人工决策；相同 ID 相同内容跳过、相同 ID 内容冲突报错；历史不能静默删除；先完整校验再 atomic write。这些原则全部继续有效。

v0.2 没有另造一个 decision schema 或 supersession system。将来 evidence/context/scope 的审核对象和 ID 引用方式需要扩展，但不能直接编辑旧 decision 以适应新 schema。当前日志仍是单写入者文件机制，不是并发写入系统。

**Promotion / deterministic rebuild**

保留 bootstrap baseline + 完整人审历史 → 确定性 approved snapshot；不从 previous promoted graph 增量 mutation；promotion 不作学术判断。当前 v0.2 builder 只是构造展示语义的 prototype，不能称作 v0.2 promotion engine。它读取 v0.1 promoted snapshot 来引用已批准结果，不回写，也不取代 v0.1 的 rebuild source of truth。

**仍然正确的 v0.1 设计**

官方文字不可变、objective boundary、canonical 与 scope 分离、AI pending、人审授权、append-safe history、promotion 与学术判断分离、引用/重复安全校验，均应保留。

**Edexcel-specific 的 prototype 限制**

Curriculum schema 固定 board/qualification/specification/tier 枚举，`CAN-ALG-` prompt 规则、Topic 2 固定文件和测试 objective 集合，以及 frontend 固定 Topic 2 view adapter，都是当前局部原型选择，不应成为 universal model 规则。本任务仅检查，未修改这些文件。

**未来需要迁移，但本次没有迁移**

Context/version 注册、跨 tier applicability、evidence provenance、review decision 目标扩展、question measurement 协议、消费者 adapter 的升级都需有计划的迁移。现有 graph、official IDs、audit history、frontend 继续使用 v0.1。

## 验证范围与实测结果

新增 artifact：5 contexts、7 competencies、5 objective references、9 scopes、13 evidence records、8 mappings、2 questions、2 question mappings、2 difficulty records。真实内容只涉及指定的两条 Edexcel objective；其他概念验证为 synthetic。

v0.2 校验包含唯一性、所有引用、相同目标一致性、source/authority 合法值、review statuses、difficulty 范围及采样约束、synthetic 标记、真实来源校验和 exclusion 最低证据要求。通过表示结构与声明的 provenance 一致，不表示新学术内容已被正式批准。

测试覆盖跨 context/stage 复用、不同 scope、课程部分重叠、tier 与 identity 分离、question difficulty 分离、support/clarify/ambiguous/insufficient/not_observed、显式排除与教材不能覆盖 syllabus、多个 mappings、错误引用、重复、synthetic 伪装和真实 wording/context 一致性。Builder 二次构造必须与保存 artifact 逻辑相同。

回归基线固定了 52 个既有 Python、output JSON、frontend 源码/配置/文档文件的 SHA-256，不读取 `.env`、`.venv` 或依赖目录。后续若有授权的 v0.1 修改，应明确更新这个测试基线，不要自动刷新以掩盖变化。Frontend build 产生的缓存/构建目录不属于源码不变性比较。

本次已有回归：

- v0.2：4 个新增 Python 文件编译通过，33 项测试通过，独立 validator 为 0 errors。
- Human Review Decision Log：11 项通过。
- Promoted Canonical Validator：41 official、10 canonical、13 mappings、13 mapped、28 unmapped；0 errors、1 warning（28 unmapped）。
- Scope Metadata Validator：5 scope records，0 errors、0 warnings。它读取 bootstrap baseline，因此报告 9 canonical / 12 mapping pairs，与 promoted graph 的 10 / 13 不同，属于现有行为，不是 v0.2 回归。
- Frontend：使用现有依赖完成 `npm run build`，TypeScript 和静态生成通过；未 install，未修改前端源码、配置或数据。

## Q1–Q10

1. **Canonical 是否 curriculum-independent？** 字段与引用结构是；没有 board/qualification/stage/tier/difficulty。自由文本中的学术身份仍由专家把关，程序不做词语黑名单式 ontology 判断。
2. **同一 skill 能否跨 IGCSE/A-Level 等阶段？** 可以，两个 synthetic vector contexts 共用同一个 canonical ID。
3. **两个 syllabus 能否部分重叠？** 可以，各 context 有独立 mapping 集合，可共享部分 IDs 并各自保留其他 IDs；另有隔离测试验证。
4. **Scope 差异是否无需新 canonical skill？** 是，真实 region 与 synthetic vector 均已验证。
5. **Foundation/Higher 是否与 difficulty 分离？** 在 v0.2 是；它们只属于 context。v0.1 旧 JSON 的遗留字段没有被改写。
6. **Past paper/textbook 是否可以作 evidence，而非 curriculum truth？** 可以。来源分类保留、映射保持 pending，不实现自动覆盖或自动批准。
7. **NOT OBSERVED 与 EXCLUDED 是否严格区分？** 是。前者是 observation status；后者是必须有独立、明确、reviewed official evidence 的范围声明。
8. **Broad objective 能否映射多个 competencies？** 可以，矩阵 fixture 有四条不同 canonical mappings。
9. **QuestionDifficulty 是否独立于 curriculum tier？** 是。只关联 question，并限制为数值任务尺度；同一 context/skill 的两个 tasks 可有不同难度。
10. **应保留哪些 Human Review / Promotion 原则？** AI pending、人工完整批准、domain 来源治理、不可静默改写的审计历史、冲突拒绝、完整历史重建、promotion 不作学术判断、正式 snapshot 与 proposal 分离。

## Issues / 需要人工决定的开放问题

- 现有 scope JSON 的 5 条记录仍带 `difficulty_level: unspecified`，但当前 CanonicalScopeMetadata 已无此字段。v0.2 不复制它；旧文件不修改。
- 已有 graph 顶层 `prototype` 标签仍为 Topic 2.6，尽管内容更广。本次不修正它。
- 真实 curriculum version、educational stage 不在 parsed source 中，保持 null。应人工确认真实版本与身份分配规则，不能自动拿 qualification code 代替版本。
- 各课程 stage 的统一命名、技能粒度、跨 board 技能等价性、何时认定新 competency，应由学术架构决定，不能靠 tier 或名称匹配自动定论。
- Context 的 source 与 applicability 应怎样关联、同一 official requirement 在多个 pathway/tier 的继承方式，需在真实多课程样本上审查后设计。
- Teacher guide 是否足以支持某类排除、什么算明确排除、矛盾官方来源如何裁决，都需要治理政策。当前 validator 规则只是保守原型边界，不是最终权威裁决标准。
- Question difficulty 的实测定义、目标人群、量表、测量时间、校准方案及版本历史尚未确定。当前每题最多一条测量记录，0–1 仅展示概念分离；不应据此比较课程或学生群体。
- Synthetic 标记和本地来源核验不是数字签名或生产认证。真正授权仍需接入可信人审系统，不能把任意 JSON 的 approved 字段当作真实人类授权。
- v0.2 validator 仅登记当前本地真实来源，未实现任意 board 的导入器、真实 past papers、Question Bank、API、数据库、UI 或 production migration。
