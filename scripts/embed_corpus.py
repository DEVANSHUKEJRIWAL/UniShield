#!/usr/bin/env python3
"""Embed sample threat-intel corpus into Qdrant (Week 3)."""

import asyncio

from packages.shared_types.constants import QdrantCollection
from services.vector_store.service import vector_store

SAMPLE_DOCS: dict[str, list[dict[str, str]]] = {
    QdrantCollection.THREAT_INTEL: [
        {"text": "T1078 Valid Accounts — adversaries use valid credentials to access systems", "technique": "T1078"},
        {"text": "T1552 Unsecured Credentials — credentials found in code repos or config files", "technique": "T1552"},
    ],
    QdrantCollection.CVE_DESCRIPTIONS: [
        {"text": "CVE-2024-1234 Remote code execution in crown-jewel API gateway", "cve": "CVE-2024-1234"},
    ],
    QdrantCollection.IR_PLAYBOOKS: [
        {"text": "Credential leak response: force reset, MFA, hunt lateral movement", "playbook": "credential_leak"},
    ],
    QdrantCollection.INSIDER_PATTERNS: [
        {"text": "Off-hours data exfiltration by privileged finance analyst", "pattern": "insider_exfil"},
    ],
    QdrantCollection.DARK_WEB_CORPUS: [
        {"text": "Credential dump for meridian.com observed on dark web forum", "domain": "meridian.com"},
    ],
}


async def main() -> None:
    results = []
    for collection, docs in SAMPLE_DOCS.items():
        result = await vector_store.embed_corpus(collection.value, docs)
        results.append(result)
        print(f"  {collection.value}: {result}")
    print(f"\nEmbedded {sum(r.get('embedded', 0) for r in results)} documents total.")


if __name__ == "__main__":
    asyncio.run(main())
