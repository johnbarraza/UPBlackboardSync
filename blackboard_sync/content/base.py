import logging
from pathlib import Path
from requests import Response

from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class BStream:
    """Base class for content that can be downloaded as a byte stream."""
    CHUNK_SIZE = 8192  # Increased from 1024 to 8KB for better performance

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
                    for chunk in stream.iter_content(chunk_size=self.CHUNK_SIZE, decode_unicode=False):
                        if chunk:  # Filter out keep-alive chunks
                            f.write(chunk)
                logger.info(f"Successfully downloaded: {path.name}")
            except Exception as e:
                logger.error(f"Failed to download {path.name}: {type(e).__name__}: {e}")
                # Clean up partial file
                if path.exists():
                    try:
                        path.unlink()
                        logger.info(f"Removed partial file: {path.name}")
                    except Exception:
                        pass
                raise

        executor.submit(_write)


class FStream:
    """Base class for content that can be written as text."""

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

        executor.submit(_write)
