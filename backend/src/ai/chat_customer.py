"""
Fast-Track AI Dispatch — customer interview + structured extraction.

Pipeline:
    1. run_interactive_interview() — short back-and-forth to gather category
       and problem details from the customer.
    2. extract_final_json()        — turns the conversation into a strict,
       registry-validated payload, ready to be matched against worker tags.

NOTE: urgency_level and is_safety_hazard are intentionally NOT extracted here.
Those are set manually elsewhere in the project for now.
"""

import json
import ollama
from typing import List
from src.core.schema import CustomerProblemSchema


# ── Master Service Registry ─────────────────────────────────────────────────
# Single source of truth: category -> {tag: description}.
# Worker profiles must use these exact category/tag strings for matching to work.
SERVICE_REGISTRY: dict[str, dict[str, str]] = {
    "plumbing": {
        "leak-detection": "Locating the source of a water leak in pipes, walls, or fixtures",
        "pipe-welding": "Welding or joining metal pipes",
        "sewer-inspection": "Camera inspection of sewer lines for blockages or damage",
        "clog-removal": "Clearing a clogged drain, toilet, or pipe",
        "water-heater-repair": "Repairing or servicing a water heater",
        "faucet-replacement": "Replacing a kitchen or bathroom faucet",
        "toilet-repair": "Fixing a running, leaking, or clogged toilet",
    },
    "electrical": {
        "wiring-repair": "Fixing damaged, exposed, or faulty wiring",
        "circuit-breaker-repair": "Diagnosing or repairing a tripped or faulty breaker",
        "outlet-installation": "Installing or replacing electrical outlets",
        "electrical-inspection": "General inspection of an electrical system",
        "lighting-installation": "Installing light fixtures, switches, or fans",
        "generator-repair": "Repairing or servicing a backup generator",
    },
    "structural": {
        "roof-repair": "Fixing roof leaks, missing shingles, or storm damage",
        "door-repair": "Fixing a stuck, broken, or off-hinge door",
        "window-repair": "Fixing a cracked, stuck, or broken window",
        "wall-patching": "Patching holes or cracks in drywall or plaster",
        "flooring-repair": "Fixing damaged, loose, or warped flooring",
        "lock-repair": "Fixing or replacing a broken door or window lock",
        "ceiling-repair": "Fixing a leaking, cracked, or sagging ceiling",
    },
}

PROBLEM_CATEGORIES: List[str] = list(SERVICE_REGISTRY.keys())
ALL_TAGS: List[str] = [tag for tags in SERVICE_REGISTRY.values() for tag in tags]
# ─────────────────────────────────────────────────────────────────────────────


def _format_registry() -> str:
    """Render the registry as readable text for the LLM prompt."""
    lines = []
    for category, tags in SERVICE_REGISTRY.items():
        lines.append(f"\n[{category}]")
        lines.extend(f"  - {tag}: {desc}" for tag, desc in tags.items())
    return "\n".join(lines)


def _build_extraction_prompt() -> str:
    return (
        "You are a strict data-extraction engine. Output ONLY valid JSON. No preamble, no markdown.\n\n"
        "From the conversation above, extract THREE fields:\n"
        "  1. problem_category   — exactly one entry from the CATEGORY LIST\n"
        "  2. service_tags       — 1-3 tags chosen ONLY from the TAG REGISTRY below\n"
        "  3. problem_description — a short, clear, one-sentence summary of what the "
        "customer said is wrong, in plain customer-facing language\n\n"
        f"CATEGORY LIST:\n{json.dumps(PROBLEM_CATEGORIES)}\n\n"
        f"TAG REGISTRY (grouped by category, with descriptions):{_format_registry()}\n\n"
        "Rules:\n"
        "- problem_category must exactly match one entry from the CATEGORY LIST.\n"
        "- service_tags must be a strict subset of the TAG REGISTRY, ideally from the chosen category.\n"
        "- Include every tag that clearly applies, capped at the 3 most relevant.\n"
        "- problem_description should be based only on what the customer actually said — "
        "do not invent details, and do not include urgency or safety commentary."
    )


