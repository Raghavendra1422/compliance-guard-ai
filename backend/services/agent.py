import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from services.rag_engine import check_single_rule

load_dotenv()


def get_llm():
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0.1,
        max_tokens=1024
    )


def generate_compliance_questions(loan_data: dict) -> list:
    """
    Agent THINKS: break the loan application into
    specific RBI compliance questions to check.
    """
    llm = get_llm()

    think_prompt = ChatPromptTemplate.from_template("""
You are a senior RBI compliance officer. Given this loan application,
generate the specific compliance questions that need to be checked
against RBI regulations.

LOAN APPLICATION:
{loan_data}

Generate 5-7 specific compliance questions to verify.
Return ONLY the questions, one per line, no numbering, no extra text.

Example format:
Does the LTV ratio comply with RBI guidelines for this loan amount?
Is the interest rate within RBI prescribed limits?
""")

    response = llm.invoke(think_prompt.format_messages(
        loan_data=str(loan_data)
    ))

    questions = [
        q.strip()
        for q in response.content.strip().split("\n")
        if q.strip() and len(q.strip()) > 10
    ]

    print(f"[Agent] Generated {len(questions)} compliance questions")
    return questions[:7]


def run_compliance_agent(loan_data: dict) -> dict:
    """
    Full agentic compliance check pipeline:
    THINK → RETRIEVE → ANSWER → VERIFY → REPORT
    """
    print("\n" + "="*50)
    print("[Agent] Starting compliance check...")
    print("="*50)

    # THINK: generate compliance questions
    print("\n[Agent] THINKING: Breaking loan into compliance questions...")
    questions = generate_compliance_questions(loan_data)

    for i, q in enumerate(questions, 1):
        print(f"  Q{i}: {q}")

    # RETRIEVE + ANSWER + VERIFY: check each rule
    print("\n[Agent] CHECKING each compliance rule...")
    results = []
    for question in questions:
        result = check_single_rule(question, loan_data)
        results.append(result)
        print(f"  ✓ {result['verdict']} — confidence: {result['confidence']}")

    # Build final report
    compliant_count    = sum(1 for r in results if r["verdict"] == "COMPLIANT")
    non_compliant      = [r for r in results if r["verdict"] == "NON_COMPLIANT"]
    needs_review       = [r for r in results if r["verdict"] == "NEEDS_REVIEW"]

    overall_compliant  = len(non_compliant) == 0
    avg_confidence     = sum(r["confidence"] for r in results) / len(results) if results else 0

    # Risk score: 0 = low risk, 100 = high risk
    risk_score = min(100, (len(non_compliant) * 30) + (len(needs_review) * 10))

    report = {
        "loan_application": loan_data,
        "overall_compliant": overall_compliant,
        "risk_score": risk_score,
        "summary": {
            "total_checks": len(results),
            "compliant": compliant_count,
            "non_compliant": len(non_compliant),
            "needs_review": len(needs_review),
            "average_confidence": round(avg_confidence, 3)
        },
        "violations": [
            {
                "question": r["question"],
                "verdict": r["verdict"],
                "explanation": r["answer"],
                "citations": r["citations"]
            }
            for r in non_compliant
        ],
        "all_checks": results,
        "recommendation": (
            "APPROVE — All compliance checks passed."
            if overall_compliant
            else f"REJECT/REVIEW — {len(non_compliant)} violation(s) found. See violations list."
        )
    }

    print("\n" + "="*50)
    print(f"[Agent] DONE — Overall: {'✅ COMPLIANT' if overall_compliant else '❌ NON-COMPLIANT'}")
    print(f"[Agent] Risk Score: {risk_score}/100")
    print("="*50 + "\n")

    return report