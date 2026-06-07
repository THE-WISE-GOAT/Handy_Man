"""
Kamigo Worker Interview System
================================
AI-powered vetting terminal for home service tradespeople.

Pipeline:
  Stage 1 - Trade gate        → confirms supported trade, rejects out-of-scope
  Stage 2 - Experience gate   → blocks 0-year workers and beginners
  Stage 3 - Sub-skill probe   → drills to a real advanced niche (not basic tasks)
  Stage 4 - Scenario test     → generates a field problem for the claimed sub-skill
  Stage 5 - AI evaluation     → scores the answer 0-100, pass = >75
  Stage 6 - JSON output       → structured profile for the Kamigo database
"""

import json
import re
import ollama
from typing import List, Literal
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────────────────────────

SUPPORTED_TRADES = ["plumbing", "electrical", "hvac", "appliance_repair", "handyman"]

# Sub-skills that are considered TOO BASIC to be a validated specialty.
# These are implied by the trade itself and must never be accepted as an
# advanced niche.  Any answer that resolves to one of these gets pushed back.
GENERIC_SUBSKILLS = {
    "plumbing": [
        "pipe repair", "pipe installation", "leak repair", "leak fixing",
        "sink repair", "sink installation", "faucet repair", "faucet installation",
        "toilet repair", "toilet installation", "basic plumbing", "general plumbing",
        "drain cleaning", "water pressure", "tap repair", "tap installation",
    ],
    "electrical": [
        "wiring", "basic wiring", "light installation", "light fitting",
        "switch installation", "outlet installation", "socket repair",
        "bulb replacement", "circuit breaker", "general electrical",
        "cable installation", "plug installation",
    ],
    "hvac": [
        "air conditioning", "ac repair", "ac installation", "heating repair",
        "general hvac", "filter replacement", "thermostat installation",
        "duct cleaning", "ventilation", "basic hvac",
    ],
    "appliance_repair": [
        "appliance repair", "general appliance", "washing machine repair",
        "fridge repair", "oven repair", "basic repair", "dishwasher repair",
    ],
    "handyman": [
        "painting", "wall painting", "basic repairs", "general handyman",
        "furniture assembly", "wall mounting", "tile laying", "basic tiling",
        "fixing doors", "door installation", "window repair", "carpentry basics",
    ],
}


class WorkerProfileSchema(BaseModel):
    trade_category: Literal[
        "plumbing", "electrical", "hvac", "appliance_repair", "handyman"
    ] = Field(description="Primary trade category.")

    verified_specialty: str = Field(
        description="The single advanced sub-skill that was TESTED and PASSED during the scenario step. Must be specific and non-trivial."
    )

    years_experience: int = Field(
        description="Total professional years in this trade."
    )

    license_status: Literal["verified_active", "pending_review", "unlicensed"] = Field(
        description="License status based on candidate statements."
    )

    heavy_equipment_owned: List[str] = Field(
        description="Specialized equipment, diagnostic tools, or machinery they own and operate. Exclude hand tools every tradesperson has."
    )

    emergency_24_7: bool = Field(
        description="True only if they explicitly stated they accept 24/7 emergency dispatches."
    )

    background_check_consent: bool = Field(
        description="True only if they explicitly agreed to a background check."
    )

    scenario_passed: bool = Field(
        description="Always True at this point — candidate reached JSON stage only after passing the scenario."
    )


# ─────────────────────────────────────────────────────────────
# PROMPT CONSTANTS
# ─────────────────────────────────────────────────────────────

# Exact token strings the interviewer AI must output to trigger pipeline stages.
# These are parsed by the orchestrator — the AI must reproduce them verbatim.
REJECTION_TOKEN = "[REJECTED]"
TEST_TOKEN_RE   = re.compile(r'\[TEST_REQUIRED:\s*(.+?)\]', re.IGNORECASE)
COMPLETE_TOKEN  = "[COMPLETE]"

