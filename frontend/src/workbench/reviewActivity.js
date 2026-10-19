// Only observable actions and completed public results enter the progress panel.
// Raw detail, provider reasoning, retries and request counts remain in audit logs.
export function reviewActivities(trace, findingCount = 0) {
  const entries = new Map();
  const put = (id, text, time) => { if (!entries.has(id)) entries.set(id, {id,text,time}); else entries.set(id,{...entries.get(id),text}); };
  const count = value => Number.isInteger(value) && value >= 0 ? value : null;
  for (const event of trace) {
    const {stage,time} = event;
    if (stage === 'prepare') put('prepare', count(event.contract_chars) !== null ? `已接收 ${event.contract_chars} 字合同，整理审查条件。` : '已接收合同，整理审查条件。', time);
    if (stage === 'admission' && event.admission?.status === 'pass') put('admission', '已完成合同属性与审查用途核对。', time);
    if (stage === 'plan') put('plan', '已建立全文研判、重点要求及修订核验的审查流程。', time);
    if (stage === 'segment') put('segment', count(event.segment_count) !== null ? `已整理 ${event.segment_count} 个条款单元，进入条款分析。` : '已整理合同条款，进入条款分析。', time);
    if (stage === 'review') put('review', '已开始全文研判，结合审查立场核对履约及责任安排。', time);
    if (stage === 'analysis_summary' && findingCount) put('findings', `已收到 ${findingCount} 条初步意见，逐项展示并继续校验。`, time);
    if (stage === 'validate') put('validate', count(event.finding_count) !== null ? `已收到完整分析结果，共 ${event.finding_count} 项；正在核对原文依据。` : '已收到完整分析结果，进入原文与修订范围校验。', time);
    if (stage === 'balance_review') put('analysis-done', '已完成本轮全文研判，汇总风险意见。', time);
    if (stage === 'aggregate_and_redline') put('aggregate', '已汇总风险条目，准备整理修订与核验结果。', time);
    if (stage === 'requirements') put('requirements', count(event.requirement_count) !== null ? `正在核对 ${event.requirement_count} 条重点要求、原文证据及要求间冲突。` : '已进入重点要求与原文证据核对。', time);
    if (stage === 'checklist') put('checklist', '已完成清单专项要求核验，结果将列于重点要求区。', time);
    if (stage === 'evidence_tool') put('evidence', '正在结合合同及参考资料补查待确认的要求。', time);
    if (stage === 'rewrite' && count(event.merged_count) !== null) put('rewrite', `已将风险归并为 ${event.merged_count} 个条款，正在整理统一修订。`, time);
    if (stage === 'rewrite' && count(event.rewritten_count) !== null) put('rewrite-done', `已形成 ${event.rewritten_count} 个条款的修订建议，准备交付核验结果。`, time);
  }
  return [...entries.values()].slice(-4);
}
