"""
Kamigo Customer Intake System
==============================
English-only, simple and friendly problem intake.
The customer describes their issue in plain words.
The AI asks at most 2-3 short follow-up questions,
then extracts a clean JSON payload for worker matching.

Flow:
  Step 1 — Customer describes problem (free text, plain English)
  Step 2 — AI fills gaps with max 3 short questions
  Step 3 — AI signals COMPLETE when enough context exists
  Step 4 — Extractor produces structured JSON for Kamigo DB
"""

import json
import re
import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai
from typing import Optional, List
from pydantic import BaseModel, Field

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("[ERROR] GEMINI_API_KEY not found. Please add it to your .env file.")
    sys.exit(1)

genai.configure(api_key=api_key)


# ─────────────────────────────────────────────────────────────
# OUTPUT SCHEMA
# Every field is Optional — only filled from what the customer
# actually said. Missing fields stay null, never guessed.
# ─────────────────────────────────────────────────────────────

class CustomerProblemSchema(BaseModel):

    # ── Core matching fields ──────────────────────────────────

    job_category: str = Field(
        description=(
            "The type of worker needed. Use a simple job title. "
            "Examples: plumber, electrician, carpenter, mechanic, painter, "
            "cleaner, cook, welder, mason, gardener, pest control, IT technician, "
            "appliance repair, AC technician, driver, handyman, tailor, photographer. "
            "Pick the closest match. Never leave blank."
        )
    )

    problem_summary: str = Field(
        description=(
            "1 to 2 plain sentences describing the customer's problem. "
            "Written so a worker immediately understands the job. "
            "Keep it simple and clear."
        )
    )

    specific_issue: str = Field(
        description=(
            "The exact fault or symptom the customer described. "
            "Examples: 'water dripping from ceiling pipe', "
            "'power trips when AC turns on', "
            "'washing machine drum not spinning', "
            "'door hinge broken and door will not close'. "
            "Use the customer's own words as much as possible."
        )
    )

    urgency: str = Field(
        description=(
            "How urgent is this? Pick one: "
            "'emergency' — danger or major damage happening right now, "
            "'high' — serious, needs fixing today, "
            "'medium' — annoying but can wait 1 to 2 days, "
            "'low' — no rush, general maintenance or small improvement. "
            "If the customer did not say, figure it out from context. "
            "Burst pipe = emergency. Dripping tap = medium. "
            "No power in whole house = high."
        )
    )

    # ── Location ──────────────────────────────────────────────

    location: Optional[str] = Field(
        default=None,
        description=(
            "Where the job needs to happen. "
            "Neighbourhood, city, or area. "
            "Examples: 'Kathmandu', 'Lalitpur', 'Pokhara', 'Biratnagar'. "
            "Null if not mentioned."
        )
    )

    # ── Problem context ───────────────────────────────────────

    problem_duration: Optional[str] = Field(
        default=None,
        description=(
            "How long has the problem been happening? "
            "Examples: 'since this morning', '3 days', 'just happened'. "
            "Null if not mentioned."
        )
    )

    affected_area: Optional[str] = Field(
        default=None,
        description=(
            "Which part of the home or property is affected? "
            "Examples: 'kitchen', 'bathroom', 'bedroom', 'whole house', 'outside'. "
            "Null if not mentioned."
        )
    )

    property_type: Optional[str] = Field(
        default=None,
        description=(
            "Type of property. "
            "Examples: 'house', 'apartment', 'shop', 'office', 'restaurant'. "
            "Null if not mentioned."
        )
    )

    # ── Scope signals for worker ──────────────────────────────

    estimated_scale: Optional[str] = Field(
        default=None,
        description=(
            "How big is the job, if mentioned or obvious. "
            "Examples: 'small repair', 'full room', 'single tap', 'whole house'. "
            "Null if not mentioned."
        )
    )

    materials_needed: Optional[List[str]] = Field(
        default=None,
        description=(
            "Parts or materials the customer mentioned needing. "
            "Examples: ['new tap', 'copper wire', 'door hinge']. "
            "Null if not mentioned."
        )
    )

    previous_attempts: Optional[str] = Field(
        default=None,
        description=(
            "Did the customer already try to fix it? What happened? "
            "Examples: 'tried tightening the valve but still leaking', "
            "'another plumber came but could not fix it'. "
            "Null if not mentioned."
        )
    )

    # ── Customer preferences ──────────────────────────────────

    budget_mentioned: Optional[str] = Field(
        default=None,
        description=(
            "Any budget the customer mentioned. "
            "Examples: 'under 2000 rupees', 'around 500', 'whatever it costs'. "
            "Null if not mentioned."
        )
    )

    preferred_time: Optional[str] = Field(
        default=None,
        description=(
            "When the customer wants the work done. "
            "Examples: 'right now', 'this evening', 'tomorrow morning', 'this weekend'. "
            "Null if not mentioned."
        )
    )

    worker_gender_preference: Optional[str] = Field(
        default=None,
        description=(
            "Did the customer ask for a male or female worker? "
            "Examples: 'female worker preferred', 'male worker'. "
            "Null if not mentioned."
        )
    )

    # ── Matching tags ─────────────────────────────────────────

    matching_tags: List[str] = Field(
        description=(
            "4 to 8 short keyword tags used to match this job to the right worker. "
            "Always include the job type and urgency level. "
            "Add location, affected area, and main symptom if known. "
            "Example for a leaking kitchen pipe: "
            "['plumbing', 'pipe leak', 'kitchen', 'medium', 'Kathmandu']. "
            "Example for a broken washing machine: "
            "['appliance repair', 'washing machine', 'not spinning', 'high', 'Pokhara']."
        )
    )

    # ── Metadata ──────────────────────────────────────────────

    confidence_level: str = Field(
        description=(
            "How clear was the customer's description? "
            "'high' — customer was clear, all main fields filled. "
            "'medium' — some guessing needed, main fields are present. "
            "'low' — customer was very vague, a lot of guessing was used."
        )
    )


