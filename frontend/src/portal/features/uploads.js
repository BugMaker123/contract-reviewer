import { readDocument } from "../services/documents.js";

export function setup(context) {
  const { importing, error, modalError, notify } = context;
  const importDocument = async (event, target, dropped = false) => {
    const file = (dropped ? event.dataTransfer.files : event.target.files)?.[0];
    if (!file || importing.value) return;
    importing.value = true;
    error.value = "";
    modalError.value = "";
    try {
      const handler = context.importHandlers?.[target];
      if (!handler) throw new Error("当前页面不支持此资料类型");
      const data = await readDocument(file);
      const message = await handler(data, file);
      notify(message || "已提取正文，请核对内容");
    } catch (err) {
      if (target === "checklist") modalError.value = err.message;
      else error.value = err.message;
    } finally {
      importing.value = false;
      if (!dropped) event.target.value = "";
    }
  };
  return { importDocument };
}
