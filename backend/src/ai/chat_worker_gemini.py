"""
Kamigo Worker Interview System — Nepal Universal Edition
=========================================================
Supports ANY local job a worker in Nepal might offer.
No hardcoded trade list. AI dynamically discovers the job,
probes for a genuine specialty, then runs a scenario test.

Pipeline:
  Stage 1 — Job discovery      → what work do they do?
  Stage 2 — Experience gate    → blocks beginners and zero-exp
  Stage 3 — Sub-skill probe    → drills to a real advanced niche
  Stage 4 — Scenario test      → AI writes a real field problem
  Stage 5 — AI evaluation      → scores 0–100, pass = >75
  Stage 6 — JSON output        → structured profile for Kamigo DB
"""

import json
import re
import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai
from typing import List, Optional
from pydantic import BaseModel, Field

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("[ERROR] GEMINI_API_KEY not found in environment. Add it to your .env file.")
    sys.exit(1)

genai.configure(api_key=api_key)


# ─────────────────────────────────────────────────────────────
# OUTPUT SCHEMA
# Dynamic — works for any job category in Nepal
# ─────────────────────────────────────────────────────────────

class WorkerProfile(BaseModel):
    full_name: Optional[str] = Field(
        default=None,
        description="Worker's name if mentioned during interview. Null if not given."
    )
    job_category: str = Field(
        description=(
            "The broad job type in plain English. "
            "Examples: plumber, electrician, carpenter, mechanic, tailor, "
            "painter, gardener, cook, delivery driver, mason, welder, "
            "cleaner, tutor, photographer, IT technician, beautician, etc."
        )
    )
    verified_specialty: str = Field(
        description=(
            "The ONE specific advanced sub-skill that was TESTED and PASSED "
            "in the scenario step. Must be precise. "
            "Examples: 'solar water heater installation and fault diagnosis', "
            "'motorcycle carburetor rebuild and tuning', "
            "'traditional Newari woodcarving and restoration', "
            "'hydraulic brake system overhaul on heavy trucks'."
        )
    )
    years_experience: int = Field(
        description="Total years of professional experience in this job."
    )
    license_or_certification: str = Field(
        description=(
            "Any license, certification, or formal training they hold. "
            "Examples: 'CTEVT certified electrician', 'driving license class A', "
            "'no formal certification', 'apprenticeship under master craftsman'."
        )
    )
    specialized_tools_or_equipment: List[str] = Field(
        description=(
            "Specialized tools, machines, or equipment they own/operate "
            "that go beyond basic hand tools. "
            "Exclude: screwdrivers, hammers, measuring tape, basic spanners. "
            "Include: welding machine, pipe inspection camera, oscilloscope, "
            "DSLR camera kit, industrial sewing machine, angle grinder, etc."
        )
    )
    service_area: Optional[str] = Field(
        default=None,
        description=(
            "Where they work: district, city, or area in Nepal. "
            "Examples: 'Kathmandu Valley', 'Pokhara', 'Biratnagar', "
            "'willing to travel across Nepal'. Null if not mentioned."
        )
    )
    emergency_available: bool = Field(
        description=(
            "True ONLY if they explicitly said they are available for "
            "urgent/emergency/after-hours calls. False if not stated."
        )
    )
    background_check_consent: bool = Field(
        description=(
            "True ONLY if they explicitly agreed to a background check. "
            "False if not stated."
        )
    )
    scenario_passed: bool = Field(
        description="Always True — worker only reaches JSON stage after passing the test."
    )
    scenario_score: int = Field(
        description="The score (0–100) the worker received on their technical scenario test."
    )


# ─────────────────────────────────────────────────────────────
# PIPELINE TOKENS
# These are the control signals the interviewer AI outputs
# to trigger the next pipeline stage. The orchestrator
# watches for these in every AI response.
# ─────────────────────────────────────────────────────────────

REJECTION_TOKEN = "[REJECTED]"
TEST_TOKEN_RE   = re.compile(r'\[TEST_REQUIRED:\s*(.+?)\]', re.IGNORECASE)
COMPLETE_TOKEN  = "[COMPLETE]"


