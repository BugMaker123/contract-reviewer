export const pages = {
  "/": {
    key: "start",
    name: "开始",
    icon: "⌂",
    data: ["lists", "categories"],
    states: ["categories", "checklists", "review"],
    features: ["uploads", "start"],
  },
  "/records": {
    key: "records",
    name: "审查记录",
    icon: "▤",
    data: [],
    states: ["records"],
    features: ["records"],
  },
  "/categories": {
    key: "categories",
    name: "业务分类维护",
    icon: "▦",
    data: [],
    states: ["categories"],
    features: ["catalog", "categories"],
  },
  "/checklists": {
    key: "checklists",
    name: "审查清单",
    icon: "☑",
    data: ["categories"],
    states: ["categories", "checklists"],
    features: ["catalog", "records", "uploads", "checklists"],
  },
};
