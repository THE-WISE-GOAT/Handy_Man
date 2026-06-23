"""
Fast-Track AI Dispatch — customer interview + structured extraction.

Public surface
--------------
  SYSTEM_PROMPT          — injected as the first message of every chat session
  MODEL_NAME             — Ollama model string used for both interview + extraction
  MAX_TURNS              — hard cap on customer messages before auto-completing
  INITIAL_GREETING       — the first thing the assistant says; seeded into history
  SERVICE_REGISTRY       — single source of truth for category → tag → description
  extract_final_json()   — converts a finished conversation into a validated payload

Design notes (read before touching the extraction logic)
----------------------------------------------------------
The static SERVICE_REGISTRY is the preferred, secure path: every category/tag
in it is guaranteed to match real worker profiles, so dispatch on a registry
match is "fully verified." That path is unchanged and still wins whenever a
job fits it.

On top of that, this module now supports jobs that genuinely fall outside the
registry (e.g. a service the platform hasn't formally catalogued yet). When
that happens, the extraction model is allowed to invent a category/tags
itself — but the result is always returned with `is_custom_category=True`,
so the caller/endpoint can tell the difference and route it differently
(e.g. a manual-matching queue) instead of silently treating an AI guess as if
it were registry-verified.

Separately, both the live chat and the extraction step now actively guard
against off-topic conversations (small talk, unrelated questions, requests
to do something other than describe a job). If a conversation never produces
a real job, `extract_final_json` returns `is_job_request=False` with empty
category/tags/description rather than fabricating something to fill the
schema.
"""

import json
import ollama
from typing import List

from src.core.schema import CustomerProblemSchema


MODEL_NAME     = "qwen2.5:14b"
MAX_TURNS      = 6          # customer messages; endpoint enforces this
INITIAL_GREETING = "Hi! What's going on — what's broken and what's happening?"

SYSTEM_PROMPT = (
    "You are a friendly, efficient dispatch assistant for a multi-service platform. "
    "Customers can book help for a wide range of services — home repairs, cleaning, "
    "automotive, beauty, tutoring, healthcare, events, and more.\n\n"

    "SCOPE — READ CAREFULLY:\n"
    "- You exist for exactly one purpose: figuring out what JOB or SERVICE PROBLEM a "
    "customer needs a worker dispatched for.\n"
    "- If the customer says anything that is NOT about a job/service they need help with "
    "— small talk, jokes, general knowledge questions, requests to write or explain "
    "something unrelated, questions about you or the platform's inner workings, or any "
    "other off-topic content — do NOT engage with that content at all, even partially. "
    "Briefly note you're only able to help book a service, and ask them to describe what "
    "they need help with.\n"
    "- This applies for the entire conversation, not just  the first message. If a "
    "customer starts on-topic and drifts off-topic, redirect them back without answering "
    "the off-topic part.\n\n"

    "You need exactly TWO things before you can close this conversation:\n"
    "  1. The SERVICE CATEGORY — what general kind of job this is (plumbing, cleaning, "
    "tutoring, etc.). It does not need to match a fixed list. If a customer describes a "
    "real job that doesn't fit anything you'd normally expect, that's fine — capture it "
    "clearly in their own words. The only requirement is that it's a genuine, schedulable "
    "job a worker or professional could actually be sent to do.\n"
    "  2. What is ACTUALLY NEEDED — enough detail to describe the request clearly "
    "(e.g. what item, what the problem or task is, any useful context).\n\n"

    "STYLE RULES:\n"
    "- Keep every reply to 1–2 short sentences. Never write long paragraphs.\n"
    "- Always acknowledge what the customer just told you before asking anything. "
    "They should feel heard, not interrogated.\n"
    "- Ask about ONE missing piece at a time. Never stack two questions in one reply.\n"
    "- Never diagnose the problem or suggest a fix — you are a dispatcher, not a technician.\n"
    "- Do NOT ask about urgency, danger, or safety — those are handled separately.\n"
    "- Do NOT repeat information the customer already gave you.\n\n"

    "WHEN A JOB DOESN'T FIT A TYPICAL CATEGORY:\n"
    "- Do not refuse a real job just because it sounds unusual or unlike the typical "
    "examples. Gather the same two things (category in their own words + description) and "
    "proceed normally — an unfamiliar job is still a job.\n"
    "- Only refuse if the request isn't a dispatchable job at all — e.g. it's not "
    "something a worker could physically show up and do (legal/medical advice unrelated "
    "to in-home care, writing or coding something, general chit-chat, shopping requests, "
    "etc.). In that case, explain you can only help book hands-on service work and ask "
    "them to describe a job, instead of moving toward completion.\n\n"

    "COMPLETION RULES:\n"
    "- The moment you have both pieces (category + clear description) AND the request is "
    "a genuine dispatchable job, write a short reassuring confirmation and end your reply "
    "with the exact string [COMPLETE].\n"
    "  Good examples:\n"
    "    'Got it — sounds like a plumbing issue with the kitchen sink. "
    "Finding you a worker now. [COMPLETE]'\n"
    "    'Perfect — I have a home cleaning request for your apartment on Saturday. "
    "Matching you now. [COMPLETE]'\n"
    "    'Noted — a car AC repair for your sedan. Getting someone to you. [COMPLETE]'\n"
    "- If the customer has already sent 5 messages and you still lack one piece, "
    "make your best inference from context, confirm it naturally, and end with [COMPLETE]. "
    "Do not keep asking indefinitely.\n"
    "- NEVER emit [COMPLETE] before you have at least a category and a basic description.\n"
    "- NEVER emit [COMPLETE] for a conversation that never became a real job request — "
    "if the customer only ever talked about unrelated things, keep redirecting instead."
)


