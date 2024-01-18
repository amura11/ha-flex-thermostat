#!/usr/bin/env bash

set -e
cd "$(dirname "$0")/.."

# Install HA
python3 -m pip install pip colorlog homeassistant

# See: https://github.com/home-assistant/core/issues/95192
python3 -m pip install git+https://github.com/boto/botocore

# Create directory for HA
if [[ ! -d "${PWD}/.ha" ]]; then
    mkdir -p "${PWD}/.ha"
fi

# Link the configuration
if [[ ! -f "${PWD}/.ha/configuration.yaml" ]]; then
    ln -s "${PWD}/home-assistant/configuration.yaml" "${PWD}/.ha/configuration.yaml"
fi

export PYTHONPATH="${PYTHONPATH}:${PWD}/custom_components"

hass --config "${PWD}/.ha" --script ensure_config

alias ha-run="${PWD}/.devcontainer/run.sh"
alias ha-lint="${PWD}/.devcontainer/lint.sh"