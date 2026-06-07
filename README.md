# Valdenmoor

AI destekli krallık yönetim RPG'si. React Native Web frontend + FastAPI backend + Supabase + Gemini.

## Hızlı başlangıç (Windows)

Proje kökünde `tek-tik-baslat.bat` dosyasına çift tıklayın.

| Servis   | Adres                    |
|----------|--------------------------|
| Frontend | http://localhost:5173    |
| Backend  | http://localhost:8001    |

## Manuel kurulum

### 1. Ortam değişkenleri

```powershell
copy .env.example .env
```

### 2. Supabase migration'ları

Supabase Dashboard → **SQL Editor**'da sırayla çalıştırın:

1. `database/schema.sql` — temel tablolar (yeni proje)
2. `database/migrations/001` – `009` dosyaları

### 3. Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn backend.main:app --reload --port 8001
```

### 4. Frontend

```powershell
cd frontend
npm install
npx serve . -l 5173
```

## Proje yapısı

```
backend/          FastAPI API (chat, game state)
frontend/         Web arayüzü (React Native Web)
database/         schema.sql, migrations/, seed_data/
```

## Önemli API uçları

| Endpoint | Açıklama |
|----------|----------|
| `POST /api/chat` | AI sohbet (SSE) — game_stats ve character_relations prompt'a enjekte edilir |
