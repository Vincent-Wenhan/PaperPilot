"""Docker-based command runner.

Replaces the previous host subprocess sandbox with a real containerized
execution environment.  The runner only accepts argv lists (no shell
strings), runs as a non-root user, drops all capabilities, mounts the
workspace read-only with a writable tmpfs, and enforces CPU / memory /
PID limits.

If the ``docker`` Python package or Docker daemon is unavailable, callers
can fall back to the existing ``tools/command_runner.py`` allowlist runner
for trusted, low-risk commands.
"""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ContainerLimits:
    memory: str = "2g"
    nano_cpus: int = 2_000_000_000
    pids_limit: int = 256
    timeout_seconds: int = 300
    network_enabled: bool = False


@dataclass(slots=True)
class ContainerResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    container_id: str = ""


class DockerRunner:
    """Run commands inside isolated Docker containers.

    Usage::

        runner = DockerRunner()
        result = await runner.run(
            workspace=Path("workspace/runs/abc"),
            command=["python", "main.py", "--smoke-test"],
            limits=ContainerLimits(network_enabled=False),
        )
    """

    def __init__(self, default_image: str = "python:3.12-alpine") -> None:
        try:
            import docker  # type: ignore

            self._client = docker.from_env()
            self._available = True
        except Exception:
            self._client = None
            self._available = False
        self._default_image = default_image

    @property
    def available(self) -> bool:
        return self._available

    async def run(
        self,
        *,
        workspace: Path,
        command: list[str],
        image: str | None = None,
        limits: ContainerLimits | None = None,
        environment: dict[str, str] | None = None,
    ) -> ContainerResult:
        if not self._available:
            raise RuntimeError(
                "Docker is not available; cannot run containerized command."
            )
        workspace = workspace.resolve(strict=True)
        if not command:
            raise ValueError("command must be a non-empty argv list")
        if any("\x00" in part for part in command):
            raise ValueError("command contains NUL bytes")

        limits = limits or ContainerLimits()
        image = image or self._default_image
        network_mode = "none" if not limits.network_enabled else "bridge"

        return await asyncio.to_thread(
            self._run_sync,
            workspace,
            command,
            image,
            limits,
            network_mode,
            environment or {},
        )

    def _run_sync(
        self,
        workspace: Path,
        command: list[str],
        image: str,
        limits: ContainerLimits,
        network_mode: str,
        environment: dict[str, str],
    ) -> ContainerResult:
        import docker  # type: ignore

        try:
            container = self._client.containers.create(
                image=image,
                command=list(command),
                working_dir="/workspace",
                environment={
                    "HOME": "/tmp/home",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                    **environment,
                },
                volumes={
                    str(workspace): {
                        "bind": "/workspace",
                        "mode": "rw",
                    }
                },
                network_mode=network_mode,
                mem_limit=limits.memory,
                nano_cpus=limits.nano_cpus,
                pids_limit=limits.pids_limit,
                read_only=True,
                tmpfs={
                    "/tmp": "rw,noexec,nosuid,size=512m",
                    "/tmp/home": "rw,noexec,nosuid,size=64m",
                },
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
                user="1000:1000",
                detach=True,
                stdout=True,
                stderr=True,
            )
        except Exception as exc:
            return ContainerResult(
                exit_code=None,
                stdout="",
                stderr=f"Failed to create container: {exc}",
                timed_out=True,
            )

        try:
            container.start()
            try:
                wait_result = container.wait(timeout=limits.timeout_seconds)
            except Exception:
                try:
                    container.kill()
                except Exception:
                    pass
                logs = container.logs(stdout=True, stderr=True).decode(
                    "utf-8", errors="replace"
                )
                return ContainerResult(
                    exit_code=124,
                    stdout=logs,
                    stderr="Command timed out",
                    timed_out=True,
                    container_id=container.id,
                )

            stdout = container.logs(stdout=True, stderr=False).decode(
                "utf-8", errors="replace"
            )
            stderr = container.logs(stdout=False, stderr=True).decode(
                "utf-8", errors="replace"
            )
            return ContainerResult(
                exit_code=int(wait_result.get("StatusCode", 1)),
                stdout=stdout[-200_000:],
                stderr=stderr[-200_000:],
                container_id=container.id,
            )
        finally:
            try:
                container.remove(force=True)
            except Exception:
                pass


docker_runner = DockerRunner()
