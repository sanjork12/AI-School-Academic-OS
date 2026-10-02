# P1B — Human Review Bundle + Trusted Publication

## 审核包为何存在

P0 正确地管理细粒度对象的不可变版本和审核，但操作员应先判断一个完整学术解释。Review Bundle 将题意、概念、能力、任务条件、证据、来源状态和阻断原因放在一起，底层仍逐对象使用 P0 的审核、依赖摘要和发布门。没有 bundle_approved 字段，也没有第二套审批表。

`academic_os/review_bundles.py` 生成 UI 中立的结构化视图；`review_rendering.py` 只负责终端文字展示。默认先展示学术含义，`--json` / `--details` 提供技术信息。展示、保存 ticket、报告和数据库初始化均不产生决定。

## 两种不同的人工工作

Source Verification 核对来源真实身份、版本、页码、范围和抽取文本，使用现有 `Service.review(..., action='verify'|'reject')`。`review-sources` 按 Question Paper、Mark Scheme、Specification 展示源文件元数据和 locator。完整性通过只说明字节/抽取一致，不能证明身份或学术解释正确。

Academic Review 判断 Concept、Competency、Task Condition 和映射是否恰当。操作员使用 `review-bundle` 查看并保存 ticket，再明确执行 `decide-bundle ... approve|reject`。审批包要求其所用来源与定位已核验且仍一致；来源核验本身不批准学术意义。低层 P0 单对象 API 保持原有兼容行为，发布门始终同时检查来源与学术批准。

四个学术包为：

- `BUNDLE-Q2-A`：Mean；primary Calculate the mean；From summary statistics。
- `BUNDLE-Q2-B`：Standard deviation；primary Calculate standard deviation；复用同一 From summary statistics。
- `BUNDLE-Q2-C-PRIMARY`：Standard deviation、Variation / spread；primary Interpret measures of variation；Compare variation using standard deviation。
- `BUNDLE-Q2-C-SECONDARY-CANDIDATE`：secondary Make contextual inferences using statistical evidence；在 Q2-CORE 中是可选探索，不是已批准的 Gold Standard。

包展示有限长度题干预览，指向现有 parsed records 的字符范围、原页链接、证据及解析警告，不复制长篇 PDF 正文。原有公式抽取问题和“较大标准差不保证更快个体”的解释限制仍需操作员审查。

## 显式发布范围：Required 与 Optional

`academic_os/publication.py` 中的不可变 `PublicationTarget` 声明 required_roots 和 optional_roots，并有内容摘要版本。

- `Q2-CORE`：required_roots 为 a、b、c-primary 的三条 mapping；optional_roots 为 c-secondary mapping。
- `Q2-WITH-SECONDARY`：四条 mapping 全部 required。因此同一个 secondary 在此目标下仍会阻断发布，除非其完整依赖已批准。

**没有按 role 过滤信任检查。** required_roots 交给原有 P0 `manifest` 计算完整传递闭包，包括反向发现的相关 evidence。optional 候选集合为 optional 闭包减 required 闭包。required 总是优先；如果某个 required 对象实际引用了 secondary，它立刻成为 required，不能被 optional 标签排除。

P1B.2 修正后，真实 Q2 的核心闭包为 43 个对象，另外 8 个仅服务于可选解释：Extreme values concept、secondary competency、mapping、3 条 concept links、2 条 evidence。原有 LINK-VARIATION-INTERPRET-EXTREMES 保留在历史库中，但不再被当前映射引用。共享概念、Task Condition 和解析结果仍属于 required。已有 P0 `check` 默认四条根的行为保留；P1B 必须明确选择 `--target Q2-CORE`。

发布单元选择**整题 Q2 的三个核心解释**：只批准 a 还不能发布该目标。一次目标发布只创建一个包含完整 required 闭包的快照。这个边界直接复用 P0 的 root selection 和单事务 publish，避免产生一个标为“Q2 核心”、实际上缺 b/c 的结果。低层 `--root` 是旧有自定义范围接口，不代表 Q2-CORE；服务拒绝把缩小的根集合冒充注册的 Q2-CORE 策略。

## 审批、拒绝、修改与原子性

Approve 对包的 required 学术对象调用现有 `Service.review`，不核验 source/locator，也不操作 optional-only 对象。当前版本和完整依赖已有有效 approve 时复用原决定，不创建重复审核。因此批准 a 的共享 Task Condition 后，b 会复用；b 自己的 mapping 仍须明确批准。

Reject 只拒绝包的解释根 mapping。拒绝一个解释不等于拒绝所有共享定义，尤其不能因为拒绝可选解释而撤回 primary 的共享概念。若要拒绝某个具体概念/条件或撤回已有决定，使用现有单对象 review 命令。

