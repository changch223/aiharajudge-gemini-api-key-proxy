import os
import io
import re
import json
import logging
from datetime import datetime, timedelta
from threading import Lock
from typing import List

from fastapi import FastAPI, File, UploadFile, Form, Request, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader

# Pillow
from PIL import Image

# Google Gen AI SDK
from google import genai
from google.genai import types

# ---------------------------
# Logging 設定
# ---------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------
# FastAPI 與 CORS 設定
# ---------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://aiharajudge.site"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# API 金鑰及 Referer 檢查設定
# ---------------------------
API_KEY = os.getenv("MY_API_KEY", "your_default_api_key")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key: str = Security(api_key_header)):
    """
    檢查 API 請求 Header 中的金鑰是否正確
    """
    if api_key != API_KEY:
        logger.warning("API key 無效")
        raise HTTPException(status_code=403, detail="無效的 API 金鑰")
    return api_key

async def check_referer(request: Request):
    """
    檢查 HTTP Referer 是否包含指定域名，若不符合則拒絕請求
    """
    referer = request.headers.get("referer")
    if referer is None or "aiharajudge.site" not in referer:
        logger.warning("Referer 檢查失敗: %s", referer)
        raise HTTPException(status_code=403, detail="不允許的 Referer")
    return True

# ---------------------------
# 限速設定（Rate Limiting）
# ---------------------------
RATE_LIMIT = 10         # 每個 IP 在規定時間內允許的請求數量
RATE_PERIOD = 60        # 時間區間（秒）

# 儲存每個 IP 的請求時間列表，簡單的 in-memory 限速（僅適用單一進程）
rate_limit_lock = Lock()
rate_limit_data = {}

async def rate_limit(request: Request):
    """
    限速檢查：同一 IP 在 RATE_PERIOD 秒內，請求次數不得超過 RATE_LIMIT 次
    """
    ip = request.client.host
    now = datetime.now()

    with rate_limit_lock:
        timestamps = rate_limit_data.get(ip, [])
        # 過濾掉超過 RATE_PERIOD 的請求時間
        timestamps = [t for t in timestamps if (now - t).seconds < RATE_PERIOD]
        if len(timestamps) >= RATE_LIMIT:
            logger.warning("限速觸發: IP %s 過於頻繁的請求", ip)
            raise HTTPException(status_code=429, detail="Too Many Requests")
        timestamps.append(now)
        rate_limit_data[ip] = timestamps

# ---------------------------
# API 日誌 Middleware
# ---------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("請求: %s %s 來自 %s", request.method, request.url.path, request.client.host)
    response = await call_next(request)
    logger.info("回應狀態碼: %s", response.status_code)
    return response

# ---------------------------
# 原有業務邏輯部分
# ---------------------------

# 取得 Gemini API KEY 並初始化 client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY)

# 定義返回 JSON 格式的 Schema (9 種ハラスメント與 総合コメント)
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "パワーハラスメント": {"type": "integer"},
        "スメルハラスメント": {"type": "integer"},
        "カスタマーハラスメント": {"type": "integer"},
        "ハラスメントハラスメント": {"type": "integer"},
        "マタニティハラスメント": {"type": "integer"},
        "リモートハラスメント": {"type": "integer"},
        "テクノロジーハラスメント": {"type": "integer"},
        "セクシュアルハラスメント": {"type": "integer"},
        "モラルハラスメント": {"type": "integer"},
        "総合コメント": {"type": "string"}
    },
    "required": [
        "パワーハラスメント",
        "スメルハラスメント",
        "カスタマーハラスメント",
        "ハラスメントハラスメント",
        "マタニティハラスメント",
        "リモートハラスメント",
        "テクノロジーハラスメント",
        "セクシュアルハラスメント",
        "モラルハラスメント",
        "総合コメント"
    ]
}

def extract_json(response_text: str):
    """
    從模型回應中提取 JSON 資料。先嘗試從 Markdown 的程式碼區塊中抓取，
    若無，再以第一個 '{' 與最後一個 '}' 作切割。
    """
    if not isinstance(response_text, str):
        response_text = str(response_text)
    
    match = re.search(r"```json\s*(\{.*\})\s*```", response_text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {"error": "No valid JSON found in response."}
        json_str = response_text[start:end+1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        return {"error": f"JSON decode error: {str(e)}"}

# 加入 API 金鑰、Referer 與限速等依賴
@app.post("/check_harassment", dependencies=[Depends(get_api_key), Depends(check_referer), Depends(rate_limit)])
async def check_harassment(
    images: List[UploadFile] = File(None),
    text: str = Form(...),
):
    """
    接收最多 3 張圖片與一段會話文本，然後利用 Gemini 2.0 Flash 將結果分析，並返回 JSON 格式。
    """
    # 將圖片轉為 PIL Image 並儲存到 contents 清單中
    contents = []
    if images:
        for imgfile in images[:3]:
            if imgfile.content_type.startswith("image/"):
                raw = await imgfile.read()
                try:
                    pil_img = Image.open(io.BytesIO(raw))
                    contents.append(pil_img)
                except Exception as e:
                    logger.error("處理圖片失敗: %s", e)
                    raise HTTPException(status_code=400, detail="無效的圖片格式")

    # system_instruction 設定：指定模型角色與指令
    system_instruction = """
あなたはハラスメントの専門家です。
入力された写真(0~3枚)と会話内容をもとに分析し、
下記9種ハラスメントを0〜100点で数値化し、
総合コメントを日本語で出力してください。
答えは必ずstrictなJSONのみで返してください。
"""

    # 組合 user_prompt：包含會話文本與輸出 JSON 格式提示
    user_prompt = f"""
【会話内容】
{text}

出力JSONのフォーマット:
{{
  "パワーハラスメント": 0〜100,
  "スメルハラスメント": 0〜100,
  "カスタマーハラスメント": 0〜100,
  "ハラスメントハラスメント": 0〜100,
  "マタニティハラスメント": 0〜100,
  "リモートハラスメント": 0〜100,
  "テクノロジーハラスメント": 0〜100,
  "セクシュアルハラスメント": 0〜100,
  "モラルハラスメント": 0〜100,
  "総合コメント": "XXX"
}}
"""
    contents.append(user_prompt)

    # 呼叫 Gemini API
    gen_config = types.GenerateContentConfig(
        temperature=0.3,
        top_p=0.95,
        top_k=10,
        max_output_tokens=512,
        system_instruction=system_instruction,
        response_schema=RESPONSE_SCHEMA,
        response_mime_type="application/json"
    )
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
        config=gen_config
    )

    # 提取並返回模型回應中的 JSON 資料
    parsed = extract_json(response.text)
    return parsed
