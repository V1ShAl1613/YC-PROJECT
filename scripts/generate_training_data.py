"""
Training Data Generator for LexVerify Legal LLM
Generates instruction-tuning dataset from the project's legal corpus.

Categories:
  1. Legal Q&A with citations       — teach citation-backed answering
  2. Citation formatting            — teach [CITE:doc_id] format
  3. Verification judgment          — teach pass/fail assessment
  4. Fallback recognition           — teach when to refuse

Output: data/training_data.jsonl (Unsloth-compatible)
Run:    python scripts/generate_training_data.py
"""

import json
import os
import sys
import sqlite3
import random
import logging
from typing import List, Dict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("training_data")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "legal.db")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "training_data.jsonl")


# ── Prompt Templates ─────────────────────────────────────────────────────────

QA_INSTRUCTIONS = [
    "Answer the following legal question using ONLY the provided document. Include a citation in [CITE:doc_id] format for every factual claim. If the document does not contain enough information, respond with: {\"fallback\": true}",
    "You are a senior legal analyst. Using ONLY the retrieved legal document below, provide a precise, citation-backed answer to the question. Every claim must reference the source with [CITE:doc_id]. Output strict JSON.",
    "Based solely on the legal document provided, answer the question with accurate citations. Do not infer or assume any facts not present in the document. Use [CITE:doc_id] format.",
    "As a verification-first legal AI, analyze the following document and answer the question. Every statement must be supported by a [CITE:doc_id] citation. If context is insufficient, output {\"fallback\": true}.",
    "Review the legal document and provide a thorough answer to the question. Cite every factual claim using [CITE:doc_id]. Accuracy takes precedence over fluency.",
]

QA_QUESTION_TEMPLATES = [
    "What are the key legal principles established in {case_name}?",
    "Summarize the ruling and its implications in {case_name} ({year}).",
    "What did the {court} hold regarding the issues in {case_name}?",
    "Explain the legal significance of the judgment in {case_name}.",
    "What legal precedent was set by {case_name} as decided by {court}?",
    "What are the grounds and reasoning provided by the court in {case_name}?",
    "Analyze the constitutional implications of {case_name} ({year}).",
    "What procedural safeguards were established in {case_name}?",
    "How does {case_name} impact the interpretation of relevant statutory provisions?",
    "What were the facts, issues, and holdings in {case_name}?",
]

JURISDICTION_QUESTIONS = {
    "india": [
        "What does this case say about fundamental rights under the Indian Constitution?",
        "How does this judgment interpret the Code of Criminal Procedure?",
        "What guidelines did the Supreme Court of India provide in this matter?",
        "Explain the bail provisions discussed in this case.",
        "What is the significance of this case for Article 21 jurisprudence?",
    ],
    "usa": [
        "What constitutional rights are discussed in this case?",
        "How does this case impact Fifth Amendment protections?",
        "What procedural due process requirements does this case establish?",
        "Explain the Supreme Court's reasoning on individual rights in this case.",
        "What is the precedential value of this ruling?",
    ],
}

VERIFICATION_SCENARIOS = [
    {
        "scenario": "valid",
        "desc": "All citations verified, no contradictions, complete fields",
        "expected": {
            "all_claims_cited": True,
            "contradictions_found": False,
            "out_of_scope_claims": False,
            "issues": []
        },
    },
    {
        "scenario": "missing_citation",
        "desc": "Answer contains claims without supporting citations",
        "expected": {
            "all_claims_cited": False,
            "contradictions_found": False,
            "out_of_scope_claims": True,
            "issues": ["The answer contains factual claims that are not supported by any cited document."]
        },
    },
    {
        "scenario": "contradiction",
        "desc": "Citations contradict each other on key legal points",
        "expected": {
            "all_claims_cited": True,
            "contradictions_found": True,
            "out_of_scope_claims": False,
            "issues": ["Citation sources present conflicting interpretations of the legal principle."]
        },
    },
]


def load_documents() -> List[Dict]:
    """Load all documents from the SQLite database."""
    db_path = os.path.abspath(DB_PATH)
    if not os.path.exists(db_path):
        logger.warning(f"Database not found at {db_path}, using demo data")
        return get_demo_documents()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM documents")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    if not rows:
        logger.warning("Database is empty, using demo data")
        return get_demo_documents()

    logger.info(f"Loaded {len(rows)} documents from database")
    return rows


