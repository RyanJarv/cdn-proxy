
dev: dev/build dev/run

dev/build:
	docker build -t cdn-proxy -f Dockerfile.dev .

dev/run:
	docker run -it -v "${PWD}:/usr/src/cdn-proxy" -w /usr/src/cdn-proxy cdn-proxy

lint:
	pylint --rcfile=.pylint.ini cdn_proxy

test:
	python3 -m pytest ./tests/test_unit.py ./tests/test_lambda_request.py