# ─────────────────────────────────────────────────────────────
# CONTROL TOKEN
# ─────────────────────────────────────────────────────────────

COMPLETE_TOKEN = "[COMPLETE]"


# ─────────────────────────────────────────────────────────────
# PROMPT 1 — INTAKE AGENT
# Friendly, English-only, minimal friction.
# Asks max 3 short questions then signals complete.
# ─────────────────────────────────────────────────────────────

INTAKE_SYSTEM_PROMPT = f"""You are Kamigo's friendly helper. Kamigo is a home services app.
Your job is to understand what problem the customer has so the right worker can be sent quickly.

YOUR PERSONALITY
Keep it warm, simple, and short — like a helpful friend.
Never use technical words. Never be formal. Keep sentences short.
Speak like you are texting a friend, not writing an email.

YOUR GOAL
You need just 3 things to find the right worker:
  1. What is the problem?
  2. How urgent is it?
  3. Where is the customer?

Everything else (which room, how long, budget, timing) is a bonus.
Only ask about those if the customer already mentioned them
or if you can get two answers with one simple question.

HOW TO UNDERSTAND VAGUE ANSWERS
Customers are not technical. They may say things like:
  "my light stopped working" → electricity problem
  "water is coming from the ceiling" → pipe leak, could be emergency
  "my fridge is not cold" → appliance repair
  "something is wrong with my AC" → AC technician needed
  "there is a smell of gas" → GAS LEAK — EMERGENCY, go straight to complete
  "I got a shock from the plug" → electric shock — EMERGENCY
  "my toilet won't flush" → plumber needed
  "water is everywhere" → flooding — EMERGENCY
  "it's not working" → ask: "What is not working?"
  "something happened" → ask: "What happened? Which part of your home?"

If the problem is clear from what they said, do NOT ask them to say it again.
If it sounds dangerous (gas, electric shock, flooding, fire), treat it as an EMERGENCY right away.

HOW TO TALK TO THE CUSTOMER

After the customer's first message:
  → Did they tell you the problem, urgency, and location?
  → If YES to all three → go straight to {COMPLETE_TOKEN}. Do not ask anything.
  → If one or two things are missing → ask the ONE most important missing thing.
    Make it simple. Give options when you can.
    Good examples:
      "Is it happening right now or has it been like this for a few days?"
      "Which part of your home — kitchen, bathroom, or somewhere else?"
      "Is this urgent, or can it wait a day or two?"

After the customer's second message:
  → Do you now have the problem, urgency, and location?
  → If YES → go to {COMPLETE_TOKEN}.
  → If still missing something → ask ONE more short question.
  → Never ask the same thing twice.

After the customer's third message:
  → This is the last question you are allowed to ask.
  → Only ask if location is still completely unknown.
  → After they reply → go to {COMPLETE_TOKEN} no matter what.

MAXIMUM 3 QUESTIONS. Never ask a 4th question.
If you have enough after 0, 1, or 2 questions → finish early.

QUESTION RULES
✓ One question at a time. Never two questions in one message.
✓ Keep questions under 12 words.
✓ Give options when possible — "Is it a leak or no water at all?"
✓ Never ask for brand names, model numbers, or technical details.
✓ Never ask something the customer already told you.
✓ Never give advice or say "try turning it off and on."
✓ Never say "please describe in more detail" — that is too hard for the customer.

EMERGENCIES
If the customer mentions any of these, say it is urgent and go straight to {COMPLETE_TOKEN}:
  • Water flooding the house
  • Gas smell or gas leak
  • Electric shock or sparks
  • Fire or smoke
  • No power in the whole house
  • Sewage overflowing inside
  • Someone was hurt

For emergencies say: "This sounds urgent! We are sending a worker to you right now."
Then append {COMPLETE_TOKEN}.

FINISHING THE CONVERSATION
When you have enough information, say one short friendly closing line and append {COMPLETE_TOKEN}.

Good closing lines:
  "Got it! We are finding the right worker for you now."
  "Perfect, we are on it! A worker will contact you shortly."
  "Thanks! We are matching you with the best worker near you."

One sentence only. Then {COMPLETE_TOKEN}. Do not list the problem back to them.

NEVER DO THESE
✗ Never ask more than 3 questions total
✗ Never give DIY or fixing advice
✗ Never say "I cannot help with that"
✗ Never ask for the customer's name or phone number
✗ Never use technical words or jargon
✗ Never say you are an AI or a bot"""


