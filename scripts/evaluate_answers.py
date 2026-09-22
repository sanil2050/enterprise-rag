from app.database.database import SessionLocal
from app.generation.citation_validator import validate_citations
from app.generation.gemini_generator import generate_answer
from app.retrieval.hybrid_search import hybrid_search
from app.retrieval.reranker import rerank
from tests.evaluation.golden_answers import GOLDEN_CASES


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def fact_is_present(answer: str, fact: str) -> bool:
    return normalize(fact) in normalize(answer)


def citation_matches_expected(citation, expected_sources) -> bool:
    return (
        citation["document"],
        citation["chunk"],
    ) in expected_sources


def evaluate_case(db, case):
    question = case["question"]

    candidates = hybrid_search(
        query=question,
        db=db,
        top_k=20,
        candidate_k=20,
        role=case["role"],
    )

    results = rerank(
        query=question,
        results=candidates,
        top_k=15,
    )

    generated = generate_answer(
        question=question,
        context=results,
    )

    validated = validate_citations(
        generated_result=generated,
        retrieved_context=results,
    )

    answer = validated["answer"]
    citations = validated["citations"]

    expected_facts = case["expected_facts"]
    expected_sources = set(case["expected_sources"])

    fact_results = [
        fact_is_present(answer, fact)
        for fact in expected_facts
    ]

    citation_results = [
        citation_matches_expected(
            citation,
            expected_sources,
        )
        for citation in citations
    ]

    fact_coverage = (
        sum(fact_results) / len(fact_results)
        if fact_results
        else 0.0
    )

    citation_accuracy = (
        sum(citation_results) / len(citation_results)
        if citation_results
        else 0.0
    )

    citation_completeness = (
        1.0
        if citations
        else 0.0
    )

    return {
        "question": question,
        "answer": answer,
        "fact_coverage": fact_coverage,
        "citation_accuracy": citation_accuracy,
        "citation_completeness": citation_completeness,
        "citations": citations,
    }


def main():
    db = SessionLocal()

    try:
        results = []

        print("=" * 80)
        print("ANSWER QUALITY EVALUATION")
        print("=" * 80)

        for index, case in enumerate(GOLDEN_CASES, start=1):
            print(
                f"\nEvaluating {index}/{len(GOLDEN_CASES)}:"
                f" {case['question']}"
            )

            result = evaluate_case(db, case)

            results.append(result)

            print(
                f"Fact coverage       : "
                f"{result['fact_coverage']:.2%}"
            )

            print(
                f"Citation accuracy   : "
                f"{result['citation_accuracy']:.2%}"
            )

            print(
                f"Citation completeness: "
                f"{result['citation_completeness']:.2%}"
            )

            print(
                f"Citations returned  : "
                f"{len(result['citations'])}"
            )

        total = len(results)

        avg_fact_coverage = (
            sum(r["fact_coverage"] for r in results)
            / total
        )

        avg_citation_accuracy = (
            sum(r["citation_accuracy"] for r in results)
            / total
        )

        avg_citation_completeness = (
            sum(r["citation_completeness"] for r in results)
            / total
        )

        print("\n" + "=" * 80)
        print("FINAL ANSWER METRICS")
        print("=" * 80)

        print(
            f"Fact coverage:          "
            f"{avg_fact_coverage:.2%}"
        )

        print(
            f"Citation accuracy:      "
            f"{avg_citation_accuracy:.2%}"
        )

        print(
            f"Citation completeness:  "
            f"{avg_citation_completeness:.2%}"
        )

        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()