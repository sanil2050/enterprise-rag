GOLDEN_CASES = [
    {
        "question": "How many vacation days do employees receive?",
        "expected_facts": [
            "20 vacation and personal days per year",
            "11 local holidays",
        ],
        "expected_sources": [
            ("leave_policy.pdf", 7),
        ],
        "role": "employee",
    },
    {
        "question": "How much can I roll over?",
        "expected_facts": [
            "vacation rolls over up to a maximum bank of 27 days",
        ],
        "expected_sources": [
            ("leave_policy.pdf", 7),
        ],
        "role": "employee",
    },
    {
        "question": "What about parental leave?",
        "expected_facts": [
            "parental leave",
        ],
        "expected_sources": [
            ("leave_policy.pdf", 10),
        ],
        "role": "employee",
    },
    {
        "question": "How much bereavement leave is available?",
        "expected_facts": [
            "bereavement leave",
        ],
        "expected_sources": [
            ("leave_policy.pdf", 11),
        ],
        "role": "employee",
    },
    {
        "question": "What happens to unused vacation days?",
        "expected_facts": [
            "unused vacation days",
        ],
        "expected_sources": [
            ("leave_policy.pdf", 7),
        ],
        "role": "employee",
    },
]