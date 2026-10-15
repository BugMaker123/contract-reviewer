import os
import json
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from io import BytesIO
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models import ContractReviewRequest, ModelConfig
from .graph import review_graph_app, get_llm_client
from .sample_contracts import SAMPLE_CONTRACTS
from .workspace_api import router as workspace_router
from .store import repository
from .word_export import SOURCES, visible_paragraph_text

@asynccontextmanager
async def lifespan(app):
    repository.interrupt_running()
    yield

app = FastAPI(
    title="LexisGraph 内部合同工作系统",
    description="合同审查、企业清单、起草与记录管理",
    version="2.1.0",
    lifespan=lifespan
)
app.include_router(workspace_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保 static 目录存在
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.post("/api/contracts/import")
async def import_contract(file: UploadFile = File(...)):
    """Extract actual document content; never substitute example contracts."""
    content = await file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "文件超过 10 MB，请拆分后上传")
    extension = os.path.splitext(file.filename or "")[1].lower()
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
            document = Document(BytesIO(content))
            text = "\n".join(visible_paragraph_text(node) for node in document.element.body.iter(qn("w:p")))
        elif extension == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted:
                raise ValueError("请先解除 PDF 密码保护")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            raise HTTPException(415, "支持 TXT、DOCX 和文字型 PDF；旧版 DOC 请先另存为 DOCX")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "文件无法解析，请检查是否损坏或加密，或改用粘贴文本")
    if not text.strip():
        raise HTTPException(422, "未提取到正文；扫描件请先进行 OCR，或直接粘贴合同文本")
    if any(ord(character) < 32 and character not in '\n\r\t' for character in text):
        raise HTTPException(422, '正文含无法识别的控制字符，请重新导出文字文件或粘贴可读正文')
    if len(text) > 200000:
        raise HTTPException(413, "合同超过 20 万字，请拆分后审查")
    source = repository.create('source', {'extension': extension, 'text': text, 'name': file.filename or '待审合同'})
    SOURCES.mkdir(parents=True, exist_ok=True)
    (SOURCES / (source['id'] + extension)).write_bytes(content)
    return {"success": True, "text": text, "title": os.path.splitext(file.filename or "待审合同")[0], 'source_id': source['id']}

@app.get("/api/samples")
async def get_samples():
    """获取预设高危合同样本列表及正文"""
    return {
        "success": True,
        "samples": SAMPLE_CONTRACTS
    }

@app.get("/api/graph/info")
async def get_graph_info():
    """获取 LangGraph 状态图节点元信息"""
    nodes = [
        {
            "id": "segment_contract",
            "name": "合同结构化切片与要件解析",
            "description": "识别各级条款编号、标题并进行法律业务分类（标的、交付、验收、权责、违约、解除等）",
            "icon": "FileText"
        },
        {
            "id": "compliance_check",
            "name": "强制法规与效力合规排查",
            "description": "依据《民法典》格式条款效力、《劳动合同法》等强制性规范排查违法与效力待定条款",
            "icon": "ShieldAlert"
        },
        {
            "id": "balance_review",
            "name": "商业权责对等性与立场抗辩审查",
            "description": "基于我方立场（甲/乙方视角）排查单方无限赔偿、主观验收拖延、既有资产流失等陷阱",
            "icon": "Scale"
        },
        {
            "id": "aggregate_and_redline",
            "name": "红线修订方案编排与逐字Diff生成",
            "description": "聚合全案风险，生成法务抗辩依据与专业修订条款（Redline对照）",
            "icon": "GitPullRequest"
        },
        {
            "id": "synthesize_summary",
            "name": "终审报告汇总与合规量化评分",
            "description": "综合计算合规健康度分值（0-100），生成核心否决项清单与法务终审意见书",
            "icon": "Award"
        }
    ]
    return {"nodes": nodes}

class CheckModelRequest(BaseModel):
    model_name: str
    api_key: str
    base_url: str

@app.post("/api/model/check")
async def check_model(req: CheckModelRequest):
    """在线测试用户填写的模型连接有效性"""
    try:
        from langchain_core.messages import HumanMessage
        client = get_llm_client({
            "model_name": req.model_name,
            "api_key": req.api_key,
            "base_url": req.base_url,
            "temperature": 0.1
        })
        if not client:
            return {"success": False, "message": "无法初始化模型客户端，请检查 API Key 格式"}
        
        response = await asyncio.wait_for(
            client.ainvoke([HumanMessage(content="Hello, please reply with 'OK'.")]),
            timeout=10.0
        )
        return {
            "success": True,
            "message": f"连接成功！模型 [{req.model_name}] 响应正常: {response.content[:30]}"
        }
    except asyncio.TimeoutError:
        return {"success": False, "message": "连接超时（10秒），请检查 Base URL 网络连通性"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}

