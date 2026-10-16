export async function readDocument(file) {
  if (!/\.(txt|docx|pdf)$/i.test(file.name))
    throw new Error("支持 DOCX、文字型 PDF 和 TXT；DOC 请先另存为 DOCX");
  if (file.size > 10 * 1024 * 1024)
    throw new Error("文件超过 10 MB，请拆分后上传");
  const body = new FormData();
  body.append("file", file);
  const response = await fetch("/api/contracts/import", {
    method: "POST",
    body,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "文件提取失败");
  return data;
}

export function appendMaterial(materials, file, data) {
  if (
    materials.length >= 5 ||
    materials.reduce((sum, item) => sum + item.text.length, 0) +
      data.text.length >
      50000
  ) {
    throw new Error("参考资料最多 5 份，合计不能超过 5 万字");
  }
  materials.push({ name: file.name, text: data.text });
}
