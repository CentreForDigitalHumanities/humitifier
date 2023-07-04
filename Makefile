styles:
	sass web/style.scss static/out.css

docker-build-dev: styles
	docker build -t humitifier-dev:latest .

docker-run-dev:
	docker run -p 8000:8000 humitifier-dev

dev-server:
	python dev.py