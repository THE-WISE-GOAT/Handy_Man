# Kamigo Worker Interview System — Nepal Edition

AI-powered worker vetting for ANY local job in Nepal.
No hardcoded trade list. Works for plumbers, mechanics, tailors,
cooks, photographers, IT technicians, welders, drivers — anything.

---

## Setup

```bash
pip install google-generativeai python-dotenv pydantic
```

Copy the env template and add your API key:
```bash
cp .env.example .env
# edit .env and paste your GEMINI_API_KEY
```

Run:
```bash
python kamigo_interview.py
```

---

## What it does

| Stage | What happens |
|-------|-------------|
| 1 — Job discovery | AI asks what work the person does. Any job is valid. |
| 2 — Experience gate | Blocks beginners, 0-year workers, gibberish answers. |
| 3 — Sub-skill probe | Drills past generic answers to find a real advanced specialty. |
| 4 — Scenario test | AI writes a real field problem specific to their specialty. |
| 5 — Evaluation | AI scores 0–100. Must score >75 to pass. |
| 6 — JSON output | Clean structured profile ready for your database. |

---

## JSON output fields

```json
{
  "full_name": "Ram Bahadur",
  "job_category": "electrician",
  "verified_specialty": "three-phase industrial panel installation and load balancing",
  "years_experience": 9,
  "license_or_certification": "CTEVT certified electrician",
  "specialized_tools_or_equipment": ["clamp meter", "insulation resistance tester"],
  "service_area": "Kathmandu Valley",
  "emergency_available": true,
  "background_check_consent": true,
  "scenario_passed": true,
  "scenario_score": 84
}
```

---

## Key design decisions

**No fixed job list** — The AI accepts any real work a person can be paid
to do in Nepal. A mechanic, a traditional Newari woodcarver, a wedding
photographer, a cook — all valid. The AI dynamically discovers the job
and adapts its questions.

**Generic answers are rejected** — If a plumber says "I fix leaks" as their
specialty, the AI pushes back. It needs something like "pressurised solar
water heater commissioning" — specific enough to write a technical test for.

**Scenario test is universal** — The scenario generator prompt works for
any trade. A tailor gets a fabric-cutting scenario. A mechanic gets a
fuel system scenario. A cook gets a prep-under-pressure scenario.

**Lenient grading for real workers** — The evaluator does not penalise
poor grammar, Nepali/Hindi mixed with English, or short answers.
It rewards correct terminology, logical steps, and practical knowledge.

**Language aware** — The interviewer replies in whatever language
the worker uses: Nepali, English, or mixed.

---

## Removing the evaluator debug log

In production, remove or comment out this block in `run_interview()`:

```python
# Show internal evaluator report (remove this in production)
print(f"[EVALUATOR REPORT]\n{verdict_log}\n")
print(f"[SCORE: {final_score}/100  |  PASS THRESHOLD: 75]\n")
```

---

## Changing the model

At the bottom of `kamigo_interview.py`:

```python
run_interview(model_name="gemini-2.5-flash")   # fast, cheap
run_interview(model_name="gemini-2.5-pro")     # smarter, more expensive
```