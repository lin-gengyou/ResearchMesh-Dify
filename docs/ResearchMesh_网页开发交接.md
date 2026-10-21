> 2026-10-21 更新：五份 DSL 已归档于 `../dify/` 并通过静态核对；交付导出为 22 连线，总计 121 连线。尚未进行目标账号导入运行验证。下文历史阶段记录中的“备份尚缺”和上传暂停描述已被本更新取代；远端上传状态以 GitHub 实际内容为准。

# 致网页开发同事：研织 ResearchMesh 网页开发交接书

日期：2026-10-21。产品名称：**研织 ResearchMesh——AI驱动的校园科研协作网络**。

你负责网页设计、开发和发布。我负责 Dify 业务流程及接口衔接，后续可继续回答你的接口、角色、状态和测试问题。项目研究包和产品功能介绍由项目负责人另外提供；本文件补充实际已经搭建的内容及接入边界。

五个 Dify 应用的当前发布版均已完成 Service API 实测。需求/能力/匹配为发布版本 #1，组队与约定、交付与贡献为 #3。所有测试身份、项目、经历和交付均为虚构数据。网页、真实身份、数据库与正式发布授权仍由网站后端实现。

源码整理与 GitHub 上传由我负责，不交给网页开发同事。已创建私有仓库 [lin-gengyou/ResearchMesh-Dify](https://github.com/lin-gengyou/ResearchMesh-Dify)，目前只有初始化 README，业务源码尚未上传。根据项目负责人最新要求，现暂停仓库上传，优先交接文档。完整 DSL 下载仍未成功取回，也由我继续负责，不将局部源码冒充完整可导入工作流。

使用方式：将本文、配套《ResearchMesh_Dify_源码与联调包.zip》、原研究包和产品功能介绍一起交给网页开发 agent。本文已经合并 API 与角色说明，可独立阅读；源码包用于运行参考适配器及查看完整虚构输入。网页开发先对接现有在线应用，不需要等待仓库上传或重建 Dify。真实密钥不在本文或附件中，部署时由项目负责人通过服务端私密配置提供。

## 1. 用户体验与 AI 的实际作用

用户只需讲述项目困难、经历和交付情况，AI 先整理出有来源的可编辑草稿；不要要求用户先把含糊想法填成完整专业需求，或自行编写 JSON。

| 环节 | AI 负责的工作 | 人和确定性代码负责的工作 |
| --- | --- | --- |
| 提出需求 | 理解困难，分开原文事实、建议和未知；含糊时给两个可选方向；整理任务、交付和关键追问 | 保留来源；负责人核对真正要发布的内容；检查执行条件与学习支持 |
| 介绍自己 | 从自然经历中提取本人动作、团队成果、独立/指导完成和学习兴趣 | 本人更正或确认使用范围；自述不升级为外部核验 |
| 寻找协作者 | 逐人逐任务判断经历关联、分项动作及引用；拟定自愿的小范围讨论建议 | 校验证据 ID、连续引用、任务范围与条件；未知不算已覆盖 |
| 周分工 | 原始演示入口可调用 AI 理解经历；正式版本化入口复用上游 AI 匹配矩阵 | 枚举组合、按人累计工时、保留无解原因，不把个人排名简单拼成团队 |
| 合作约定 | 根据选中分工起草条款；把自然语言修改意见整理成定位明确的改动 | 保留版本差异；每次换版重新分别确认；禁止超出本人任务或预算 |
| 交付与贡献 | 把提交说明对应到验收项，提取有原文支持的本人贡献候选 | 验收者决定通过/退回/争议；本人核对贡献；公开与验收分别授权 |

产品应让用户看到“AI 已帮我整理好，我只核对关键决定”。JSON 数据包和来源摘要由后端处理；普通页面显示卡片、可编辑字段、依据与操作按钮。原生 Dify Web App 是开发演示入口，部分会同时显示机器输出，不能直接当作最终用户界面。

## 2. 已建应用与运行边界

全部仍在原 Dify 账号的五个应用内，没有创建第六个或删除旧应用。应用 ID 和访问入口如下；开发演示页不等于最终产品网页。

| 服务 | 应用 ID | 访问入口 |
| --- | --- | --- |
| 需求理解与审核 | `e5e69010-0855-41c2-b58d-55f4e2c9a496` | [编排](https://cloud.dify.ai/app/e5e69010-0855-41c2-b58d-55f4e2c9a496/workflow) · [开发演示](https://udify.app/workflow/hF7B6DI2ET0sov6z) |
| 个人经历与能力草稿 | `e301e495-d5d9-45a3-9b0f-b8834e4e5a94` | [编排](https://cloud.dify.ai/app/e301e495-d5d9-45a3-9b0f-b8834e4e5a94/workflow) · [开发演示](https://udify.app/workflow/AWGIuaxS48uJUaAi) |
| 供需匹配与证据解释 | `15bb815e-221d-4e9e-a0de-957b95679a2e` | [编排](https://cloud.dify.ai/app/15bb815e-221d-4e9e-a0de-957b95679a2e/workflow) · [开发演示](https://udify.app/workflow/B75tUWiyg8I2h0aS) |
| 组队、周分工与合作约定 | `0400a63d-801e-4c48-a956-0938f3420608` | [编排](https://cloud.dify.ai/app/0400a63d-801e-4c48-a956-0938f3420608/workflow) · [开发演示](https://udify.app/workflow/IOaxC37VvHvh7YzT) |
| 交付验收与贡献记录 | `5f017ac1-8be1-4d76-921e-96c4bc273c5c` | [编排](https://cloud.dify.ai/app/5f017ac1-8be1-4d76-921e-96c4bc273c5c/workflow) · [开发演示](https://udify.app/workflow/nVexNpmxfmbxcb3F) |

| 服务 | 节点 / 连接 | Start 输入 | 常用成功输出 |
| --- | ---: | --- | --- |
| 需求理解与审核 | 20 / 23 | project_brief 必填；clarification_notes 可空 | exploration_card；或 review_card、need_review_record、need_matching_handoff |
| 个人经历与能力草稿 | 10 / 11 | experience | profile_card、profile_packet、profile_route、matching_evidence、revision_input |
| 匹配解释 | 13 / 13 | need_json、candidates_json | recommendation_card、decision_packet |
| 组队、周分工与约定 | 41 / 52 | need_json、candidates_json | matched_team_card、matched_team_packet；或约定各版本输出 |
| 交付验收与贡献 | 16 / 20 | agreement_json、submission_text | result、contribution_packet |

表中 `*_packet`、`*_handoff`、`*_json`、matching_evidence 通常是 **JSON 字符串**。解析 Dify 外层响应后，再按契约解析该字段一次；不要把字符串当对象，也不要对所有文本盲目反复 JSON.parse。

不同分支的输出字段并不统一。Dify succeeded 只表示流程执行完成，可能产出待补充、阻断、拒绝或无可行方案。必须按分支字段、route 和 packet.status 判断业务状态，不能见到 200 或 SUCCESS 就提示“匹配成功/合作成立/验收完成”。

全部 11 个 LLM 节点已改用账号现有 DeepSeek API 提供方下的 deepseek-v4-flash，温度 0、最大输出 8192、显式关闭思考；主匹配保留结构化输出。节点显示值不是费用承诺，tokens 不等于 Dify credits，Dify 显示成本 0 也不等于 DeepSeek 不收费。模型凭据在 Dify 提供方设置中维护。

## 3. 业务链及后端装配顺序

### 3.1 需求草稿 → 审核 → 当前需求

模糊描述进入方向探索：给 A/B 建议、少量关键问题，用户选择或补充后 AI 整理一轮草稿。选择方向不等于确认资源已就绪或需求已开放。完整叙述则进入执行条件、技能必要性、独立程度及指导支持检查，再由负责人审核。

审核出口 `need_matching_handoff` 的 route 是 `await_backend_confirmation`，不是可以直接发起匹配。其 reviewed_snapshot、source_workflow_run_id、source_draft_sha256 必须一起保留。runnable_matching_input=false、identity_verified=false 是实际边界，不能直接把标记改成 true 冒充鉴权。

后端按 `researchmesh_need_matching_step11/review_bridge.py` 的 `task_proposal` 生成可核对的任务预填项。再由负责人核对标准化条件：需求 ID/版本、负责人、标题、每周工时、开始日、有效期、场地、1–6 项任务。AI 已提取的完整任务动作不得被拆分时遗漏或静默截断；不确定日期应由负责人补一次，不能推导成虚假的精确日期。

`prepare_review_need` 要求 confirmation 和 current 同时绑定同一审核来源及规范化摘要。current 必须来自受保护数据库的最新记录；浏览器不能自行提供权威 current、actor_id、owner_confirmed。

正式匹配入口为 `need_json={module:"review_handoff",handoff,confirmation,current}`，candidates_json 是后端筛选出的本轮授权候选快照。Python 参考见 stage11；完整虚构输入见该目录 live_fixture.json。

### 3.2 本人经历 → 本轮匹配线索

能力应用保持一个自然语言必填框。本人可确认用于匹配讨论、更正、仅存私有。**更正框非空时，即使点确认也先进入 revision_requested，不能授权旧内容。** 网页的“按更正重整”应读取 revision_input，启动一次新运行，之后再次本人核对；当前 Dify 不会无限自动回环。

主要 profile_route：confirmed_matching_clues、revision_requested、private_draft、no_personal_claims、blocked。无有效线索分支返回 capability_card/capability_packet/capability_route；超时分支返回 profile_timeout_card/profile_timeout_packet。空状态保留原草稿，不生成虚构能力。

`candidate_from_confirmed_profile` 位于 stage7，接受实际 End 输出。后端明确选择当前快照中 1–3 条与本次需求相关的经历，装配参与者 ID、意愿、时间和场地。不得静默取前三条当作授权选择。

**该适配函数不是鉴权服务，也不证明客户端未伪造 profile。** 后端必须先验证登录者与档案归属、当前 route/授权状态、精确 profile/evidence 内容快照、选中证据 ID。来源 draft_hash 是原始能力草稿摘要，不是确认后的整个 profile_packet 的摘要，也不是数字签名。

确认后的自述保持 support_type=self_reported、task_scope_accepted=false；指导完成保持 guided。团队控制代码、兴趣等不得归到本人的已具备技能。source_span 按 Python Unicode 码点计数，前端不能直接当 UTF-16 下标，含 emoji 时可用 Array.from 或按引用定位。

### 3.3 匹配解释与有限探索

当前匹配支持最多 10 名候选、6 项任务，每人最多 3 条通过适配器选定的经历。先核对开放状态、授权可见性、意愿、场地、日期及工时，再做逐项模型评估。

relation=direct 只是 AI 判断的相关性；effective 才是严格校验后的任务覆盖。本人自述可能有关联，但仍为 unknown；只有符合引用、材料类型、本人确认、当前任务范围、独立程度及分项动作要求的材料才可能算直接覆盖。provided_excerpt 也只是提供的文本片段，并不代表系统实际浏览了原网页、执行了代码或验证真实性。

仅有自述或部分相关经历时可进入 exploration_candidates，提出自愿的 10–30 分钟短讨论或小样例想法。它不算必需项覆盖、不自动邀请、不承诺真实交付。等待意愿/时间确认时不能显示“已可开始”。不要把没有硬性覆盖的人从所有学习协作入口完全清空。

必需项指本轮任务必须完成，不代表所有技能都要求入门前掌握。skill_requirements、requirements_policy 和 learning_support 要保留，并在页面说明可以指导完成或边做边学的条件。

### 3.4 匹配结果 → 周分工

正式入口使用 stage12 `team_from_match`，need_json 封装 module=team_from_match、decision_packet、current、planning_confirmation；candidates_json 必须与匹配对应的候选快照一致。后端绑定 latest_matching_sha256、matching_candidates_sha256、planning_sha256；候选资料改变就重新匹配，不沿用旧矩阵。

planning 预填并核对 week_start（不早于需求开始日的周一）、每项 task_hours、weekly_task_budget、max_people、existing_member_ids。数值必须明确确认；不得把两周总预算 8 小时当作每周 8 小时，也不得把个人周空闲 6 小时自动分配给只有 4 小时的本人任务。

这一分支复用严格校验后的 AI 矩阵，直接做组合搜索，**零额外模型调用**。最多 3 人参与一个方案，每项任务一名主责，按人累计不超周可用工时。最多比较 3 个不被明显支配的组合；不支持复杂并行依赖、跨周自动排程或名额占用事务。

输出 matched_team_packet.status 可为 proposed、no_feasible_assignment、search_incomplete。无解应说明证据/工时/人数冲突，搜索不完整不能说成没有任何可能方案。正式网站使用这一版本化入口；旧直接 need/people 组队入口保留为开发演示，不能获得同等来源保证。

### 3.5 选中本人分工 → 合作约定

后端保存实际组队结果为 current.latest_team_sha256，使用 stage12 `agreement_from_team`，核对当前需求、匹配、周计划和分工摘要，并选择 plan_index 与 performer_id。仅提取该承担者本人的任务及累计工时，不能把其他成员任务、整项目周期或整项目预算复制过来。

调用组队应用既有 module=agreement 入口；candidates_json 仍需传字符串（例如 []）。AI 将自然验收想法整理成逐任务条款，区分原文、建议及未知；不会自动补报酬、退出方式或截止日期。已确认工作周与到期日是不同字段；到期未约定就显示“未约定”。

流程顺序：负责人确认 v1 → 承担者确认 v1；任一方提出修改后，AI 整理一轮修改并产生 v2，负责人和承担者都重新确认 v2。旧接受记录不沿用到新版本。当前只做一轮 AI 修改；仍需修改会保留为待协调，网页可以在明确业务规则下发起新一轮，不能自动无限收费循环。

任务 acceptance 用对应 task_id；公共 due/inputs/support/reward/withdrawal 必须 task_id=""、task_anchor=""。这个规则已修正提示词，严格校验保留。修改超出职责、引用不符或公共条款误挂任务时应 blocked，不要通过前端隐藏错误继续交付。

常用出口：v1 为 agreement_card/packet/route/json；v2 为 agreement_v2_card/packet/route/json。只有同版本双方接受且 route=ready 后，后端才能生成交付入口。其他分支包括负责人未接受、修改阻断、拒绝和超时，不能仅依赖输出字段存在判断合作成立。

### 3.6 约定 → 交付 → 私有贡献/公开草稿

由 stage13 `delivery_with_provenance` 对照后端 current，复核最新约定版本、双方角色、接受记录、条款 hash，以及当前需求、匹配、周计划、组队来源。通过后装配 agreement_json，用户只需填写 submission_text。

保留 source_context：need_id/version、source_review_run_id、source_draft_sha256、source_matching_sha256、planning_sha256、source_team_sha256、allocated_hours、time_window。它会进入 Dify 提交快照和最终 contribution_packet.agreement.source_context；格式有效不等于来源已经认证。

AI 生成验收辅助卡，验收者可 approve/revise/dispute。只有 approve 才进入贡献者本人核对。本人可 public_draft/private/revise；public_draft 只是同意生成待发布稿，还没有公开。贡献更正需复核，不能覆盖原提交和原验收记录后冒充已经双方确认。

result 为展示文案，contribution_packet 为机器结果。分别展示验收状态、本人贡献核对、公开意愿。即使验收通过也不会自动写入技能认证、发送消息或公开主页。当前 formal_state_update=false、identity_verified=false 反映 Dify 运行演示边界，网页必须实现自己的真实状态写入和授权流程。

## 4. 网页端需要实现的内容

建议页面顺序：需求工作台、个人经历工作台、匹配说明、周分工方案、合作约定、交付与贡献、用户主页/本人管理区。可以共用卡片与流程侧栏，不必把五个应用暴露成五套割裂入口。

| 页面/能力 | 必须呈现的内容 |
| --- | --- |
| 需求工作台 | 一句话起步、AI方向建议、少量关键追问、事实/建议/未知标签、负责人核对 |
| 个人经历 | 本人动作、归属、指导/独立程度、兴趣单列、更正与私有选项 |
| 匹配 | 逐项依据、缺口、学习支持、条件待确认、探索讨论入口，不展示虚假成功概率 |
| 周分工 | 明确工作周、按人/任务工时、方案差异、无解或搜索未完成状态 |
| 约定 | 当前版本、条款差异、本人任务范围、分别确认记录、修改和拒绝入口 |
| 交付 | 当前接受版、自然语言提交、逐项辅助核对、通过/退回/争议、本人贡献核对 |
| 用户主页 | 昵称/可选学校专业、具体经历、兴趣、合作意向、本人贡献；默认私有预览 |
| 本人管理 | 待处理人工环节、草稿、更正、私有记录、公开选择和撤回 |

主页参考在 stage8 `home_profile.py` 及《用户主页_内容与数据约定.md》。访客只拿服务端白名单投影，不能把私有全文发到浏览器再用 CSS 隐藏。匹配使用授权、经历确认、贡献公开草稿授权、最终主页发布是四种不同决定；贡献还有自己的精确内容 hash 授权。没有内容时显示真实空状态，不造数量、徽章、履历或能力分。

## 5. 服务端责任与并发

浏览器只能调用你的网站后端。Dify app key 留在服务端，Dify 的 user 使用稳定的会话/业务标识；真实角色权限由登录态决定，不能把 Dify user 当身份核验。

至少持久化以下关系：用户/档案归属、当前需求版本和快照、参与授权与证据选择、匹配快照、周计划及其确认、所选分工、约定版本/双方事件、提交版本、验收事件、贡献核对、公开记录，以及 Dify run 与当前人工节点映射。

每次提交人工选择、选方案或生成交付入口，都在事务中重读当前版本/授权/角色；若换版，返回明确的“内容已更新，请重新核对”，不覆盖别人的新状态。创建业务操作要有幂等键；网络断开后接回同一个 Dify run，禁止盲目重发创建工作流 POST。前端收到提交确认不等于工作流已完成。

Dify Human Input 的 form_token 是可执行操作的凭证，只存服务端，不能出现在公开仓库、日志、页面 URL 或发给不对应的用户。表单应按当前定义字段白名单提交并核对 action；服务端再确认这个登录人就是该节点对应角色。详见 API 文档。

当前 Python 模块提供契约检查与数据转换，不实现真实身份、数据库、持久化幂等、事务或消息队列。摘要只能发现内容不一致，不能防止一个任意客户端把内容和 hash 一起伪造。

## 6. 验证证据与实际限制

本包原有 7 组测试共 88 项通过；新增上游 API/权限/重放测试 8 项通过，共 96 项测试。能力到当前匹配另有 9 项断言通过，本地检查不新增模型调用。本次发布后实测：组队承接匹配 6 步/0 token；旧需求版本阻断 6 步/0 token；交付验收→本人私有贡献 13 步/1746 tokens；旧约定版本阻断 4 步/0 token。记录见 stage14 api_verification.json。上游当前发布版另实测：能力本人确认 8 步/1020 tokens；完整需求审核 13 步/4070 tokens；模糊需求选 A 后保留草稿 16 步/7441 tokens；本人自述到匹配探索 12 步/3142 tokens。上游本轮共 4 次运行、15673 tokens，人工暂停续接的累计 tokens 只计最终值，不重复相加。tokens 不代表账单或 credits。

前期真实 Dify 草稿运行已覆盖模糊需求方向探索、完整需求审核、本人更正和私有、匹配探索与直接覆盖、分工承接、约定 v2 重新确认、验收及贡献不同选择。没有做真实人员参与试用、真实文件/代码执行验收、24 小时自然等待超时、并发负载及生产安全测试，不能拿演示通过冒充这些测试通过。

完整当前 DSL 下载尚未取回。在线五应用保留完整配置；本包源码和节点拓扑不是完整可导入 DSL。若换账号或迁移，需要从 Dify 工作室各应用“导出 DSL”，清理环境值和提供方绑定，再在目标 Dify 配置模型和重新发布/联调；不能使用旧阶段 YAML 覆盖现有成果。

## 7. 实施顺序与验收

先接一个需求或经历页，用你的网站后端真正跑通启动、人工等待、提交、续接和结果持久化；再接其余主链。然后做跨用户角色权限、换版冲突、重复提交和断线恢复；之后做主页私有预览/逐条公开/撤回；最后统一视觉与发布。

交给你的页面开发不应重写 Dify 的 AI 提示词、放宽证据规则或为了演示顺畅默认接受约定。遇到字段、角色、状态不清时请列出具体 run、节点、输入/输出键及预期行为；不要发送真实密钥或有效表单令牌。我会根据已建流程回答和修补 Dify 侧问题。

产品最终验收应至少包含：含糊描述有可理解产出；更正不授权旧经历；自述仍能探索但不冒充硬性覆盖；旧来源阻断；工时区分每周/总计/本人任务；换版双方重确认；验收与公开分离；旁观者无法代确认；私有信息不出现在访客响应；断线恢复不重复收费启动；拒绝、退回、争议、超时和空状态可理解。


## 8. API、人工角色与失败分支（接入必读）

这是现有在线服务接入参考；不是已部署的 ResearchMesh 后端。当前五应用已发布，五项服务当前版本均已实测；需求包含完整审核和模糊方向探索两条 API 路径。

### HTTP 与人工暂停

基地址 `https://api.dify.ai/v1`；每个应用使用自己的 Bearer app key。不能拿组队 key 调需求或能力应用。以下凭据只保存在服务端。

| 步骤 | 方法与路径 | 要点 |
| --- | --- | --- |
| 参数检查 | GET /parameters | 读取当前发布版 Start 输入，不代表执行了模型 |
| 启动 | POST /workflows/run | inputs、稳定 user、response_mode=streaming |
| 读取待处理表单 | GET /form/human_input/{form_token} | 取当前 inputs、user_actions，不能只猜字段 |
| 提交本人操作 | POST /form/human_input/{form_token} | inputs、action、同一稳定 user；{} 只是接收确认 |
| 续接同一运行 | GET /workflow/{run_id}/events?user=...&include_state_snapshot=true&continue_on_pause=true | 注意这里 workflow 是单数；不得改为重新 POST 启动 |
| 查询结果 | GET /workflows/run/{run_id} | 最终 status、outputs、tokens、error |

`reference/researchmesh_api_step6/dify_client.py` 是 Python 标准库参考客户端。禁止在超时后自动重试创建工作流 POST；先查已持久化的 run 或按业务幂等记录恢复。模型超时、服务错误和契约阻断应分别显示。

SSE 重点事件：human_input_required、workflow_paused、node_finished、human_input_form_filled、human_input_form_timeout、workflow_finished、error。重连可能重放历史节点事件，且不一定重发 filled 事件；按成功 node_finished 移除已完成表单，并用 workflow_paused.paused_nodes 快照校准当前待办。

统一角色处理使用 `reference/researchmesh_finalize_step15/dify_event_contract.py`，保留原约定与交付角色，新增 need_owner、profile_owner。已用本轮实际脱敏事件和权限反例测试；旧 stage6 类只处理约定/交付，保留供历史回归，不作为完整上游接入类。

提交需求/能力节点时，服务端提供受保护的 role_actor_ids（need_owner 或 profile_owner 对应真实登录用户 ID），缺失或不匹配即拒绝。这个映射不能直接采用客户端值。约定的 owner 和 performer 仍必须是两个明确独立角色。

### 人工节点映射

| 服务/节点 | node_id | 必须对应的登录角色 | 输入字段 | action |
| --- | --- | --- | --- | --- |
| 需求方向选择 | 1792384003831 | 需求提出者 | draft_note | choose_a / choose_b / revise |
| 需求正式审核 | 1792335658268 | 需求负责人 | review_note | approve / revise |
| 本人经历确认 | 1792496533023 | 该档案本人 | profile_correction | confirm_use / revise / save_private |
| 约定负责人 v1 | 1792463257417 | 约定 owner_id | requested_changes | accept / revise / decline |
| 约定承担者 v1 | 1792463915587 | 约定 performer_id | requested_changes | accept / revise / decline |
| 约定负责人 v2 | 1792478884718 | 约定 owner_id | requested_changes | accept / revise / decline |
| 约定承担者 v2 | 1792479365090 | 约定 performer_id | requested_changes | accept / revise / decline |
| 交付验收 | 1792415339919 | 约定 reviewer_id（当前即负责人） | review_note | approve / revise / dispute |
| 本人贡献核对 | 1792416719562 | 约定 performer_id | contribution_correction | public_draft / private / revise |

模型/人工节点 ID 与重新导入的应用可能改变，迁移后需要更新映射。UI 中文按钮显示名不是 API action。提交时读取实时表单字段白名单并检查 action，不能把开发者备注字段当做登录身份。

同一 run 的 Dify user 保持稳定，负责人的操作和承担者的操作可以使用同一传输 user，但你的网站后端必须分别检查真实账号角色。平台 user 不提供业务角色分离。

### 结果与失败分支

| 服务/分支 | 展示字段 | 机器字段/判断 |
| --- | --- | --- |
| 需求方向探索 | exploration_card | 当前该分支以可读草稿为主，不能直接当已开放需求 |
| 需求审核 | review_card | need_review_record、need_matching_handoff；handoff 还须后端规范化确认 |
| 能力本人核对 | profile_card | profile_route、profile_packet、matching_evidence、revision_input |
| 无有效经历 | capability_card | capability_packet、capability_route |
| 能力超时 | profile_timeout_card | profile_timeout_packet，未授权匹配 |
| 匹配成功执行 | recommendation_card | decision_packet，逐项检查 effective、pending 和探索状态 |
| 匹配前置阻断 | unavailable_card | matching_blocked_packet |
| 周分工承接 | matched_team_card | matched_team_packet.status，可能无解或搜索未完成 |
| 周分工前置阻断 | pending_card | team_blocked_packet |
| 旧直接组队演示 | team_card | team_packet，仅演示，不代替版本化正式入口 |
| 合作约定 v1 | agreement_card | agreement_packet、agreement_route、agreement_json |
| 合作约定 v2 | agreement_v2_card | agreement_v2_packet、agreement_v2_route、agreement_v2_json |
| 修改被阻断 | revision_blocked_card | revision_blocked_packet、revision_blocked_route |
| 交付与本人贡献 | result | contribution_packet |
| 交付前置阻断 | preflight_blocked | blocked_route |

其他拒绝/待协调/超时输出应按实际 End 分支处理，不能假定每次都有主成功出口。本表从已保存实际结果与现有契约整理；具体实时字段仍以当前 form 定义为准；迁移或改节点后需要重新核验。

已完成表单重复读取可能返回 HTTP 412；应查询/续接原 run，不能据此再启动工作流。本轮交付验收提交已被接收后，重复读取旧表单观察到 412；没有再次提交相同选择。错应用 key / 非法 action 前期亦有反例验证，不能把 form_token 当作无限可用公开链接。


## 9. 附件入口与工作边界

配套源码包解压后的根目录为 ResearchMesh。先看 README.md、docs/代码入口.md、docs/apps.json；当前统一人工角色处理代码在 reference/researchmesh_finalize_step15/dify_event_contract.py，API 客户端在 reference/researchmesh_api_step6/dify_client.py。阶段号用于保留测试上下文，不是要求你按旧阶段顺序重新开发。

跨应用适配的正式入口：stage7 candidate_from_confirmed_profile；stage11 prepare_review_need/check_current_match；stage12 team_from_match/agreement_from_team；stage13 delivery_with_provenance。各模块与实际完整输入见对应目录 live_fixture.json、delivery_fixture.json。当前输入由网站后端从数据库与登录态装配，不让用户手写。

本地复核命令为 `python3 scripts/run_contract_tests.py`，需要 Python 3.12 标准库。已在独立目录运行通过 96 项测试，另有 9 项能力衔接断言；未来样例日期过期时，应成组更新虚构日期、确认记录及摘要，而不能关闭校验。此命令不调用模型、不访问 Dify。

网站同事接手后的首个交付应为一个真正贯通的纵向小闭环：自然语言输入 → 后端调用 Dify → 等待本人/负责人 → 当前角色提交 → 续接同一运行 → 保存并展示结果。先验证这一闭环，再连接匹配和后续合作，不必一开始铺满页面。

下一轮向 Dify 负责人提问时，请列出具体页面动作、app 名、node_id、run_id、输入/输出字段和预期状态。可提供脱敏样例，不能发送真实密钥、有效 form_token 或他人私有资料。我继续负责回答接口问题、修补 Dify、收取 DSL 和后续 GitHub 上传；这些工作不转交给你。

## 10. 暂停时的准确状态

- Dify：五个应用当前版本已发布；业务主链已有实际运行证据；五项服务当前发布版均有 API 实测覆盖，但并非所有分支都重新做过发布版 API 穷举测试。
- 网页：尚无由本轮工作完成并发布的最终成品网站；设计、数据库、鉴权、事务、运行持久化和网站发布交由网页同事实现。
- 用户主页：已有内容与数据投影参考、私有/公开边界及本地测试；尚未上线真实主页。
- GitHub：私有仓库已建，业务源码尚未上传，现按项目负责人要求暂停。
- 完整备份：五份完整当前 DSL 尚缺，在线应用原成果仍保留；附件源码不等于完整可导入迁移包。
- 凭据：每个应用现各有一个 app key，私密保存，本文与附件均不附实际值；网页不能直接调用带 app key 的 Dify API。
- 竞赛展示：可展示 100 节点、119 连线、11 个 LLM 节点及各分支的真实职责；不能把节点数量当作性能或真实用户协作效果证据。