# ─────────────────────────────────────────────────────────────
# PROMPT 1 — INTERVIEWER
# The main conversational AI. Runs the full interview.
# ─────────────────────────────────────────────────────────────

INTERVIEWER_SYSTEM_PROMPT = f"""You are a professional technical vetting officer for Kamigo — a local services platform in Nepal.
Your job is to interview workers who want to register on the platform to provide paid services to customers.

Kamigo connects customers with skilled local workers across ALL types of work:
trades, crafts, repair, domestic, transport, creative, technical, and personal services.
There is NO restricted list of jobs. Any legitimate work a person can be hired to do in Nepal is valid.

════════════════════════════════════════════════════
YOUR MISSION
════════════════════════════════════════════════════
Discover the worker's job, verify they have real experience,
uncover ONE genuine advanced specialty, then trigger a test.

════════════════════════════════════════════════════
STRICT RULES — FOLLOW EVERY ONE
════════════════════════════════════════════════════

RULE 1 — ONE QUESTION PER TURN
Ask exactly ONE question per response.
Never combine two questions.
Keep each response under 30 words.
Be direct. No filler phrases.

────────────────────────────────────────────────────
RULE 2 — LANGUAGE
Respond in the same language the worker uses.
If they write in Nepali, reply in Nepali.
If they write in English, reply in English.
If they mix both, follow their lead.
────────────────────────────────────────────────────

────────────────────────────────────────────────────
RULE 3 — INFORMATION TO COLLECT (collect in this order)
  a) What is their job or work?
  b) How many years of professional experience?
  c) Do they have any license, certificate, or formal training?
  d) What is their ONE advanced specialty? (see Rule 5)
  e) What specialized tools or equipment do they own?
  f) Which area in Nepal do they work in?
  g) Are they available for emergency/urgent calls?
  h) Do they consent to a background check?

Collect these strictly one at a time. Do not skip ahead.
Do not ask about equipment until you have the specialty.
────────────────────────────────────────────────────

────────────────────────────────────────────────────
RULE 4 — REJECTION TRIGGERS
Output ONLY the exact token {REJECTION_TOKEN} (nothing else) when:

  • Worker says they have 0 years of experience.
  • Worker calls themselves a beginner, student, or trainee.
  • Worker says they are "still learning" or "just started".
  • Worker's response is complete gibberish with no work relevance
    (e.g. random letters, math formulas like "2+2", song lyrics,
    nonsense words, completely off-topic responses).
  • Worker provides evasive non-answers THREE times in a row.
  • Worker becomes abusive or threatening.

IMPORTANT: Do NOT reject on the FIRST unclear answer.
Give ONE follow-up question to clarify before rejecting.
After the follow-up, if still invalid → {REJECTION_TOKEN}.
────────────────────────────────────────────────────

────────────────────────────────────────────────────
RULE 5 — SUB-SKILL PROBING (most critical rule)

Goal: Find ONE genuine advanced niche — not a basic task
that any person with that job title can do.

STEP A — First, ask for their primary focus:
  "What type of [job] work do you do most often?"
  OR
  "What is your main speciality within [job]?"

STEP B — If the answer is vague, probe deeper with ONE of:
  "Do you work on residential or commercial projects?"
  "What is the most complex job you have completed recently?"
  "What specific technique or equipment do you specialise in?"
  "Give me one example of a job only an expert in your field could do."

STEP C — Reject generic answers.
  Generic means: any basic task that comes with the job title.
  Examples of answers that are TOO BASIC to accept as a specialty:

  Mechanic → "I fix cars" / "engine repair" / "tyre change"
  Plumber → "fix leaks" / "install pipes" / "unclog drains"
  Electrician → "install wiring" / "fix switches" / "change bulbs"
  Carpenter → "make furniture" / "fix doors" / "wood cutting"
  Tailor → "stitch clothes" / "make shirts" / "repair clothes"
  Painter → "paint walls" / "house painting" / "colour mixing"
  Cook → "cook food" / "make dal bhat" / "general cooking"
  Driver → "drive vehicle" / "transport people" / "car driving"
  Cleaner → "clean house" / "sweep floors" / "mopping"
  Mason → "build walls" / "brick laying" / "plastering"

  These are what ANY person in that job can do. They do NOT qualify.

  If the worker claims something too basic, push back ONCE:
  "That is common for most [job] workers. What advanced or specialist
   work do you do that requires specific skill or training?"

  If after TWO push-backs they still cannot name anything advanced
  → output {REJECTION_TOKEN}.

STEP D — Accept answers that show genuine specialisation.
  Valid advanced specialties look like:

  Mechanic → "motorcycle carburetor rebuilding and fuel system tuning"
  Plumber → "solar water heater installation and pressurised system commissioning"
  Electrician → "three-phase industrial panel installation and load balancing"
  Carpenter → "traditional Newari wood carving and antique furniture restoration"
  Tailor → "hand-embroidered Dhaka fabric garments and custom traditional wear"
  Cook → "authentic Newar feast preparation for large events (100+ guests)"
  Welder → "TIG welding of stainless steel food-grade equipment"
  IT technician → "CCTV and access control system installation and networking"
  Photographer → "high-altitude trekking and wildlife photography"

  When you have identified a valid advanced specialty,
  STOP all other questions and output exactly:
  [TEST_REQUIRED: <the exact specialty in plain words>]

  The specialty name must be specific enough that a technical
  scenario test question can be written about it.
────────────────────────────────────────────────────

────────────────────────────────────────────────────
RULE 6 — AFTER THE SCENARIO TEST
The system will inject a message telling you the test result.
  • If the worker PASSED: immediately output {COMPLETE_TOKEN}
  • If the worker FAILED: immediately output {REJECTION_TOKEN}
────────────────────────────────────────────────────

────────────────────────────────────────────────────
TONE
Professional and respectful. Not warm, not cold.
No greetings after the opening. No compliments.
No filler like "Great!" or "Thank you for sharing."
Just direct, clear questions.
────────────────────────────────────────────────────"""


