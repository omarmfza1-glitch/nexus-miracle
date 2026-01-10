# Nexus Miracle - مركز اتصال طبي ذكي
# دليل المشروع الشامل

---

## 1. نظرة عامة على المشروع

### 1.1 ما هو Nexus Miracle؟
نظام مركز اتصال طبي مدعوم بالذكاء الاصطناعي للمملكة العربية السعودية. يتعامل مع المكالمات الهاتفية باستخدام:
- **VAD** (Voice Activity Detection): كشف النشاط الصوتي
- **ASR** (Automatic Speech Recognition): تحويل الصوت لنص عبر ElevenLabs Scribe
- **LLM** (Large Language Model): معالجة اللغة عبر Google Gemini
- **TTS** (Text-to-Speech): تحويل النص لصوت عبر ElevenLabs

### 1.2 الشخصيات الصوتية
- **سارة (Sara)**: الصوت الرئيسي، تتحدث مع المرضى
- **نكسس (Nexus)**: الصوت الثانوي للمعلومات الطبية

### 1.3 البنية التقنية
```
┌─────────────────────────────────────────────────────────┐
│                    Telnyx (VoIP)                        │
└─────────────────────┬───────────────────────────────────┘
                      │ WebSocket
┌─────────────────────▼───────────────────────────────────┐
│                 FastAPI Backend                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
│  │   VAD   │→ │   ASR   │→ │   LLM   │→ │   TTS   │    │
│  │ Silero  │  │ElevenLabs│  │ Gemini  │  │ElevenLabs│   │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │
│                      │                                  │
│              ┌───────▼───────┐                          │
│              │   SQLite DB   │                          │
│              └───────────────┘                          │
└─────────────────────────────────────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────────────┐
│              Next.js 14 Frontend                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Admin Panel  │  │   Calendar   │  │  Booking UI  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 2. هيكل المشروع

### 2.1 المجلدات الرئيسية
```
c:\Users\omarm\Nexus\
├── app/                    # Backend FastAPI
│   ├── config.py          # إعدادات التطبيق (Pydantic Settings)
│   ├── main.py            # نقطة الدخول الرئيسية
│   ├── exceptions.py      # استثناءات مخصصة
│   ├── crud/              # عمليات قاعدة البيانات
│   ├── events/            # نظام Event Bus
│   │   ├── __init__.py
│   │   └── event_bus.py   # Publish/Subscribe pattern
│   ├── models/            # نماذج SQLAlchemy
│   │   └── database.py    # CallLog, FillerPhrase, etc.
│   ├── routers/           # API endpoints
│   │   ├── admin.py       # /api/admin/* (Settings, Voices, Prompt)
│   │   ├── appointments.py # /api/appointments
│   │   ├── doctors.py     # /api/doctors
│   │   ├── health.py      # /api/health
│   │   ├── insurance.py   # /api/insurance
│   │   ├── patients.py    # /api/patients
│   │   └── telephony.py   # /api/telephony (Telnyx webhooks)
│   ├── schemas/           # Pydantic models
│   ├── services/          # Business logic
│   │   ├── asr_service.py # ElevenLabs Scribe
│   │   ├── db_service.py  # Database operations
│   │   ├── llm_service.py # Google Gemini
│   │   ├── tts_service.py # ElevenLabs TTS
│   │   └── vad_service.py # Silero VAD
│   └── utils/             # أدوات مساعدة
│       ├── circuit_breaker.py # حماية من الأعطال
│       └── monitoring.py  # مقاييس الأداء
│
├── frontend/              # Next.js 14 Frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── admin/     # لوحة التحكم
│   │   │   │   ├── layout.tsx      # التخطيط الرئيسي
│   │   │   │   ├── page.tsx        # Dashboard
│   │   │   │   ├── appointments/   # قائمة المواعيد
│   │   │   │   ├── calendar/       # التقويم (FullCalendar)
│   │   │   │   ├── doctors/        # إدارة الأطباء
│   │   │   │   ├── call-logs/      # سجل المكالمات
│   │   │   │   ├── filler-phrases/ # عبارات الانتظار
│   │   │   │   ├── voice-settings/ # إعدادات الصوت
│   │   │   │   ├── system-prompt/  # System Prompt
│   │   │   │   └── environment/    # متغيرات البيئة
│   │   │   └── book/      # واجهة الحجز للمرضى
│   │   │       ├── page.tsx        # الصفحة الرئيسية
│   │   │       ├── calendar/       # اختيار الموعد
│   │   │       ├── confirm/        # تأكيد الحجز
│   │   │       └── success/        # صفحة النجاح
│   │   ├── components/ui/ # مكونات shadcn/ui
│   │   └── lib/
│   │       └── api.ts     # API client
│   ├── package.json
│   └── tailwind.config.ts
│
├── scripts/               # سكربتات الاختبار
│   ├── test_ai_pipeline.py    # اختبار VAD/ASR/LLM/TTS
│   ├── test_telnyx.py         # اختبار Telnyx
│   ├── load_test.py           # اختبار الحمل (100 req/s)
│   └── integration_tests.py   # اختبارات التكامل
│
├── tests/                 # الاختبارات
│   └── integration/
│       ├── test_phone_booking_flow.py
│       └── test_error_recovery.py
│
├── data/                  # بيانات التطبيق
│   ├── nexus.db          # قاعدة البيانات SQLite
│   ├── voice_settings.json
│   └── environment_settings.json
│
├── docker-compose.yml     # تشغيل محلي
├── Dockerfile            # Backend image
├── requirements.txt      # Python dependencies
└── .env                  # متغيرات البيئة (لا ترفع على Git!)
```

---

## 3. الـ APIs المتاحة

### 3.1 Health & Admin
| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET | `/api/health` | فحص صحة الخدمة |
| GET | `/api/admin/settings` | الإعدادات العامة |
| PUT | `/api/admin/settings` | تحديث الإعدادات |
| GET | `/api/admin/voices` | إعدادات الأصوات (Sara/Nexus) |
| PUT | `/api/admin/voices` | تحديث إعدادات الصوت |
| POST | `/api/admin/voices/test` | اختبار TTS |
| GET | `/api/admin/prompt` | System Prompt |
| PUT | `/api/admin/prompt` | تحديث Prompt |
| GET | `/api/admin/environment` | متغيرات البيئة |
| PUT | `/api/admin/environment` | تحديث البيئة |
| GET | `/api/admin/fillers` | عبارات الانتظار |
| POST | `/api/admin/fillers` | إضافة عبارة |
| DELETE | `/api/admin/fillers/{id}` | حذف عبارة |
| GET | `/api/admin/calls` | سجل المكالمات |

### 3.2 Appointments
| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET | `/api/appointments` | جميع المواعيد |
| POST | `/api/appointments` | إنشاء موعد جديد |
| GET | `/api/appointments/{id}` | موعد محدد |
| PUT | `/api/appointments/{id}` | تحديث موعد |
| DELETE | `/api/appointments/{id}` | حذف موعد |

### 3.3 Doctors
| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET | `/api/doctors` | جميع الأطباء |
| GET | `/api/doctors/{id}` | طبيب محدد |
| GET | `/api/doctors/{id}/availability` | أوقات الطبيب المتاحة |

### 3.4 Telephony (Telnyx Webhooks)
| Method | Endpoint | الوصف |
|--------|----------|-------|
| POST | `/api/telephony/webhook` | استقبال أحداث المكالمات |
| POST | `/api/telephony/call` | بدء مكالمة جديدة |

---

## 4. الخدمات (Services)

### 4.1 VAD Service (`app/services/vad_service.py`)
- **المكتبة**: Silero VAD
- **الوظيفة**: كشف متى يتحدث المستخدم ومتى يصمت
- **الأحداث**: `SPEECH_START`, `SPEECH_CONTINUE`, `SPEECH_END`, `SILENCE`
- **الإعدادات**:
  - `vad_threshold`: 0.5 (عتبة الكشف)
  - `vad_min_silence_ms`: 700ms (مدة الصمت قبل اعتبار النهاية)

### 4.2 ASR Service (`app/services/asr_service.py`)
- **المكتبة**: ElevenLabs Scribe
- **الوظيفة**: تحويل الصوت إلى نص
- **اللغة**: العربية السعودية
- **الدقة المستهدفة**: >95%

### 4.3 LLM Service (`app/services/llm_service.py`)
- **المكتبة**: Google Gemini 2.0 Flash
- **الوظيفة**: توليد الردود الذكية
- **الشخصيات**: Sara (ودودة)، Nexus (طبي)
- **JSON Parsing**: للتبديل بين الشخصيات

### 4.4 TTS Service (`app/services/tts_service.py`)
- **المكتبة**: ElevenLabs Flash v2.5
- **الأصوات**:
  - Sara: `settings.elevenlabs_voice_sara`
  - Nexus: `settings.elevenlabs_voice_nexus`
- **الإعدادات**:
  - `stability`: 0.5
  - `similarity_boost`: 0.75
  - `speed`: 1.0

---

## 5. نظام الأحداث (Event Bus)

### 5.1 الموقع
`app/events/event_bus.py`

### 5.2 أنواع الأحداث
```python
class EventType(str, Enum):
    APPOINTMENT_CREATED = "appointment.created"
    APPOINTMENT_UPDATED = "appointment.updated"
    APPOINTMENT_CANCELLED = "appointment.cancelled"
    APPOINTMENT_CONFIRMED = "appointment.confirmed"
    CALL_STARTED = "call.started"
    CALL_ENDED = "call.ended"
    CALL_ERROR = "call.error"
    SETTINGS_UPDATED = "settings.updated"
    VOICE_SETTINGS_UPDATED = "voice_settings.updated"
    FILLERS_UPDATED = "fillers.updated"
    PROMPT_UPDATED = "prompt.updated"
