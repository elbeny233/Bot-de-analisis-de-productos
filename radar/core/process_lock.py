import os
from pathlib import Path


class MonitorAlreadyRunning(RuntimeError):
    pass


class ProcessLock:
    """Bloqueo del SO liberado incluso al terminar abruptamente el proceso."""

    def __init__(self, path: Path):
        self.path = path
        self.file = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            handle.close()
            raise MonitorAlreadyRunning(
                "Ya existe un monitor usando esta base de datos. Detén la otra instancia."
            ) from error
        self.file = handle
        return self

    def release(self):
        if self.file is not None:
            try:
                if os.name == "nt":
                    import msvcrt

                    self.file.seek(0)
                    msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
            finally:
                self.file.close()
                self.file = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *_):
        self.release()