Modify 使用现有 `Service.stage(items, expected_heads, request_id)` 追加新候选版本，不原地修改；review/revoke/revise/supersede 语义保留。修改后相关审批 stale，相关快照按 P0 策略阻断读取。P1B 不实现一个自动修改或替人修正学术内容的按钮。

包决策有一个外层 IMMEDIATE 事务；每次现有 Service.review 在 SQLite SAVEPOINT 内执行。最后的包请求凭据与所有子审核在同一事务提交。任何错误——包括最后写幂等凭据失败——回滚整个包，包括审核头、子请求与快照阻断事件。

SQLite schema 仍为 migration 1，不增加审批表或持久化 bundle 状态。包收据存于既有 requests：保存操作员、时间、原因、reviewed ticket、创建的决定 ID 和复用的决定 ID，仅供审计，发布从不依赖该收据中的“包状态”。子审核保留对象版本、依赖清单、操作员、时间、决定、理由和 supersedes，理由也注明 bundle/request。本机 OS 操作员和 DB 文件权限仍是信任边界；没有新增 web auth 或 RBAC。

## Ticket、stale 与并发

包输出 review_ticket，包含包定义版本、required 对象版本和当前审核头，加确定性摘要。它是乐观并发检查凭据，不是认证签名。操作员提交的是刚才实际审阅的 ticket，而不是让程序悄悄读取新版本批准。

内容、相关证据闭包或审核头改变时，旧 ticket 失败，错误列出 expected/current 对象版本或决定 ID。共享对象在别处新获批准也属于审核头变化：需要刷新查看该包，再保存新 ticket；系统不会自动替操作员接受一个新状态。optional-only 变更不会使无关 primary ticket 失效。

同一个 request ID、相同 ticket/action/reviewer/reason 重试返回原收据，不重复写决定。相同 ID 不同请求报冲突。并发 approve/reject 中只有一个能提交，另一个明确失败。

## 正式快照与读取

目标发布复用 P0 的 schema、来源、locator、学术审批、版本、冲突和撤回检查。发布结果包含 required 对象、版本、有效决定，以及确定性的 `semantic_units`：question part、概念、能力及其角色、任务条件、parsed reference、evidence references。

pending secondary 及其独有的关系/证据不在 snapshot.objects、versions 或 semantic_units 中。publication_target 元数据会列出策略的 optional_roots，以说明排除规则；该声明不是 optional 内容或批准。策略定义及版本写入快照哈希，后续程序配置不会悄悄改变已有快照所代表的根集合。

同一目标、同一版本及有效审核重复发布得到相同快照 ID。正式读取只能走 `Service.snapshot`；读取时重新检查当前 required 闭包与审核。撤回、必需内容改变或后来出现冲突证据会拒绝读取。optional-only 的拒绝或修改不影响无依赖关系的 core 快照。离线 JSON 仍不能自动知晓后续撤回。

## condition 与 task_condition 审计

实际读取了四个当前记录，它们是不同语义层，不是通用发布谓词：

- `condition:COND-SUMMARY`：**Q2 的具体给定事实**，包含 coach A、n=120、sum x=6612、sum x²=364902、单位和公式抽取警告；有 question_id=Q2。
- `condition:COND-COMPARE`：**Q2 的具体比较场景**，包含 coach B 的人数、均值、SD、最快跑者人数相等，以及评分跟进说明；有 question_id=Q2。
- `task_condition:TC-SUMMARY-STATISTICS`：**可复用任务形式** From summary statistics，不携带该题数值或 question_id。
- `task_condition:TC-COMPARE-VARIATION-SD`：**可复用任务形式** Compare variation using standard deviation，不把教练/跑者写进 canonical identity。

不变量：具体题目事实留在 condition；跨题共享的评估形式留在 task_condition；课程要求范围留在 scope；信任条件由发布策略与 P0 gate 表达。P1B 不做危险合并、迁移或删除。

## 真实 Q2 操作员流程

以下写入命令仅供操作员实际完成审阅后执行；本轮自动化没有对真实库执行 verify、approve、reject 或 publish。

