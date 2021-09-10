build:
	yarn run build

dev:
	docker run -it -p 127.0.0.1::3000 -v "${PWD}:/app" -w /app --entrypoint sh node:16-alpine3.14

test:
	docker run -it -p 127.0.0.1::3000 -v "${PWD}:/app" -w /app --entrypoint sh node:16-alpine3.14 /usr/local/bin/yarn test

start:
	id="$$(docker run -it -d -p 127.0.0.1::3000 -v "${PWD}:/app" -w /app node:16-alpine3.14 /usr/local/bin/yarn start)" \
		&& port="$$(docker port "$${id}" | cut -d: -f2)" \
		&& open "http://localhost:$${port}" \
		&& docker attach "$$id"
