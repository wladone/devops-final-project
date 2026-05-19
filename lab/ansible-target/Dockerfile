FROM docker:27-cli AS dockercli

FROM ubuntu:24.04

ARG TARGET_USER=devops
ARG TARGET_PASSWORD=devops123!

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        openssh-server \
        python3 \
        sudo \
    && rm -rf /var/lib/apt/lists/*

COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=dockercli /usr/local/libexec/docker/cli-plugins /usr/local/libexec/docker/cli-plugins

RUN mkdir -p /var/run/sshd \
    && useradd --create-home --shell /bin/bash "${TARGET_USER}" \
    && echo "${TARGET_USER}:${TARGET_PASSWORD}" | chpasswd \
    && usermod -aG sudo "${TARGET_USER}" \
    && printf "%s ALL=(ALL) NOPASSWD:ALL\n" "${TARGET_USER}" > "/etc/sudoers.d/${TARGET_USER}" \
    && chmod 440 "/etc/sudoers.d/${TARGET_USER}"

COPY sshd_config /etc/ssh/sshd_config

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D", "-e"]
