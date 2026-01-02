# 🏥 Nexus Miracle

AI-powered medical contact center for Saudi Arabia.

## 🚀 Features

- **Real-time Voice AI**: ASR + LLM + TTS pipeline with <800ms latency
- **Dual Voice Support**: Sara (Arabic female) & Nexus (Arabic male)
- **Telnyx Integration**: Phone call handling via webhooks & WebSocket
- **ElevenLabs**: Scribe for ASR, Flash v2.5 for TTS
- **Google Gemini**: Flash model for conversational AI
- **Silero VAD**: Voice activity detection

## 📁 Project Structure

```
app/
├── main.py           # FastAPI application
├── config.py         # Pydantic settings
├── exceptions.py     # Custom exceptions
├── routers/          # API endpoints
├── models/           # Data models
└── services/         # AI service integrations
```

## ⚡ Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR-USERNAME/nexus-miracle.git
cd nexus-miracle
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env
# Edit .env with your API keys
```

### 3. Run Server

```bash
python -m uvicorn app.main:app --reload
```

### 4. Access API

- Swagger Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/health

## 🔑 Environment Variables

| Variable | Description |
|----------|-------------|
| `TELNYX_API_KEY` | Telnyx API key |
| `ELEVENLABS_API_KEY` | ElevenLabs API key |
| `GOOGLE_API_KEY` | Google Gemini API key |
| `ELEVENLABS_VOICE_SARA` | Sara voice ID |
| `ELEVENLABS_VOICE_NEXUS` | Nexus voice ID |

## 📡 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `POST /api/telephony/webhook` | Telnyx webhooks |
| `WS /api/telephony/ws` | Audio WebSocket |
| `GET /api/admin/settings` | Admin settings |
| `CRUD /api/appointments` | Appointments |

## 🐳 Docker

```bash
docker-compose up --build
```

## 📄 License

MIT License
