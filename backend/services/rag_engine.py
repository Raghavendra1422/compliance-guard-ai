import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from services.ingestor import search_regulations, vectorstore
from langchain_core.documents import Document
load_dotenv()


def get_llm():
    """Return Groq LLM instance."""
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0.1,
        max_tokens=2048
    )


def multi_query_retrieve(question: str, n_results: int = 5) -> list:
    """
    Deep RAG: generate 3 different versions of the question,
    retrieve chunks for each, then combine unique results.
    """
    llm = ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.1-8b-instant",
        temperature=0.1,
        max_tokens=200
    )

    rephrase_prompt = ChatPromptTemplate.from_template("""
You are an RBI compliance expert. Given this compliance question, 
generate 3 different ways to search for the answer in RBI regulations.
Return ONLY the 3 questions, one per line, nothing else.

Original question: {question}

3 search queries:""")

    response = llm.invoke(rephrase_prompt.format_messages(question=question))
    queries = [q.strip() for q in response.content.strip().split("\n") if q.strip()]
    queries = queries[:3]
    queries.append(question)

    seen_ids = set()
    all_chunks = []

    for query in queries:
        results = search_regulations(query=query, n_results=n_results)
        for chunk in results:
            chunk_id = chunk["metadata"].get("chunk_id", "")
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                all_chunks.append(chunk)

    all_chunks.sort(key=lambda x: x["relevance_score"], reverse=True)

    print("\n=== TOP RETRIEVED CHUNKS ===")

    for i, chunk in enumerate(all_chunks[:5]):
        print(f"\nChunk {i+1}")
        print("Score:", chunk["relevance_score"])
        print(chunk["content"][:400])

    print("\n===========================\n")

    return all_chunks[:8]


def verify_answer(answer: str, chunks: list, question: str) -> dict:
    """Strict hallucination guard."""

    llm = ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.1-8b-instant",
        temperature=0.1,
        max_tokens=300
    )

    context = "\n\n".join([
        f"[Chunk {i+1}]: {chunk['content']}"
        for i, chunk in enumerate(chunks[:5])
    ])

    verify_prompt = ChatPromptTemplate.from_template("""
You are a strict RBI compliance auditor.

QUESTION:
{question}

ANSWER:
{answer}

RBI REGULATION EVIDENCE:
{context}

Rules:
1. Every factual claim must appear in the evidence.
2. If even one important claim is unsupported, mark SUPPORTED as NO.
3. Never use outside knowledge.

Return EXACTLY:
SUPPORTED: yes/no
CONFIDENCE: number between 0 and 1
REASON: short explanation
CORRECTIONS: corrected answer or "none"
""")

    response = llm.invoke(
        verify_prompt.format_messages(
            question=question,
            answer=answer,
            context=context
        )
    )

    lines = response.content.strip().split("\n")
    result = {"supported": False, "confidence": 0.0, "reason": "", "corrections": "none"}

    for line in lines:
        if line.startswith("SUPPORTED:"):
            result["supported"] = "yes" in line.lower()
        elif line.startswith("CONFIDENCE:"):
            try:
                result["confidence"] = float(line.split(":", 1)[1].strip())
            except:
                result["confidence"] = 0.0
        elif line.startswith("REASON:"):
            result["reason"] = line.split(":", 1)[1].strip()
        elif line.startswith("CORRECTIONS:"):
            result["corrections"] = line.split(":", 1)[1].strip()

    return result


