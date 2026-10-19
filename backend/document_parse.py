"""Isolated parser; parent enforces time and concurrency budgets."""
import json
import sys
from io import BytesIO
from fastapi import HTTPException
from .word_export import visible_paragraph_text


def extract(content, extension):
    try:
        if extension == ".txt":
            if content.startswith((b'\xff\xfe\x00\x00', b'\x00\x00\xfe\xff')):
                text = content.decode('utf-32')
            elif content.startswith((b'\xff\xfe', b'\xfe\xff')):
                text = content.decode('utf-16')
            else:
                try:
                    text = content.decode("utf-8-sig")
                except UnicodeDecodeError:
                    text = content.decode("gb18030")
        elif extension == ".docx":
            from docx import Document
            from docx.oxml.ns import qn
            from zipfile import ZipFile
            with ZipFile(BytesIO(content)) as archive:
                entries = archive.infolist()
                if len(entries) > 2048 or sum(item.file_size for item in entries) > 50 * 1024 * 1024 or any(item.file_size > 1024 * max(item.compress_size, 1) for item in entries):
                    raise HTTPException(413, 'DOCX 解压规模超过限制，请拆分文档')
            document = Document(BytesIO(content))
            text = "\n".join(visible_paragraph_text(node) for node in document.element.body.iter(qn("w:p")))
        elif extension == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted:
                raise ValueError("请先解除 PDF 密码保护")
            if len(reader.pages) > 300:
                raise HTTPException(413, 'PDF 超过 300 页，请拆分文档')
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            raise HTTPException(415, "支持 TXT、DOCX 和文字型 PDF；旧版 DOC 请先另存为 DOCX")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "文件无法解析，请检查是否损坏或加密，或改用粘贴文本")
    return text


if __name__ == '__main__':
    try:
        print(json.dumps({'text': extract(sys.stdin.buffer.read(), sys.argv[1])}, ensure_ascii=False))
    except HTTPException as error:
        print(json.dumps({'status': error.status_code, 'error': error.detail}, ensure_ascii=False))