def get_demo_documents() -> List[Dict]:
    """Fallback demo documents if DB is unavailable."""
    return [
        {
            "doc_id": "IK_2023_0001",
            "case_name": "Arnesh Kumar v. State of Bihar & Anr.",
            "court": "Supreme Court of India",
            "year": 2014,
            "jurisdiction": "india",
            "judge": "C.K. Prasad, Pinaki Chandra Ghose",
            "source": "indian_kanoon",
            "url": "https://indiankanoon.org/doc/78847226/",
            "summary": "Guidelines on arrest under Section 41 CrPC",
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
            "judge": "Y.V. Chandrachud, P.N. Bhagwati",
            "source": "indian_kanoon",
            "url": "https://indiankanoon.org/doc/697591/",
            "summary": "Leading case on anticipatory bail under Section 438 CrPC",
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
            "judge": "M.H. Beg, Y.V. Chandrachud, V.R. Krishna Iyer",
            "source": "indian_kanoon",
            "url": "https://indiankanoon.org/doc/1766147/",
            "summary": "Expanded Article 21 — procedure must be fair, just and reasonable",
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
            "summary": "Miranda rights — right to silence and attorney before interrogation",
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


# ── Generators ────────────────────────────────────────────────────────────────

def generate_qa_examples(docs: List[Dict]) -> List[Dict]:
    """Generate legal Q&A instruction-tuning pairs."""
    examples = []

    for doc in docs:
        doc_id = doc.get("doc_id", "UNKNOWN")
        case_name = doc.get("case_name", "Unknown Case")
        court = doc.get("court", "Unknown Court")
        year = doc.get("year", "Unknown")
        jurisdiction = doc.get("jurisdiction", "unknown")
        text = doc.get("text", doc.get("summary", ""))
        url = doc.get("url", "")
        source = doc.get("source", "unknown")

        if not text or len(text) < 50:
            continue

        # Generate multiple Q&A pairs per document
        questions = []

        # Template-based questions
        for tmpl in random.sample(QA_QUESTION_TEMPLATES, min(3, len(QA_QUESTION_TEMPLATES))):
            questions.append(tmpl.format(
                case_name=case_name, court=court, year=year
            ))

        # Jurisdiction-specific questions
        jx_qs = JURISDICTION_QUESTIONS.get(jurisdiction, [])
        if jx_qs:
            questions.extend(random.sample(jx_qs, min(2, len(jx_qs))))

        for question in questions:
            instruction = random.choice(QA_INSTRUCTIONS)

            context = (
                f"[DOCUMENT ID: {doc_id}]\n"
                f"Case: {case_name}\n"
                f"Court: {court} | Year: {year} | Source: {source}\n"
                f"URL: {url}\n"
                f"Content:\n{text}"
            )

            # Build expected answer
            snippet = text[:300].strip()
            answer_text = (
                f"Based on the ruling in {case_name} ({court}, {year}), "
                f"{snippet} [CITE:{doc_id}]"
            )

            output = json.dumps({
                "fallback": False,
                "answer": answer_text,
                "citations": [{
                    "id": doc_id,
                    "case_name": case_name,
                    "court": court,
                    "year": year,
                    "paragraph": text[:200],
                    "url": url,
                    "source": source,
                    "relevance_score": round(random.uniform(0.85, 0.98), 2),
                }]
            }, indent=2)

            examples.append({
                "instruction": instruction,
                "input": f"LEGAL QUESTION: {question}\n\nRETRIEVED LEGAL DOCUMENTS:\n{context}",
                "output": output,
            })

    logger.info(f"Generated {len(examples)} Q&A examples")
    return examples


def generate_citation_format_examples(docs: List[Dict]) -> List[Dict]:
    """Teach the model proper citation formatting."""
    examples = []

    for doc in docs:
        doc_id = doc.get("doc_id", "UNKNOWN")
        case_name = doc.get("case_name", "Unknown Case")
        court = doc.get("court", "Unknown Court")
        year = doc.get("year", "Unknown")
        text = doc.get("text", "")
        url = doc.get("url", "")
        source = doc.get("source", "unknown")

        if not text:
            continue

        instruction = (
            "Given the following raw case data, produce a properly formatted citation object "
            "in JSON format with all required fields: id, case_name, court, year, paragraph, "
            "url, source, relevance_score."
        )

        input_text = (
            f"Document ID: {doc_id}\n"
            f"Title: {case_name}\n"
            f"Court: {court}\n"
            f"Year: {year}\n"
            f"Source: {source}\n"
            f"URL: {url}\n"
            f"Key paragraph: {text[:300]}"
        )

        output = json.dumps({
            "id": doc_id,
            "case_name": case_name,
            "court": court,
            "year": year,
            "paragraph": text[:200],
            "url": url,
            "source": source,
            "relevance_score": round(random.uniform(0.88, 0.97), 2),
        }, indent=2)

        examples.append({
            "instruction": instruction,
            "input": input_text,
            "output": output,
        })

    logger.info(f"Generated {len(examples)} citation format examples")
    return examples


def generate_verification_examples(docs: List[Dict]) -> List[Dict]:
    """Teach the model to verify citations and detect issues."""
    examples = []

    for scenario in VERIFICATION_SCENARIOS:
        for doc in docs:
            doc_id = doc.get("doc_id", "UNKNOWN")
            case_name = doc.get("case_name", "Unknown Case")
            year = doc.get("year", "Unknown")
            text = doc.get("text", "")

            if not text:
                continue

            instruction = (
                "You are a legal fact-checker. Review the answer and its citations below. "
                "Check for: (1) whether every claim has a supporting citation, "
                "(2) whether any citations contradict each other, "
                "(3) whether there are claims beyond what the cited documents say. "
                "Respond in JSON."
            )

            if scenario["scenario"] == "valid":
                answer = f"The court held that {text[:200]} [CITE:{doc_id}]"
                citations = f"[{doc_id}] {case_name} ({year}): {text[:300]}"
            elif scenario["scenario"] == "missing_citation":
                answer = f"The court held that {text[:200]}. Furthermore, it is well established in legal doctrine that additional principles apply."
                citations = f"[{doc_id}] {case_name} ({year}): {text[:300]}"
            else:  # contradiction
                answer = f"The court held that {text[:200]} [CITE:{doc_id}]"
                citations = (
                    f"[{doc_id}] {case_name} ({year}): {text[:200]}\n"
                    f"[FAKE_002] Conflicting Case ({year}): The opposite interpretation applies."
                )

            input_text = f"ANSWER:\n{answer}\n\nCITATIONS USED:\n{citations}"
            output = json.dumps(scenario["expected"], indent=2)

            examples.append({
                "instruction": instruction,
                "input": input_text,
                "output": output,
            })

    logger.info(f"Generated {len(examples)} verification examples")
    return examples


def generate_fallback_examples(docs: List[Dict]) -> List[Dict]:
    """Teach the model when to refuse and return fallback."""
    examples = []

    fallback_questions = [
        "What is the current stock price of Tesla?",
        "Write me a poem about the ocean.",
        "What is the weather forecast for tomorrow?",
        "Explain quantum computing in simple terms.",
        "How to cook pasta carbonara?",
        "What are the latest developments in cryptocurrency regulation?",
        "Tell me a joke.",
        "What is the meaning of life?",
    ]

    for question in fallback_questions:
        instruction = random.choice(QA_INSTRUCTIONS)
        input_text = f"LEGAL QUESTION: {question}\n\nRETRIEVED LEGAL DOCUMENTS:\n[No relevant documents found]"
        output = json.dumps({"fallback": True})

        examples.append({
            "instruction": instruction,
            "input": input_text,
            "output": output,
        })

    # Also generate fallback for unrelated documents
    for doc in docs[:2]:
        text = doc.get("text", "")
        doc_id = doc.get("doc_id", "")
        if not text:
            continue

        unrelated_questions = [
            "What does this case say about environmental law?",
            "Explain the corporate merger guidelines from this document.",
            "What tax provisions are discussed here?",
        ]

        for question in unrelated_questions:
            context = (
                f"[DOCUMENT ID: {doc_id}]\n"
                f"Case: {doc.get('case_name', '')}\n"
                f"Content:\n{text[:300]}"
            )
            instruction = random.choice(QA_INSTRUCTIONS)
            input_text = f"LEGAL QUESTION: {question}\n\nRETRIEVED LEGAL DOCUMENTS:\n{context}"
            output = json.dumps({"fallback": True})

            examples.append({
                "instruction": instruction,
                "input": input_text,
                "output": output,
            })

    logger.info(f"Generated {len(examples)} fallback examples")
    return examples


def generate_multi_document_examples(docs: List[Dict]) -> List[Dict]:
    """Generate examples that use multiple documents for a richer answer."""
    examples = []

    if len(docs) < 2:
        return examples

    # Create pairs/triples of documents from the same jurisdiction
    by_jurisdiction: Dict[str, List[Dict]] = {}
    for doc in docs:
        jx = doc.get("jurisdiction", "unknown")
        by_jurisdiction.setdefault(jx, []).append(doc)

    for jx, jx_docs in by_jurisdiction.items():
        if len(jx_docs) < 2:
            continue

        for i in range(min(5, len(jx_docs) - 1)):
            pair = jx_docs[i : i + 2]

            instruction = random.choice(QA_INSTRUCTIONS)

            context_parts = []
            citations = []
            answer_parts = []

            for doc in pair:
                doc_id = doc.get("doc_id", "UNKNOWN")
                case_name = doc.get("case_name", "Unknown")
                court = doc.get("court", "Unknown")
                year = doc.get("year", "Unknown")
                text = doc.get("text", "")
                url = doc.get("url", "")
                source = doc.get("source", "unknown")

                context_parts.append(
                    f"[DOCUMENT ID: {doc_id}]\n"
                    f"Case: {case_name}\n"
                    f"Court: {court} | Year: {year} | Source: {source}\n"
                    f"URL: {url}\n"
                    f"Content:\n{text[:500]}"
                )

                answer_parts.append(
                    f"In {case_name} ({court}, {year}), {text[:150].strip()} [CITE:{doc_id}]"
                )

                citations.append({
                    "id": doc_id,
                    "case_name": case_name,
                    "court": court,
                    "year": int(year) if str(year).isdigit() else 0,
                    "paragraph": text[:200],
                    "url": url,
                    "source": source,
                    "relevance_score": round(random.uniform(0.85, 0.96), 2),
                })

            question = f"Compare and analyze the legal principles from these related cases in {jx.upper()} jurisdiction."
            context = "\n\n".join(context_parts)
            answer = " Furthermore, ".join(answer_parts)

            output = json.dumps({
                "fallback": False,
                "answer": answer,
                "citations": citations,
            }, indent=2)

            examples.append({
                "instruction": instruction,
                "input": f"LEGAL QUESTION: {question}\n\nRETRIEVED LEGAL DOCUMENTS:\n{context}",
                "output": output,
            })

    logger.info(f"Generated {len(examples)} multi-document examples")
    return examples


def main():
    """Generate the full training dataset."""
    logger.info("=" * 60)
    logger.info("LexVerify Training Data Generator")
    logger.info("=" * 60)

    docs = load_documents()
    logger.info(f"Working with {len(docs)} documents")

    all_examples = []
    all_examples.extend(generate_qa_examples(docs))
    all_examples.extend(generate_citation_format_examples(docs))
    all_examples.extend(generate_verification_examples(docs))
    all_examples.extend(generate_fallback_examples(docs))
    all_examples.extend(generate_multi_document_examples(docs))

    # Shuffle for training
    random.seed(42)
    random.shuffle(all_examples)

    # Write JSONL
    output_path = os.path.abspath(OUTPUT_PATH)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for ex in all_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    logger.info(f"✅ Generated {len(all_examples)} training examples")
    logger.info(f"   Output: {output_path}")
    logger.info(f"   File size: {os.path.getsize(output_path) / 1024:.1f} KB")

    # Print category breakdown
    categories = {
        "Q&A": sum(1 for e in all_examples if "LEGAL QUESTION:" in e["input"] and '"fallback": false' in e["output"].lower()),
        "Citation Format": sum(1 for e in all_examples if "raw case data" in e["instruction"]),
        "Verification": sum(1 for e in all_examples if "fact-checker" in e["instruction"]),
        "Fallback": sum(1 for e in all_examples if '"fallback": true' in e["output"].lower()),
        "Multi-Doc": sum(1 for e in all_examples if "Compare and analyze" in e.get("input", "")),
    }
    logger.info("Category breakdown:")
    for cat, count in categories.items():
        logger.info(f"   {cat}: {count}")


if __name__ == "__main__":
    main()