#  Master Service Registry ──────────────────────────────────────────────────
# Single source of truth: category → {tag: description}.
# Worker profiles must use these exact strings for matching to work.
# This list is treated as the PREFERRED set, not an exhaustive one — see the
# module docstring for how jobs outside this registry are handled.

SERVICE_REGISTRY: dict[str, dict[str, str]] = {

    # Home infrastructure
    "plumbing": {
        "leak-detection":       "Locating the source of a water leak in pipes, walls, or fixtures",
        "pipe-repair":          "Repairing or replacing damaged water or drainage pipes", 
        "pipe-welding":         "Welding or joining metal pipes",
        "sewer-inspection":     "Camera inspection of sewer lines for blockages or damage",
        "clog-removal":         "Clearing a clogged drain, toilet, or pipe",
        "water-heater-repair":  "Repairing or servicing a water heater or geyser",
        "water-tank-cleaning":  "Draining, scrubbing, and disinfecting a water storage tank",
        "faucet-replacement":   "Replacing a kitchen or bathroom faucet or tap",
        "toilet-repair":        "Fixing a running, leaking, or clogged toilet",
        "water-pump-repair":    "Repairing or replacing a domestic water pump",
    },

    "electrical": {
        "wiring-repair":            "Fixing damaged, exposed, or faulty wiring",
        "circuit-breaker-repair":   "Diagnosing or repairing a tripped or faulty breaker / MCB",
        "outlet-installation":      "Installing or replacing electrical outlets or sockets",
        "electrical-inspection":    "General safety inspection of an electrical system",
        "lighting-installation":    "Installing light fixtures, switches, or ceiling fans",
        "generator-repair":         "Repairing or servicing a backup generator or inverter",
        "solar-panel-installation": "Installing or maintaining solar panels and inverter systems",
        "earthing-installation":    "Installing or repairing electrical grounding / earthing",
        "meter-box-work":           "Work on electricity meters, distribution boards, or consumer units",
    },

    "construction": {
        "roof-repair":         "Fixing roof leaks, missing tiles/shingles, or storm damage",
        "door-repair":         "Fixing a stuck, broken, or off-hinge door",
        "window-repair":       "Fixing a cracked, stuck, or broken window",
        "wall-patching":       "Patching holes or cracks in drywall, plaster, or brick",
        "flooring-repair":     "Fixing damaged, loose, warped, or cracked flooring",
        "ceiling-repair":      "Fixing a leaking, cracked, or sagging ceiling",
        "tiling":              "Laying or repairing floor or wall tiles",
        "waterproofing":       "Applying waterproof coating to roofs, bathrooms, or terraces",
        "demolition":          "Controlled demolition of walls, structures, or fittings",
        "masonry":             "Brickwork, stonework, concrete repair, or block construction",
        "staircase-repair":    "Fixing or replacing stairs, railings, or banisters",
        "lock-repair":         "Fixing or replacing a broken door or window lock",
    },

    # Climate & appliances
    "hvac": {
        "ac-installation":      "Installing a new air conditioning unit",
        "ac-repair":            "Diagnosing and repairing a malfunctioning AC unit",
        "ac-cleaning":          "Deep cleaning of AC filters, coils, and drainage",
        "ac-gas-refill":        "Recharging refrigerant / gas in an AC system",
        "heater-repair":        "Repairing a room heater, storage heater, or heat pump",
        "ventilation-repair":   "Fixing exhaust fans, ventilation ducts, or air handlers",
        "duct-cleaning":        "Cleaning HVAC ductwork and vents",
    },

    "appliance-repair": {
        "washing-machine-repair": "Repairing a front-load or top-load washing machine",
        "refrigerator-repair":    "Repairing a fridge, freezer, or refrigerator-freezer combo",
        "oven-repair":            "Repairing a gas or electric oven, stove, or range",
        "microwave-repair":       "Repairing a microwave oven",
        "dishwasher-repair":      "Repairing a built-in or freestanding dishwasher",
        "tv-repair":              "Repairing a television set",
        "water-purifier-repair":  "Repairing or servicing an RO or UV water purifier",
        "mixer-grinder-repair":   "Repairing kitchen mixers, grinders, or blenders",
        "iron-repair":            "Repairing a clothes iron or steam iron",
    },

    # Cleaning & hygiene
    "cleaning": {
        "home-cleaning":        "Regular or one-time cleaning of a house or apartment",
        "deep-cleaning":        "Thorough top-to-bottom cleaning including hard-to-reach areas",
        "office-cleaning":      "Cleaning commercial office or workspace premises",
        "carpet-cleaning":      "Steam or dry cleaning of carpets and rugs",
        "sofa-cleaning":        "Deep cleaning of upholstered sofas and chairs",
        "kitchen-cleaning":     "Deep cleaning of kitchen surfaces, appliances, and cabinets",
        "bathroom-sanitisation": "Disinfection and scrubbing of bathrooms and toilets",
        "window-cleaning":      "Cleaning interior and exterior glass windows",
        "tank-cleaning":        "Cleaning overhead or underground water storage tanks",
        "post-construction-cleaning": "Cleaning a space after renovation or construction work",
    },

    "pest-control": {
        "cockroach-treatment":  "Targeted treatment to eliminate cockroach infestations",
        "termite-treatment":    "Chemical or non-chemical treatment for termites / white ants",
        "rodent-control":       "Trapping or exterminating rats and mice",
        "mosquito-treatment":   "Fogging or spraying to control mosquito populations",
        "bed-bug-treatment":    "Heat or chemical treatment to eliminate bed bugs",
        "ant-control":          "Removing ant colonies from structures or gardens",
        "general-fumigation":   "Full-property fumigation for multiple pest types",
    },

    # Outdoor & vehicle
    "landscaping": {
        "lawn-mowing":          "Cutting and trimming grass on lawns",
        "garden-maintenance":   "General upkeep of plants, beds, and borders",
        "tree-trimming":        "Pruning or trimming trees and large shrubs",
        "tree-removal":         "Felling and removal of a dead or hazardous tree",
        "landscape-design":     "Planning and designing an outdoor garden layout",
        "irrigation-setup":     "Installing or repairing drip or sprinkler irrigation systems",
        "pathway-paving":       "Laying or repairing garden paths, driveways, or patios",
        "fence-installation":   "Installing or repairing garden fencing or walls",
        "plant-care":           "Watering, fertilising, and nurturing indoor or outdoor plants",
    },

    "painting": {
        "interior-painting":    "Painting walls, ceilings, or interior woodwork inside a building",
        "exterior-painting":    "Painting outside walls, facades, or exterior woodwork",
        "waterproof-painting":  "Applying weather-resistant or waterproof paint coatings",
        "texture-painting":     "Applying textured or decorative paint finishes",
        "furniture-painting":   "Repainting or refinishing wooden or metal furniture",
        "metal-painting":       "Painting gates, grilles, railings, or metal structures",
        "wall-priming":         "Applying primer coats before finishing paint",
        "epoxy-flooring":       "Applying epoxy or resin coatings to concrete floors",
    },

    "moving": {
        "home-relocation":      "Packing and moving all household belongings to a new address",
        "office-relocation":    "Moving office furniture and equipment to a new premises",
        "furniture-moving":     "Moving heavy or bulky furniture within or between properties",
        "packing-service":      "Professional packing of items for transport or storage",
        "loading-unloading":    "Loading or unloading a truck or van at a property",
        "vehicle-transport":    "Transporting a car or bike on a flatbed or trailer",
        "storage-service":      "Short or long-term storage of household or business items",
        "courier-delivery":     "Pickup and delivery of small parcels or documents",
    },

    "automotive": {
        "car-wash":             "Exterior and interior cleaning of a car or SUV",
        "oil-change":           "Draining and replacing engine oil and oil filter",
        "tyre-change":          "Removing and fitting new or spare tyres",
        "tyre-puncture-repair": "Patching or plugging a punctured tyre",
        "battery-replacement":  "Replacing a flat or dead car battery",
        "car-denting-painting": "Repairing dents and repainting body panels",
        "car-ac-repair":        "Diagnosing or repairing a vehicle air conditioning system",
        "car-electrical-repair":"Fixing electrical faults in a vehicle",
        "car-inspection":       "General vehicle health and safety inspection",
        "roadside-assistance":  "Emergency help for a broken-down or stranded vehicle",
        "bike-service":         "Routine service or repair of a motorcycle or scooter",
    },

    # Tech & security
    "it-support": {
        "computer-repair":      "Diagnosing and repairing desktop or laptop hardware faults",
        "virus-removal":        "Removing malware, viruses, or spyware from a device",
        "data-recovery":        "Recovering lost or deleted files from storage devices",
        "software-installation":"Installing or configuring operating systems or software",
        "network-setup":        "Setting up or troubleshooting a home or office network",
        "wifi-troubleshooting": "Diagnosing and fixing Wi-Fi connectivity issues",
        "printer-setup":        "Connecting, configuring, or repairing a printer",
        "cctv-installation":    "Installing CCTV cameras and recording systems",
        "phone-repair":         "Repairing cracked screens, batteries, or hardware on smartphones",
        "smart-home-setup":     "Installing smart bulbs, plugs, doorbells, or home automation",
    },

    "security": {
        "cctv-installation":    "Installing indoor or outdoor CCTV surveillance cameras",
        "alarm-installation":   "Installing burglar alarms or motion-sensor alert systems",
        "intercom-installation":"Installing video or audio intercom / doorbell systems",
        "safe-installation":    "Installing a wall or floor safe",
        "access-control":       "Installing key-card, fingerprint, or pin-access door locks",
        "electric-fence":       "Installing or repairing electric security fencing",
        "security-audit":       "Assessing physical security vulnerabilities of a property",
    },

    # Personal & wellness
    "beauty-wellness": {
        "haircut-home":         "Home visit for a haircut, trim, or hair styling",
        "hair-colour":          "Hair colouring, highlights, or bleaching service",
        "facial-treatment":     "Skin care facial treatment at home",
        "massage-therapy":      "Relaxation or therapeutic massage at home",
        "manicure-pedicure":    "Nail care and grooming for hands and feet",
        "waxing":               "Hair removal waxing service at home",
        "bridal-makeup":        "Professional makeup for a wedding or special event",
        "mehendi":              "Henna / mehendi application for hands or feet",
        "spa-at-home":          "Full spa package at the customer's location",
    },

    "fitness": {
        "personal-training":    "One-on-one fitness coaching and workout sessions at home",
        "yoga-instruction":     "Guided yoga sessions at home or a preferred location",
        "zumba-dance":          "Aerobic dance fitness sessions",
        "physiotherapy":        "Therapeutic exercises and physical rehabilitation at home",
        "diet-consultation":    "Personalised nutrition and diet planning session",
        "gym-equipment-setup":  "Assembling or installing home gym equipment",
    },

    # Professional services
    "tutoring": {
        "school-tutoring":      "Academic tutoring for school-level subjects",
        "exam-preparation":     "Coaching for entrance exams, board exams, or competitive tests",
        "language-lessons":     "Teaching a new language (English, Mandarin, etc.)",
        "music-lessons":        "Instrument or vocal coaching at home",
        "art-craft-lessons":    "Art, drawing, or craft workshops",
        "coding-lessons":       "Programming and coding education for beginners or students",
        "adult-literacy":       "Basic reading, writing, or numeracy support for adults",
    },

    "home-healthcare": {
        "home-nursing":         "Skilled nursing care provided at the patient's home",
        "elder-care":           "Assistance and supervision for elderly individuals at home",
        "physiotherapy-home":   "At-home physiotherapy and rehabilitation sessions",
        "wound-care":           "Professional cleaning and dressing of wounds at home",
        "injection-service":    "Administering prescribed injections at home",
        "blood-test-home":      "Blood sample collection at home for lab testing",
        "medical-equipment-rental": "Renting medical equipment such as wheelchairs or nebulisers",
        "caregiver-support":    "Daily assistance for patients recovering from illness or surgery",
    },

    "events-catering": {
        "event-planning":       "Planning and coordinating a wedding, party, or corporate event",
        "catering-service":     "Providing food and beverages for events or gatherings",
        "tent-decoration":      "Setting up tents, lighting, and decorations for outdoor events",
        "sound-system-setup":   "Installing and operating a PA or DJ sound system",
        "photography-video":    "Event photography or videography coverage",
        "birthday-decoration":  "Decorating a venue for a birthday celebration",
        "wedding-planning":     "Full wedding coordination from venue to day-of logistics",
        "waitstaff-service":    "Providing trained serving staff for events",
    },

    "laundry": {
        "laundry-pickup":       "Pickup, washing, and delivery of clothes",
        "dry-cleaning":         "Professional dry cleaning of delicate or formal garments",
        "ironing-service":      "Steam or dry ironing of washed clothes",
        "shoe-cleaning":        "Cleaning and polishing shoes or sneakers",
        "carpet-laundry":       "Washing and drying large carpets or rugs",
        "curtain-cleaning":     "Taking down, washing, and re-hanging curtains",
        "tailoring-alteration": "Adjusting, hemming, or altering clothing",
        "stitch-repair":        "Repairing torn seams, buttons, or zippers on garments",
    },
}

