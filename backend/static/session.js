/* Tab-scoped working copy: contracts are not persisted across browser sessions. */
window.LexisSession = {
  read(key) { try { return JSON.parse(sessionStorage.getItem(key) || 'null'); } catch { return null; } },
  write(key, value) { sessionStorage.setItem(key, JSON.stringify(value)); },
  severityLabel(value) { return { critical: '重大风险', warning: '一般风险', info: '优化建议', favorable: '有利条款' }[value] || '待确认'; }
};
