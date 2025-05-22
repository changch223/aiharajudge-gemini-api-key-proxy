# 🧠 Harassment AI Gemini Proxy

A secure and schema-controlled FastAPI backend for detecting harassment types using Google Gemini 2.0 Flash.  
Supports multi-modal input (text + image) and returns structured JSON scores based on Japanese government guidelines.

- Used in production on [aiharajudge.site](https://aiharajudge.site)  
- Includes API key validation, referer check, and rate limiting  
- Deployed via Google Cloud Run

---

## 🚀 Features

- Accepts up to 3 screenshots + text via `POST /check_harassment`
- Calls Gemini 2.0 Flash via [Google Generative AI Python SDK](https://github.com/google/generative-ai-python)
- Returns **strict JSON** with 9 harassment scores and an AI-generated support message
- Includes:
  - API key verification (`X-API-Key` header)
  - HTTP Referer check (`aiharajudge.site`)
  - Per-IP rate limiting (10 requests/min)
- Image support via Pillow + Gemini native vision model
- Response schema enforced with `response_schema`

---

## ✨ Harassment Types Evaluated

This API returns structured scores (0–100) for:

- パワーハラスメント (Power Harassment)  
- スメルハラスメント (Smell Harassment)  
- カスタマーハラスメント (Customer Harassment)  
- ハラスメントハラスメント (Harassment of Reporting Harassment)  
- マタニティハラスメント (Maternity Harassment)  
- リモートハラスメント (Remote Harassment)  
- テクノロジーハラスメント (Technology Harassment)  
- セクシュアルハラスメント (Sexual Harassment)  
- モラルハラスメント (Moral Harassment)  
- 総合コメント: AI-generated supportive message in Japanese

---

## 🧪 Example Request

### Endpoint

```http
POST /check_harassment
Headers:
  X-API-Key: YOUR_SECRET_KEY
  Content-Type: multipart/form-data
```

---

## 🧾 Form Data

| Field   | Type                        | Description                                 |
|---------|-----------------------------|---------------------------------------------|
| `text`  | `string` (required)         | Conversation message or description         |
| `images` | `List[UploadFile]` (optional, max 3) | Screenshots (JPG, PNG, etc.)      |

---

## 🧠 Prompt Structure

The Gemini prompt includes:

- **System instruction**:  
  “Act as a harassment expert. Based on the uploaded screenshots and conversation text, analyze and rate the following 9 types of harassment (0–100). Also provide a supportive message as the '総合コメント'.”

- **User content**:  
  The user-provided `text` (conversation) and up to 3 uploaded screenshots (images).

- **Output format**:  
  Strict JSON matching a defined schema, including:

```json
{
  "パワーハラスメント": 0,
  "スメルハラスメント": 0,
  "カスタマーハラスメント": 0,
  "ハラスメントハラスメント": 0,
  "マタニティハラスメント": 0,
  "リモートハラスメント": 0,
  "テクノロジーハラスメント": 0,
  "セクシュアルハラスメント": 0,
  "モラルハラスメント": 0,
  "総合コメント": "AI-generated supportive explanation here"
}
```
---

## 📄 License

MIT License

---

## 🙋 Author

Created by **Chia-Wei Chang**  
Used in production at [aiharajudge.site](https://aiharajudge.site)  
Feedback, questions, and contributions welcome!