# ─────────────────────────────────────────────────────────────
# PROMPT 2 — SCENARIO GENERATOR
# Writes the technical test question for any job type.
# ─────────────────────────────────────────────────────────────

SCENARIO_GENERATOR_PROMPT = """\
You are a senior technical supervisor who has managed skilled workers
across many trades and services in Nepal for over 20 years.

Your task: Write ONE realistic, practical test scenario for a worker
claiming expertise in the specific sub-skill given to you.

The scenario MUST:
  1. Describe a real on-the-job situation or problem the worker would face.
  2. Be specific to the sub-skill — not generic to the whole job category.
  3. Require hands-on field knowledge to answer correctly.
     A person who only read about the job cannot answer it well.
  4. End with a direct question: "What would you do?" or
     "Walk me through your exact steps."
  5. Be 45–65 words. No longer.
  6. Sound like a supervisor speaking to a worker, not a textbook.

Write ONLY the scenario. No title, no label, no introduction."""


# ─────────────────────────────────────────────────────────────
# PROMPT 3 — EVALUATOR
# Grades the worker's scenario answer for any job type.
# ─────────────────────────────────────────────────────────────

EVALUATOR_PROMPT_TEMPLATE = """\
You are an expert assessor grading a practical interview for a skilled worker.

Sub-skill being tested: {sub_skill}
Scenario given to the worker: {scenario}
Worker's answer: {answer}

GRADING RULES — read carefully:

AWARD MARKS FOR:
  ✓ Job-specific terminology (tool names, part names, material names,
    technique names, process steps) — even if spelled wrong or informal
  ✓ Correct troubleshooting or work sequence, even if brief
  ✓ Identification of the core problem or key challenge
  ✓ Mention of safety, quality checks, or common mistakes to avoid
  ✓ Practical knowledge that only comes from doing the job, not reading about it

DO NOT PENALISE:
  ✗ Poor grammar, spelling mistakes, or broken English
  ✗ Short answers (a skilled worker may answer in 2–3 sentences)
  ✗ Casual or informal language
  ✗ Mixing Nepali/Hindi words with English
  ✗ Not knowing a single technical term if the overall approach is correct

SCORE ZERO IF:
  ✗ The answer has no connection to the scenario or sub-skill
  ✗ The answer is pure filler ("I would fix it", "I know how to do it")
  ✗ The answer shows no understanding of the specific work involved

PARTIAL CREDIT (40–74):
  → Correct direction but missing key steps or tools
  → Right tools mentioned but wrong sequence
  → Understands the problem but gives incomplete solution

PASS THRESHOLD: Score above 75 means real field knowledge is demonstrated.

Write a 2–3 sentence assessment explaining your grade.
Then output EXACTLY (on separate lines, no extra text):
SCORE: <integer 0 to 100>
VERDICT: PASS
or
SCORE: <integer 0 to 100>
VERDICT: FAIL"""


