"""
Simple evaluation runner that doesn't need OpenAI.
Uses Groq to evaluate our RAG system.
Run with: python evaluations/run_evaluation.py
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ingestor import search_regulations
from services.rag_engine import check_single_rule
from evaluations.test_dataset import test_cases
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import json

load_dotenv()


def get_llm():
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0.1,
        max_tokens=512
    )


def evaluate_faithfulness(question, answer, contexts, llm) -> dict:
    context_text = "\n\n".join(contexts[:5])

    prompt = ChatPromptTemplate.from_template("""
You are evaluating if an AI answer is faithful to source documents.

QUESTION: {question}

AI ANSWER: {answer}

SOURCE DOCUMENTS:
{contexts}

INSTRUCTIONS:
- Read the AI answer carefully
- Check if the KEY FACTS (numbers, percentages, rules) in the answer 
  appear in the source documents
- Be lenient — the exact wording does not need to match
- If the main claim is supported, score high
- Only fail if the AI invented facts not in any source document

Respond in JSON only, no markdown:
{{"score": 0.0 to 1.0, "verdict": "PASS or FAIL", "reason": "one sentence"}}
""")

    response = llm.invoke(prompt.format_messages(
        question=question, answer=answer, contexts=context_text
    ))

    try:
        text = response.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception:
        return {"score": 0.5, "verdict": "UNKNOWN", "reason": "Could not parse"}


def evaluate_answer_relevancy(question, answer, llm) -> dict:
    """Check if answer actually addresses the question."""
    prompt = ChatPromptTemplate.from_template("""
You are an evaluator checking if an AI answer is relevant to the question.

QUESTION: {question}
AI ANSWER: {answer}

Does the answer directly address what was asked?
Respond in JSON only:
{{
    "score": 0.0 to 1.0,
    "verdict": "PASS or FAIL",
    "reason": "one sentence explanation"
}}
""")

    response = llm.invoke(prompt.format_messages(
        question=question, answer=answer
    ))

    try:
        text = response.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception:
        return {"score": 0.5, "verdict": "UNKNOWN", "reason": "Could not parse"}


def evaluate_contextual_recall(question, contexts, expected_output, llm) -> dict:
    """Check if retrieved contexts contain all necessary information."""
    context_text = "\n\n".join(contexts[:5])

    prompt = ChatPromptTemplate.from_template("""
You are an evaluator checking if retrieved documents contain enough information.

QUESTION: {question}
EXPECTED ANSWER SHOULD COVER: {expected_output}
RETRIEVED DOCUMENTS: {contexts}

Do the retrieved documents contain the information needed to answer correctly?
Respond in JSON only:
{{
    "score": 0.0 to 1.0,
    "verdict": "PASS or FAIL",
    "missing_info": ["any important info not found in retrieved docs"],
    "reason": "one sentence explanation"
}}
""")

    response = llm.invoke(prompt.format_messages(
        question=question,
        expected_output=expected_output,
        contexts=context_text
    ))

    try:
        text = response.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception:
        return {"score": 0.5, "verdict": "UNKNOWN", "reason": "Could not parse"}


def run_full_evaluation():
    """Run all evaluation metrics on all test cases."""
    llm = get_llm()

    print("\n" + "="*60)
    print("  COMPLIANCE-GUARD AI — RAG EVALUATION")
    print("  Using DeepEval-style metrics with Groq LLM")
    print("="*60)

    results = []
    total_faithfulness    = 0
    total_relevancy       = 0
    total_recall          = 0
    passed                = 0
    failed                = 0

    for i, tc in enumerate(test_cases[:3], 1):
        print(f"\n[{i}/{len(test_cases)}] Testing: {tc['id']}")
        print(f"  Q: {tc['input'][:70]}...")

        # Get RAG response
        chunks = search_regulations(
            query=tc.get("context_query", tc["input"]),
            n_results=5,
            category=tc["category"]
        )
        contexts = [c["content"] for c in chunks]

        result = check_single_rule(
            question=tc["input"],
            loan_data={"loan_type": tc["category"]}
        )
        answer = result["answer"]

        # Run evaluations
        faith   = evaluate_faithfulness(tc["input"], answer, contexts, llm)
        relev   = evaluate_answer_relevancy(tc["input"], answer, llm)
        recall  = evaluate_contextual_recall(
            tc["input"], contexts, tc["expected_output"], llm
        )

        faith_score  = faith.get("score", 0)
        relev_score  = relev.get("score", 0)
        recall_score = recall.get("score", 0)
        avg_score    = (faith_score + relev_score + recall_score) / 3

        total_faithfulness += faith_score
        total_relevancy    += relev_score
        total_recall       += recall_score

        tc_passed = avg_score >= 0.6
        if tc_passed:
            passed += 1
        else:
            failed += 1

        print(f"  Faithfulness    : {faith_score:.2f}  {faith.get('verdict','')}")
        print(f"  Answer Relevancy: {relev_score:.2f}  {relev.get('verdict','')}")
        print(f"  Context Recall  : {recall_score:.2f}  {recall.get('verdict','')}")
        print(f"  Average Score   : {avg_score:.2f}  {'✅ PASS' if tc_passed else '❌ FAIL'}")

        results.append({
            "id": tc["id"],
            "question": tc["input"],
            "faithfulness": faith_score,
            "answer_relevancy": relev_score,
            "contextual_recall": recall_score,
            "average": avg_score,
            "passed": tc_passed,
            "faith_reason":  faith.get("reason", ""),
            "relev_reason":  relev.get("reason", ""),
            "recall_reason": recall.get("reason", ""),
            
        })
        time.sleep(15)
    # Final Summary
    n = len(test_cases)
    avg_faith  = total_faithfulness / n
    avg_relev  = total_relevancy / n
    avg_recall = total_recall / n
    overall    = (avg_faith + avg_relev + avg_recall) / 3

    print("\n" + "="*60)
    print("  EVALUATION SUMMARY")
    print("="*60)
    print(f"  Total Test Cases    : {n}")
    print(f"  Passed              : {passed} ✅")
    print(f"  Failed              : {failed} ❌")
    print(f"  Pass Rate           : {round((passed/n)*100, 1)}%")
    print("-"*60)
    print(f"  Avg Faithfulness    : {avg_faith:.3f}  {'✅' if avg_faith >= 0.7 else '❌'}")
    print(f"  Avg Answer Relevancy: {avg_relev:.3f}  {'✅' if avg_relev >= 0.7 else '❌'}")
    print(f"  Avg Context Recall  : {avg_recall:.3f}  {'✅' if avg_recall >= 0.6 else '❌'}")
    print(f"  Overall RAG Score   : {overall:.3f}  {'✅ GOOD' if overall >= 0.65 else '⚠️ NEEDS IMPROVEMENT'}")
    print("="*60)

    # Save results to JSON
    import datetime
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "summary": {
            "total": n,
            "passed": passed,
            "failed": failed,
            "pass_rate": round((passed/n)*100, 1),
            "avg_faithfulness": round(avg_faith, 3),
            "avg_answer_relevancy": round(avg_relev, 3),
            "avg_contextual_recall": round(avg_recall, 3),
            "overall_score": round(overall, 3),
        },
        "test_cases": results
    }

    os.makedirs("evaluations/reports", exist_ok=True)
    report_path = f"evaluations/reports/eval_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n  📊 Full report saved to: {report_path}")
    print("="*60)

    return report


if __name__ == "__main__":
    run_full_evaluation()