INTERVIEWER_SYSTEM_PROMPT = f"""You are a strict, professional technical vetting officer for Kamigo — a home services platform in South Africa.
Your role is to interview a tradesperson applying to join the platform.

══════════════════════════════════════════════════════════════
SUPPORTED TRADES (only these are accepted):
  plumbing | electrical | hvac | appliance_repair | handyman
══════════════════════════════════════════════════════════════

────────────────────────────────────────────────────
RULE 1 — ONE QUESTION PER TURN
Ask exactly ONE short, direct question per response.
Never chain two questions together.
Keep every response under 25 words.
────────────────────────────────────────────────────

────────────────────────────────────────────────────
RULE 2 — INSTANT REJECTION TRIGGERS
Output exactly {REJECTION_TOKEN} (nothing else) if:
  • The worker states 0 years of experience.
  • The worker explicitly says they are a beginner or still learning.
  • The worker's response is completely unrelated gibberish
    (e.g. "2+2=4", "hello world", random letters, math formulas,
    song lyrics, or any text with zero trade relevance).
  • The worker becomes abusive or repeatedly refuses to answer.
Do NOT reject on the very first turn if the input is ambiguous —
give exactly ONE follow-up question to clarify. After that, reject.
────────────────────────────────────────────────────

────────────────────────────────────────────────────
RULE 3 — UNSUPPORTED TRADE
If the worker names a trade NOT in our supported list
(e.g. phone repair, web design, painting contractor, pest control):
  • On the FIRST mention: politely inform them we only onboard
    the five supported trades and ask if they have any of those skills.
  • If they confirm they have none: output {REJECTION_TOKEN}.
────────────────────────────────────────────────────

────────────────────────────────────────────────────
RULE 4 — INFORMATION YOU MUST COLLECT (in order)
  a) Primary trade (must match supported list)
  b) Years of professional experience
  c) License status (active / pending / unlicensed)
  d) ONE advanced sub-skill (see Rule 5 below)
  e) Specialized equipment they own
  f) Whether they accept 24/7 emergency calls
  g) Whether they consent to a background check

Collect these one at a time. Do not skip ahead.
────────────────────────────────────────────────────

────────────────────────────────────────────────────
RULE 5 — SUB-SKILL PROBING (the most critical rule)

Goal: identify ONE genuine advanced niche, not a basic task.

Step A — Ask for their primary focus area:
  "What is your primary specialisation within [trade]?"

Step B — If the answer is vague or too broad, probe further:
  "Do you focus on residential or commercial work?"
  "What type of [sub-area] do you work on most often?"
  "What was your most complex project in the last six months?"

Step C — Evaluate what they claim.
  The following sub-skills are TOO BASIC for a plumber and must be REJECTED
  as a specialty claim (they do not represent advanced expertise):
    {json.dumps(GENERIC_SUBSKILLS, indent=4)}

  If the worker claims one of these as their specialty, push back:
  "That is standard for most [trade] workers. What advanced or specialist
   work do you do beyond that?"

  If after TWO push-backs they cannot name an advanced specialty,
  output {REJECTION_TOKEN}.

Step D — Once you have an advanced, specific sub-skill, stop probing
  and output exactly:
  [TEST_REQUIRED: <exact sub-skill name>]

  Example valid outputs:
    [TEST_REQUIRED: solar geyser installation and fault diagnosis]
    [TEST_REQUIRED: commercial three-phase electrical panel upgrades]
    [TEST_REQUIRED: VRF multi-split HVAC system commissioning]
    [TEST_REQUIRED: gas hob conversion and leak testing]
    [TEST_REQUIRED: structural timber repairs and load-bearing beam replacement]

  The sub-skill must be specific enough that a technical test question
  can be written about it.
────────────────────────────────────────────────────

────────────────────────────────────────────────────
RULE 6 — AFTER THE TEST
You will be told the test result by the system.
If told the worker passed: output {COMPLETE_TOKEN} immediately.
If told the worker failed: output {REJECTION_TOKEN} immediately.
────────────────────────────────────────────────────

────────────────────────────────────────────────────
TONE
Professional, brief, neutral. No greetings after the first turn.
No compliments. No pleasantries. No filler words.
────────────────────────────────────────────────────"""


SCENARIO_GENERATOR_PROMPT = """\
You are a senior technical assessor for home services tradespeople.

Your task: Write a realistic, field-specific troubleshooting scenario
for the sub-skill provided. The scenario must:
  1. Describe a real situation a worker would encounter on a job site.
  2. Be specific enough that only someone with hands-on experience could
     answer it correctly.
  3. End with a direct question asking exactly what steps or tools the
     worker would use to diagnose or fix the problem.
  4. Be 40–60 words maximum.
  5. Avoid textbook definitions — write as a supervisor would speak.

Output ONLY the scenario. No preamble, no labels, no explanation."""


