# 🚀 Full-Stack Job Processing & Identity API

This project is a powerful, production-ready Full-Stack web application powered by a scalable asynchronous **Python FastAPI backend**. 

To visually demonstrate the complex backend systems working seamlessly in real-time, a minimal **Next.js React dashboard** was built strictly as a frontend interaction layer. The core architectural focus of this project is entirely on the Backend Engineering!

It is designed to solve three major backend problems elegantly:
1. 🔐 **User Authentication:** Users register and log in securely via `bcrypt` hashed passwords and `JWT Bearer Tokens`.
2. 🔑 **API Key Generation & Rate Limiting:** Authenticated users provision unique API keys linked statically to their ID. The backend absolutely enforces a **5 request per minute** sliding-window usage limit on these keys, exposing live metrics over tracking endpoints.
3. ⚙️ **Background Job Processing:** Users submit simulated heavy tasks. The backend queues and executes them instantly using native FastAPI `BackgroundTasks`, transitioning the state smoothly inside the database from `pending` ⏳ -> `in_progress` 🔄 -> `completed` ✅.

---

## 🛠 Tech Stack

**Backend (Core System):**
* 🐍 Python (>= 3.11)
* ⚡ FastAPI + Uvicorn
* 💾 SQLite + SQLAlchemy (Async engine)
* 📦 Package Manager: `uv`
* 🛡️ Security: `passlib` (bcrypt), `PyJWT`, CORS Middleware

**Frontend (Visualization Layer):**
* ⚛️ Next.js + React (App Router)
* 🎨 Tailwind CSS

---

## 💻 How to Run the Project Locally

Follow these exact steps to clone the repository and boot the local environments on your machine safely.

### 1. Repository Setup & Backend API Configuration (FastAPI) 
The backend handles the entire SQLite database mapping natively via Python. We will use the lightning-fast `uv` package manager to build the dependencies.

Open your terminal and execute:
```bash
# 1. Clone the repository down to your machine
git clone https://github.com/Praroop1435/job-processing.git
cd job-processing

# 2. Sync all Python dependencies flawlessly using uv
uv sync

# 3. Boot the FastAPI Server via uvicorn
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
You can view the Auto-Generated Backend Swagger Documentation at **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**.

### 2. Start the Frontend Dashboard (Next.js)
The frontend serves exclusively as the visual testing suite connecting to the backend logic via standard REST hooks.

Open a **new separate terminal window**:
```bash
# 1. Navigate strictly into the frontend folder
cd job-processing/frontend

# 2. Install standard Node modules
npm install

# 3. Boot the Next.js development server
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser! Register an arbitrary account (e.g., `user@test.com` & `123123`) to pierce the secure dashboard gateway.

---

## 🧠 Backend System Architecture

Because this repository strictly demonstrates backend data processing and security logic, here is exactly what is happening underneath the hood:

### 🧩 The SQLite Relational Database (`aiosqlite`)
The entire application dynamically builds relationships utilizing asynchronous SQLAlchemy mapping. All data is managed across three distinct tables: `UserDB`, `APIKeyDB`, and `JobDB`. To maintain strict encapsulation, every single `APIKeyDB` generated must point internally to a `user_id` Foreign Key strictly belonging to a registered `UserDB` identity.

### 🛡️ Authentication Protocol (`auth.py`)
Registration operates strictly over `pydantic[email]` validations. We intercept raw passwords dynamically, hash them natively applying standard `passlib` `bcrypt==3.2.2`, and return active `PyJWT` tokens via `Oauth2` bearer sequences to lock downstream access seamlessly.

### 🚦 Sliding-Window Rate Limiting (`services.py`)
Unlike generic token-bucket limiting logic, this engine leverages strict timestamp calculations directly out of the persistent `job_processing.db`! When protected endpoints are slammed with fetch requests, the database specifically checks if `last_reset` exceeds 60 seconds. If `request_count` hits the hardcoded limit naturally within the active window, the backend throws a strict `HTTP 429 Too Many Requests` restriction exception instantly!

### ⏳ Asynchronous Background Workers (`main.py`)
Utilizing high-performance `BackgroundTasks`, heavy backend execution logic occurs silently *after* the client perfectly receives an HTTP `202 Accepted` confirmation mapping back their unique `job_id`. The backend safely spawns native non-blocking wait routines (`asyncio.sleep()`) and completely transitions SQL database states independent of the main Python thread.

---

## 🧪 Postman Developer Testing
If you would like to test the backend API completely independently of the visual Next.js frontend, this repository includes an explicitly configured Postman file.

Simply import `postman_collection.json` into Postman. It includes automatic Authentication token tracking scripts that dynamically construct your Bearer Headers specifically for testing the Rate-limiter seamlessly!