def extract_final_json(chat_history: list[dict], model_name: str) -> CustomerProblemSchema:
    """Convert a finished interview into a validated, registry-checked payload."""
    cleaned_history = [msg for msg in chat_history if msg["role"] != "system"]
    payload = [{"role": "system", "content": _build_extraction_prompt()}] + cleaned_history

    response = ollama.chat(
        model=model_name,
        messages=payload,
        format=CustomerProblemSchema.model_json_schema(),
        options={"temperature": 0.0},
    )

    raw_content = response["message"]["content"].strip()

    # Strip markdown fences small models sometimes emit despite instructions
    if raw_content.startswith("```json"):
        raw_content = raw_content.split("```json", 1)[1].rsplit("```", 1)[0].strip()
    elif raw_content.startswith("```"):
        raw_content = raw_content.split("```", 1)[1].rsplit("```", 1)[0].strip()

    result = CustomerProblemSchema.model_validate_json(raw_content)

    # Hard guardrails: normalize + silently drop anything that doesn't match the registry
    result.problem_category = result.problem_category.strip().lower()
    result.service_tags = [t for t in result.service_tags if t in ALL_TAGS]

    return result


def print_summary(data: CustomerProblemSchema) -> None:
    """Human-readable recap, shown separately from the raw JSON payload."""
    category_flag = "" if data.problem_category in PROBLEM_CATEGORIES else "  (⚠ unrecognized category)"
    print(f"\nCategory    : {data.problem_category.title()}{category_flag}")
    print(f"Tags        : {', '.join(data.service_tags) if data.service_tags else '— none matched —'}")
    print(f"Description : {data.problem_description}")


def run_interactive_interview() -> None:
    MODEL_NAME = "qwen2.5:14b"

    system_prompt = (
        "You are a friendly, efficient dispatch assistant for home repairs. "
        "You need exactly 2 things: (1) category of the problem, "
        "(2) what's actually happening, in enough detail to describe the problem clearly.\n\n"
        "STYLE:\n"
        "- Warm but brief — never more than 2 short sentences.\n"
        "- Briefly acknowledge what the user told you before asking anything else, "
        "so they feel heard.\n"
        "- Ask about ONE missing piece at a time. Never stack questions.\n"
        "- Never diagnose the problem or suggest a fix — you're a dispatcher, not a technician.\n"
        "- Do NOT ask about urgency or safety — that's handled separately.\n\n"
        "COMPLETION:\n"
        "- The moment both things are clear, give a short reassuring confirmation and end with "
        "the exact tag [COMPLETE]. Example: 'Got it — sounds like a plumbing issue with the "
        "kitchen sink. Finding you a worker now. [COMPLETE]'"
    )

    conversation_history = [{"role": "system", "content": system_prompt}]

    print("=" * 50)
    print(" Fast-Track AI Dispatch Terminal")
    print(" Type 'exit' to quit.")
    print("=" * 50 + "\n")

    initial_greeting = "Hi! What's going on — what's broken and what's happening?"
    print(f"AI: {initial_greeting}")
    conversation_history.append({"role": "assistant", "content": initial_greeting})

    max_turns = 6
    turn_count = 0

    while turn_count < max_turns:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "exit":
            print("Exiting...")
            return

        conversation_history.append({"role": "user", "content": user_input})
        turn_count += 1

        print("AI is evaluating...")
        response = ollama.chat(
            model=MODEL_NAME,
            messages=conversation_history,
            options={"temperature": 0.0},
        )

        ai_message = response["message"]["content"].strip()
        conversation_history.append({"role": "assistant", "content": ai_message})

        if "[COMPLETE]" in ai_message or turn_count >= max_turns:
            clean_message = ai_message.replace("[COMPLETE]", "").strip() or "Got it, processing now."
            print(f"\nAI: {clean_message}")
            break
        else:
            print(f"\nAI: {ai_message}")

    print("\n" + "=" * 50)
    print(" EXTRACTING STRUCTURED PAYLOAD")
    print("=" * 50)

    try:
        structured_data = extract_final_json(conversation_history, MODEL_NAME)
        print_summary(structured_data)
        print("\nRaw payload:")
        print(json.dumps(structured_data.model_dump(), indent=2))
    except Exception as e:
        print(f"\n[ERROR] Extraction failed: {e}")


if __name__ == "__main__":
    run_interactive_interview()