# Devel container
ARG PYTHON_VERSION=3.13.7
ARG UV_VERSION=0.8.17
ARG PULUMI_VERSION=3.200.0

FROM ghcr.io/astral-sh/uv:$UV_VERSION AS uv
FROM pulumi/pulumi-python:$PULUMI_VERSION AS pulumi

FROM python:$PYTHON_VERSION-slim

ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/local/bin:$PATH"
ENV PULUMI_BACKEND_URL=file://~/.pulumi

WORKDIR /app

COPY --from=uv /uv /uvx /usr/local/bin/
COPY --from=pulumi /pulumi/bin/pulumi /usr/local/bin/
COPY --from=pulumi /pulumi/bin/pulumi-language-python /usr/local/bin/
COPY --from=pulumi /pulumi/bin/pulumi-language-python-exec /usr/local/bin/
COPY --from=pulumi /pulumi/bin/pulumi-analyzer-policy-python /usr/local/bin/


COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --compile-bytecode --no-install-project --no-install-workspace --python-preference only-system

COPY . /app

CMD ["pulumi", "version"]
