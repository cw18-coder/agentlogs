import asyncio
from collections.abc import Generator
from contextlib import contextmanager
from os import PathLike
from pathlib import Path
from queue import Queue
import sqlite3
import json
from typing import Any
import zstandard as zstd

class Database:
    path: Path
    pool: Queue[sqlite3.Connection]

    def __init__(
        self,
        path: str | PathLike[str],
        pool_size: int = 20,
        create: bool = True,
        schema_path: str | PathLike[str] | None = None
    ):
        self.path = Path(path)

        if not self.path.exists():
            if create:
                self.path.parent.mkdir(parents=True, exist_ok=True)

                conn = sqlite3.connect(self.path)

                if schema_path is not None:
                    with open(schema_path, "r", encoding="utf-8") as f:
                        conn.executescript(f.read())

                conn.close()
            else:
                raise FileNotFoundError(
                    f"Database file does not exist: {self.path}"
                )

        self.pool = Queue(maxsize=pool_size)

        for _ in range(pool_size):
            conn = sqlite3.connect(
                self.path,
                timeout=30,
                check_same_thread=False,
            )

            # SQLite performance/concurrency settings
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA cache_size=-64000")
            conn.execute("PRAGMA temp_store=MEMORY")
            self.pool.put(conn)

    @contextmanager
    def connect(
        self,
        immediate: bool = False,
    ) -> Generator[sqlite3.Connection, None, None]:
        conn = self.pool.get()

        try:
            if immediate:
                conn.execute("BEGIN IMMEDIATE")

            yield conn

            conn.commit()

        except (Exception, asyncio.CancelledError, KeyboardInterrupt):
            conn.rollback()
            raise

        finally:
            self.pool.put(conn)

    def close(self) -> None:
        while not self.pool.empty():
            conn = self.pool.get()
            conn.close()

    def __enter__(self):
        return self

    def __exit__(
        self, 
        exc_type: type[BaseException] | None, 
        exc_value: BaseException | None, 
        traceback: object | None
    ):
        self.close()

class PayloadStorage:
    path: Path
    cctx: zstd.ZstdCompressor
    dctx: zstd.ZstdDecompressor
    n_shard_levels: int
    n_characters_per_shard: int

    def __init__(
        self, 
        path: str | PathLike[str],
        compression_level: int = 3,
        n_shard_levels: int = 3, 
        n_characters_per_shard: int = 1
    ):
        self.path = Path(path)
        self.cctx = zstd.ZstdCompressor(level=compression_level)
        self.dctx = zstd.ZstdDecompressor()
        self.n_shard_levels = n_shard_levels
        self.n_characters_per_shard = n_characters_per_shard

    def get_path(self, resource_type: str, id: int) -> Path:
        n_shard_caracters = self.n_shard_levels * self.n_characters_per_shard
        return self.path / resource_type / Path(*[
            str(id).zfill(n_shard_caracters)[::-1][i:i+self.n_characters_per_shard][::-1]
            for i in range(0, n_shard_caracters, self.n_characters_per_shard)
        ]) / f"{id}.json.zst"

    def has_payload(self, resource_type: str, id: int) -> bool:
        return self.get_path(resource_type, id).exists()

    def save_payload(self, resource_type: str, id: int, payload: Any) -> bool:
        path = self.get_path(resource_type, id)
        existed = path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "wb") as file:
            file.write(self.cctx.compress(
                json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ))
        return not existed

    def load_payload(self, resource_type: str, id: int) -> Any:
        path = self.get_path(resource_type, id)
        try:
            with open(path, "rb") as file:
                return json.loads(
                    self.dctx.decompress(file.read()).decode("utf-8")
                )
        except FileNotFoundError:
            return None