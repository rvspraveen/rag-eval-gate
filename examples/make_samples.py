"""Regenerate the bundled synthetic eval set and app runs.

Everything here is fictional: "Northwind Traders" and its handbook do not exist.
The output is deterministic, so CI can check the committed files are current.

    python examples/make_samples.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

HERE = Path(__file__).parent

# (topic, gold handbook passage, question, reference answer)
FACTS = [
    (
        "pto",
        "Full-time employees accrue 1.5 days of paid time off per month, up to 30 days.",
        "How much PTO do full-time employees accrue?",
        "1.5 days per month, capped at 30 days.",
    ),
    (
        "pto-carry",
        "Up to 5 unused PTO days carry over into the next calendar year.",
        "How many PTO days carry over?",
        "Up to 5 unused days carry over.",
    ),
    (
        "sick",
        "Sick leave is separate from PTO and allows 10 paid days per year.",
        "How many paid sick days are there?",
        "10 paid sick days per year.",
    ),
    (
        "parental",
        "Primary caregivers receive 16 weeks of paid parental leave.",
        "How long is paid parental leave for primary caregivers?",
        "16 weeks of paid leave.",
    ),
    (
        "remote",
        "Employees may work remotely up to 3 days per week with manager approval.",
        "How many remote days are allowed per week?",
        "Up to 3 days per week with manager approval.",
    ),
    (
        "stipend",
        "The home office stipend is 600 dollars, paid once in the first month.",
        "What is the home office stipend?",
        "A one-time 600 dollar stipend.",
    ),
    (
        "expense",
        "Expenses over 75 dollars require an itemised receipt.",
        "When is an itemised receipt required?",
        "For expenses over 75 dollars.",
    ),
    (
        "expense-deadline",
        "Expense reports must be submitted within 30 days of purchase.",
        "What is the deadline for expense reports?",
        "Within 30 days of purchase.",
    ),
    (
        "travel-class",
        "Flights under 6 hours are booked in economy class.",
        "What class are short flights booked in?",
        "Economy for flights under 6 hours.",
    ),
    ("per-diem", "The domestic travel meal per diem is 65 dollars per day.", "What is the domestic meal per diem?", "65 dollars per day."),
    (
        "hotel",
        "Hotel bookings should not exceed 220 dollars per night in major cities.",
        "What is the hotel cap in major cities?",
        "220 dollars per night.",
    ),
    ("401k", "The company matches 401k contributions up to 4 percent of salary.", "What is the 401k match?", "Up to 4 percent of salary."),
    (
        "vesting",
        "The 401k match vests fully after 2 years of service.",
        "When does the 401k match vest?",
        "Fully after 2 years of service.",
    ),
    (
        "health",
        "Medical coverage begins on the first day of the month after the start date.",
        "When does medical coverage begin?",
        "The first day of the month after starting.",
    ),
    (
        "dental",
        "Dental insurance covers two cleanings per year at no cost.",
        "How many free dental cleanings are covered?",
        "Two cleanings per year.",
    ),
    (
        "learning",
        "Each employee has a learning budget of 1500 dollars per year.",
        "What is the annual learning budget?",
        "1500 dollars per year.",
    ),
    (
        "conference",
        "Conference attendance requires approval two weeks in advance.",
        "How early must conference attendance be approved?",
        "Two weeks in advance.",
    ),
    (
        "review",
        "Performance reviews happen twice a year, in April and October.",
        "When are performance reviews held?",
        "Twice a year, in April and October.",
    ),
    ("probation", "New hires complete a 90 day introductory period.", "How long is the introductory period?", "90 days."),
    ("referral", "A successful employee referral earns a 2000 dollar bonus.", "What is the referral bonus?", "2000 dollars."),
    ("laptop", "Laptops are refreshed every 3 years.", "How often are laptops refreshed?", "Every 3 years."),
    (
        "password",
        "Passwords must be at least 14 characters and are rotated yearly.",
        "What is the minimum password length?",
        "14 characters.",
    ),
    ("mfa", "Multi-factor authentication is required for email and the VPN.", "Where is MFA required?", "For email and the VPN."),
    (
        "badge",
        "Lost badges must be reported to security within 24 hours.",
        "How quickly must a lost badge be reported?",
        "Within 24 hours.",
    ),
    (
        "holiday",
        "The office observes 11 paid public holidays each year.",
        "How many paid public holidays are there?",
        "11 paid public holidays.",
    ),
    ("volunteer", "Employees get 2 paid volunteer days per year.", "How many volunteer days are there?", "2 paid days per year."),
    ("wellness", "The wellness reimbursement is 50 dollars per month.", "What is the wellness reimbursement?", "50 dollars per month."),
    (
        "commute",
        "Public transit passes are reimbursed up to 120 dollars per month.",
        "How much transit is reimbursed?",
        "Up to 120 dollars per month.",
    ),
    (
        "resign",
        "Employees are asked to give 2 weeks notice before resigning.",
        "How much notice should be given when resigning?",
        "2 weeks notice.",
    ),
    ("hours", "Core collaboration hours are 10am to 3pm local time.", "What are the core collaboration hours?", "10am to 3pm local time."),
]

# Plausible but wrong-for-the-question passages used as retrieval distractors.
DISTRACTORS = [
    "The cafeteria is open from 8am to 2pm on weekdays.",
    "Parking permits are issued by the facilities team.",
    "The quarterly all-hands meeting is held in the main auditorium.",
    "Printer toner can be requested through the IT portal.",
    "Visitors must sign in at reception and wear a guest badge.",
    "The company newsletter is published on the first Monday of each month.",
    "Meeting rooms can be booked up to four weeks ahead.",
    "Bike storage is available in the basement of building B.",
]

# Off-context answers for the regressed run (sound confident, unsupported by retrieval).
DRIFT = "Policies vary by region, so please contact your manager for the exact details that apply to you."

N_LOSE_GOLD = 8
N_DRIFT = 5


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def main() -> None:
    rng = random.Random(42)
    dataset, base, good, regressed = [], [], [], []
    ids = [f"q{n:02d}-{topic}" for n, (topic, *_) in enumerate(FACTS, start=1)]
    lose_gold = set(rng.sample(ids, N_LOSE_GOLD))
    drift = set(rng.sample(sorted(set(ids) - lose_gold), N_DRIFT))
    reorder = set(rng.sample(ids, 3))

    for qid, (_topic, gold, question, answer) in zip(ids, FACTS, strict=True):
        d1, d2 = rng.sample(DISTRACTORS, 2)
        dataset.append({"id": qid, "question": question, "ground_truth_context": [gold], "ground_truth_answers": [answer]})
        base.append({"id": qid, "retrieved_context": [gold, d1, d2], "answer": gold})

        # good run: a slightly different retriever; on 3 items the gold chunk slips to rank 2.
        ctx = [d1, gold, d2] if qid in reorder else [gold, d2, d1]
        good.append({"id": qid, "retrieved_context": ctx, "answer": gold})

        # regressed run: the gold chunk disappears on some items, answers drift on others.
        d3 = rng.choice([x for x in DISTRACTORS if x not in (d1, d2)])
        ctx = [d1, d2, d3] if qid in lose_gold else [gold, d1, d2]
        ans = DRIFT if qid in drift else (answer if qid in lose_gold else gold)
        regressed.append({"id": qid, "retrieved_context": ctx, "answer": ans})

    _write(HERE / "dataset.jsonl", dataset)
    _write(HERE / "baseline_run.jsonl", base)
    _write(HERE / "good_run.jsonl", good)
    _write(HERE / "regressed_run.jsonl", regressed)
    print(f"wrote {len(dataset)} items: dataset, baseline_run, good_run, regressed_run")


if __name__ == "__main__":
    main()
