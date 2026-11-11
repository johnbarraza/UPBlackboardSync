import os
import re
import time
import logging
from pathlib import Path
from datetime import datetime
from requests import Response

from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Files written during the current sync as (path, download timestamp).
# ponytail: module-global, fine while only one sync runs at a time.
written: list[tuple[Path, float]] = []


def has_extension(name: str) -> bool:
    """True if name ends in a real-looking extension (.pdf, .do, .xlsx)."""
    return re.search(r'\.[A-Za-z0-9]{1,5}$', name) is not None


def _finish(path: Path, posted: datetime | None) -> None:
    """Record the download and stamp mtime with the Blackboard date."""
    now = time.time()
    written.append((path, now))
    if posted is not None:
        os.utime(path, (now, posted.timestamp()))


class BStream:
    """Base class for content that can be downloaded as a byte stream."""
    CHUNK_SIZE = 8192  # Increased from 1024 to 8KB for better performance
    # When the item was posted/updated in Blackboard; becomes file mtime.
    posted: datetime | None = None

    def write_base(self, path: Path, executor: ThreadPoolExecutor,
                   stream: Response) -> None:
        """Schedule the write operation."""

        def _write() -> None:
            # Ensure parent directories exist before writing the file
            parent = path.parent
            if parent:
                parent.mkdir(parents=True, exist_ok=True)

            try:
                with path.open("wb") as f:
                    # Download with larger chunks and handle incomplete reads
                    for chunk in stream.iter_content(
                            chunk_size=self.CHUNK_SIZE,
                            decode_unicode=False):
                        if chunk:  # Filter out keep-alive chunks
                            f.write(chunk)
                logger.info(f"Successfully downloaded: {path.name}")
            except Exception as e:
                logger.error(
                    "Failed to download %s: %s: %s",
                    path.name,
                    type(e).__name__,
                    e,
                )
                # Clean up partial file
                if path.exists():
                    try:
                        path.unlink()
                        logger.info(f"Removed partial file: {path.name}")
                    except Exception:
                        pass
                raise
            _finish(path, self.posted)

        executor.submit(_write)


class FStream:
    """Base class for content that can be written as text."""
    posted: datetime | None = None

    def write_base(self, path: Path, executor: ThreadPoolExecutor,
                   body: str) -> None:
        """Schedule the write operation."""

        def _write() -> None:
            # Ensure parent directories exist before writing the file
            parent = path.parent
            if parent:
                parent.mkdir(parents=True, exist_ok=True)

            with path.open('w', encoding='utf-8') as f:
                f.write(body)
            _finish(path, self.posted)

        executor.submit(_write)
