import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema import Document
from services.ingestor import search_regulations, vectorstore

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
    This finds MORE relevant chunks than a single query.
    """
    llm = get_llm()

    # Ask the LLM to rephrase the question 3 different ways
    rephrase_prompt = ChatPromptTemplate.from_template("""
You are an RBI compliance expert. Given this compliance question, 
generate 3 different ways to search for the answer in RBI regulations.
Return ONLY the 3 questions, one per line, nothing else.

Original question: {question}

3 search queries:""")

    response = llm.invoke(rephrase_prompt.format_messages(question=question))
    queries = [q.strip() for q in response.content.strip().split("\n") if q.strip()]
    queries = queries[:3]  # max 3
    queries.append(question)  # always include original

    # Retrieve chunks for each query, collect unique ones
    seen_ids = set()
    all_chunks = []

    for query in queries:
        results = search_regulations(query=query, n_results=n_results)
        for chunk in results:
            chunk_id = chunk["metadata"].get("chunk_id", "")
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                all_chunks.append(chunk)

    # Sort by relevance score, return top results
    all_chunks.sort(key=lambda x: x["relevance_score"], reverse=True)
    return all_chunks[:8]  # return top 8 unique chunks


def verify_answer(answer: str, chunks: list, question: str) -> dict:
    """
    Hallucination Guard: check if the answer is actually
    supported by the retrieved RBI regulation chunks.
    Returns confidence score and verification result.
    """
    llm = get_llm()

    # Build context from chunks
    context = "\n\n".join([
        f"[Chunk {i+1}]: {chunk['content']}"
        for i, chunk in enumerate(chunks[:5])
    ])

    verify_prompt = ChatPromptTemplate.from_template("""
You are a strict fact-checker for RBI compliance answers.

QUESTION: {question}

ANSWER GIVEN: {answer}

ACTUAL RBI REGULATION CHUNKS:
{context}

Check if the answer is supported by the regulation chunks above.
Respond in this exact format:
SUPPORTED: yes/no
CONFIDENCE: 0.0 to 1.0
REASON: one sentence explanation
CORRECTIONS: any corrections needed, or "none"
""")

    response = llm.invoke(verify_prompt.format_messages(
        question=question,
        answer=answer,
        context=context
    ))

    # Parse the structured response
    lines = response.content.strip().split("\n")
    result = {
        "supported": False,
        "confidence": 0.0,
        "reason": "",
        "corrections": "none"
    }

    for line in lines:
        if line.startswith("SUPPORTED:"):
            result["supported"] = "yes" in line.lower()
        elif line.startswith("CONFIDENCE:"):
            try:
                result["confidence"] = float(line.split(":")[1].strip())
            except Exception:
                result["confidence"] = 0.5
        elif line.startswith("REASON:"):
            result["reason"] = line.split(":", 1)[1].strip()
        elif line.startswith("CORRECTIONS:"):
            result["corrections"] = line.split(":", 1)[1].strip()

    return result


def check_single_rule(question: str, loan_data: dict) -> dict:
    """
    Check ONE compliance rule using the full RAG + verify loop.
    This is called multiple times by the agent for each rule.
    """
    llm = get_llm()

    # Step 1: Deep retrieve relevant chunks
    print(f"  [RAG] Retrieving chunks for: {question[:60]}...")
    chunks = multi_query_retrieve(question, n_results=5)

    if not chunks:
        return {
            "question": question,
            "verdict": "UNABLE_TO_CHECK",
            "answer": "No relevant RBI regulations found for this question.",
            "confidence": 0.0,
            "citations": [],
            "verified": False
        }

    # Step 2: Build context from retrieved chunks
    context = "\n\n".join([
        f"[RBI Regulation - Chunk {i+1}]:\n{chunk['content']}"
        for i, chunk in enumerate(chunks[:5])
    ])

    # Step 3: Generate compliance verdict
    compliance_prompt = ChatPromptTemplate.from_template("""
You are a strict RBI compliance officer checking loan applications.

COMPLIANCE QUESTION: {question}

LOAN APPLICATION DATA:
{loan_data}

RELEVANT RBI REGULATIONS:
{context}

Based ONLY on the RBI regulations provided above, answer the compliance question.
Give your response in this exact format:

VERDICT: COMPLIANT / NON_COMPLIANT / NEEDS_REVIEW
EXPLANATION: Clear explanation citing specific regulation
VIOLATED_RULE: The specific rule that is violated (or "none")
RECOMMENDATION: What action to take
""")

    response = llm.invoke(compliance_prompt.format_messages(
        question=question,
        loan_data=str(loan_data),
        context=context
    ))

    answer = response.content.strip()

    # Step 4: Verify the answer (hallucination check)
    print(f"  [Verify] Checking answer for hallucinations...")
    verification = verify_answer(answer, chunks, question)

    # Step 5: If confidence too low, retry with different query
    if verification["confidence"] < 0.5:
        print(f"  [Retry] Low confidence ({verification['confidence']}), retrying...")
        chunks = multi_query_retrieve(
            question + " " + verification["corrections"],
            n_results=5
        )
        context = "\n\n".join([c['content'] for c in chunks[:5]])
        response = llm.invoke(compliance_prompt.format_messages(
            question=question,
            loan_data=str(loan_data),
            context=context
        ))
        answer = response.content.strip()
        verification = verify_answer(answer, chunks, question)

    # Parse verdict from answer
    verdict = "NEEDS_REVIEW"
    for line in answer.split("\n"):
        if line.startswith("VERDICT:"):
            v = line.split(":", 1)[1].strip()
            if "NON_COMPLIANT" in v:
                verdict = "NON_COMPLIANT"
            elif "COMPLIANT" in v:
                verdict = "COMPLIANT"
            else:
                verdict = "NEEDS_REVIEW"
            break

    # Build citations from chunks
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