# Agent Cloud Dashboard

Next.js dashboard for the Agent Cloud platform. Dark-mode-first, minimal UI with system metrics, workflows, agent marketplace, schedules, and system health.

## Stack

- **Next.js 14** (App Router)
- **React 18**, **TypeScript**
- **TailwindCSS** for styling
- **shadcn-style** UI components (Radix primitives)
- **React Flow** for workflow DAG
- **Recharts** for charts

## Setup

```bash
cd dashboard
npm install
cp .env.local.example .env.local
# Edit .env.local: set NEXT_PUBLIC_API_URL to your backend (e.g. http://localhost:8000)
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Backend API

The dashboard expects the Agent Cloud FastAPI backend to be running. If the backend does not allow cross-origin requests, add CORS middleware (e.g. `CORSMiddleware` with `allow_origins=["http://localhost:3000"]`) so the browser can call the API.

Backend endpoints used:

- `GET /system/metrics` — queue, workers, containers, tasks
- `GET /system/workers`, `GET /system/queue`, `GET /system/containers`
- `GET /workflows/:task_id` — workflow view for DAG
- `GET /tasks` — task list (workflows list)
- `GET /agents/store`, `POST /agents/run`
- `GET /schedule`, `POST /schedule`, `DELETE /schedule/:id`

## Routes

| Route | Description |
|-------|-------------|
| `/` | Main dashboard (metrics, charts) |
| `/workflows` | Task list; link to detail |
| `/workflows/[task_id]` | Workflow DAG (React Flow) |
| `/agents` | Agent marketplace, Run agent modal |
| `/schedules` | Schedules list, create, disable |
| `/system` | Workers, queue, container pool |