先查看来源和原页：

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 review-sources
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 review-sources --details
```

### P1B.1 来源核验票据流程

三个固定来源包：`SOURCE-BUNDLE-MS-Q2`（source:MS 和 MS-Q2-a/b/c）、`SOURCE-BUNDLE-QP-Q2`（source:QP 和 QP-Q2、QP-Q2-a/b/c）、`SOURCE-BUNDLE-SPEC-2.3`（source:SPEC 和 SPEC-2.3）。包定义只组织现有对象，不增加信任表，不改学术模型。

1. 用 `review-source` 查看身份依据、课程/版本、文件、完整性、定位摘要、原页链接及版本状态。
2. 在 PDF 阅读器打开输出的原页链接，逐项核对原件身份、页码、范围、抽取文本与摘要；完整性通过不等于身份正确。完整抽取文本可用既有 `inspect locator:QP-Q2-a` 查看，无需手工构造版本参数。
3. 保存本次审阅的票据，并对照其版本完成检查。若保存前后版本有变化，重新检查该版本；不要把后来生成的票据代替原先审阅版本。
4. 完成检查后，明确执行 verify 或 reject，填写真实理由和唯一请求 ID。
5. 重新运行 `review-sources`，核对该包显示 VERIFIED。
6. 三个来源包全部核验后，继续下方 Academic Review Bundle 流程。

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 review-source SOURCE-BUNDLE-QP-Q2
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 review-source SOURCE-BUNDLE-QP-Q2 --save-ticket var/review_qp.ticket
# 以下仅供人工完成核验后执行；开发和自动化测试没有在真实库执行：
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 decide-source SOURCE-BUNDLE-QP-Q2 verify `
  --ticket var/review_qp.ticket --reason '填写实际核验依据' --request-id operator-source-qp-001
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 review-sources
```

MS 和 SPEC 使用各自包 ID、独立票据文件和请求 ID，逐包实际审阅。拒绝时将动作改为 `reject`；**来源包 reject 拒绝来源和包内全部 locator**，与学术包只拒绝解释根的范围不同。需要只拒绝某个片段时，原有单对象 P0 接口仍可用。

界面明确显示：**Source verification does not approve academic interpretation.** 来源全部 VERIFIED 而学术未批准时，`check --target Q2-CORE` 仍阻断发布。

票据复用 P1B `guard` / `require_current_ticket`：固定包定义摘要、来源及 locator 的完整依赖版本和当前决定头。版本或审核头变化会报 stale/conflict，列出 expected/current；文件字节变化即使没有创建新版本，也被核验前的完整性检查拒绝。票据由排他创建保存，不覆盖旧文件；摘要不是签名或身份认证，不能防御拥有本机写权限的恶意操作员。

`Service.review_source_bundle` 使用一个 IMMEDIATE 外层事务，按 source 在先、locator 在后的顺序调用原有 P0 `Service.review`；子审核仍使用 SAVEPOINT。任何失败回滚全部子记录、审核头、幂等收据和快照阻断事件。已有有效 verify 被复用；原请求完全相同的重试返回原收据，相同 ID 不同内容报冲突。换新 ID、用新票据确认已核验包，只新增包收据，不重复创建对象决定。拒绝或版本变化仍通过原有发布门和快照状态检查阻断使用。

CLI 操作员身份仍取自 `local-os:<当前账户>`。信任边界仍是本机 OS 账户和 SQLite 写权限，没有生产认证。未来 API 可直接调用 `review_source` 和 `review_source_bundle`；必须另行提供可信身份认证，不能把候选 JSON 的 reviewer/verified 字段当凭据。

新增回归命令（所有决定都在临时库和复制的 PDF 上）：

```powershell
python -X utf8 -m unittest tests_p0.test_source_bundles -v
python -X utf8 scripts/demo_p1b1_temporary.py
```

临时演示复制三份原件、登记候选，实际调用来源 CLI 保存票据并核验，再执行测试学术审批及发布。脚本没有 `--db` 参数，只创建和清理临时库；CLI 收据的账户来自本机，理由和请求 ID 明确标记 TEST ONLY。输出 `output/p1b1_source_review/temporary-demo.json` 仅为测试证据。

然后按学术包查看与决定：

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 review-bundles
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 review-bundle BUNDLE-Q2-A --save-ticket q2-a-ticket.json
# 审阅完成后由操作员明确执行 approve，或将动作替换为 reject：
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 decide-bundle BUNDLE-Q2-A approve `
  --ticket q2-a-ticket.json --reason '填写实际学术判断依据' --request-id operator-q2-a-001
```

按相同步骤处理 BUNDLE-Q2-B、BUNDLE-Q2-C-PRIMARY；每次决定后再查看下一包，识别已经批准的共享对象。票据文件排他创建，不覆盖旧审阅记录；刷新时用新文件名。BUNDLE-Q2-C-SECONDARY-CANDIDATE 可以保持 pending，不执行任何动作。

检查阻断；只有操作员决定满足条件后才发布并读取：

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 check --target Q2-CORE
# 下两步本轮没有在真实库执行：
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 publish --target Q2-CORE --output output/p1b_snapshots
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 snapshot <返回的快照ID>
```

check 被阻断退出 2；不合法、过期或冲突写入退出 1；只读展示退出 0 不代表批准。

