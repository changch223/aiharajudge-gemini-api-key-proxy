from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class InputData(BaseModel):
    text: str

categories = [
    "パワーハラスメント（パワハラ）",
    "スメルハラスメント",
    "カスタマーハラスメント（カスハラ）",
    "ハラスメントハラスメント（ハラハラ）",
    "マタニティハラスメント（マタハラ）",
    "リモートハラスメント（リモハラ）",
    "テクノロジーハラスメント（テクハラ）",
    "セクシュアルハラスメント（セクハラ）",
    "モラルハラスメント（モラハラ）"
]

# Proxy 設定
PROXY_URL = "https://你的-cloud-run-url/app.p"
PROXY_TOKEN = os.getenv("PROXY_TOKEN")  # 自訂 token，和 proxy 那邊要一致

@app.post("/check_harassment")
async def check_harassment(data: InputData):
    headers = {
        "Authorization": f"Bearer {PROXY_TOKEN}",
        "Content-Type": "application/json"
    }

    # prompt 內容：一樣可以自由調整
    contents = [{
        "parts": [{
            "text": f"""
あなたはハラスメント専門家です。
以下のテキストを読み取り、それぞれの種類のハラスメントに該当する可能性を、1〜100でスコアを出してください。

対象テキスト：
{data.text}

以下の9項目にスコアをお願いします：
- パワハラ
- スメハラ
- カスハラ
- ハラハラ
- マタハラ
- リモハラ
- テクハラ
- セクハラ
- モラハラ

出力は JSON として次のように返してください：
{{\"パワーハラスメント（パワハラ）\": 数字, ...（略）}}
"""
        }]
    }]

    payload = {
        "model_name": "gemini-1.5-flash",
        "contents": contents,
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 1024
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(PROXY_URL, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.RequestError as e:
            return {"error": f"Request failed: {str(e)}"}
        except httpx.HTTPStatusError as e:
            return {"error": f"Proxy returned HTTP error {e.response.status_code}: {e.response.text}"}