def check_single_rule(question: str, loan_data: dict) -> dict:
    """Check ONE compliance rule using the full RAG + verify loop."""
    llm = get_llm()

    # Step 1: Deep retrieve relevant chunks
    print(f"  [RAG] Retrieving chunks for: {question[:60]}...")
    chunks = multi_query_retrieve(question, n_results=5)

    if not chunks:
        return {
            "question": question,
            "verdict": "UNABLE_TO_CHECK",
            "answer": "No relevant RBI regulations found.",
            "confidence": 0.0,
            "citations": [],
            "verified": False
        }

    context = "\n\n".join([
        f"[RBI Regulation - Chunk {i+1}]:\n{chunk['content']}"
        for i, chunk in enumerate(chunks[:5])
    ])

    # Step 2: Generate compliance verdict
    compliance_prompt = ChatPromptTemplate.from_template("""
You are a senior RBI compliance officer. Answer the compliance question
using ONLY the RBI regulations provided below.

QUESTION:
{question}

LOAN APPLICATION DATA:
{loan_data}

RBI REGULATIONS:
{context}

STRICT RULES:
1. Use ONLY the regulations provided above
2. Never use outside knowledge
3. For LTV questions: find the correct bracket (up to 30L = 90%, 30-75L = 80%, above 75L = 75%)
4. Quote the exact regulation text as evidence
5. If you find the rule, give a direct clear answer with the specific percentage
6. Only say NEEDS_REVIEW if the regulation truly does not exist in provided text
7. Do not say "not explicitly stated" if the information IS in the chunks

Return EXACTLY in this format:

VERDICT: COMPLIANT / NON_COMPLIANT / NEEDS_REVIEW

EXPLANATION:
Clear direct explanation with specific numbers from the regulation.

EVIDENCE:
Copy the exact text from the regulation that supports your answer.

VIOLATED_RULE:
Specific rule violated or "none"

RECOMMENDATION:
What action to take.
""")

    response = llm.invoke(compliance_prompt.format_messages(
        question=question,
        loan_data=str(loan_data),
        context=context
    ))

    answer = response.content.strip()

    # Safety Check 1
    if "EVIDENCE:" not in answer:
        print("  [Safety] Malformed response, flagging NEEDS_REVIEW")
        answer = """VERDICT: NEEDS_REVIEW\nEXPLANATION:\nInsufficient regulatory evidence found.\nEVIDENCE:\nnone\nVIOLATED_RULE:\nnone\nRECOMMENDATION:\nManual compliance review required."""

    # Step 3: Verify the answer
    print(f"  [Verify] Checking answer for hallucinations...")
    verification = verify_answer(answer, chunks, question)

    # Step 4: Retry logic with nested Safety Check
    if verification["confidence"] < 0.75 and "EVIDENCE:\nnone" not in answer:
        print(f"  [Retry] Low confidence ({verification['confidence']}), retrying...")
        chunks = multi_query_retrieve(
            question + " " + (verification["corrections"] if verification["corrections"] != "none" else ""),
            n_results=5
        )
        context = "\n\n".join([c['content'] for c in chunks[:5]])
        
        response = llm.invoke(compliance_prompt.format_messages(
            question=question,
            loan_data=str(loan_data),
            context=context
        ))
        answer = response.content.strip()

        # Safety Check 2 (Inside Retry)
        if "EVIDENCE:" not in answer:
            answer = """VERDICT: NEEDS_REVIEW\nEXPLANATION:\nInsufficient regulatory evidence found.\nEVIDENCE:\nnone\nVIOLATED_RULE:\nnone\nRECOMMENDATION:\nManual compliance review required."""

        verification = verify_answer(answer, chunks, question)

    # Step 5: Robust Verdict Parsing
    verdict = "NEEDS_REVIEW"
    for line in answer.split("\n"):
        if line.strip().startswith("VERDICT:"):
            v_raw = line.split(":", 1)[1].strip().upper()
            # Stricter matching to avoid "COMPLIANT" matching inside "NON_COMPLIANT"
            if v_raw == "NON_COMPLIANT":
                verdict = "NON_COMPLIANT"
            elif v_raw == "COMPLIANT":
                verdict = "COMPLIANT"
            else:
                verdict = "NEEDS_REVIEW"
            break

    # Build citations
    citations = [
        {
            "circular_id": c["metadata"].get("circular_id"),
            "source_file": c["metadata"].get("source_file"),
            "relevance": c["relevance_score"],
            "excerpt": c["content"][:200] + "..."
        }
        for c in chunks[:3]
    ]

    return {
        "question": question,
        "verdict": verdict,
        "answer": answer,
        "confidence": verification["confidence"],
        "verified": verification["supported"],
        "citations": citations
    }