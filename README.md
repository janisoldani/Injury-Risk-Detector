# Injury Risk Detector

A comprehensive system for predicting training injury risk based on physiological data (HRV, sleep, RHR), symptoms, and planned training sessions.

## Features

- **Risk Score (0-100)** with traffic light visualization (Green/Yellow/Red)
- **Safety Rules** - Deterministic rules that override ML predictions for critical situations
- **HRV Analysis** - Z-score normalization against 28-day baseline
- **ACWR Monitoring** - Acute:Chronic Workload Ratio for load management
- **FIT File Import** - Parse Garmin and other FIT format files
- **Session Planner** - Real-time risk preview for planned workouts
- **Alternative Recommendations** - Suggested safer workout alternatives

## Tech Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **SQLAlchemy 2.0** - Async ORM with PostgreSQL/SQLite support
- **Pydantic v2** - Data validation and serialization
- **Alembic** - Database migrations

### Frontend
- **React 18** with TypeScript
- **Vite** - Fast build tool
- **TailwindCSS** - Utility-first CSS
- **TanStack Query** - Data fetching and caching
- **Recharts** - Data visualization

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (optional, for PostgreSQL)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend runs at `http://localhost:3000` and proxies API requests to the backend.

## Verification

### Run Backend Tests

```bash
cd backend
pytest -v
```

### Run Frontend Tests

```bash
cd frontend
npm run test
```

### Build Frontend

```bash
cd frontend
npm run build
npm run lint
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Business logic
│   │       ├── safety_rules.py    # R0-R4 safety rules
│   │       ├── risk_scorer.py     # Heuristic scoring
│   │       ├── recommender.py     # Alternatives engine
│   │       ├── fit_parser.py      # FIT file processor
│   │       └── scoring_config.py  # Configurable thresholds
│   ├── config/
│   │   └── scoring_config.yaml    # Tunable parameters
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Route pages
│   │   ├── lib/             # API client, utilities
│   │   └── types/           # TypeScript types
│   └── tests/
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/predictions/{user_id}` | POST | Get risk prediction |
| `/api/v1/imports/fit` | POST | Upload FIT file |
| `/api/v1/symptoms/{user_id}` | POST | Log symptoms |
| `/api/v1/planned-sessions/{user_id}` | POST | Plan a session |
| `/api/v1/workouts/{user_id}` | GET | List workouts |
| `/api/v1/users/{user_id}` | GET | Get user profile |

## Safety Rules

| Rule | Trigger | Action |
|------|---------|--------|
| R0 | Pain ≥ 7 or Swelling | Force RED |
| R1 | Illness or Fever | Force RED |
| R2 | Consecutive Rest Days > 3 | Warn on return |
| R3 | HRV < -2.0 z-score | Force YELLOW |
| R4 | ACWR > 1.5 | Force YELLOW |

## Configuration

Scoring thresholds can be tuned without code changes via `backend/config/scoring_config.yaml`:

```yaml
hrv:
  severe_threshold: -1.5
  severe_points: 25
  moderate_threshold: -1.0
  moderate_points: 15
acwr:
  critical_threshold: 1.5
  critical_points: 25
```

## Roadmap

- [x] v1 MVP - Backend + Frontend with heuristic scoring
- [ ] v2 - Apple HealthKit integration
- [ ] v3 - Multi-user cloud deployment
- [ ] v4 - ML model training with user feedback

## License

Private project - All rights reserved.