```

### 5.3 الاستخدام
```python
from app.events import event_bus, EventType

# الاشتراك في حدث
@event_bus.on(EventType.APPOINTMENT_CREATED)
async def handle_new_appointment(event):
    print(f"New appointment: {event.data}")

# نشر حدث
await event_bus.publish(EventType.APPOINTMENT_CREATED, {
    "patient": "محمد",
    "doctor": "د. فهد"
})
```

---

## 6. Circuit Breaker (حماية الأعطال)

### 6.1 الموقع
`app/utils/circuit_breaker.py`

### 6.2 كيف يعمل
1. يتتبع الأخطاء المتتالية
2. بعد 5 أخطاء: يفتح الدائرة (يرفض الطلبات)
3. بعد 30 ثانية: يحاول مرة أخرى (half-open)
4. إذا نجح: يغلق الدائرة (طبيعي)

### 6.3 الرسائل البديلة (عربي)
| الخدمة | الرسالة |
|--------|---------|
| ASR | "عذراً، ما سمعتك زين. ممكن تعيد؟" |
| LLM | "النظام مشغول، لحظة وأرجع لك" |
| TTS | "عذراً، في مشكلة تقنية. حاول مرة ثانية" |

---

## 7. Frontend (Next.js 14)

### 7.1 لوحة التحكم (Admin)
- **المسار**: `/admin`
- **الملف**: `frontend/src/app/admin/layout.tsx`
- **الميزات**:
  - Dashboard مع إحصائيات
  - إدارة المواعيد
  - تقويم تفاعلي (FullCalendar)
  - إعدادات الصوت
  - System Prompt
  - سجل المكالمات

### 7.2 التقويم (Calendar)
- **المسار**: `/admin/calendar`
- **المكتبة**: FullCalendar
- **الميزات**:
  - عرض يوم/أسبوع/شهر
  - Drag & Drop لإعادة الجدولة
  - تأكيد/إلغاء المواعيد
  - فلترة حسب الطبيب/الحالة

### 7.3 واجهة الحجز (Booking)
- **المسار**: `/book`
- **الميزات**:
  - اختيار الطبيب
  - اختيار التاريخ والوقت
  - إدخال بيانات المريض
  - التحقق من رقم الجوال السعودي
  - إرسال WhatsApp

---

## 8. قاعدة البيانات

### 8.1 النوع
SQLite (محلي) → PostgreSQL (إنتاج)

### 8.2 الموقع
`data/nexus.db`

### 8.3 الجداول
```sql
-- المواعيد
appointments (
    id, patient_name, patient_phone, doctor_id,
    scheduled_at, status, source, notes, created_at
)

