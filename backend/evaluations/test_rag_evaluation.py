"""
DeepEval RAG Evaluation for Compliance-Guard AI
Run with: deepeval test run evaluations/test_rag_evaluation.py
Or:       pytest evaluations/test_rag_evaluation.py -v
"""

import pytest
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deepeval import assert_test
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    ContextualRecallMetric,
    ContextualPrecisionMetric,
)
from deepeval.test_case import LLMTestCase

from services.ingestor import search_regulations
from services.rag_engine import check_single_rule
from evaluations.test_dataset import test_cases
from dotenv import load_dotenv

load_dotenv()


# ── DeepEval uses Groq through LangChain ──────────────────────
# We set this so DeepEval knows which model to use for evaluation
os.environ["OPENAI_API_KEY"] = "placeholder"  # DeepEval needs this set


def get_rag_response(input_question: str, category: str) -> tuple:
    """
    Run our RAG system on a question.
    Returns (answer, retrieved_contexts)
    """
    # Get retrieved chunks
    chunks = search_regulations(
        query=input_question,
        n_results=5,
        category=category if category else None
    )

    contexts = [chunk["content"] for chunk in chunks]

    # Get AI answer using our compliance checker
    loan_data = {
        "loan_type": category,
        "question": input_question
    }

    result = check_single_rule(
        question=input_question,
        loan_data=loan_data
    )

    return result["answer"], contexts


# ── Individual Test Cases ──────────────────────────────────────

@pytest.mark.parametrize("tc", test_cases)
def test_faithfulness(tc):
    """
    FAITHFULNESS: Is the AI answer based ONLY on retrieved RBI chunks?
    Catches hallucinations — AI should not make up regulations.
    Threshold: 0.7 (70% of claims must be supported by retrieved context)
    """
    print(f"\n[Eval] Testing Faithfulness: {tc['id']} — {tc['input'][:50]}...")

    answer, contexts = get_rag_response(tc["input"], tc["category"])

    test_case = LLMTestCase(
        input=tc["input"],
        actual_output=answer,
        retrieval_context=contexts,
        expected_output=tc["expected_output"],
    )

    metric = FaithfulnessMetric(
        threshold=0.7,
        model="gpt-3.5-turbo",   # DeepEval uses this for evaluation
        include_reason=True
    )

    assert_test(test_case, [metric])


@pytest.mark.parametrize("tc", test_cases)
def test_answer_relevancy(tc):
    """
    ANSWER RELEVANCY: Does the answer actually address the question asked?
    Catches off-topic or vague answers.
    Threshold: 0.7
    """
    print(f"\n[Eval] Testing Answer Relevancy: {tc['id']}...")

    answer, contexts = get_rag_response(tc["input"], tc["category"])

    test_case = LLMTestCase(
        input=tc["input"],
        actual_output=answer,
        retrieval_context=contexts,
    )

    metric = AnswerRelevancyMetric(
        threshold=0.7,
        model="gpt-3.5-turbo",
        include_reason=True
    )

    assert_test(test_case, [metric])


@pytest.mark.parametrize("tc", test_cases)
def test_contextual_recall(tc):
    """
    CONTEXTUAL RECALL: Did we retrieve ALL the relevant RBI rules?
    Catches cases where important regulations were missed during retrieval.
    Threshold: 0.6
    """
    print(f"\n[Eval] Testing Contextual Recall: {tc['id']}...")

    answer, contexts = get_rag_response(tc["input"], tc["category"])

    test_case = LLMTestCase(
        input=tc["input"],
        actual_output=answer,
        retrieval_context=contexts,
        expected_output=tc["expected_output"],
    )

    metric = ContextualRecallMetric(
        threshold=0.6,
        model="gpt-3.5-turbo",
        include_reason=True
    )

    assert_test(test_case, [metric])


@pytest.mark.parametrize("tc", test_cases)
def test_contextual_precision(tc):
    """
    CONTEXTUAL PRECISION: Are the retrieved chunks actually relevant?
    Catches noise — retrieving wrong regulation sections.
    Threshold: 0.6
    """
    print(f"\n[Eval] Testing Contextual Precision: {tc['id']}...")

    answer, contexts = get_rag_response(tc["input"], tc["category"])

    test_case = LLMTestCase(
        input=tc["input"],
        actual_output=answer,
        retrieval_context=contexts,
        expected_output=tc["expected_output"],
    )

    metric = ContextualPrecisionMetric(
        threshold=0.6,
        model="gpt-3.5-turbo",
        include_reason=True
    )

    assert_test(test_case, [metric])