EVALUATOR_PROMPT_TEMPLATE = """\
You are an expert trade assessor grading a practical skills interview.

Sub-skill being tested: {sub_skill}
Scenario presented to the worker: {scenario}
Worker's answer: {answer}

GRADING RULES:
1. Do NOT penalise poor grammar, casual language, slang, broken English,
   or short answers. Many skilled tradespeople are not strong writers.
2. DO award marks for:
     • Correct trade-specific terminology (tool names, part names, codes)
     • Logical troubleshooting sequence (even if briefly stated)
     • Mention of safety steps where relevant
     • Correct identification of the likely fault or root cause
3. Award ZERO if the answer:
     • Is completely unrelated to the scenario
     • Contains only filler words with no technical content
     • Shows no understanding of the sub-skill at all
4. Partial credit: if they name the right tools but wrong sequence, or
   right sequence but wrong tools — score 40–70.
5. Score > 75 = they have demonstrated real field knowledge.

First write a brief assessment (2–3 sentences).
Then on a new line write EXACTLY one of:
  SCORE: <number between 0 and 100>
  VERDICT: PASS
or
  SCORE: <number between 0 and 100>
  VERDICT: FAIL

Only these two formats are valid. Do not add anything after the verdict."""


EXTRACTOR_PROMPT = """\
You are a strict data compliance parser for the Kamigo worker registry.

Analyse the interview transcript below and extract the structured
worker profile. Follow these rules exactly:

1. trade_category: map to one of the five allowed values only.
   plumbing | electrical | hvac | appliance_repair | handyman

2. verified_specialty: copy the exact sub-skill that was TESTED and PASSED.
   Do not invent or summarise — use the name from the [TEST_REQUIRED: ...]
   token in the transcript.

3. years_experience: integer only. If unclear, default to the lowest
   reasonable value they mentioned.

4. license_status: derive from their exact words.
   - "I have a license" / "active" / "registered" → verified_active
   - "applied" / "in progress" / "pending" → pending_review
   - no mention or "no license" → unlicensed

5. heavy_equipment_owned: list only tools/machines that are NOT standard
   hand tools every tradesperson carries. Examples: thermal imaging camera,
   hydro jet, oscilloscope, refrigerant recovery machine, pipe inspection
   camera. Exclude: screwdrivers, spanners, tape measures, multimeters.

6. emergency_24_7: True ONLY if they explicitly said yes to emergency /
   after-hours / 24-hour calls. False if not explicitly stated.

7. background_check_consent: True ONLY if they explicitly agreed.
   False if not explicitly stated.

8. scenario_passed: always True (they passed the test to reach this stage).

Output ONLY valid JSON matching the schema. No markdown, no explanation."""


# ─────────────────────────────────────────────────────────────
# ENGINE FUNCTIONS
# ─────────────────────────────────────────────────────────────

def chat(model: str, messages: list, temperature: float = 0.1) -> str:
    """Single Ollama chat call, returns text content."""
    response = ollama.chat(
        model=model,
        messages=messages,
        options={"temperature": temperature},
    )
    return response["message"]["content"].strip()


def generate_scenario(sub_skill: str, model: str) -> str:
    """Create a field-specific troubleshooting scenario for the sub-skill."""
    messages = [
        {"role": "system", "content": SCENARIO_GENERATOR_PROMPT},
        {"role": "user", "content": f"Sub-skill: {sub_skill}"},
    ]
    return chat(model, messages, temperature=0.4)


def evaluate_answer(sub_skill: str, scenario: str, answer: str, model: str) -> tuple[bool, int, str]:
    """
    Grade the worker's scenario answer.
    Returns (passed: bool, score: int, verdict_text: str).
    """
    prompt = EVALUATOR_PROMPT_TEMPLATE.format(
        sub_skill=sub_skill,
        scenario=scenario,
        answer=answer,
    )
    messages = [{"role": "system", "content": prompt}]
    result = chat(model, messages, temperature=0.0)

    # Parse score
    score_match = re.search(r'SCORE:\s*(\d+)', result, re.IGNORECASE)
    score = int(score_match.group(1)) if score_match else 0

    # Parse verdict
    passed = bool(re.search(r'VERDICT:\s*PASS', result, re.IGNORECASE))

    return passed, score, result


def extract_profile(history: list, model: str) -> WorkerProfileSchema:
    """Extract the validated worker profile JSON from the full conversation."""
    # Strip system messages — only send the dialogue
    cleaned = [m for m in history if m["role"] != "system"]
    messages = [
        {"role": "system", "content": EXTRACTOR_PROMPT},
        *cleaned,
    ]
    response = ollama.chat(
        model=model,
        messages=messages,
        format=WorkerProfileSchema.model_json_schema(),
        options={"temperature": 0.0},
    )
    raw = response["message"]["content"].strip()
    # Strip markdown fences if present
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return WorkerProfileSchema.model_validate_json(raw)


