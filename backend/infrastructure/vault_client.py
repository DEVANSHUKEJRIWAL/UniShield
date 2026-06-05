"""Secret storage — file-backed locally, Vault KV when configured."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Optional


class VaultClient:
    """
    Minimal secret store for repo connector tokens.
    Uses HashiCorp Vault when VAULT_ADDR is set; otherwise a local directory.
    """

    def __init__(
        self,
        vault_addr: Optional[str] = None,
        vault_token: Optional[str] = None,
        local_path: Optional[str] = None,
    ) -> None:
        self._vault_addr = vault_addr or os.getenv("VAULT_ADDR")
        self._vault_token = vault_token or os.getenv("VAULT_TOKEN", "")
        self._local_path = Path(local_path or os.getenv("UNISHIELD_VAULT_PATH", "/tmp/unishield-vault"))
        self._hvac = None
        if self._vault_addr:
            try:
                import hvac

                self._hvac = hvac.Client(url=self._vault_addr, token=self._vault_token)
            except ImportError:
                self._hvac = None

    async def write_secret(self, path: str, token: str) -> None:
        if self._hvac:
            await asyncio.to_thread(
                self._hvac.secrets.kv.v2.create_or_update_secret,
                path=path.replace("secret/", ""),
                secret={"token": token},
            )
            return
        target = self._local_path / f"{path.replace('/', '_')}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(
            target.write_text,
            json.dumps({"token": token}),
            encoding="utf-8",
        )

    async def read_secret(self, path: str) -> str:
        if self._hvac:
            result = await asyncio.to_thread(
                self._hvac.secrets.kv.v2.read_secret_version,
                path=path.replace("secret/", ""),
            )
            return result["data"]["data"]["token"]
        target = self._local_path / f"{path.replace('/', '_')}.json"
        if not target.exists():
            raise FileNotFoundError(f"Vault secret not found: {path}")
        data = json.loads(await asyncio.to_thread(target.read_text, encoding="utf-8"))
        return data["token"]

    async def delete_secret(self, path: str) -> None:
        if self._hvac:
            await asyncio.to_thread(
                self._hvac.secrets.kv.v2.delete_metadata_and_all_versions,
                path=path.replace("secret/", ""),
            )
            return
        target = self._local_path / f"{path.replace('/', '_')}.json"
        if target.exists():
            await asyncio.to_thread(target.unlink)
