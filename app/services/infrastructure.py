import os

import psutil

from app.models import InfrastructureMetrics


class InfrastructureService:
    def __init__(self) -> None:
        procfs_path = os.getenv("PSUTIL_PROCFS_PATH")

        if procfs_path:
            psutil.PROCFS_PATH = procfs_path

        self._host_root = os.getenv(
            "HOST_ROOT_PATH",
            "/host/root",
        )

    def get_metrics(self) -> InfrastructureMetrics:
        cpu_percent = psutil.cpu_percent(interval=0.2)

        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage(self._host_root)

        return InfrastructureMetrics(
            cpu_percent=round(cpu_percent, 1),

            memory_used_percent=round(memory.percent, 1),
            memory_used_bytes=memory.used,
            memory_total_bytes=memory.total,

            swap_used_percent=round(swap.percent, 1),
            swap_used_bytes=swap.used,
            swap_total_bytes=swap.total,

            disk_used_percent=round(disk.percent, 1),
            disk_used_bytes=disk.used,
            disk_total_bytes=disk.total,
        )
