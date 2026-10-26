import { auth } from './auth.js';
/* Legacy desktop cache. Web work is always restored from a server record ID. */
export const LexisSession = {
  read(key) {
    if(auth.web) return null;
    try {
      return JSON.parse(sessionStorage.getItem(key) || "null");
    } catch {
      return null;
    }
  },
  write(key, value) {
    if(auth.web) return;
    sessionStorage.setItem(key, JSON.stringify(value));
  },
  severityLabel(value) {
    return (
      {
        critical: "重大风险",
        warning: "一般风险",
        info: "优化建议",
        favorable: "有利条款",
      }[value] || "待确认"
    );
  },
};
