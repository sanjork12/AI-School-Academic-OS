# P0：可信来源、版本化审核与安全发布

本模块提供可被 CLI、后续 API 和解析器复用的 `academic_os.service.Service`。原有 v0.1/v0.2/v0.3 示例、输出、pinned hashes 和旧审核日志不迁移、不重写。旧 promotion 脚本不属于 P0 发布路径；其 JSON 中的审批不会被导入为可信记录。

## 运行与真实样例

在 `D:\AI-School-Academic-OS` 运行，Python 3.10+，依赖见 `requirements-p0.txt`；本次环境已具备依赖。无模型调用。

```powershell
python -X utf8 scripts/demo_p0_q2.py
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 pending
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 inspect part_mapping:MAP-Q2-a-MEAN-CALC
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 check
```

演示通过实际 CLI 执行初始化、3 份来源登记、8 个定位抽取、35 个候选对象入库、证据查看和发布检查。默认真实样例检查退出码 **2**，表示正确阻断；演示不提交任何审核。再次运行同一导入请求幂等，不清空数据库。若需要独立复现，可指定新的 `--db var/p0_q2_fresh.sqlite3`。

证据和结果存入 `output/p0_acceptance/`。原件路径为 `output/academic_knowledge_v03/source_audit_20260919/sources/`：

- `9MA0-2025-31-QP.pdf`：PDF 第 4 页，Q2(a/b/c)，总和 6612、平方和 364902、n=120；B 组均值 55.1、标准差 3.6。
- `9MA0-2025-31-MS.pdf`：PDF 第 7 页，(a) 55.1，(b) 2.2，评分说明也接受样本标准差约 2.21；(c) 对教练 B 的情境判断及从 (b) 跟进评分说明。
- `9MA0-Specification-Issue4.pdf`：PDF 第 35 页、印刷页 31、Statistics 2.3，集中趋势和离散程度。这里记录的是可见章节标签，不制造 syllabus objective ID。

定位保存原始整页受控抽取文本、文本摘要、摘要哈希、文件版本、零基 `page_index`、标准化页面矩形和 `file:///...#page=N` 返回链接。CLI 的 `--page` 使用人类习惯的一基页码。PDF 公式抽取存在排版缺陷，原样保留，不偷偷修复为“官方正文”；查看原页是定位审核的一部分。

真实候选全部待审核。程序已完成文件登记、文本抽取和一致性检查；本轮对原页的检查没有写成人工凭据。来源身份、定位准确性、registry 定义、条件和映射都仍需操作员决定。Q2(c) 的较大标准差解释是评分方案的情境性推断，不能当作一般数学保证。CONTEXT-INFER 没有宣称已证明具体考纲对应；该课程关联仍 unresolved，未创建官方 objective 或已批准的 scope 关系。另三条映射的 2.3 scope 仍是候选。

## 操作员审核

CLI 仅信任本机 OS 操作员和数据库文件权限。审核者来自 `getpass.getuser()`，记录为 `local-os:<账户>`。这是本机信任边界，**没有生产认证、用户授权或防数据库管理员篡改能力**。候选 JSON 不能携带已批准/已核验状态或审批凭据；系统拒绝这些字段，不把它们转换为审核。

`inspect` 返回当前版本、依赖摘要、当前审核 ID、完整证据包及历史。操作员先查看实际 PDF 和证据，然后执行单个明确决定。以下代码只是操作说明，本轮没有运行审批：

```powershell
$db = 'var/p0_q2.sqlite3'
$item = python -X utf8 -m academic_os --db $db inspect source:QP | ConvertFrom-Json
# 完成身份/版本/来源检查后，填写真实检查理由，再单独执行：
python -X utf8 -m academic_os --db $db review source:QP verify `
  --expected-version $item.version --expected-dependencies $item.dependency_digest `
  --expected-decision none --request-id operator-source-QP-001 `
  --reason '请替换为操作员实际检查依据'
```

1. `verify` 用于 source、locator；先核验 source 身份，再核验 locator 原页、文字、区域和摘要。文件存在、SHA 一致仅说明登记内容一致，不说明身份真实或解释正确。
2. `approve` 用于 competency、mapping、evidence、context、condition、question/part 和 scope。P0 保守地要求所用非来源对象全部有有效人工批准。academic approval 与 source verification 分开。
3. `reject` 明确拒绝，`revise` 请求修订；二者立即阻断发布。修订内容通过 `stage` 产生新版本，旧决定保留。
4. `revoke` 撤回已有决定。`supersede --replacement-action approve|reject|revise|verify` 明确替代旧决定；`--expected-decision` 必须填写 inspect 返回的旧 ID。每次决定都记录 supersedes，不跳过已有节点。
5. 初次审核 `--expected-decision none`；以后使用实际当前 ID。版本、依赖或当前决定有变化时拒绝提交，操作员应重新查看，不覆盖别人的审核。

相同 request ID 和相同内容返回原结果；相同 ID 不同内容报冲突。若需全新决定，使用新 request ID。

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 check
# 只有 check 全部通过后，下列命令才会成功；真实样例目前会拒绝：
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 publish --output output/p0_snapshots
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 snapshot <实际快照ID>
```

