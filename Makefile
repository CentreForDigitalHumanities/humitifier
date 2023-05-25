docker-build:
	docker build -t humitifier-app .

docker-run:
	docker run -p 8080:8080 humitifier-app

dev-server:
	ENVIRONMENT="dev" uvicorn humitifier.app:app --port 8000