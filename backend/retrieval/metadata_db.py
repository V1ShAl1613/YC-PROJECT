"""
MetadataDB — PostgreSQL-backed structured metadata store.
Falls back to SQLite in development if PG is not available.
"""

import os
import json
import logging
import asyncio
from typing import Optional, Dict, List, Any

logger = logging.getLogger("metadata_db")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/legal.db")


class MetadataDB:
    """
    Stores structured legal document metadata:
    case_name, court, year, jurisdiction, judge, source, url, summary, full_text
    """

    def __init__(self):
        self._backend = None
        self._init_sync()

    def _init_sync(self):
        try:
            import asyncpg
            self._backend = "asyncpg"
            self._pool = None
            logger.info("MetadataDB: asyncpg backend (PostgreSQL)")
        except ImportError:
            self._backend = "sqlite"
            self._init_sqlite()
            logger.info("MetadataDB: SQLite backend (development mode)")

    def _init_sqlite(self):
        import sqlite3
        os.makedirs("./data", exist_ok=True)
        self._db_path = "./data/legal.db"
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                case_name TEXT,
                court TEXT,
                year INTEGER,
                jurisdiction TEXT,
                judge TEXT,
                source TEXT,
                url TEXT,
                summary TEXT,
                text TEXT,
                metadata_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jurisdiction ON documents(jurisdiction)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_year ON documents(year)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_court ON documents(court)")
        conn.commit()
        conn.close()
        self._seed_demo_data()

    def _seed_demo_data(self):
        """Seed sample cases for development."""
        import sqlite3
        conn = sqlite3.connect(self._db_path)
        demo_cases = [
            {
                "doc_id": "IK_2023_0001",
                "case_name": "Arnesh Kumar v. State of Bihar & Anr.",
                "court": "Supreme Court of India",
                "year": 2014,
                "jurisdiction": "india",
                "judge": "C.K. Prasad, Pinaki Chandra Ghose",
                "source": "indian_kanoon",
                "url": "https://indiankanoon.org/doc/78847226/",
                "summary": "Guidelines on arrest under Section 41 CrPC; police cannot arrest without warrant mechanically",
                "text": (
                    "The power of arrest without warrant should not be exercised in a routine manner. "
                    "The police officer must have reason to believe that the person has committed a "
                    "cognizable offence. Section 41A CrPC mandates issue of notice before arrest for "
                    "offences carrying less than 7 years imprisonment. Magistrates must apply mind while "
                    "authorizing detention under Section 167 CrPC. The Magistrate before remanding the "
                    "accused to further detention must carefully peruse the police report. Remand should "
                    "not be mechanical. Non-compliance of Section 41A CrPC entitles the accused to "
                    "bail and the police officer liable for departmental action."
                ),
            },
            {
                "doc_id": "IK_2023_0002",
                "case_name": "Gurbaksh Singh Sibbia v. State of Punjab",
                "court": "Supreme Court of India",
                "year": 1980,
                "jurisdiction": "india",
                "judge": "Y.V. Chandrachud, P.N. Bhagwati, N.L. Untwalia, R.S. Pathak, O. Chinnappa Reddy",
                "source": "indian_kanoon",
                "url": "https://indiankanoon.org/doc/697591/",
                "summary": "Leading case on anticipatory bail under Section 438 CrPC; expansive interpretation of the provision",
                "text": (
                    "Section 438 of the Code of Criminal Procedure confers a power of wide amplitude on "
                    "the High Court and the Court of Session to grant anticipatory bail. The provision "
                    "is intended to protect persons against needless arrests and ignominious detention. "
                    "The Court must weigh the nature and gravity of accusation, antecedents of the "
                    "applicant, possibility of fleeing justice, and likelihood of repeating the offence. "
                    "The power conferred by Section 438 is of an extraordinary character and must be "
                    "exercised sparingly. An anticipatory bail order does not in any way limit or affect "
                    "the rights of the police to conduct investigations."
                ),
            },
            {
                "doc_id": "IK_2023_0003",
                "case_name": "Maneka Gandhi v. Union of India",
                "court": "Supreme Court of India",
                "year": 1978,
                "jurisdiction": "india",
                "judge": "M.H. Beg, Y.V. Chandrachud, V.R. Krishna Iyer, N.L. Untwalia, P.N. Bhagwati, S. Murtaza Fazal Ali, P.S. Kailasam",
                "source": "indian_kanoon",
                "url": "https://indiankanoon.org/doc/1766147/",
                "summary": "Expanded the interpretation of Article 21 — procedure established by law must also be fair, just and reasonable",
                "text": (
                    "The procedure established by law for depriving a person of his life or personal liberty "
                    "must be right, just and fair, and not arbitrary, fanciful or oppressive. The expression "
                    "'procedure established by law' in Article 21 must satisfy the requirement of Article 14 "
                    "and Article 19. Articles 14, 19 and 21 are not mutually exclusive but constitute a "
                    "golden triangle. Any law depriving a person of personal liberty must be tested on the "
                    "anvil of all three fundamental rights."
                ),
            },
            {
                "doc_id": "CL_2023_0001",
                "case_name": "Miranda v. Arizona",
                "court": "Supreme Court of the United States",
                "year": 1966,
                "jurisdiction": "usa",
                "judge": "Earl Warren",
                "source": "courtlistener",
                "url": "https://www.courtlistener.com/opinion/107252/miranda-v-arizona/",
                "summary": "Established Miranda rights — suspects must be informed of right to silence and attorney before interrogation",
                "text": (
                    "The prosecution may not use statements, whether exculpatory or inculpatory, "
                    "stemming from custodial interrogation of the defendant unless it demonstrates the "
                    "use of procedural safeguards effective to secure the privilege against self-incrimination. "
                    "Prior to any questioning, the person must be warned that he has a right to remain silent, "
                    "that any statement he does make may be used as evidence against him, and that he has a "
                    "right to the presence of an attorney, either retained or appointed. The defendant may "
                    "waive effectuation of these rights, provided the waiver is made voluntarily, knowingly "
                    "and intelligently."
                ),
            },
        ]

        for case in demo_cases:
            conn.execute(
                """
                INSERT OR IGNORE INTO documents
                (doc_id, case_name, court, year, jurisdiction, judge, source, url, summary, text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case["doc_id"], case["case_name"], case["court"],
                    case["year"], case["jurisdiction"], case["judge"],
                    case["source"], case["url"], case["summary"], case["text"],
                ),
            )
        conn.commit()
        conn.close()
        logger.info(f"Seeded {len(demo_cases)} demo cases")

    async def get(self, doc_id: str) -> Optional[Dict]:
        if self._backend == "sqlite":
            return self._sqlite_get(doc_id)
        return await self._pg_get(doc_id)

    def _sqlite_get(self, doc_id: str) -> Optional[Dict]:
        import sqlite3
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    async def _pg_get(self, doc_id: str) -> Optional[Dict]:
        # PostgreSQL async implementation
        if not self._pool:
            await self._connect_pg()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM documents WHERE doc_id = $1", doc_id
            )
            return dict(row) if row else None

    async def _connect_pg(self):
        import asyncpg
        self._pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)

    async def insert(self, doc: Dict) -> bool:
        if self._backend == "sqlite":
            return self._sqlite_insert(doc)
        return await self._pg_insert(doc)

    def _sqlite_insert(self, doc: Dict) -> bool:
        import sqlite3
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                """
                INSERT OR REPLACE INTO documents
                (doc_id, case_name, court, year, jurisdiction, judge, source, url, summary, text, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.get("doc_id"), doc.get("case_name"), doc.get("court"),
                    doc.get("year"), doc.get("jurisdiction"), doc.get("judge"),
                    doc.get("source"), doc.get("url"), doc.get("summary"),
                    doc.get("text"), json.dumps(doc.get("metadata", {})),
                ),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"SQLite insert error: {e}")
            return False

    async def _pg_insert(self, doc: Dict) -> bool:
        if not self._pool:
            await self._connect_pg()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO documents (doc_id, case_name, court, year, jurisdiction,
                judge, source, url, summary, text, metadata_json)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (doc_id) DO NOTHING
                """,
                doc.get("doc_id"), doc.get("case_name"), doc.get("court"),
                doc.get("year"), doc.get("jurisdiction"), doc.get("judge"),
                doc.get("source"), doc.get("url"), doc.get("summary"),
                doc.get("text"), json.dumps(doc.get("metadata", {})),
            )
            return True
