# 模板校验结果约定

流程：选择已发布模板及版本 → 校验合同 → 自动保存结果 → 展示统计与未通过项。
无人工审批、审核人填写或确认提交；校验完成即留档。

现有接口：`POST /api/contract-templates/{template_id}/validate`。
请求包含 `release_id`（已发布版本 ID）与 `source_id`（上传合同 ID）。
响应包含 `id`、`passed`（JSON boolean）、`report`、模板版本及文件校验值。
后续 BPM 包装可使用 `passed`，无需读取页面文案或人工结论。

- `passed: true`：`report.status == "pass"`，字段规则全部通过，无固定内容差异，无转人工、未检查项或完整性限制。
- `passed: false`：规则不符、固定内容差异、转人工字段或无法完整校验。具体原因见 `report`。
- 解析失败、记录不存在、版本冲突等保持 HTTP 4xx/5xx；不保存为一次成功计算的 FALSE，调用方应按接口错误处理。
- TRUE 表示模板自动规则通过，不代表合同整体法律风险判断或已提交 BPM 审批。

`GET /api/template-validations` 提供历史分页，`passed=all|true|false` 可筛选。
`GET /api/template-validations/{id}` 返回计算报告。旧人工结论保留在原始存储中，但不影响 passed，也不再展示为待审核状态。
人工确认接口已移除。报告仅展示统计、字段未通过项、固定条款差异及完整性限制。
