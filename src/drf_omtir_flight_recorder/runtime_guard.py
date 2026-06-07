from __future__ import annotations

import os

ENV_DEPLOYMENT_MODE = "DRF_OMTIR_DEPLOYMENT_MODE"

FORBIDDEN_DEPLOYMENT_MODES = {
    "production",
    "prod",
    "enterprise",
    "enterprise_prod",
    "live_enforcement",
}


class DeploymentGuardError(RuntimeError):
    """Raised when the local MVP is started in a forbidden deployment mode."""


def current_deployment_mode() -> str:
    return os.getenv(ENV_DEPLOYMENT_MODE, "local_mvp").strip().lower()


def enforce_local_mvp_scope() -> None:
    mode = current_deployment_mode()

    if mode in FORBIDDEN_DEPLOYMENT_MODES:
        raise DeploymentGuardError(
            "drf-omtir-flight-recorder v0.1.x is a local MVP / "
            "controlled-environment runtime and cannot execute in "
            f"deployment mode: {mode}"
        )