## 隔离验收与真实库保护

```powershell
python -X utf8 scripts/demo_p1b_temporary.py
python -X utf8 -m unittest tests_p0.test_review_bundles
python -X utf8 -m unittest discover -p 'test_*.py'
```

临时演示无 `--db` 参数，不打开真实库。它复制已有三份原件到临时目录，通过 Service.stage 建立临时 Q2 数据，使用 TEST-ONLY 身份验证和审核；报告注明这是测试决定，临时库结束后删除。它证明：

1. 初始：source_verified=false、human_approved=false、publishable=false。
2. 仅来源核验：true、false、false。
3. 批准三个 core 包：true、true、true。
4. 发布并经 Service.snapshot 读取成功，secondary 仍 pending 且不在可信对象中。

`output/p1b_review/` 提供 acceptance.json、q2-review-bundles.json、source-review-bundles.json、temporary-publication-test.json 与测试日志。真实库应保持 0 条审核、0 个快照；本轮还比较整个 SQLite 文件 SHA 和全部既有表，确认没有改写候选历史或信任状态。

## 已存在的历史保护错误

基线实际为 211 项：210 通过、0 failure、1 error、0 skipped。

错误来自 `test_academic_knowledge_v03.V03Tests.test_preserved_project_files`，读取 `output/academic_knowledge_v03/stable_baseline_sha256.json` 中的保护清单。清单要求根目录文件 `AI_Academic_Operating_System_Brainstorm_CN.pptx`，SHA-256 为 `a267fdd5e503290d5a21ede8d341f38a999d27637e67bfcf991cb5cf6d7aa89f`。

这是一项受保护的历史项目演示材料，当前 Q2 的三份正式来源均为 PDF，发布闭包没有依赖该 PPT。当前工作区没有同名文件；已有的教学演示 PPT 是不同文件、不同哈希，不能代替。仓库中未找到可说明其删除/移动经过的记录或同名备份，**实际缺失原因无法从现有证据确定**，不能断言是本轮代码造成。

最小正确修复是从原始备份恢复同一文件并核对既定哈希。本轮不伪造、不跳过、不修改清单；最终报告将此仓库历史完整性错误与 P1B 功能测试结果分开。

## 限制与下一步

本轮仅支持已配置的 Q2 审核包与两个显式发布目标，不是通用工作流引擎。没有 Q4、ontology 扩张、Learning Specification、学生模型、难度、生成器、前端改动或模型调用。共享对象审批采用严格 CAS，版本/审核头变化须重新查看；大包逐对象校验偏保守，尚未做性能缓存。

下一步是操作员实际逐项核验三个来源族，然后审阅 a、b、c-primary 核心解释，保留 secondary 待定，最后通过 Q2-CORE 发布门。恢复历史 PPT 可独立处理，不替代学术审核。


## P1B.2：Q2(c) canonical 概念边界修正

首次人工审阅指出，评分方案中的 Extreme values 推理属于 Q2(c) 的具体问题情境，不能据此断言 Interpret measures of variation 总是依赖 Extreme values。主解释现在只引用 Standard deviation 和 Variation / spread；primary competency 和 Compare variation using standard deviation 条件不变。

`academic_os.examples.q2_semantics.build_boundary_correction(graph)` 生成只包含该主映射的 staging/CAS 计划。已有 `Service.stage` 追加不可变版本；不删除历史链接，不改审核记录。生成新候选的 `build_plan` 同步采用正确边界。Extreme values 仍保留在评分证据、原定位文本和主映射的题目解释备注中；secondary 的全部候选关系保持原样、继续 pending。

真实库修订只新增一个版本（72 → 73），对象头数量仍为 52；32 条人工决定逐条保留，快照仍为 0。Q2(a)、Q2(b) 保持批准，Q2(c) primary 仍未批准。来源核验 true，学术批准 false，发布 false。历史链接作为不再使用的候选保留；是否进一步处置它属于未来独立审核，本次没有替操作员拒绝或撤回。

原 `var/review_q2c_primary.ticket` 文件保持原样，因主映射版本与依赖闭包改变而失效。已在隔离的真实库副本中尝试提交旧票据，收到包含 expected/current 版本的 stale/conflict 错误，未新增审核记录。操作员应重新检查修正后的解释，再另存新票据：

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 review-bundle BUNDLE-Q2-C-PRIMARY --save-ticket var/review_q2c_primary_v2.ticket
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 check --target Q2-CORE
```

上述查看不产生批准。修订计划、前后状态和测试证据位于 `output/p1b2_boundary/`。原有 P1A/P1B 验收输出作为历史记录保留，不覆盖。新增回归：`python -X utf8 -m unittest tests_p0.test_q2c_boundary -v`。