# ─────────────────────────────────────────────────────────────
# PROMPT 4 — JSON EXTRACTOR
# Parses the full conversation into a clean profile.
# ─────────────────────────────────────────────────────────────

EXTRACTOR_PROMPT = """\
You are a strict data parser for the Kamigo worker registration system in Nepal.

Read the interview transcript carefully and extract the worker profile.
Follow every rule below precisely.

FIELD RULES:

full_name:
  Extract only if the worker gave their name during the interview.
  If not mentioned, output null.

job_category:
  The broad job title in plain English.
  Normalise to a standard label: "plumber", "electrician", "mechanic",
  "carpenter", "tailor", "cook", "welder", "painter", "mason",
  "cleaner", "driver", "photographer", "IT technician", etc.

verified_specialty:
  Copy the EXACT sub-skill name from the [TEST_REQUIRED: ...] token
  in the transcript. Do not rewrite, summarise, or shorten it.
  This must match exactly what was tested.

years_experience:
  Integer only. If a range was given (e.g. "8 to 10 years"), use the lower number.
  If unclear, use the most conservative number mentioned.

license_or_certification:
  Exact description of any formal credential.
  If none mentioned: "no formal certification".
  If they mentioned training/apprenticeship but no formal cert: describe it.

specialized_tools_or_equipment:
  List only non-basic tools or machines they mentioned owning or regularly using.
  Do NOT include: screwdrivers, hammers, spanners, measuring tape,
  basic drill, paintbrush, mop, broom, or any tool every person in
  that job would have.
  DO include: welding machine, DSLR camera kit, industrial sewing machine,
  pipe inspection camera, thermal imager, oscilloscope, angle grinder,
  motorcycle lift, commercial mixer, etc.
  If nothing specialized was mentioned, output an empty list [].

service_area:
  District, city, or region in Nepal where they work.
  If not mentioned, output null.

emergency_available:
  True ONLY if they explicitly said yes to emergency/urgent/after-hours calls.
  Any ambiguous answer → False.

background_check_consent:
  True ONLY if they explicitly agreed to a background check.
  Any ambiguous answer → False.

scenario_passed:
  Always output true. The worker only reaches extraction after passing.

scenario_score:
  The integer score from the SCORE: line in the evaluator report
  that was injected into the transcript. Extract it exactly.

Output ONLY valid JSON. No markdown fences. No explanation. No extra keys."""


# ─────────────────────────────────────────────────────────────
# GEMINI API HELPERS
# ─────────────────────────────────────────────────────────────

def _to_gemini_history(history: list) -> list:
    """Convert internal history format to Gemini's expected format."""
    result = []
    for msg in history:
        if msg["role"] == "system":
            continue
        role = "user" if msg["role"] == "user" else "model"
        result.append({"role": role, "parts": [msg["content"]]})
    return result


def _get_system_prompt(history: list) -> Optional[str]:
    return next((m["content"] for m in history if m["role"] == "system"), None)


def chat(model_name: str, history: list, temperature: float = 0.1) -> str:
    """Send conversation history to Gemini and return the response text."""
    system_prompt = _get_system_prompt(history)
    gemini_history = _to_gemini_history(history)

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,
    )
    response = model.generate_content(
        gemini_history,
        generation_config=genai.GenerationConfig(temperature=temperature),
    )
    return response.text.strip()