-- سجل المكالمات
call_logs (
    id, phone, start_time, end_time, duration_seconds,
    call_status, transcript, summary
)

-- عبارات الانتظار
filler_phrases (
    id, text, category, speaker, audio_url, is_active
)

-- الأطباء
doctors (
    id, name, specialty, branch, is_active
)

-- المرضى
patients (
    id, name, phone, national_id, insurance_id
)
```

---

## 9. متغيرات البيئة (.env)

```env
# التطبيق
APP_NAME=Nexus Miracle
APP_ENV=development
DEBUG=true

# Telnyx
TELNYX_API_KEY=your_key
TELNYX_CONNECTION_ID=your_connection_id
TELNYX_PHONE_NUMBER=+966xxxxxxxxx

# ElevenLabs
ELEVENLABS_API_KEY=your_key
ELEVENLABS_VOICE_SARA=voice_id_for_sara
ELEVENLABS_VOICE_NEXUS=voice_id_for_nexus
ELEVENLABS_MODEL=eleven_flash_v2_5

# Google Gemini
GOOGLE_API_KEY=your_key
GEMINI_MODEL=gemini-2.0-flash

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/nexus.db

# الصوت
AUDIO_SAMPLE_RATE=16000
VAD_THRESHOLD=0.5
VAD_MIN_SILENCE_MS=700
```

---

## 10. تشغيل المشروع

### 10.1 المتطلبات
- Python 3.11+
- Node.js 20+
- Git

### 10.2 تثبيت Backend
```bash
cd c:\Users\omarm\Nexus
pip install -r requirements.txt
```

### 10.3 تشغيل Backend
```bash
python -m uvicorn app.main:app --reload --port 8000
```

### 10.4 تثبيت Frontend
```bash
cd frontend
npm install
```

### 10.5 تشغيل Frontend
```bash
npm run dev
# يعمل على http://localhost:3001
```

### 10.6 الروابط
- **Backend API**: http://localhost:8000/docs
- **Frontend**: http://localhost:3001
- **Admin Panel**: http://localhost:3001/admin
- **Booking**: http://localhost:3001/book

---

## 11. Docker

### 11.1 تشغيل محلي
```bash
docker-compose up --build
```

### 11.2 الخدمات
| الخدمة | Port | الوصف |
|--------|------|-------|
| backend | 8000 | FastAPI |
| frontend | 3000 | Next.js |
| redis | 6379 | Cache/PubSub |

---

## 12. الاختبارات

### 12.1 اختبارات الوحدات
```bash
python -m pytest tests/integration/ -v
```

### 12.2 اختبار الحمل
```bash
python scripts/load_test.py
```
**النتائج المتوقعة**:
- 100 req/s
- Latency < 100ms
- Error rate < 1%

### 12.3 اختبارات التكامل
```bash
python scripts/integration_tests.py
```

### 12.4 اختبار AI Pipeline
```bash
python scripts/test_ai_pipeline.py
```

---

## 13. النشر (Deployment)

### 13.1 Railway (الحالي)
- URL: https://nexus-miracle.up.railway.app

### 13.2 Google Cloud Run (المستقبل)
- Region: me-central1 (Qatar)
- Database: Cloud SQL (PostgreSQL)
- Redis: Memorystore

---

## 14. حالة المشروع

### 14.1 ما تم إنجازه ✅
- [x] Phase 1-5: AI Pipeline (VAD, ASR, LLM, TTS)
- [x] Phase 6: Patient Booking Interface
- [x] Phase 7: Admin Calendar
- [x] Phase 8: Integration & Load Tests
- [x] Event Bus
- [x] Circuit Breaker
- [x] Docker Compose

### 14.2 ما يحتاج إكمال ⏳
- [ ] WebSocket للتحديثات اللحظية
- [ ] PostgreSQL migration
- [ ] Cloud Run deployment
- [ ] Real Telnyx integration testing
- [ ] WhatsApp API integration

---

## 15. ملاحظات هامة

1. **لا ترفع `.env` على GitHub** - يحتوي مفاتيح سرية
2. **الـ Frontend يعمل على port 3001** وليس 3000
3. **الـ APIs تحت `/api/admin/`** وليس `/api/` مباشرة
4. **SQLite للتطوير فقط** - استخدم PostgreSQL للإنتاج
5. **الأوامر تعلق أحياناً** - شغلها يدوياً في PowerShell

---

*آخر تحديث: 2026-01-10*
