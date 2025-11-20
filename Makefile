.PHONY: help up down restart logs clean install-backend install-frontend test

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services with Docker Compose
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View logs from all services
	docker-compose logs -f

logs-backend: ## View backend logs
	docker-compose logs -f backend

logs-frontend: ## View frontend logs
	docker-compose logs -f frontend

logs-celery: ## View celery worker logs
	docker-compose logs -f celery_worker

clean: ## Stop services and remove volumes
	docker-compose down -v
	rm -rf backend/__pycache__
	rm -rf backend/app/__pycache__
	rm -rf frontend/.next
	rm -rf frontend/node_modules

install-backend: ## Install backend dependencies locally
	cd backend && pip install -r requirements.txt
	python -m spacy download en_core_web_lg

install-frontend: ## Install frontend dependencies locally
	cd frontend && npm install

dev-backend: ## Run backend locally (outside Docker)
	cd backend && uvicorn app.main:app --reload

dev-frontend: ## Run frontend locally (outside Docker)
	cd frontend && npm run dev

dev-celery: ## Run celery worker locally
	cd backend && celery -A app.celery_worker.celery_app worker --loglevel=info

db-migrate: ## Create a new database migration
	cd backend && alembic revision --autogenerate -m "$(message)"

db-upgrade: ## Apply database migrations
	cd backend && alembic upgrade head

db-downgrade: ## Rollback last migration
	cd backend && alembic downgrade -1

db-shell: ## Access PostgreSQL shell
	docker-compose exec postgres psql -U user -d resume_tool

redis-cli: ## Access Redis CLI
	docker-compose exec redis redis-cli

build: ## Build Docker images
	docker-compose build

rebuild: ## Rebuild Docker images (no cache)
	docker-compose build --no-cache

ps: ## Show running containers
	docker-compose ps

init: ## Initialize project (first time setup)
	@echo "Creating .env file..."
	@if [ ! -f .env ]; then cp .env.example .env; echo ".env created. Please edit it with your configuration."; else echo ".env already exists."; fi
	@echo "Building and starting services..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	sleep 10
	@echo "Setup complete! Visit http://localhost:3000"