def generate_scenario(sub_skill: str, model_name: str) -> str:
    """Generate a field-specific test scenario for the claimed sub-skill."""
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SCENARIO_GENERATOR_PROMPT,
    )
    response = model.generate_content(
        f"Sub-skill to test: {sub_skill}",
        generation_config=genai.GenerationConfig(temperature=0.5),
    )
    return response.text.strip()


def evaluate_answer(
    sub_skill: str, scenario: str, answer: str, model_name: str
) -> tuple[bool, int, str]:
    """
    Grade the worker's scenario answer.
    Returns: (passed: bool, score: int, full_evaluator_report: str)
    """
    prompt = EVALUATOR_PROMPT_TEMPLATE.format(
        sub_skill=sub_skill,
        scenario=scenario,
        answer=answer,
    )
    model = genai.GenerativeModel(model_name=model_name)
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=0.0),
    )
    result = response.text.strip()

    score_match = re.search(r'SCORE:\s*(\d+)', result, re.IGNORECASE)
    score = int(score_match.group(1)) if score_match else 0
    passed = bool(re.search(r'VERDICT:\s*PASS', result, re.IGNORECASE))

    return passed, score, result


def extract_profile(history: list, score: int, model_name: str) -> WorkerProfile:
    """
    Parse the full conversation into a structured WorkerProfile.
    Uses Gemini's native JSON mode for reliable output.
    """
    gemini_history = _to_gemini_history(history)

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=EXTRACTOR_PROMPT,
    )
    response = model.generate_content(
        gemini_history,
        generation_config=genai.GenerationConfig(
            temperature=0.0,
            response_mime_type="application/json",
        ),
    )
    raw = response.text.strip()
    # Strip any accidental markdown fences
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    profile = WorkerProfile.model_validate_json(raw)
    # Ensure score is always accurate from the evaluator, not hallucinated
    profile.scenario_score = score
    return profile


# ─────────────────────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────────────────────

DIVIDER     = "=" * 62
SUB_DIVIDER = "─" * 62

def print_header():
    print(f"\n{DIVIDER}")
    print("  KAMIGO — Worker Registration & Vetting Terminal")
    print("  Nepal Local Services Platform")
    print(f"  Type 'exit' at any time to quit.")
    print(f"{DIVIDER}\n")

def print_stage(label: str):
    print(f"\n{SUB_DIVIDER}")
    print(f"  {label}")
    print(f"{SUB_DIVIDER}")

def print_terminated(reason: str):
    print(f"\n{DIVIDER}")
    print(f"  INTERVIEW TERMINATED")
    print(f"  Reason: {reason}")
    print(f"{DIVIDER}\n")

def print_success(profile_json: str):
    print(f"\n{DIVIDER}")
    print("  VERIFICATION COMPLETE — WORKER PROFILE GENERATED")
    print(f"{DIVIDER}")
    print("\n" + profile_json + "\n")


# ─────────────────────────────────────────────────────────────
# MAIN INTERVIEW ORCHESTRATOR
# ─────────────────────────────────────────────────────────────

