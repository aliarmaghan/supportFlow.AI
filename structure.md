customer-support-agent/
│
├── src/
│   ├── __init__.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py                    # FastAPI application
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py                # Configuration settings
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py              # Database manager
│   │   └── migrations/                # Alembic migrations folder
│   │       ├── env.py
│   │       ├── script.py.mako
│   │       └── versions/
│   │           └── xxxx_initial.py    # Migration files
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── cache.py                   # Redis cache manager
│   │   ├── conversation_memory.py     # Original in-memory (Phase 4)
│   │   └── production_memory.py       # Production memory system
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database_models.py         # SQLAlchemy models
│   │   └── ticket_models.py           # Pydantic models
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   └── knowledge_base.py          # Knowledge base search
│   │
│   └── workflows/
│       ├── __init__.py
│       ├── async_tasks.py             # Celery tasks
│       ├── conversation_agent.py      # Production conversation agent
│       └── ticket_classifier.py       # Ticket classification
│
├── data/
│   └── knowledge_base/
│       └── articles.json              # Sample KB articles (optional)
│
├── tests/
│   ├── __init__.py
│   ├── test_classification.py
│   ├── test_conversation.py
│   └── test_memory.py
│
├── .env                               # Environment variables
├── .env.example                       # Example env file
├── .gitignore                         # Git ignore file
├── alembic.ini                        # Alembic configuration
├── celery_app.py                      # Celery application
├── docker-compose.yml                 # Docker compose configuration
├── Dockerfile.api                     # Dockerfile for API
├── Dockerfile.celery                  # Dockerfile for Celery
├── init-db.sql                        # Database initialization
├── requirements.txt                   # Python dependencies
├── dev.ps1                            # Development helper (PowerShell)
├── dev.sh                             # Development helper (Bash)
├── test_api.py                        # API testing script
├── test_production.py                 # ⭐ Production system test (ROOT)
├── test_redis_docker.py               # Redis connection test
├── verify_structure.py                # Project structure verification
└── README.md                          # Project documentation