# ─────────────────────────────────────────────────────────────
# PROMPT 2 — JSON EXTRACTOR
# Silent background agent. Never seen by customer.
# Produces the structured payload for Kamigo worker matching.
# ─────────────────────────────────────────────────────────────

EXTRACTOR_SYSTEM_PROMPT = """You are a silent data extraction engine for the Kamigo platform.

You will receive a conversation between a customer and an intake assistant.
Read it carefully and extract every useful detail into a structured JSON payload
for the worker-matching database.

EXTRACTION RULES

1. USE PLAIN ENGLISH
   All fields must be in plain, simple English.
   Keep descriptions short and clear — written for a worker to read quickly.

2. INFER FROM CONTEXT
   Customers are not technical. Read between the lines:
   "my light stopped working"       → electrician, light or power fault
   "water coming from ceiling"      → plumber, pipe leak
   "fridge not cold"                → appliance repair, cooling fault
   "AC not cooling" / "AC is off"   → AC technician
   "toilet won't flush"             → plumber
   "got a shock from socket"        → electrician, EMERGENCY
   "smell of gas"                   → gas technician or plumber, EMERGENCY
   "water everywhere"               → plumber, flooding, EMERGENCY
   "it's not working"               → use other context to pick category
   Map everything to the most logical job_category and specific_issue.

3. URGENCY RULES
   emergency → flooding, gas leak, electric shock, fire, sewage overflow, injury
   high      → no power at all, major leak, broken security door, no water at all
   medium    → appliance broken, dripping tap, door issues, slow drain, AC not cooling
   low       → painting, cleaning, gardening, minor cosmetic jobs

4. MATCHING TAGS
   Generate 4 to 8 short searchable tags.
   Always include: job type + urgency level + main symptom.
   Add location, affected area, specific item if known.
   Example — bathroom pipe leaking for 2 days:
   ["plumbing", "pipe leak", "bathroom", "medium", "2 days"]

5. CONFIDENCE LEVEL
   high   → customer was clear, location known, problem obvious
   medium → some guessing needed, main fields are present
   low    → very vague, a lot of guessing was used

6. NULL POLICY
   Only use null for Optional fields if the information was truly not mentioned
   and cannot be reasonably guessed from context.
   Never make up addresses, prices, or brand names.

7. OUTPUT
   Output ONLY valid JSON. No markdown. No explanation. No extra keys."""