def run_interview(model_name: str = "gemini-2.5-flash") -> Optional[WorkerProfile]:
    """
    Run the full Kamigo worker interview.
    Returns the WorkerProfile on success, None on failure/exit.
    """
    history: list = [{"role": "system", "content": INTERVIEWER_SYSTEM_PROMPT}]

    print_header()

    opening = (
        "Welcome to the Kamigo worker registration process. "
        "What type of work or service do you provide?"
    )
    print(f"AI: {opening}\n")
    history.append({"role": "assistant", "content": opening})

    MAX_TURNS   = 18    # Enough for organic one-question-at-a-time flow
    turn        = 0
    final_score = 0
    passed      = False

    # ── Main conversation loop ────────────────────────────────
    while turn < MAX_TURNS:

        try:
            raw_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n[SESSION ENDED]")
            return None

        if not raw_input:
            continue

        if raw_input.lower() in ("exit", "quit", "bye"):
            print("\n[SESSION ENDED BY WORKER]")
            return None

        history.append({"role": "user", "content": raw_input})
        turn += 1

        # ── Get AI response ───────────────────────────────────
        try:
            ai_reply = chat(model_name, history, temperature=0.1)
        except Exception as e:
            print(f"\n[SYSTEM ERROR] Could not reach AI model: {e}")
            print("Please check your API key and internet connection.")
            return None

        # ── Check for rejection ───────────────────────────────
        if REJECTION_TOKEN in ai_reply.upper():
            print(
                "\nAI: Thank you for your time. Unfortunately your application "
                "does not meet our minimum requirements at this stage."
            )
            print_terminated("Worker did not meet vetting criteria.")
            return None

        # ── Check for scenario test trigger ───────────────────
        test_match = TEST_TOKEN_RE.search(ai_reply)
        if test_match:
            sub_skill = test_match.group(1).strip()

            # Show the AI message up to (but not including) the token
            visible_reply = ai_reply[:test_match.start()].strip()
            if visible_reply:
                print(f"\nAI: {visible_reply}\n")

            print_stage(f"TECHNICAL SCENARIO TEST  →  '{sub_skill}'")
            print("Generating your test scenario...\n")

            # Generate scenario
            try:
                scenario = generate_scenario(sub_skill, model_name)
            except Exception as e:
                print(f"[SYSTEM ERROR] Could not generate scenario: {e}")
                return None

            print(f"AI (Test Question):\n\n    {scenario}\n")

            # Get worker's answer
            try:
                worker_answer = input("You (describe your approach): ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n[SESSION ENDED]")
                return None

            if not worker_answer or worker_answer.lower() in ("exit", "quit"):
                print("\n[SESSION ENDED — no answer provided]")
                return None

            print("\n[Evaluating your answer...]\n")

            # Evaluate
            try:
                passed, final_score, verdict_log = evaluate_answer(
                    sub_skill, scenario, worker_answer, model_name
                )
            except Exception as e:
                print(f"[SYSTEM ERROR] Evaluation failed: {e}")
                return None

            # Show internal evaluator report (remove this in production)
            print(f"[EVALUATOR REPORT]\n{verdict_log}\n")
            print(f"[SCORE: {final_score}/100  |  PASS THRESHOLD: 75]\n")

            if passed:
                print("AI: Technical verification complete. Your expertise has been confirmed.")

                # Inject result back into history so extractor can see it
                history.append({
                    "role": "assistant",
                    "content": (
                        f"[TEST_REQUIRED: {sub_skill}]\n"
                        f"System record: Worker answered the scenario test for "
                        f"'{sub_skill}'. Evaluator score: {final_score}/100. "
                        f"Result: PASS. {COMPLETE_TOKEN}"
                    ),
                })
                break  # Exit loop → go to JSON extraction

            else:
                print(
                    "AI: Your answer did not demonstrate sufficient field knowledge "
                    "for this specialty. This application cannot proceed."
                )
                print_terminated(
                    f"Scenario test failed — score {final_score}/100 "
                    f"(required >75) for '{sub_skill}'."
                )
                return None

        # ── Check for early completion ─────────────────────────
        elif COMPLETE_TOKEN in ai_reply:
            clean = ai_reply.replace(COMPLETE_TOKEN, "").strip()
            if clean:
                print(f"\nAI: {clean}\n")
            history.append({"role": "assistant", "content": ai_reply})
            passed = True
            break

        # ── Normal conversational turn ─────────────────────────
        else:
            print(f"\nAI: {ai_reply}\n")
            history.append({"role": "assistant", "content": ai_reply})

    # ── Max turns reached without reaching scenario ───────────
    if not passed:
        print_terminated(
            "Maximum interview length reached without completing the scenario test."
        )
        return None

    # ── Stage 6: Extract structured JSON profile ──────────────
    print_stage("COMPILING WORKER PROFILE FOR DATABASE")
    print("Processing...\n")

    try:
        profile = extract_profile(history, final_score, model_name)
    except Exception as e:
        print(f"[ERROR] Could not compile profile: {e}")
        print("The raw conversation has been preserved for manual review.")
        return None

    profile_json = json.dumps(profile.model_dump(), indent=2, ensure_ascii=False)
    print_success(profile_json)
    return profile


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_interview(model_name="gemini-2.5-flash")