from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import io
import re
import json

# Pillow
from PIL import Image

# Google Gen AI SDK
# (以前の from google.generativeai.types import GenerationConfig は削除し、
#  代わりに from google.genai import types を使う)
from google import genai
from google.genai import types

app = FastAPI()

# CORS 設定（必要に応じて allow_origins を変更）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1) 環境変数からキーを読み込み、Client を初期化
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY)

# 2) 9種ハラスメント(整数) + 総合コメント(文字列) 用の schema
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
    モデル応答から JSON を抽出。Markdown コードブロックや
    大カッコ {} を探してパースする。
    """
    if not isinstance(response_text, str):
        response_text = str(response_text)

    # ```json ... ``` を検索
    match = re.search(r"```json\s*(\{.*\})\s*```", response_text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        # それ以外は先頭の '{' から最後の '}' までを切り出し
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {"error": "No valid JSON found in response."}
        json_str = response_text[start:end+1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        return {"error": f"JSON decode error: {str(e)}"}

@app.post("/check_harassment")
async def check_harassment(
    images: List[UploadFile] = File(None),
    text: str = Form(...),
):
    """
    最大3枚の画像と会話テキストを受け取り、
    Gemini 2.0 Flash を使ってハラスメントスコアを JSON で返す。
    """

    # 1) 画像を PIL Image に変換して contents に追加
    contents = []
    if images:
        for imgfile in images[:3]:
            if imgfile.content_type.startswith("image/"):
                raw = await imgfile.read()
                pil_img = Image.open(io.BytesIO(raw))
                contents.append(pil_img)

    # 2) system_instruction (専門家としての振る舞いなど)
    system_instruction = """
あなたはハラスメントの専門家です。
入力された写真(0~3枚)と会話内容をもとに分析し、
下記9種ハラスメントを0〜100点で数値化し、
総合コメントを日本語で出力してください。
答えは必ずstrictなJSONのみで返してください。
"""

    # 3) user_prompt
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

    # 4) Gemini へのリクエスト
    #   client.models.generate_content(...) でも client.generate_content(...) でもOK
    gen_config = types.GenerateContentConfig(
        temperature=0.3,
        top_p=0.95,
        top_k=10,
        max_output_tokens=512,
        system_instruction=system_instruction,
        response_schema=RESPONSE_SCHEMA
    )
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
        config=gen_config
    )

    # 5) 応答を JSON 化
    parsed = extract_json(response.text)
    return parsed
