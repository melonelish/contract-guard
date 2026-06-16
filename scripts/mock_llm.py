#!/usr/bin/env python3
"""
ContractGuard — Mock LLM Server (前端独立联调用)

启动: python scripts/mock_llm.py
端口: 8001
用途: 返回预设的审查结果，前端无需真实 LLM API Key 即可开发测试

预设场景:
  GET  /api/v1/mock/review/fast     → 3s 返回（模拟快速审查）
  GET  /api/v1/mock/review/slow     → 15s 返回 + WebSocket 阶段推送（模拟大合同）
  GET  /api/v1/mock/review/highrisk → 返回高风险合同（8 处风险）
  GET  /api/v1/mock/review/clean    → 返回清洁合同（0 风险）
  POST /api/v1/mock/contracts/upload → 模拟上传
  WS   /ws/review/{task_id}           → 模拟渐进式进度推送
"""
import asyncio, json, time, uuid
from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ContractGuard Mock LLM")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ═══════════ Preset Data ═══════════
PRESET_REVIEWS = {
    "fast": {
        "summary": {"total_risks": 3, "high": 1, "medium": 2, "low": 0},
        "risks": [
            {
                "risk_id": "R1", "level": "high", "title": "违约金比例过高",
                "clause_ref": "7.1", "original": "违约金为合同总额的50%",
                "suggestion": "建议修改为20%，且不超过实际损失",
                "law_basis": "《民法典》第585条 · 违约金不得超过损失的30%"
            },
            {
                "risk_id": "R2", "level": "medium", "title": "验收时间过长",
                "clause_ref": "10.1", "original": "货到15个工作日内验收",
                "suggestion": "建议缩短至3个工作日",
                "law_basis": "行业惯例 · 家具类验收周期3日足够"
            },
            {
                "risk_id": "R3", "level": "medium", "title": "管辖约定建议调整",
                "clause_ref": "12.1", "original": "甲方所在地人民法院管辖",
                "suggestion": "建议改为合同签订地人民法院",
                "law_basis": "《民事诉讼法》第35条"
            }
        ]
    },
    "highrisk": {
        "summary": {"total_risks": 8, "high": 4, "medium": 3, "low": 1, "comment": 1},
        "risks": [
            {"risk_id": "R1", "level": "high", "title": "违约金比例过高(50%)", "clause_ref": "7.1", "original": "违约金为合同总额50%", "suggestion": "改为20%"},
            {"risk_id": "R2", "level": "high", "title": "预付款比例过高(70%)", "clause_ref": "3.1", "original": "预付款为合同总额70%", "suggestion": "改为30%"},
            {"risk_id": "R3", "level": "high", "title": "无质保条款", "clause_ref": "缺失", "original": "—", "suggestion": "增加质保期条款(12-36个月)"},
            {"risk_id": "R4", "level": "high", "title": "无限期保密义务", "clause_ref": "15.2", "original": "保密义务永久有效", "suggestion": "限定期限(合同终止后3-5年)"},
            {"risk_id": "R5", "level": "medium", "title": "验收标准模糊", "clause_ref": "8.1", "original": "符合相关国家标准", "suggestion": "明确为GB/T 3324-2017"},
            {"risk_id": "R6", "level": "medium", "title": "逾期天数过长", "clause_ref": "7.1", "original": "逾期超过15日", "suggestion": "缩短至5个工作日"},
            {"risk_id": "R7", "level": "medium", "title": "付款节点不明确", "clause_ref": "4.2", "original": "验收合格后付款", "suggestion": "绑定具体验收标准"},
            {"risk_id": "R8", "level": "low", "title": "通知方式建议补充", "clause_ref": "18.3", "original": "书面通知", "suggestion": "增加电子邮件作为通知方式"},
        ]
    },
    "clean": {
        "summary": {"total_risks": 0, "high": 0, "medium": 0, "low": 0},
        "risks": [],
        "note": "✅ 未发现明显风险，合同整体规范"
    }
}

# ═══════════ REST Endpoints ═══════════

@app.get("/api/v1/health")
async def health():
    return {"status": "healthy (mock)", "version": "1.0.0-mock"}

@app.get("/api/v1/mock/review/{scenario}")
async def mock_review(scenario: str, delay: float = 0):
    """返回预设审查结果。?delay=3 模拟延迟"""
    if scenario not in PRESET_REVIEWS:
        return {"error": f"Unknown scenario '{scenario}', options: fast|slow|highrisk|clean"}
    
    await asyncio.sleep(delay or (3 if scenario == "fast" else 0))

    task_id = f"mock-{uuid.uuid4().hex[:8]}"
    return {
        "code": 0,
        "data": {
            "review_id": f"rv-{task_id}",
            "task_id": task_id,
            "contract": {
                "title": "办公家具采购合同（Mock）",
                "pages": 12,
                "clauses": 28,
                "type": "采购合同"
            },
            "result": PRESET_REVIEWS[scenario],
            "disclaimer": "⚠️ 本报告由 AI 自动生成，不构成法律意见。签署前请咨询执业律师。",
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    }

@app.post("/api/v1/mock/contracts/upload")
async def mock_upload():
    """模拟文件上传"""
    return {
        "code": 0,
        "data": {
            "contract_id": f"ct-{uuid.uuid4().hex[:8]}",
            "filename": "办公家具采购合同.pdf",
            "file_size": 245760,
            "status": "uploaded"
        }
    }

@app.get("/api/v1/reviews/{review_id}/export")
async def mock_export(review_id: str, format: str = "pdf"):
    """模拟报告导出（返回 JSON 提示）"""
    return {"code": 0, "message": f"Mock export: {review_id}.{format} (生产环境返回文件流)"}

# ═══════════ WebSocket ═══════════

@app.websocket("/ws/review/{task_id}")
async def ws_mock_progress(ws: WebSocket, task_id: str):
    """模拟渐进式审查进度推送"""
    await ws.accept()

    stages = [
        (5,  "stage", "parsing",    "PDF 文本提取完成，共 12 页"),
        (10, "stage", "parsing",    "识别到 28 条条款，2 个表格"),
        (15, "stage", "parsing",    "条款结构化完成"),
        (22, "stage", "analyzing",  "正在分析条款 5/28", 5, 28),
        (35, "stage", "analyzing",  "正在分析条款 12/28", 12, 28),
        (48, "stage", "analyzing",  "正在分析条款 20/28", 20, 28),
        (62, "stage", "analyzing",  "正在分析条款 28/28", 28, 28),
        (75, "stage", "analyzing",  "正在交叉校验条款间矛盾..."),
        (85, "stage", "analyzing",  "条款分析完成，检测到 3 处风险"),
        (90, "stage", "reporting",  "正在生成审查报告..."),
        (95, "stage", "validating", "正在校验法条引用..."),
        (100,"complete","completed", ""),
    ]

    for progress, evt_type, stage, detail, *extra in stages:
        payload = {
            "event": evt_type if evt_type == "complete" else "stage",
            "stage": stage,
            "progress": progress,
            "detail": detail
        }
        if extra:
            payload["clause_current"], payload["clause_total"] = extra[0], extra[1]
        if progress == 100:
            payload["review_id"] = task_id
            payload["duration_sec"] = 8
        await ws.send_json(payload)
        await asyncio.sleep(0.5)  # 模拟处理时间

    await ws.close()

# ═══════════ Main ═══════════
if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("🧪 ContractGuard Mock LLM Server")
    print(f"   REST API:  http://localhost:8001/api/v1/")
    print(f"   WebSocket: ws://localhost:8001/ws/review/{{task_id}}")
    print(f"   Scenarios: fast | highrisk | clean")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8001)
