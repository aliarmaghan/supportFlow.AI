# Development helper script for full stack

param(
    [Parameter(Mandatory=$false)]
    [string]$Command = "help"
)

switch ($Command) {
    "start" {
        Write-Host " Starting full development stack..." -ForegroundColor Green
        docker-compose up -d
        Write-Host " Services started!" -ForegroundColor Green
        Write-Host " Access Points:" -ForegroundColor Cyan
        Write-Host "  - API: http://localhost:8000/docs" -ForegroundColor White
        Write-Host "  - Flower (Celery): http://localhost:5555" -ForegroundColor White
        Write-Host "  - Redis UI: http://localhost:8081" -ForegroundColor White
        Write-Host "  - PgAdmin: http://localhost:5050" -ForegroundColor White
        Write-Host "  - Prometheus:  http://localhost:9090" -ForegroundColor White
        Write-Host "  - Grafana: http://localhost:3000" -ForegroundColor White
    }
    "stop" {
        Write-Host " Stopping all services..." -ForegroundColor Yellow
        docker-compose stop
    }
    "restart" {
        Write-Host " Restarting services..." -ForegroundColor Yellow
        docker-compose restart
    }
    "logs" {
        docker-compose logs -f
    }
    "logs-api" {
        docker-compose logs -f api
    }
    "logs-celery" {
        docker-compose logs -f celery_worker
    }
    "test" {
        Write-Host " Running tests..." -ForegroundColor Cyan
        python src/test_production.py
    }
    "test-api" {
        Write-Host " Running API tests..." -ForegroundColor Cyan
        python test_api.py
    }
    "clean" {
        Write-Host " Cleaning up (will delete all data)..." -ForegroundColor Red
        $confirm = Read-Host "Are you sure? (yes/no)"
        if ($confirm -eq "yes") {
            docker-compose down -v
            Write-Host "✅ Cleaned up!" -ForegroundColor Green
        }
    }
    "build" {
        Write-Host " Building Docker images..." -ForegroundColor Cyan
        docker-compose build
    }
    "status" {
        Write-Host " Service Status:" -ForegroundColor Cyan
        docker-compose ps
    }
    "shell-api" {
        Write-Host " Opening API container shell..." -ForegroundColor Cyan
        docker-compose exec api bash
    }
    "shell-db" {
        Write-Host " Opening database shell..." -ForegroundColor Cyan
        docker-compose exec postgres psql -U support_user -d support_db
    }
    "migrate" {
        Write-Host " Running database migrations..." -ForegroundColor Cyan
        alembic upgrade head
    }
    "dev-api" {
        Write-Host " Starting API in local development mode..." -ForegroundColor Green
        uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
    }
    "dev-celery" {
        Write-Host " Starting Celery worker in local development mode..." -ForegroundColor Green
        celery -A celery_app worker --loglevel=info --concurrency=4
    }
    "dev-flower" {
        Write-Host " Starting Flower monitoring..." -ForegroundColor Green
        celery -A celery_app flower --port=5555
    }
    default {
        Write-Host "Available commands:" -ForegroundColor Yellow
        Write-Host "Docker Commands:" -ForegroundColor Cyan
        Write-Host "  start       - Start all services in Docker"
        Write-Host "  stop        - Stop all services"
        Write-Host "  restart     - Restart services"
        Write-Host "  build       - Rebuild Docker images"
        Write-Host "  clean       - Remove all containers and data"
        Write-Host "  status      - Check service status"
        Write-Host "Logs:" -ForegroundColor Cyan
        Write-Host "  logs        - View all logs"
        Write-Host "  logs-api    - View API logs"
        Write-Host "  logs-celery - View Celery logs"
        Write-Host " Testing:" -ForegroundColor Cyan
        Write-Host "  test        - Run production tests"
        Write-Host "  test-api    - Run API tests"
        Write-Host "Development:" -ForegroundColor Cyan
        Write-Host "  dev-api     - Run API locally (not in Docker)"
        Write-Host "  dev-celery  - Run Celery locally (not in Docker)"
        Write-Host "  dev-flower  - Run Flower monitoring"
        Write-Host "  migrate     - Run database migrations"
        Write-Host "Shell Access:" -ForegroundColor Cyan
        Write-Host "  shell-api   - Open API container shell"
        Write-Host "  shell-db    - Open database shell"
    }
}