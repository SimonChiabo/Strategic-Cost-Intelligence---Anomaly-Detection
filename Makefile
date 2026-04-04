.PHONY: setup migrate generate-data db-up db-down

setup:
	python -m venv venv
	.\venv\Scripts\python -m pip install --upgrade pip
	.\venv\Scripts\pip install -r requirements.txt
	.\venv\Scripts\pre-commit install || echo "Configure pre-commit hooks in .pre-commit-config.yaml later"

db-up:
	docker-compose up -d

db-down:
	docker-compose down -v

migrate:
	.\venv\Scripts\alembic upgrade head

generate-data:
	.\venv\Scripts\python src/ingestion/mock_data_generator.py
