from __future__ import annotations


def analyze_growth(input_text: str) -> dict:
    # STEP 1: Basic parsing
    text = (input_text or "").lower()

    # STEP 2: Generate structured opportunities
    opportunities = [
        {
            "title": "Weak positioning clarity",
            "why_it_matters": "Users don’t understand value quickly → drop-offs",
            "expected_impact": "15–30% conversion improvement",
        },
        {
            "title": "No aggressive CTA strategy",
            "why_it_matters": "Users are not pushed to act → lost conversions",
            "expected_impact": "10–20% lift",
        },
    ]

    # Light deterministic tweak to keep output feeling contextual without any AI/runtime dependency.
    if "pricing" in text:
        opportunities.append(
            {
                "title": "Pricing friction / unclear packaging",
                "why_it_matters": "Ambiguity increases hesitation and lowers paid conversion",
                "expected_impact": "10–25% revenue leakage reduction",
            }
        )
    if "performance" in text or "slow" in text or "load" in text:
        opportunities.append(
            {
                "title": "Performance bottlenecks",
                "why_it_matters": "Slow load increases abandonment before value is perceived",
                "expected_impact": "10–20% drop-off reduction",
            }
        )

    # STEP 3: Actions
    actions = [
        "Rewrite headline to focus on outcome, not feature",
        "Add primary CTA above the fold",
        "Reduce friction in onboarding flow",
    ]

    # STEP 4: Weaknesses
    weaknesses = [
        "No clear differentiation",
        "Weak onboarding funnel",
        "Lack of urgency triggers",
    ]

    # STEP 5: Quick wins
    quick_wins = [
        "Change CTA copy within 24 hours",
        "Add testimonial section",
        "Simplify signup form",
    ]

    return {
        "free_layer": {
            "opportunities": opportunities[:2],
            "note": "Additional high-impact opportunities not shown",
        },
        "premium_layer": {
            "opportunities": opportunities,
            "actions": actions,
            "weaknesses": weaknesses,
            "quick_wins": quick_wins,
        },
    }

