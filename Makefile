.PHONY: setup start stop clean frontend-deps backend-deps dev help

# Store process IDs in files for easier management
BACKEND_PID_FILE := .backend.pid
FRONTEND_PID_FILE := .frontend.pid

help:
	@echo "Apartment Finder Development Commands"
	@echo "-------------------------------------"
	@echo "make setup          - Set up development environment (venv, dependencies)"
	@echo "make start          - Start both backend and frontend servers"
	@echo "make stop           - Stop all running servers"
	@echo "make clean          - Remove virtual environment and other generated files"
	@echo "make backend-deps   - Install/update backend dependencies using UV"
	@echo "make frontend-deps  - Install/update frontend dependencies"

setup: backend-deps frontend-deps
	@echo "✅ Development environment is ready!"

backend-deps:
	@echo "Setting up Python environment..."
	@if [ ! -d "venv" ]; then \
		python3 -m venv venv; \
	fi
	@. venv/bin/activate && \
	if ! command -v uv &> /dev/null; then \
		echo "Installing UV..."; \
		pip install uv; \
	fi
	@echo "Installing backend dependencies with UV..."
	@. venv/bin/activate && cd backend && uv pip install -r requirements.txt
	@echo "✅ Backend dependencies installed"

frontend-deps:
	@echo "Installing frontend dependencies..."
	@if [ ! -d "frontend/node_modules" ]; then \
		cd frontend && npm install; \
	fi
	@echo "✅ Frontend dependencies installed"

start: stop
	@echo "🚀 Starting development servers..."
	@echo "Ensuring ports are available..."
	@-lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	
	@echo "Starting backend server..."
	@. venv/bin/activate && cd backend && \
	python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 & echo $$! > $(BACKEND_PID_FILE)
	
	@sleep 2
	
	@echo "Starting frontend server..."
	@cd frontend && npm run dev & echo $$! > $(FRONTEND_PID_FILE)
	
	@echo "✅ Development servers are running"
	@echo "- Backend: http://localhost:8000"
	@echo "- Frontend: Check the terminal output (likely http://localhost:5173)"
	@echo "- Use 'make stop' to stop the servers"

stop:
	@echo "🛑 Shutting down development servers..."
	
	@# Stop browser processes
	@-pkill -f "chromium" 2>/dev/null || echo "No Chromium processes found"
	@-pkill -f "chrome" 2>/dev/null || echo "No Chrome processes found"
	
	@# Stop backend processes
	@if [ -f $(BACKEND_PID_FILE) ]; then \
		pid=$$(cat $(BACKEND_PID_FILE)); \
		echo "Stopping backend (PID: $$pid)..."; \
		kill -9 $$pid 2>/dev/null || true; \
		rm $(BACKEND_PID_FILE); \
	fi
	@-lsof -ti:8000 | xargs kill -9 2>/dev/null || echo "No processes on port 8000"
	
	@# Stop frontend processes
	@if [ -f $(FRONTEND_PID_FILE) ]; then \
		pid=$$(cat $(FRONTEND_PID_FILE)); \
		echo "Stopping frontend (PID: $$pid)..."; \
		kill -9 $$pid 2>/dev/null || true; \
		rm $(FRONTEND_PID_FILE); \
	fi
	@-lsof -ti:3000,5173,5174,5175 | xargs kill -9 2>/dev/null || echo "No processes on frontend ports"
	
	@# Kill any remaining processes
	@-pkill -f "uvicorn" 2>/dev/null || echo "No uvicorn processes found"
	@-pkill -f "fastapi" 2>/dev/null || echo "No FastAPI processes found"
	@-pkill -f "remix vite:dev" 2>/dev/null || echo "No Remix processes found"
	@-pkill -f "vite" 2>/dev/null || echo "No Vite processes found"
	@-pkill -f "apartment_finder" 2>/dev/null || echo "No apartment finder processes found"
	
	@echo "✅ All processes have been stopped"

clean: stop
	@echo "🧹 Cleaning up development environment..."
	@if [ -d "venv" ]; then \
		echo "Removing virtual environment..."; \
		rm -rf venv; \
	fi
	@echo "Removing temporary files..."
	@rm -f $(BACKEND_PID_FILE) $(FRONTEND_PID_FILE)
	@echo "✅ Cleanup complete"

# Default target
.DEFAULT_GOAL := help 