`check` 成功退出 0、阻断退出 2；错误及被拒绝的写入退出 1。`snapshot` 对不可用快照退出 2 且不返回 payload。`publish --root kind:id` 可选择范围，默认四条 Q2 映射。不能通过缩小范围排除被选对象的真实依赖或针对它的冲突证据。

## 版本、依赖和发布契约

- 内容版本为归一化完整对象的 SHA-256，包含正文、定义、元数据和显式 `judgment_refs`，不是可变 ID 的摘要。source 另有实际文件字节 SHA-256，locator 绑定确切 source 内容版本。
- 映射闭包包括自身、competency 定义、证据、定位、来源、question/part、curriculum context，以及实际使用的 condition/scope。判断额外输入必须通过 `judgment_refs` 声明。新增指向该闭包对象的 evidence 也纳入依赖，防止未附到 evidence_ids 的冲突被遗漏。无关对象不会进入该审批摘要。
- 每个决定保存闭包的 `key → version` 清单与摘要。内容变化动态计算 `stale`，历史行不改写。撤回不要求篡改内容版本，但作为独立硬门阻断发布。
- staging 可保存 pending/draft 和已批准 mapping 引用尚未批准的 competency。正式发布要求 schema/引用有效、所有使用的来源和定位核验有效、registry 和所有学术对象批准有效、依赖未变化、无冲突/未解决 scope/撤回。confidence 不参与这些条件。
- `source_verified`、`human_approved`、`publishable` 独立返回。学术批准不能替代来源核验；来源核验也不能替代学术批准。
- 原始 staging 对象的 draft/pending 字段保持原样。正式快照由有效 journal 决定生成 approved/verified 状态，并写入对应决定 ID；每个对象另保留 `content_version` 指向不可变原候选版本。快照整体另有 SHA-256，因此不会把改过状态的投影冒充原内容版本。
- 相同对象版本和相同有效审核重复发布返回相同快照 ID；审核换版会产生不同审计身份。数据库内快照、版本、审核、请求凭据、阻断记录有 UPDATE/DELETE 禁止触发器。
- 撤回/替代审核/改变内容向快照状态注册表追加阻断事件，不改旧快照字节。正式读取还重算完整闭包和发布门，捕获后来新增的冲突证据、文件变化或审核变化。一旦记录阻断，恢复文件不会自动复活旧快照。
- 导出使用排他创建，不覆盖不同内容，并设只读属性。**所有消费者必须经 `Service.snapshot(id)` 检查当前可用性**；离线复制的 JSON 无法自动获知后续撤回，不是可绕过注册表的服务接口。本机管理员可改变文件权限，导出只读不等于操作系统级防篡改。文件检查是调用时检查，不是持续监控。

## 工程组织与兼容

- `academic_os/models.py`：继承有效 v0.3 SourceDocument、SourceLocator 和域模型，增加文件身份声明、定位文本及 P0 scope；候选输入严格校验。
- `academic_os/core.py`：纯依赖、审批有效性、发布规则，无存储/模型调用。
- `academic_os/sources.py`：登记、可重复页抽取、文件和文本一致性。
- `academic_os/compatibility.py`：复用现有 v0.3 `validate_document` 和 `ExternalTrust` 的引用/来源规则，可信数据来自 SQLite journal；不沿用旧 review digest 的依赖遗漏。
- `academic_os/storage.py`、`migrations/001_initial.sql`：SQLite 外键、初始化迁移、追加日志、事务和幂等凭据。写入使用 IMMEDIATE，迁移 EXCLUSIVE；显式 CAS 防止静默覆盖。
- `academic_os/service.py`：可复用应用服务。`cli.py` 仅做参数、操作员身份和输出适配。
- `academic_os/examples/q2.py`：真实数据适配器，导入模块不写文件或创建审批。不是发布器。
- `tests_p0/fixtures.py`：临时 PDF 与 TEST-ONLY 审核者；成功发布测试完全隔离于真实资料。

旧 v0.3 格式继续可读且其测试保留。P0 snapshot 是带版本、可信审核与投影状态的独立 envelope，不冒充旧单文件 prototype。P0 暂不支持概念 registry、嵌套 action classification、resource 条件等扩展；显式拒绝，不静默漏校验。

## 下一阶段边界

解析器输出 `Candidate(kind, payload, judgment_refs)` 列表，经 `Service.stage(items, expected_heads, request_id)` 入 staging；新对象 expected head 为 null，修改对象传旧版本。解析器只能产生候选，不接受其 reviewer/approved/verified。question parsing 应保留原文 locator，mapping 应显式声明参与判断的 scope/context/conditions，不能用 confidence 替代审核。

未来 API 的认证适配层负责可靠的 reviewer 身份和授权，再调用 `Service.review` 的版本/依赖/决定 CAS 接口。前端读取 `inspect` 和 `check`；正式内容读取必须调用 `snapshot`。学生系统、掌握度、完整题库、多模型、云部署不在本轮范围。

## 测试复现

```powershell
python -X utf8 -m unittest tests_p0.test_workflow
python -X utf8 -m unittest discover -p 'test_*.py'
```

基线 132 项；P0 新增结果与完整测试日志见 `output/p0_acceptance/acceptance.json` 和 `full-tests.log`。自动化成功路径只使用 TEST-ONLY fixtures；真实 Q2 无人工批准时必须阻断，测试不会修改真实来源或 pinned hashes。
