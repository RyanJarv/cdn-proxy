build:
	yarn run build

dev:
	docker run -it -p 127.0.0.1::3000 -v "${PWD}:/app" -w /app --entrypoint sh node:16-alpine3.14

test:
	docker run -it -p 127.0.0.1::3000 -v "${PWD}:/app" -w /app --entrypoint sh node:16-alpine3.14 yarn test

start:
	docker run -it -p 127.0.0.1::3000 -v "${PWD}:/app" -w /app --entrypoint sh node:16-alpine3.14 yarn start
