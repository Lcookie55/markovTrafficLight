# Smart Traffic Light Control with a Markov Decision Process

Design: `AI Final Term Report.docx`. Build plan: [PLAN.md](PLAN.md).

- `core/mtl/` – the Python MDP project (simulator, 96-state model, Value/Policy Iteration, Q-Learning, controllers, safety layer, experiments)
- `api/` – FastAPI: REST + WebSocket live stream
- `web/` – React + Vite + TypeScript visualization
- `configs/scenarios.json` – all parameters and scenarios S1–S5
- `outputs/` – `policy_*.csv`, `results.csv`, `summary.csv`, model/Q-learning checks

## Setup (Windows / PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e "core[dev]"
cd web; npm install; npm run build; cd ..
```

## Run the demo (one process)

```powershell
.venv\Scripts\python -m uvicorn api.main:app --port 8000
```

Open http://localhost:8000. Views: **Live simulation** (MDP vs a second controller on identical arrivals), **Policy explorer** (change γ / switching cost and re-solve), **Benchmark** (S1–S5 table and charts).

Hot-reload development: run `uvicorn api.main:app --reload --port 8000` and `cd web; npm run dev` (http://localhost:5173, proxies `/api` and `/ws`).

## Reproduce the numbers

```powershell
.venv\Scripts\python core\scripts\solve.py             # policy tables, VI == PI check
.venv\Scripts\python core\scripts\run_experiments.py   # S1-S5 x 5 seeds x 4 controllers, model-vs-sim, Q-learning
```

## Tests

```powershell
cd core; ..\.venv\Scripts\python -m pytest            # simulator, safety, model, solvers
cd ..; .venv\Scripts\python -m pytest api\tests       # REST + WebSocket
cd web; npm test                                      # frontend reducer
```

## Modelling choices beyond the report

These are assumptions I made where the report was silent. They are all set in `configs/scenarios.json`.

| Choice | Value |
|---|---|
| Effective lanes per approach | 1.4 (an axis discharges 7 veh per 5 s step). It was picked so that S2 is heavily loaded, S3/S4 are loaded but stable, and S1 is light. |
| SWITCH step | 5 s = 3 s yellow + 1 s all-red + 1 s of the new green; the elapsed counter then restarts at 0 |
| Controller types | `mdp` (policy solved for the scenario's mean λ), `mdp_nominal` (one policy solved at λ = 0.2 / 0.2), `fixed` (30/30), `lqf` (longest-queue-first, margin 2) |
| S5 model rate | time-averaged λ (0.142) because the model needs one constant rate |
| Bucket approximation | exact queue count uniform within its level; elapsed step uniform within its bucket |
