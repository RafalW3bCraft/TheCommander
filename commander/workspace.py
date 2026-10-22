import os
from pathlib import Path

from commander.contracts import Note
from commander.errors import DomainError


class Workspace:
    def __init__(self, root, owner):
        self.root = Path(root).absolute()
        self.owner = str(owner)

    def check(self):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Reject symlinks throughout configured path, including its parents.
        if any(p.is_symlink() for p in [self.root, *self.root.parents]):
            raise DomainError("Workspace must not contain symlinks", 403)
        directory = self.root / self.owner
        directory.mkdir(exist_ok=True, mode=0o700)
        if directory.is_symlink():
            raise DomainError("Workspace symlink denied", 403)
        return directory

    def write(self, name, content):
        note = Note(name=name, content=content)
        directory = self.check()
        dfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fd = os.open(
                note.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd
            )
            with os.fdopen(fd, "w") as stream:
                stream.write(note.content)
                stream.flush()
                os.fsync(stream.fileno())
            os.fsync(dfd)
        except FileExistsError:
            raise DomainError("A note with that name already exists", 409) from None
        finally:
            os.close(dfd)
        return {
            "name": name,
            "bytes": len(content.encode()),
            "verified": self.read(name) == content,
        }

    def read(self, name):
        Note(name=name, content="validation")
        directory = self.check()
        dfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dfd)
            with os.fdopen(fd) as stream:
                text = stream.read(20001)
            if len(text) > 20000:
                raise DomainError("File too large", 413)
            return text
        except OSError:
            raise DomainError("Note unavailable or unsafe", 404) from None
        finally:
            os.close(dfd)

    def list(self):
        return [
            {"name": p.name}
            for p in self.check().glob("*.md")
            if p.is_file() and not p.is_symlink()
        ][:200]
