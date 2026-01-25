# Injury Risk Detector - Backend

FastAPI backend for injury risk prediction and training recommendations.

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose

### Setup

1. **Start PostgreSQL and Redis:**
   ```bash
   docker-compose up -d
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create .env file:**
   ```bash
   cp .env.example .env
   ```

5. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

7. **Open API docs:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

### Users
- `POST /api/v1/users` - Create user
- `GET /api/v1/users/me` - Get current user
- `PATCH /api/v1/users/me` - Update current user

### Workouts
- `POST /api/v1/workouts` - Log workout
- `GET /api/v1/workouts` - List workouts
- `GET /api/v1/workouts/{id}` - Get workout

### Symptoms
- `POST /api/v1/symptoms` - Log symptoms
- `GET /api/v1/symptoms/today` - Get today's entry
- `GET /api/v1/symptoms` - List symptoms

### Planned Sessions
- `POST /api/v1/planned-sessions` - Plan session
- `GET /api/v1/planned-sessions` - List sessions
- `GET /api/v1/planned-sessions/upcoming` - Get next session
- `POST /api/v1/planned-sessions/{id}/complete` - Mark completed

### Predictions
- `POST /api/v1/predictions/evaluate` - Evaluate risk for session
- `POST /api/v1/predictions/quick-evaluate` - Quick risk evaluation
- `GET /api/v1/predictions/{session_id}` - Get prediction details
- `POST /api/v1/predictions/labels` - Create ML training label

## Testing

```bash
pytest tests/ -v
```

## Project Structure

```
backend/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   │   ├── safety_rules.py    # R0-R4 safety gates
│   │   ├── risk_scorer.py     # Heuristic scoring
│   │   └── recommender.py     # Recommendations
│   └── ml/              # ML pipeline
│       ├── features.py        # Feature engineering
│       └── baseline.py        # User baseline calculation
├── alembic/             # Database migrations
├── tests/               # pytest tests
├── docker-compose.yml   # PostgreSQL + Redis
└── requirements.txt     # Dependencies
```

## Risk Score Thresholds

| Score | Level  | Meaning |
|-------|--------|---------|
| 0-35  | Green  | Training as planned |
| 36-60 | Yellow | Modification recommended |
| 61-100| Red    | Recovery recommended |

## Safety Rules

- **R0:** Acute pain (≥7) or swelling → RED
- **R1:** Moderate pain (5-6) → No impact sports
- **R2:** High DOMS (≥7) in target muscles → Avoid that muscle group
- **R3:** Poor HRV + elevated RHR → Max Z2
- **R4:** Already hard session today → Second session easy
