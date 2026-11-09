"""Trusted in-container exporter. Invoked with python -I -c, never as job code."""

import io
import os
import signal
import stat
import sys
import tarfile


def main():
    # Terminate surviving descendants before reading output. This exec has a
    # separate stdout stream and the same unprivileged UID as the job.
    own = os.getpid()
    stopped = set()
    for _ in range(8):
        pending = []
        for entry in os.listdir("/proc"):
            if entry.isdigit() and int(entry) not in {1, own}:
                pid = int(entry)
                if pid not in stopped:
                    pending.append(pid)
        if not pending:
            break
        for pid in pending:
            try:
                os.kill(pid, signal.SIGSTOP)
                stopped.add(pid)
            except ProcessLookupError:
                pass
    else:
        raise ValueError("Unable to quiesce job processes")
    for pid in stopped:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    directory = os.open("/tmp/output", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        names = os.listdir(directory)
        if len(names) > 5:
            raise ValueError("Too many artifacts")
        with tarfile.open(
            fileobj=sys.stdout.buffer, mode="w|", format=tarfile.USTAR_FORMAT
        ) as archive:
            for name in sorted(names):
                descriptor = os.open(
                    name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=directory
                )
                try:
                    info = os.fstat(descriptor)
                    if not stat.S_ISREG(info.st_mode) or info.st_size > 1048576:
                        raise ValueError("Invalid artifact")
                    data = os.read(descriptor, 1048577)
                    if len(data) != info.st_size:
                        raise ValueError("Artifact changed")
                    item = tarfile.TarInfo("output/" + name)
                    item.size = len(data)
                    archive.addfile(item, io.BytesIO(data))
                finally:
                    os.close(descriptor)
    finally:
        os.close(directory)


if __name__ == "__main__":
    main()