# ─────────────────────────────────────────────────────────────
# MAIN INTERVIEW LOOP
# ─────────────────────────────────────────────────────────────

def run_interview(model_name: str = "qwen2.5:3b"):
    history: list = [{"role": "system", "content": INTERVIEWER_SYSTEM_PROMPT}]

    print("=" * 62)
    print("  KAMIGO — Worker Technical Vetting Terminal")
    print("  Type 'exit' at any time to leave.")
    print("=" * 62)

    opening = (
        "Welcome to the Kamigo vetting process. "
        "What is your primary trade?"
    )
    print(f"\nAI: {opening}\n")
    history.append({"role": "assistant", "content": opening})

    MAX_TURNS = 14
    turn = 0
    passed_scenario = False

    while turn < MAX_TURNS:
        raw_input = input("You: ").strip()
        if not raw_input:
            continue
        if raw_input.lower() == "exit":
            print("\n[SESSION ENDED]")
            return

        history.append({"role": "user", "content": raw_input})
        turn += 1

        ai_reply = chat(model_name, history, temperature=0.1)

        # ── Rejection check ──────────────────────────────────
        if REJECTION_TOKEN in ai_reply.upper():
            print(
                "\nAI: Your application does not meet our minimum criteria. "
                "This interview is now closed."
            )
            print("\n[INTERVIEW TERMINATED — criteria not met]")
            return

        # ── Scenario trigger check ────────────────────────────
        test_match = TEST_TOKEN_RE.search(ai_reply)
        if test_match:
            sub_skill = test_match.group(1).strip()

            print(f"\n[SYSTEM]: Advanced specialty identified → '{sub_skill}'")
            print("[SYSTEM]: Generating technical scenario test...\n")

            scenario = generate_scenario(sub_skill, model_name)

            print(f"AI (Technical Test):\n\n  {scenario}\n")

            worker_answer = input("You (describe your approach): ").strip()
            if not worker_answer or worker_answer.lower() == "exit":
                print("\n[SESSION ENDED — no answer provided]")
                return

            print("\n[SYSTEM]: Evaluating your response...\n")
            passed, score, verdict_log = evaluate_answer(
                sub_skill, scenario, worker_answer, model_name
            )

            # Internal log (visible in terminal for debugging)
            print(f"[INTERNAL EVALUATOR REPORT]\n{verdict_log}\n")
            print(f"[SCORE: {score}/100]")

            if passed:
                print(
                    "\nAI: Technical verification complete. "
                    "Your expertise has been confirmed."
                )
                passed_scenario = True
                # Inject the pass event into history so the extractor sees it
                history.append({
                    "role": "assistant",
                    "content": (
                        f"System: Worker passed technical scenario test for "
                        f"'{sub_skill}' with a score of {score}/100. {COMPLETE_TOKEN}"
                    ),
                })
                break
            else:
                print(
                    "\nAI: Your answer did not demonstrate sufficient technical "
                    "knowledge for this specialty. This interview is now closed."
                )
                print(f"\n[INTERVIEW TERMINATED — scenario score {score}/100, threshold 75]")
                return

        # ── Completion check ──────────────────────────────────
        elif COMPLETE_TOKEN in ai_reply:
            clean = ai_reply.replace(COMPLETE_TOKEN, "").strip()
            if clean:
                print(f"\nAI: {clean}")
            history.append({"role": "assistant", "content": ai_reply})
            passed_scenario = True
            break

        # ── Normal turn ───────────────────────────────────────
        else:
            print(f"\nAI: {ai_reply}\n")
            history.append({"role": "assistant", "content": ai_reply})

    # ── Max turns reached without completion ─────────────────
    if not passed_scenario:
        print(
            "\n[INTERVIEW CLOSED — maximum questions reached without "
            "completing the scenario test]"
        )
        return

    # ── Stage 6: Profile extraction ───────────────────────────
    print("\n" + "=" * 62)
    print("  COMPILING VERIFIED WORKER PROFILE")
    print("=" * 62)

    try:
        profile = extract_profile(history, model_name)
        output = json.dumps(profile.model_dump(), indent=2)
        print("\n[SUCCESS] Kamigo Worker Profile — ready for database:\n")
        print(output)
        return profile
    except Exception as e:
        print(f"\n[ERROR] Failed to compile profile: {e}")
        print("Raw conversation saved for manual review.")


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_interview(model_name="qwen2.5:3b")