@app.post("/api/review")
async def review_contract_sync(req: ContractReviewRequest):
    """标准同步审查接口"""
    initial_state = {
        "contract_title": req.contract_title,
        "contract_type": req.contract_type,
        "party_role": req.party_role,
        "contract_text": req.contract_text,
        "model_config": req.model_config_data.model_dump(),
        "review_focus": req.review_focus or [],
        "segments": [],
        "compliance_issues": [],
        "balance_issues": [],
        "all_issues": [],
        "overall_summary": {},
        "execution_logs": []
    }
    final_state = await review_graph_app.ainvoke(initial_state)
    return {
        "success": True,
        "data": {
            "segments": final_state.get("segments"),
            "issues": final_state.get("all_issues"),
            "tax_settlement": final_state.get("tax_settlement_audit"),
            "summary": final_state.get("overall_summary"),
            "logs": final_state.get("execution_logs")
        }
    }

@app.post("/api/review/stream")
async def review_contract_stream(req: ContractReviewRequest):
    """
    基于 SSE (Server-Sent Events) 的流式状态机审查接口。
    随着 LangGraph 逐步执行每个节点，实时向前端推送节点状态、进度日志与阶段性审查成果！
    """
    initial_state = {
        "contract_title": req.contract_title,
        "contract_type": req.contract_type,
        "party_role": req.party_role,
        "contract_text": req.contract_text,
        "model_config": req.model_config_data.model_dump(),
        "review_focus": req.review_focus or [],
        "segments": [],
        "compliance_issues": [],
        "balance_issues": [],
        "all_issues": [],
        "overall_summary": {},
        "execution_logs": []
    }

    async def event_generator() -> AsyncGenerator[str, None]:
        # 初始握手事件
        yield f"event: init\ndata: {json.dumps({'message': 'LangGraph 审查状态机初始化就绪', 'title': req.contract_title})}\n\n"
        await asyncio.sleep(0.1)

        try:
            # 使用 LangGraph astream 捕获节点状态变更
            current_state = initial_state
            async for output in review_graph_app.astream(initial_state):
                for node_name, node_output in output.items():
                    # 提取该节点产出的最新日志
                    latest_log = None
                    if "execution_logs" in node_output and node_output["execution_logs"]:
                        latest_log = node_output["execution_logs"][-1]
                    
                    event_data = {
                        "node": node_name,
                        "status": "completed",
                        "log": latest_log,
                        "data_preview": {}
                    }
                    current_state.update(node_output)

                    if node_name == "segment_contract":
                        event_data["data_preview"] = {
                            "segment_count": len(node_output.get("segments", [])),
                            "segments": node_output.get("segments", [])
                        }
                    elif node_name == "compliance_check":
                        event_data["data_preview"] = {
                            "compliance_issues_count": len(node_output.get("compliance_issues", []))
                        }
                    elif node_name == "balance_review":
                        event_data["data_preview"] = {
                            "balance_issues_count": len(node_output.get("balance_issues", []))
                        }
                    elif node_name == "aggregate_and_redline":
                        event_data["data_preview"] = {
                            "all_issues_count": len(node_output.get("all_issues", [])),
                            "issues": node_output.get("all_issues", [])
                        }
                    elif node_name == "synthesize_summary":
                        event_data["data_preview"] = {
                            "summary": node_output.get("overall_summary", {})
                        }

                    yield f"event: node_update\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.3)

            # 最终全量汇聚通知
            result = {
                "segments": current_state.get("segments", []),
                "issues": current_state.get("all_issues", []),
                "tax_settlement": current_state.get("tax_settlement_audit"),
                "summary": current_state.get("overall_summary", {}),
                "logs": current_state.get("execution_logs", [])
            }
            yield f"event: complete\ndata: {json.dumps({'success': True, 'data': result}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/")
async def serve_index():
    """返回全新 MARKUP 风格的合同助手首页"""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), media_type="text/html; charset=utf-8")
    return HTMLResponse("<h1>LexisGraph 服务运行中，正在生成首页资源...</h1>", media_type="text/html; charset=utf-8")

@app.get("/workbench")
@app.get("/workbench.html")
async def serve_workbench():
    """返回合同专业审查工作台单页界面"""
    wb_file = os.path.join(STATIC_DIR, "workbench.html")
    if os.path.exists(wb_file):
        with open(wb_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), media_type="text/html; charset=utf-8", headers={'Cache-Control':'no-store'})
    return HTMLResponse("<h1>合同审查工作台未找到</h1>", media_type="text/html; charset=utf-8")
