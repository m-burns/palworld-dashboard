import os

import psutil

from app.models import InfrastructureMetrics


class InfrastructureService:
    def __init__(self) -> None:
        procfs_path = os.getenv("PSUTIL_PROCFS_PATH")

        if procfs_path:
            psutil.PROCFS_PATH = procfs_path

    def get_metrics(self) -> InfrastructureMetrics:
        return InfrastructureMetrics(
            cpu_percent=round(
                psutil.cpu_percent(interval=0.2),
                1,
            ),
        )