PROBLEM_CATEGORIES: List[str] = list(SERVICE_REGISTRY.keys())
ALL_TAGS: List[str] = [
    tag for tags in SERVICE_REGISTRY.values() for tag in tags
]


def build_fresh_history() -> list[dict]:
    """Seed the conversation with the system prompt and the opening greeting."""
    return [
        {"role": "system",    "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": INITIAL_GREETING},
    ]


def count_user_turns(history: list[dict]) -> int:
    """How many messages has the customer sent in this session so far?"""
    return sum(1 for msg in history if msg["role"] == "user")


# Extraction pipeline 

def _format_registry() -> str:
    lines: list[str] = []
    for category, tags in SERVICE_REGISTRY.items():
        lines.append(f"\n[{category}]")
        lines.extend(f"  - {tag}: {desc}" for tag, desc in tags.items())
    return "\n".join(lines)


def _build_extraction_prompt() -> str:
    return (
        "You are a strict data-extraction engine. "
        "Output ONLY valid JSON — no preamble, no markdown fences, no extra keys.\n\n"
        "From the conversation above, extract exactly FIVE fields:\n"
        "  1. is_job_request      — true only if the customer ultimately described a "
        "genuine, dispatchable service job: something a worker or professional could "
        "actually be sent to physically do. False if the conversation is small talk, a "
        "general question, a request unrelated to booking a service, or otherwise never "
        "turned into a real job.\n"
        "  2. problem_category    — the best category for the job.\n"
        "       * STRONGLY PREFER an exact, lowercase match from CATEGORY LIST below — "
        "this is the verified, preferred path.\n"
        "       * Only if the job genuinely does not fit ANY entry in CATEGORY LIST, "
        "invent a short, lowercase, hyphenated category name in the same style as the "
        "existing ones (e.g. 'pet-grooming', 'appliance-installation'). Never force-fit a "
        "job into a category that clearly doesn't match it.\n"
        "       * If is_job_request is false, set this to an empty string.\n"
        "  3. is_custom_category  — true if problem_category is NOT an exact CATEGORY "
        "LIST match (i.e. you invented it); false if it is an exact match; false if "
        "is_job_request is false.\n"
        "  4. service_tags        — 1–3 short, lowercase, hyphenated tags describing the "
        "specific task.\n"
        "       * If problem_category is an exact CATEGORY LIST match, prefer tags from "
        "TAG REGISTRY for that category; invent a new tag only if none fit.\n"
        "       * If problem_category is custom, invent 1–4 sensible tags in the same "
        "style.\n"
        "       * Empty list if is_job_request is false.\n"
        "  5. problem_description — one clear sentence summarising what the customer "
        "reported, in plain customer-facing language. Empty string if is_job_request is "
        "false. Do not invent details the customer didn't say; do not mention urgency or "
        "safety.\n\n"
        f"CATEGORY LIST (preferred, not exhaustive):\n{json.dumps(PROBLEM_CATEGORIES)}\n\n"
        f"TAG REGISTRY (grouped by category):{_format_registry()}"
    )


