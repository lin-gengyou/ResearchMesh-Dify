# Dify Service API 接入说明

这是现有在线服务接入参考；不是已部署的 ResearchMesh 后端。当前五应用已发布，五项服务当前版本均已实测；需求包含完整审核和模糊方向探索两条 API 路径。

## HTTP 与人工暂停

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

## 人工节点映射

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

## 结果与失败分支

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
