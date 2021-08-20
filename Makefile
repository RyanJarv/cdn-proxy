
dev: dev/build dev/run

dev/build:
	docker build -t cdn-proxy -f Dockerfile.dev .

dev/run:
	docker run -it cdn-proxy