def _sanitize_custom_tags(tags: list[str]) -> list[str]:
    """
    Light cleanup for AI-invented tags (used only when the job falls outside
    the static registry): lowercase, strip, dedupe, cap at 3, drop empties.
    """
    cleaned: list[str] = []
    for raw_tag in tags:
        tag = raw_tag.strip().lower()
        if not tag or tag in cleaned:
            continue
        cleaned.append(tag)
        if len(cleaned) == 3:
            break
    return cleaned


def _blank_non_job_result(result: CustomerProblemSchema) -> CustomerProblemSchema:
    """Normalise any 'no real job here' outcome to one consistent shape."""
    result.is_job_request = False
    result.problem_category = ""
    result.is_custom_category = False
    result.service_tags = []
    result.problem_description = ""
    return result


def extract_final_json(
    chat_history: list[dict],
    model_name: str = MODEL_NAME,
) -> CustomerProblemSchema:
    """
    Convert a completed interview history into a validated payload.

    Two outcomes are possible:
      - Registry match: problem_category is an exact SERVICE_REGISTRY key and
        service_tags are a verified subset of that category's tags.
        is_custom_category=False. This is the secure, preferred path.
      - Custom job: the conversation described a real job that doesn't fit
        the static registry. The model's own category/tags are kept (lightly
        sanitised) and is_custom_category=True, so the caller can route it
        differently (e.g. a manual-matching queue) instead of trusting it as
        registry-verified.
      - No job at all: if the conversation never produced a genuine job
        request (e.g. it stayed off-topic), is_job_request=False and every
        other field is blanked out — there is nothing to dispatch.

    Strips the system prompt from history before sending so the extraction
    engine sees only the real dialogue.
    """
    cleaned = [msg for msg in chat_history if msg["role"] != "system"]
    messages = [{"role": "system", "content": _build_extraction_prompt()}] + cleaned

    response = ollama.chat(
        model=model_name,
        messages=messages,
        format=CustomerProblemSchema.model_json_schema(),
        options={"temperature": 0.0},
    )

    raw = response["message"]["content"].strip()

    # Small models sometimes emit markdown fences despite instructions
    if raw.startswith("```json"):
        raw = raw.split("```json", 1)[1].rsplit("```", 1)[0].strip()
    elif raw.startswith("```"):
        raw = raw.split("```", 1)[1].rsplit("```", 1)[0].strip()

    try:
        result = CustomerProblemSchema.model_validate_json(raw)
    except ValueError as exc:
        raise ValueError(
            f"Extraction model returned invalid JSON it could not be parsed from: {raw!r}"
        ) from exc

    # Nothing dispatchable ever surfaced — don't fabricate a category/tags
    # just to fill the schema.
    if not getattr(result, "is_job_request", True):
        return _blank_non_job_result(result)

    category = result.problem_category.strip().lower()
    result.problem_category = category

    if not category or not result.problem_description.strip():
        # Incomplete extraction despite is_job_request=True — treat as no job
        # rather than dispatching a half-empty request.
        return _blank_non_job_result(result)

    if category in PROBLEM_CATEGORIES:
        # Registry match — the secure, fully-verified path. Tags are hard-
        # filtered against THIS category's own tags (not just any tag from
        # any category, which the previous version allowed by mistake).
        result.is_custom_category = False
        result.service_tags = [
            t.strip().lower()
            for t in result.service_tags
            if t.strip().lower() in SERVICE_REGISTRY[category]
        ][:3]
    else:
        # Genuine job, outside the static registry. Keep the model's own
        # category/tags, lightly sanitised, and flag it clearly.
        result.is_custom_category = True
        result.service_tags = _sanitize_custom_tags(result.service_tags)

    return result