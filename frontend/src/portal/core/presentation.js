import { pages } from "../pages.js";

export function createPresentation() {
  const navigation = Object.entries(pages).map(([href, route]) => ({
    href,
    key: route.key,
    name: route.name,
    icon: route.icon,
  }));
  const modes = [
    { id: "quick", name: "快速审查", description: "基础规则与关键风险" },
    { id: "deep", name: "深度审查", description: "背景、尺度与参考资料" },
    { id: "checklist", name: "清单审查", description: "按企业要求逐项核验" },
    { id: "compare", name: "对比审查", description: "对照参考合同定位变更" },
  ];
  const sources = [
    { id: "file", name: "📤 上传合同" },
    { id: "paste", name: "✍️ 粘贴正文" },
  ];
  const roles = [
    { value: "中立审慎", label: "通用审查 · 中立审慎（默认）" },
    { value: "乙方(卖方/开发方/服务方)", label: "乙方 · 供应商/服务方" },
    { value: "甲方(买方/采购方/委托方)", label: "甲方 · 买方/采购方" },
  ];
  const taskStatuses = {
    draft: "待审查",
    running: "审查中",
    queued: "排队中",
    pending_review: "待复核",
    completed: "已完成",
    failed: "失败",
    interrupted: "已中断",
  };
  const statusName = (status) =>
    ({
      ...taskStatuses,
      background: "确认背景",
      outline: "确认大纲",
      text: "正文草稿",
    })[status] || status;
  const statusColor = (status) =>
    status === "completed"
      ? "green"
      : ["failed", "interrupted", "pending_review"].includes(status)
        ? "amber"
        : ["running","queued"].includes(status)
          ? "blue"
          : "";
  const modeName = (id) => modes.find((mode) => mode.id === id)?.name || id;
  const dateTime = (stamp) =>
    stamp
      ? new Date(stamp).toLocaleString("zh-CN", {
          timeZone: "Asia/Shanghai",
          hour12: false,
        })
      : "—";

  return {
    navigation,
    modes,
    sources,
    roles,
    taskStatuses,
    statusName,
    statusColor,
    modeName,
    dateTime,
  };
}
