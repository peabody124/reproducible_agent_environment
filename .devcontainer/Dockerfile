FROM mcr.microsoft.com/devcontainers/python:3.11

RUN apt-get update && apt-get install -y ripgrep && rm -rf /var/lib/apt/lists/*

USER vscode
RUN curl -fsSL https://claude.ai/install.sh | bash
RUN pip install pyright

ENV PATH="/home/vscode/.local/bin:${PATH}"
