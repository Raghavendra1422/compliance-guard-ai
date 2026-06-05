"""
End-to-end compliance decision evaluation.
Tests what actually matters: does the system make correct COMPLY/REJECT decisions?
This is more meaningful than RAG retrieval metrics for a compliance application.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.agent import run_compliance_agent
from dotenv import load_dotenv
import json
import time

load_dotenv()

# Ground truth test cases — we KNOW what the correct decision should be
compliance_test_cases = [
    {
        "id": "E2E-001",
        "description": "High LTV violation — 45 lakh loan at 90% LTV",
        "loan_data": {
            "applicant_name": "Test User",
            "loan_type": "home_loan",
            "loan_amount_inr": 4500000,
            "property_value_inr": 5000000,
            "ltv_ratio": 90,
            "interest_rate_percent": 8.5,
            "tenure_years": 20,
            "applicant_income_monthly": 75000,
            "cibil_score": 720,
            "existing_loans": 0,
            "applicant_city": "Mumbai",
            "loan_purpose": "purchase"
        },
        "expected_compliant": False,    # should FAIL — LTV 90% > 80% limit
        "expected_violations": ["LTV"],
    },
    {
        "id": "E2E-002",
        "description": "Clean loan — all within RBI limits",
        "loan_data": {
            "applicant_name": "Test User",
            "loan_type": "home_loan",
            "loan_amount_inr": 3500000,
            "property_value_inr": 5000000,
            "ltv_ratio": 70,             # 70% — well within 80% limit
            "interest_rate_percent": 8.5,
            "tenure_years": 20,
            "applicant_income_monthly": 100000,
            "cibil_score": 780,
            "existing_loans": 0,
            "applicant_city": "Mumbai",
            "loan_purpose": "purchase"
        },
        "expected_compliant": True,     # should PASS
        "expected_violations": [],
    },
    {
        "id": "E2E-003",
        "description": "Tenure violation — 25 years exceeds 20 year limit",
        "loan_data": {
            "applicant_name": "Test User",
            "loan_type": "home_loan",
            "loan_amount_inr": 2500000,
            "property_value_inr": 4000000,
            "ltv_ratio": 62,
            "interest_rate_percent": 8.5,
            "tenure_years": 25,          # exceeds 20 year RBI limit
            "applicant_income_monthly": 80000,
            "cibil_score": 740,
            "existing_loans": 0,
            "applicant_city": "Delhi",
            "loan_purpose": "purchase"
        },
        "expected_compliant": False,    # should FAIL — tenure > 20 years
        "expected_violations": ["tenure"],
    },
    {
        "id": "E2E-004",
        "description": "Small loan high LTV — 20 lakh at 95% LTV",
        "loan_data": {
            "applicant_name": "Test User",
            "loan_type": "home_loan",
            "loan_amount_inr": 2000000,
            "property_value_inr": 2100000,
            "ltv_ratio": 95,             # 95% > 90% limit for loans up to 30L
            "interest_rate_percent": 8.5,
            "tenure_years": 15,
            "applicant_income_monthly": 60000,
            "cibil_score": 700,
            "existing_loans": 0,
            "applicant_city": "Chennai",
            "loan_purpose": "purchase"
        },
        "expected_compliant": False,    # should FAIL — LTV 95% > 90% limit
        "expected_violations": ["LTV"],
    },
    {
        "id": "E2E-005",
        "description": "Large loan — 80 lakh at 76% LTV — barely over 75% limit",
        "loan_data": {
            "applicant_name": "Test User",
            "loan_type": "home_loan",
            "loan_amount_inr": 8000000,
            "property_value_inr": 10500000,
            "ltv_ratio": 76,             # 76% > 75% limit for loans above 75L
            "interest_rate_percent": 9.0,
            "tenure_years": 20,
            "applicant_income_monthly": 200000,
            "cibil_score": 800,
            "existing_loans": 0,
            "applicant_city": "Bangalore",
            "loan_purpose": "purchase"
        },
        "expected_compliant": False,    # should FAIL — LTV 76% > 75% limit
        "expected_violations": ["LTV"],
    },
]


def run_e2e_evaluation():
    print("\n" + "="*60)
    print("  COMPLIANCE-GUARD AI — END-TO-END EVALUATION")
    print("  Testing: Does system make correct COMPLY/REJECT decisions?")
    print("="*60)

    passed = 0
    failed = 0
    results = []

    for i, tc in enumerate(compliance_test_cases, 1):
        print(f"\n[{i}/{len(compliance_test_cases)}] {tc['id']}: {tc['description']}")

        try:
            report = run_compliance_agent(tc["loan_data"])

            actual_compliant = report["overall_compliant"]
            expected_compliant = tc["expected_compliant"]
            decision_correct = actual_compliant == expected_compliant

            # Check if expected violations were caught
            violations_text = " ".join([
                v["question"].lower()
                for v in report.get("violations", [])
            ])

            violations_caught = []
            violations_missed = []
            for expected_v in tc["expected_violations"]:
                if expected_v.lower() in violations_text:
                    violations_caught.append(expected_v)
                else:
                    violations_missed.append(expected_v)

            overall_pass = decision_correct and len(violations_missed) == 0

            if overall_pass:
                passed += 1
                print(f"  ✅ PASS — Decision correct: {'COMPLIANT' if actual_compliant else 'NON-COMPLIANT'}")
            else:
                failed += 1
                print(f"  ❌ FAIL")
                print(f"     Expected: {'COMPLIANT' if expected_compliant else 'NON-COMPLIANT'}")
                print(f"     Got     : {'COMPLIANT' if actual_compliant else 'NON-COMPLIANT'}")
                if violations_missed:
                    print(f"     Missed violations: {violations_missed}")

            print(f"  Risk Score: {report['risk_score']}/100")
            print(f"  Violations found: {report['summary']['non_compliant']}")

            results.append({
                "id": tc["id"],
                "description": tc["description"],
                "expected_compliant": expected_compliant,
                "actual_compliant": actual_compliant,
                "decision_correct": decision_correct,
                "violations_caught": violations_caught,
                "violations_missed": violations_missed,
                "risk_score": report["risk_score"],
                "passed": overall_pass
            })

            # Wait between cases to avoid rate limiting
            if i < len(compliance_test_cases):
                print(f"  Waiting 20s before next case...")
                time.sleep(20)

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            failed += 1

    # Summary
    total = len(compliance_test_cases)
    pass_rate = round((passed/total)*100, 1)

    print("\n" + "="*60)
    print("  END-TO-END EVALUATION SUMMARY")
    print("="*60)
    print(f"  Total Cases    : {total}")
    print(f"  Passed         : {passed} ✅")
    print(f"  Failed         : {failed} ❌")
    print(f"  Pass Rate      : {pass_rate}%")
    print("-"*60)

    if pass_rate >= 80:
        print(f"  Overall Grade  : ✅ PRODUCTION READY ({pass_rate}%)")
    elif pass_rate >= 60:
        print(f"  Overall Grade  : ⚠️ NEEDS IMPROVEMENT ({pass_rate}%)")
    else:
        print(f"  Overall Grade  : ❌ SIGNIFICANT ISSUES ({pass_rate}%)")

    print("="*60)

    # Save report
    import datetime
    os.makedirs("evaluations/reports", exist_ok=True)
    path = f"evaluations/reports/e2e_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(path, "w") as f:
        json.dump({"summary": {
            "total": total, "passed": passed,
            "failed": failed, "pass_rate": pass_rate
        }, "results": results}, f, indent=2)

    print(f"\n  📊 Report saved: {path}")
    return pass_rate


if __name__ == "__main__":
    run_e2e_evaluation()