# ─────────────────────────────────────────────────────────────
# GEMINI API HELPERS
# ─────────────────────────────────────────────────────────────

def _build_gemini_history(history: list) -> list:
    """Convert internal message format to Gemini's expected format."""
    result = []
    for msg in history:
        if msg["role"] == "system":
            continue
        role = "user" if msg["role"] == "user" else "model"
        result.append({"role": role, "parts": [msg["content"]]})
    return result


def chat(model_name: str, history: list, temperature: float = 0.2) -> str:
    """Send conversation history to Gemini, return response text."""
    system_prompt = next(
        (m["content"] for m in history if m["role"] == "system"), None
    )
    gemini_history = _build_gemini_history(history)

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,
    )
    response = model.generate_content(
        gemini_history,
        generation_config=genai.GenerationConfig(temperature=temperature),
    )
    return response.text.strip()


def extract_json(history: list, model_name: str) -> CustomerProblemSchema:
    """Extract structured problem JSON from the conversation history."""
    gemini_history = _build_gemini_history(history)

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=EXTRACTOR_SYSTEM_PROMPT,
    )
    response = model.generate_content(
        gemini_history,
        generation_config=genai.GenerationConfig(
            temperature=0.0,
            response_mime_type="application/json",
        ),
    )
    raw = response.text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    return CustomerProblemSchema.model_validate_json(raw)


# ─────────────────────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────────────────────

DIVIDER = "=" * 56

def print_header():
    print(f"\n{DIVIDER}")
    print("  Kamigo — What can we help you fix today?")
    print(f"  Type 'exit' to quit.")
    print(f"{DIVIDER}\n")

def print_json_output(data: dict):
    print(f"\n{DIVIDER}")
    print("  PROBLEM CAPTURED — Finding your worker now...")
    print(f"{DIVIDER}")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"{DIVIDER}\n")


# ─────────────────────────────────────────────────────────────
# MAIN INTAKE LOOP
# ─────────────────────────────────────────────────────────────

def run_customer_intake(model_name: str = "gemini-2.5-flash") -> Optional[CustomerProblemSchema]:
    """
    Run the Kamigo customer intake session.
    Returns structured CustomerProblemSchema on success, None on exit.
    """
    history: list = [{"role": "system", "content": INTAKE_SYSTEM_PROMPT}]

    print_header()

    opening = "Hi! What problem do you need help with today? Just tell us what happened."
    print(f"Kamigo: {opening}\n")
    history.append({"role": "assistant", "content": opening})

    MAX_TURNS = 6
    turn      = 0

    while turn < MAX_TURNS:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n[Session ended]")
            return None

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "bye"):
            print("\nKamigo: Okay, come back anytime!")
            return None

        history.append({"role": "user", "content": user_input})
        turn += 1

        try:
            ai_reply = chat(model_name, history, temperature=0.2)
        except Exception as e:
            print(f"\n[ERROR] Could not reach AI: {e}")
            return None

        if COMPLETE_TOKEN in ai_reply:
            visible = ai_reply.replace(COMPLETE_TOKEN, "").strip()
            if visible:
                print(f"\nKamigo: {visible}\n")
            history.append({"role": "assistant", "content": ai_reply})
            break
        else:
            print(f"\nKamigo: {ai_reply}\n")
            history.append({"role": "assistant", "content": ai_reply})
    else:
        history.append({
            "role": "assistant",
            "content": "Got it! Finding the right worker for you now. [COMPLETE]"
        })
        print("\nKamigo: Got it! Finding the right worker for you now.\n")

    print("[Finding the best worker for you...]\n")

    try:
        result = extract_json(history, model_name)
        print_json_output(result.model_dump())
        return result
    except Exception as e:
        print(f"\n[ERROR] Could not extract problem data: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_customer_intake(model_name="gemini-2.5-flash")