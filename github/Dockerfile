# Container image that runs your code
FROM alpine:3.14

RUN apk update && apk add --no-cache \
	openssh-server \
	wget \
	openrc

RUN sed -i -e 's/AllowTcpForwarding no/AllowTcpForwarding yes/' /etc/ssh/sshd_config && \
	passwd -d root

RUN wget -O ngrok.zip https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip && \
	unzip ngrok.zip && \
	cp ngrok /usr/local/bin

# Copies your code file from your action repository to the filesystem path `/` of the container
COPY github/entrypoint.sh /entrypoint.sh

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["/entrypoint.sh"]
