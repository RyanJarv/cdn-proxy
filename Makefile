
dev: dev/build dev/run

dev/build:
	docker build -t cdn-proxy -f Dockerfile.dev .

dev/run:
	docker run -it -v "${PWD}:/usr/src/cdn-proxy" -w /usr/src/cdn-proxy cdn-proxy


PACKAGE := pacu
MODULES := $(wildcard $(PACKAGE)/*.py)


.PHONY: watch
watch: install .clean-test ## Continuously run all CI tasks when files chanage
	poetry run sniffer
