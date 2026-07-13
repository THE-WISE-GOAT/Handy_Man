"""
Fast-Track AI Dispatch — customer interview + structured extraction.

Public surface
--------------
  SYSTEM_PROMPT          — injected as the first message of every chat session
  MODEL_NAME              — NIM chat model string used for interview + extraction
  EMBEDDING_MODEL_NAME    — NIM embedding model used to shortlist categories
  MAX_TURNS               — hard cap on customer messages before auto-completing
  INITIAL_GREETING        — the first thing the assistant says; seeded into history
  SERVICE_REGISTRY         — preferred category -> tag -> description set
  CATEGORY_DESCRIPTIONS    — one-line disambiguation per category, used both in
                              the extraction prompt and as the embedding corpus
  extract_final_json()    — converts a finished conversation into a validated payload
"""

import json
import logging
import math
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from openai import OpenAI

from src.core.schema import CustomerProblemSchema, CategoryMatch

logger = logging.getLogger(__name__)

# Force Python to search one directory layer up
base_dir = Path(__file__).resolve().parent.parent.parent  # Steps out of ai -> src -> backend
env_path = base_dir.parent / ".env"                       # Targets the root folder .env

load_dotenv(dotenv_path=env_path)

# ── NVIDIA NIM client ────────────────────────────────────────────────────────
# OpenAI-compatible endpoint — only base_url + api_key differ from stock OpenAI.
# Key format: nvapi-xxxx  (generate at build.nvidia.com -> "Get API Key")
# To use a different model from the NIM catalog, change MODEL_NAME only.
_nvidia_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],  # set in .env / environment
)

MODEL_NAME = "meta/llama-3.1-8b-instruct"
MAX_TURNS         = 20  # customer messages; endpoint enforces this
INITIAL_GREETING  = "Hi! What's going on — what's broken and what's happening?"

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
    "- This applies for the entire conversation, not just the first message. If a "
    "customer starts on-topic and drifts off-topic, redirect them back without answering "
    "the off-topic part.\n\n"

    "WHAT YOU NEED, AND WHOSE JOB IT IS:\n"
    "You need exactly TWO things before you can close this conversation:\n"
    "  1. WHAT IS ACTUALLY NEEDED — a concrete, physical description of the task: what "
    "item or area is involved, what's wrong with it or what needs to be done to it, and "
    "any detail that distinguishes this from a similar-sounding job (e.g. 'install a "
    "timer on the water tank' vs 'clean the water tank' are different jobs even though "
    "both involve a tank).\n"
    "  2. Enough specificity that someone could act on it without guessing.\n\n"
    "You do NOT need the customer to name a trade, category, or department — that "
    "classification is handled separately and automatically after this conversation "
    "ends, from whatever physical task they describe. NEVER ask the customer 'what type "
    "of job is this' or 'which category does this fall under' or similar. If a customer "
    "says something like 'I don't know, you decide' or 'figure it out yourself' about "
    "the category, that is expected and fine — simply continue asking about the TASK "
    "itself (what needs doing, to what, where) until you have enough detail, without ever "
    "asking them to classify it.\n\n"

    "STYLE RULES:\n"
    "- Keep every reply to 1–2 short sentences. Never write long paragraphs.\n"
    "- Always acknowledge what the customer just told you before asking anything. " # something here
    "They should feel heard, not interrogated.\n"
    "- Ask about ONE missing piece at a time. Never stack two questions in one reply.\n"
    "- Never diagnose the problem or suggest a fix — you are a dispatcher, not a technician.\n"
    "- Do NOT ask about urgency, danger, or safety — those are handled separately.\n"
    "- Do NOT repeat information the customer already gave you.\n"
    "- Prioritize getting a SPECIFIC physical description over closing quickly. Reaching "
    "[COMPLETE] with a vague description (e.g. 'something with the tank') is worse than "
    "asking one more question to pin down exactly what's needed.\n\n"

    "WHEN A JOB DOESN'T FIT A TYPICAL EXAMPLE:\n"
    "- Do not refuse a real job just because it sounds unusual. Gather a clear physical "
    "description and proceed normally — an unfamiliar job is still a job.\n"
    "- Only refuse if the request isn't a dispatchable job at all — e.g. it's not "
    "something a worker could physically show up and do (legal/medical advice unrelated "
    "to in-home care, writing or coding something, general chit-chat, shopping requests, " # something here
    "etc.). In that case, explain you can only help book hands-on service work and ask "
    "them to describe a job, instead of moving toward completion.\n\n"

    "COMPLETION RULES:\n"
    "- The moment you have a specific, concrete description of the task AND the request "
    "is a genuine dispatchable job, write a short reassuring confirmation and end your "
    "reply with the exact string [COMPLETE]. Do NOT mention a category or trade name in "
    "this confirmation — just acknowledge the task itself.\n"
    "  Good examples:\n"
    "    'Got it — a leak under the kitchen sink. Finding you a worker now. [COMPLETE]'\n"
    "    'Perfect — a one-time deep clean of your apartment this Saturday. Matching you "
    "now. [COMPLETE]'\n"
    "    'Noted — installing a timer on your water tank. Getting someone to you. "
    "[COMPLETE]'\n"
    "- If the customer has already sent 5 messages and the task still isn't fully "    # something here
    "specific, make your best inference from what they've said, confirm it naturally, "
    "and end with [COMPLETE]. Do not keep asking indefinitely.\n"
    "- NEVER emit [COMPLETE] before you have a concrete description of an actual task.\n"
    "- NEVER emit [COMPLETE] for a conversation that never became a real job request — "
    "if the customer only ever talked about unrelated things, keep redirecting instead."
)


#  Master Service Registry ──────────────────────────────────────────────────
# Preferred category -> {tag: description}. Worker profiles use these exact
# strings when they're used, but this set is a bias toward known-good
# matches, not an exhaustive whitelist — see module docstring.

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
        "home-cleaning":              "Regular or one-time cleaning of a house or apartment",
        "deep-cleaning":              "Thorough top-to-bottom cleaning including hard-to-reach areas",
        "office-cleaning":            "Cleaning commercial office or workspace premises",
        "carpet-cleaning":            "Steam or dry cleaning of carpets and rugs",
        "sofa-cleaning":              "Deep cleaning of upholstered sofas and chairs",
        "kitchen-cleaning":           "Deep cleaning of kitchen surfaces, appliances, and cabinets",
        "bathroom-sanitisation":      "Disinfection and scrubbing of bathrooms and toilets",
        "window-cleaning":            "Cleaning interior and exterior glass windows",
        "tank-cleaning":              "Cleaning overhead or underground water storage tanks",
        "post-construction-cleaning": "Cleaning a space after renovation or construction work",
    },

    "pest-control": {
        "cockroach-treatment": "Targeted treatment to eliminate cockroach infestations",
        "termite-treatment":   "Chemical or non-chemical treatment for termites / white ants",
        "rodent-control":      "Trapping or exterminating rats and mice",
        "mosquito-treatment":  "Fogging or spraying to control mosquito populations",
        "bed-bug-treatment":   "Heat or chemical treatment to eliminate bed bugs",
        "ant-control":         "Removing ant colonies from structures or gardens",
        "general-fumigation":  "Full-property fumigation for multiple pest types",
    },

    # Outdoor & vehicle
    "landscaping": {
        "lawn-mowing":        "Cutting and trimming grass on lawns",
        "garden-maintenance": "General upkeep of plants, beds, and borders",
        "tree-trimming":      "Pruning or trimming trees and large shrubs",
        "tree-removal":       "Felling and removal of a dead or hazardous tree",
        "landscape-design":   "Planning and designing an outdoor garden layout",
        "irrigation-setup":   "Installing or repairing drip or sprinkler irrigation systems",
        "pathway-paving":     "Laying or repairing garden paths, driveways, or patios",
        "fence-installation": "Installing or repairing garden fencing or walls",
        "plant-care":         "Watering, fertilising, and nurturing indoor or outdoor plants",
    },

    "painting": {
        "interior-painting":   "Painting walls, ceilings, or interior woodwork inside a building",
        "exterior-painting":   "Painting outside walls, facades, or exterior woodwork",
        "waterproof-painting": "Applying weather-resistant or waterproof paint coatings",
        "texture-painting":    "Applying textured or decorative paint finishes",
        "furniture-painting":  "Repainting or refinishing wooden or metal furniture",
        "metal-painting":      "Painting gates, grilles, railings, or metal structures",
        "wall-priming":        "Applying primer coats before finishing paint",
        "epoxy-flooring":      "Applying epoxy or resin coatings to concrete floors",
    },

    "moving": {
        "home-relocation":   "Packing and moving all household belongings to a new address",
        "office-relocation": "Moving office furniture and equipment to a new premises",
        "furniture-moving":  "Moving heavy or bulky furniture within or between properties",
        "packing-service":   "Professional packing of items for transport or storage",
        "loading-unloading": "Loading or unloading a truck or van at a property",
        "vehicle-transport": "Transporting a car or bike on a flatbed or trailer",
        "storage-service":   "Short or long-term storage of household or business items",
        "courier-delivery":  "Pickup and delivery of small parcels or documents",
    },

    "automotive": {
        "car-wash":              "Exterior and interior cleaning of a car or SUV",
        "oil-change":            "Draining and replacing engine oil and oil filter",
        "tyre-change":           "Removing and fitting new or spare tyres",
        "tyre-puncture-repair":  "Patching or plugging a punctured tyre",
        "battery-replacement":   "Replacing a flat or dead car battery",
        "car-denting-painting":  "Repairing dents and repainting body panels",
        "car-ac-repair":         "Diagnosing or repairing a vehicle air conditioning system",
        "car-electrical-repair": "Fixing electrical faults in a vehicle",
        "car-inspection":        "General vehicle health and safety inspection",
        "roadside-assistance":   "Emergency help for a broken-down or stranded vehicle",
        "bike-service":          "Routine service or repair of a motorcycle or scooter",
    },

    # Tech & security
    "it-support": {
        "computer-repair":       "Diagnosing and repairing desktop or laptop hardware faults",
        "virus-removal":         "Removing malware, viruses, or spyware from a device",
        "data-recovery":         "Recovering lost or deleted files from storage devices",
        "software-installation": "Installing or configuring operating systems or software",
        "network-setup":         "Setting up or troubleshooting a home or office network",
        "wifi-troubleshooting":  "Diagnosing and fixing Wi-Fi connectivity issues",
        "printer-setup":         "Connecting, configuring, or repairing a printer",
        "cctv-installation":     "Installing CCTV cameras and recording systems",
        "phone-repair":          "Repairing cracked screens, batteries, or hardware on smartphones",
        "smart-home-setup":      "Installing smart bulbs, plugs, doorbells, or home automation",
    },

    "security": {
        "cctv-installation":     "Installing indoor or outdoor CCTV surveillance cameras",
        "alarm-installation":    "Installing burglar alarms or motion-sensor alert systems",
        "intercom-installation": "Installing video or audio intercom / doorbell systems",
        "safe-installation":     "Installing a wall or floor safe",
        "access-control":        "Installing key-card, fingerprint, or pin-access door locks",
        "electric-fence":        "Installing or repairing electric security fencing",
        "security-audit":        "Assessing physical security vulnerabilities of a property",
    },

    # Personal & wellness
    "beauty-wellness": {
        "haircut-home":      "Home visit for a haircut, trim, or hair styling",
        "hair-colour":       "Hair colouring, highlights, or bleaching service",
        "facial-treatment":  "Skin care facial treatment at home",
        "massage-therapy":   "Relaxation or therapeutic massage at home",
        "manicure-pedicure": "Nail care and grooming for hands and feet",
        "waxing":            "Hair removal waxing service at home",
        "bridal-makeup":     "Professional makeup for a wedding or special event",
        "mehendi":           "Henna / mehendi application for hands or feet",
        "spa-at-home":       "Full spa package at the customer's location",
    },

    "fitness": {
        "personal-training":   "One-on-one fitness coaching and workout sessions at home",
        "yoga-instruction":    "Guided yoga sessions at home or a preferred location",
        "zumba-dance":         "Aerobic dance fitness sessions",
        "physiotherapy":       "Therapeutic exercises and physical rehabilitation at home",
        "diet-consultation":   "Personalised nutrition and diet planning session",
        "gym-equipment-setup": "Assembling or installing home gym equipment",
    },

    # Professional services
    "tutoring": {
        "school-tutoring":  "Academic tutoring for school-level subjects",
        "exam-preparation": "Coaching for entrance exams, board exams, or competitive tests",
        "language-lessons": "Teaching a new language (English, Mandarin, etc.)",
        "music-lessons":    "Instrument or vocal coaching at home",
        "art-craft-lessons": "Art, drawing, or craft workshops",
        "coding-lessons":   "Programming and coding education for beginners or students",
        "adult-literacy":   "Basic reading, writing, or numeracy support for adults",
    },

    "home-healthcare": {
        "home-nursing":             "Skilled nursing care provided at the patient's home",
        "elder-care":               "Assistance and supervision for elderly individuals at home",
        "physiotherapy-home":       "At-home physiotherapy and rehabilitation sessions",
        "wound-care":               "Professional cleaning and dressing of wounds at home",
        "injection-service":        "Administering prescribed injections at home",
        "blood-test-home":          "Blood sample collection at home for lab testing",
        "medical-equipment-rental": "Renting medical equipment such as wheelchairs or nebulisers",
        "caregiver-support":        "Daily assistance for patients recovering from illness or surgery",
    },

    "events-catering": {
        "event-planning":      "Planning and coordinating a wedding, party, or corporate event",
        "catering-service":    "Providing food and beverages for events or gatherings",
        "tent-decoration":     "Setting up tents, lighting, and decorations for outdoor events",
        "sound-system-setup":  "Installing and operating a PA or DJ sound system",
        "photography-video":  "Event photography or videography coverage",
        "birthday-decoration": "Decorating a venue for a birthday celebration",
        "wedding-planning":    "Full wedding coordination from venue to day-of logistics",
        "waitstaff-service":   "Providing trained serving staff for events",
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
ALL_TAGS: List[str] = [tag for tags in SERVICE_REGISTRY.values() for tag in tags]


# ── Category disambiguation ───────────────────────────────────────────────
# One sentence per category explaining what it actually covers — and, for
# categories that are easy to confuse via word-association (e.g. "gate"
# pattern-matching to "security"), explicitly what it does NOT cover and
# which category to use instead. This text is injected directly into the
# extraction prompt and is also what gets embedded for category shortlisting
# (see _category_corpus_text below), so it earns its keep twice.

CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "plumbing": "Water supply, drainage, pipes, tanks, taps, toilets, water heaters and pumps.",
    "electrical": "Wiring, breakers, outlets, lighting, generators, solar, earthing — any work on components that carry mains power, including motors and their wiring on otherwise non-electrical fixtures.",
    "construction": "Structural and fixed-hardware repair: roofs, doors, windows, walls, floors, ceilings, tiling, masonry, gates, and locks — the physical/mechanical hardware itself, not any motor or wiring that powers it (that's electrical).",
    "hvac": "Air conditioning, heating, ventilation, and ductwork.",
    "appliance-repair": "Repairing a specific standalone home appliance — washing machine, fridge, oven, microwave, dishwasher, TV, water purifier.",
    "cleaning": "Washing or sanitising a space, surface, or item — no repair work involved.",
    "pest-control": "Eliminating insects, rodents, or other pests.",
    "landscaping": "Outdoor plants, lawns, trees, irrigation, and garden paving or fencing.",
    "painting": "Applying paint or protective coatings to a surface.",
    "moving": "Packing, loading, or transporting belongings between locations.",
    "automotive": "Repair, maintenance, or servicing of cars, bikes, or other vehicles.",
    "it-support": "Computers, phones, networks, printers, software, and smart-home device setup.",
    "security": "Surveillance, alarm, and access-control SYSTEMS — cameras, intercoms, alarm panels, safes — installed to monitor or protect a property. Does NOT cover the physical gate, door, lock, or motor hardware itself; a stuck or broken gate/door/lock is construction (and electrical if it's motorized), not security, even though gates and locks relate to access.",
    "beauty-wellness": "Personal grooming and spa services performed on a person.",
    "fitness": "Personal training, yoga, or physiotherapy exercise sessions for a person.",
    "tutoring": "Teaching an academic subject, language, instrument, or skill.",
    "home-healthcare": "Medical, nursing, or caregiving support for a person at home.",
    "events-catering": "Planning, decorating, catering, or staffing an event.",
    "laundry": "Washing, drying, ironing, or altering clothing and textiles.",
}


def build_fresh_history() -> list[dict]:
    """Seed the conversation with the system prompt and the opening greeting."""
    return [
        {"role": "system",    "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": INITIAL_GREETING},
    ]


def count_user_turns(history: list[dict]) -> int:
    """How many messages has the customer sent in this session so far?"""
    return sum(1 for msg in history if msg["role"] == "user")


# ── Category retrieval (embeddings) ─────────────────────────────────────────
# Pre-filters which categories the extraction model has to reason over, using
# semantic similarity instead of asking a single LLM call to pick correctly
# out of all ~19 categories / ~160 tags every time. This is a RECALL aid, not
# a decision-maker — extract_final_json still lets the model invent a
# category outside the shortlist when nothing here genuinely fits (see
# _build_extraction_prompt). If the embedding call fails for any reason, the
# caller falls back to the full registry — this layer is a quality
# improvement, never a hard dependency for dispatch to keep functioning.

EMBEDDING_MODEL_NAME = "nvidia/nv-embedqa-e5-v5"

_category_corpus_cache: dict[str, list[float]] | None = None


def _category_corpus_text(category: str) -> str:
    """Aggregate text representing one category's full meaning, for embedding."""
    tags = SERVICE_REGISTRY[category]
    description = CATEGORY_DESCRIPTIONS.get(category, "")
    tag_lines = "; ".join(f"{tag} ({desc})" for tag, desc in tags.items())
    return f"{category}. {description} Includes: {tag_lines}"


def _embed(texts: list[str], input_type: str) -> list[list[float]]:
    """
    Call the NVIDIA embedding NIM. input_type must be 'passage' for corpus /
    reference text (the registry) or 'query' for the text being searched
    with (the customer's description) — this model family requires that
    distinction for good retrieval accuracy.
    """
    response = _nvidia_client.embeddings.create(
        model=EMBEDDING_MODEL_NAME,
        input=texts,
        extra_body={"input_type": input_type},
    )
    return [item.embedding for item in response.data]


def _get_category_index() -> dict[str, list[float]]:
    """
    Lazily embed every registry category once per process and cache it.
    SERVICE_REGISTRY doesn't change at runtime, so there's no reason to
    re-embed it on every extraction call.
    """
    global _category_corpus_cache
    if _category_corpus_cache is None:
        categories = list(SERVICE_REGISTRY.keys())
        vectors = _embed(
            [_category_corpus_text(c) for c in categories], input_type="passage"
        )
        _category_corpus_cache = dict(zip(categories, vectors))
    return _category_corpus_cache


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


#start here
def _shortlist_categories(problem_text: str, top_k: int = 7) -> list[str] | None:
    """
    Rank registry categories by semantic similarity to what the customer
    described, return the top_k names. Returns None on any failure
    (embedding endpoint down, empty input, etc.) so the caller can fall back
    to handing the model the full registry instead of breaking extraction
    over what should be a quality improvement, not a hard dependency.
    """
    if not problem_text.strip():
        return None
    try:
        index = _get_category_index()
        [query_vector] = _embed([problem_text], input_type="query")
        ranked = sorted(
            index.items(),
            key=lambda item: _cosine_similarity(query_vector, item[1]),
            reverse=True,
        )
        return [category for category, _ in ranked[:top_k]]
    except Exception as exc:
        logger.warning(
            "Category shortlist embedding failed, falling back to full registry: %s",
            exc,
        )
        return None


# ── Extraction pipeline ───────────────────────────────────────────────────────

def _format_registry(categories: list[str] | None = None) -> str:
    lines: list[str] = []
    for category in (categories if categories else SERVICE_REGISTRY.keys()):
        tags = SERVICE_REGISTRY[category]
        description = CATEGORY_DESCRIPTIONS.get(category, "")
        lines.append(f"\n[{category}] — {description}")
        lines.extend(f"  - {tag}: {desc}" for tag, desc in tags.items())
    return "\n".join(lines)


def _build_extraction_prompt(candidate_categories: list[str] | None = None) -> str:
    shortlist_note = (
        ""
        if not candidate_categories
        else (
            "\nCANDIDATE CATEGORIES — a semantic search over the full taxonomy "
            "pre-selected these as the most likely fits for this job, ranked by "
            "relevance:\n"
            f"{json.dumps(candidate_categories)}\n"
            "Treat this as a head start, NOT a constraint. If the job genuinely "
            "needs a category outside this list — from elsewhere in the full "
            "taxonomy, or a brand new invented one — use it anyway. Never "
            "force-fit a job into a candidate category just because it was "
            "shortlisted.\n"
        )
    )

    return (
        "You are a strict data-extraction engine. "
        "Output ONLY valid JSON — no preamble, no markdown fences, no extra keys.\n\n"
        "From the conversation above, extract exactly THREE fields:\n"
        "  1. is_job_request — true only if the customer ultimately described a "
        "genuine, dispatchable service job: something a worker or professional "
        "could actually be sent to physically do. False if the conversation is "
        "small talk, a general question, a request unrelated to booking a "
        "service, or otherwise never turned into a real job.\n\n"
        "  2. categories — a list of 1 to 3 objects, ONE per trade genuinely "
        "needed for this job, ordered with the MOST CENTRAL trade first. Most "
        "jobs need exactly one. Only list more than one when the job truly "
        "spans separate trades that would be staffed by different workers — "
        "e.g. installing a timer on a water tank needs a plumber for the tank "
        "fitting AND an electrician for the timer's wiring. Do not pad this "
        "list with categories that only loosely relate to the job.\n"
        "     Each object has exactly three fields:\n"
        "       - category: a short, lowercase, hyphenated name for that "
        "trade. Prefer an exact match from CATEGORY LIST when the job "
        "genuinely belongs there. If it doesn't fit ANY entry, invent a new "
        "one in the same style (e.g. 'pet-grooming'). Never force a job into "
        "a category that doesn't actually match it just because it's in the "
        "list, and never pick a category based on a loose word association — "
        "judge it by what the worker would actually need to know how to do, "
        "and check the category's description below before choosing it.\n"
        "       - tags: 1–3 short, lowercase, hyphenated tags describing the "
        "SPECIFIC part of the task that THIS trade — and only this trade — "
        "would handle. Never put a tag here that actually belongs to a "
        "different trade's category, even if it's part of the same overall "
        "job.\n"
        "         Tag PRECISION always wins over registry membership: if TAG "
        "REGISTRY has a tag that accurately describes the task, use it. If "
        "the closest registry tag would describe a DIFFERENT or less "
        "specific task than what the customer actually asked for, invent a "
        "new, precise tag instead — never choose a registry tag just because "
        "it's 'close enough'.\n"
        "       - is_custom_category: true if EITHER this category is not an "
        "exact CATEGORY LIST match, OR any of its tags had to be invented "
        "because nothing in TAG REGISTRY for that category precisely "
        "described the task. False only when both the category and every "
        "one of its tags are exact, verified registry matches.\n"
        "     Empty list if is_job_request is false.\n\n"
        "  3. problem_description — 1-2 plain sentences describing the "
        "physical task or problem itself: what needs doing, to what, and "
        "where. Empty string if is_job_request is false. Do not invent "
        "details the customer didn't say; do not mention urgency or "
        "safety.\n"
        "     This text will later be embedded and matched against worker "
        "job_description text from the worker vetting pipeline, so:\n"
        "       - Never use first-person voice ('my sink is leaking') or "
        "third-person customer framing ('the customer's sink is "
        "leaking') — state the task directly, e.g. 'Leaking pipe under "
        "the kitchen sink needs repair.'\n"
        "       - Strip conversational filler, apologies, and requests "
        "for help ('please help', 'can someone fix') — describe only the "
        "physical task.\n"
        "       - Use the same plain, concrete vocabulary as TAG REGISTRY "
        "below for the matched category or categories, so wording lines "
        "up with how worker capabilities are described for the same "
        "domain. Do not force a registry term that doesn't genuinely fit "
        "the task.\n"
        "       - If the job spans more than one trade, cover every trade "
        "listed in categories, but stay concise — 2 sentences is a "
        "ceiling, not a target.\n\n"
        "REMEMBER: CATEGORY LIST and TAG REGISTRY below are a preferred, "
        "commonly-used set — not the only valid answers. Treat them as "
        "helpful defaults, not a constraint that overrides accuracy. "
        "Inventing a new category or tag is the CORRECT choice whenever it "
        "more accurately describes the real job; never distort the job to "
        "fit an existing entry. Likewise, a category's PRESENCE in the list "
        "doesn't mean it's the right one for THIS job — judge every category "
        "by its description, not just its name. A word in the customer's "
        "description sounding similar to a category name (e.g. a 'gate' "
        "sounding like 'security') is not evidence that category is correct.\n"
        f"{shortlist_note}\n"
        "WORKED EXAMPLE — a job spanning two trades, including a category "
        "that LOOKS related by word-association but ISN'T:\n"
        "  Customer: \"My automatic sliding driveway gate is stuck halfway "
        "open. I think the motor's dead, and the manual release lever is "
        "jammed too so I can't push it by hand either.\"\n"
        "  Correct extraction:\n"
        "  {\n"
        "    \"is_job_request\": true,\n"
        "    \"categories\": [\n"
        "      {\"category\": \"construction\", \"tags\": [\"gate-repair\", "
        "\"manual-release-fixing\"], \"is_custom_category\": true},\n"
        "      {\"category\": \"electrical\", \"tags\": "
        "[\"electric-motor-replacement\"], \"is_custom_category\": true}\n"
        "    ],\n"
        "    \"problem_description\": \"Automatic sliding driveway gate "
        "stuck halfway open due to a dead motor and a jammed manual release "
        "lever.\"\n"
        "  }\n"
        "  This is NOT 'security', even though gates control access to a "
        "property. The job here is fixing stuck hardware — structural and "
        "electrical repair — not monitoring or protecting the property. "
        "'security' only applies when the job itself is about surveillance, "
        "alarms, or access-control systems (cameras, intercoms, alarm "
        "panels), not the physical mechanism of a gate, door, or lock.\n"
        "  STYLE NOTE: this example illustrates categorisation and "
        "description FORMAT only. If your own problem_description starts "
        "to closely mirror its exact wording for a different job, that's a "
        "sign you're echoing the example rather than describing what this "
        "customer actually said — rewrite using only this conversation's "
        "details, in your own words.\n\n"
        f"CATEGORY LIST (preferred, not exhaustive):\n{json.dumps(PROBLEM_CATEGORIES)}\n\n"
        f"TAG REGISTRY (grouped by category, examples only):"
        f"{_format_registry(candidate_categories)}"
    )


def _sanitize_tag_list(tags: list[str], max_count: int = 3) -> list[str]:
    """Lowercase, strip, dedupe, drop empties, cap length. Never filters by registry membership — that's a policy decision made by the caller, not a cleanup step."""
    cleaned: list[str] = []
    for raw_tag in tags:
        tag = raw_tag.strip().lower()
        if not tag or tag in cleaned:
            continue
        cleaned.append(tag)
        if len(cleaned) == max_count:
            break
    return cleaned


def _sanitize_categories(categories: list[CategoryMatch], max_count: int = 3) -> list[CategoryMatch]:
    """
    Normalise the model's category list: lowercase names, sanitise each
    entry's own tags independently (so a tag never leaks across trades),
    merge duplicate category names instead of silently dropping one, and
    cap the total number of categories. is_custom_category is recomputed
    here rather than trusted blindly from the model, the same way the old
    single-category pipeline always did.
    """
    merged: dict[str, list[str]] = {}
    order: list[str] = []
    for entry in categories:
        name = entry.category.strip().lower()
        if not name:
            continue
        cleaned_tags = _sanitize_tag_list(entry.tags, max_count=3)
        if name not in merged:
            merged[name] = []
            order.append(name)
        for tag in cleaned_tags:
            if tag not in merged[name]:
                merged[name].append(tag)

    result: list[CategoryMatch] = []
    for name in order[:max_count]:
        tags = merged[name][:3]
        if name in PROBLEM_CATEGORIES:
            registry_tags = SERVICE_REGISTRY[name]
            is_custom = any(t not in registry_tags for t in tags) or not tags
        else:
            is_custom = True
        result.append(CategoryMatch(category=name, tags=tags, is_custom_category=is_custom))
    return result


def _blank_non_job_result(result: CustomerProblemSchema) -> CustomerProblemSchema:
    """Normalise any 'no real job here' outcome to one consistent shape."""
    result.is_job_request = False
    result.categories = []
    result.problem_description = ""
    return result


# ── Worked-example echo guard ────────────────────────────────────────────────
# Small models occasionally reproduce a prompt's own worked example almost
# verbatim instead of describing the real conversation, especially when the
# real job is topically close to the example. This is a targeted guard
# against that specific, observed failure mode — not a general plagiarism
# detector — so it's deliberately cheap: an exact/near-exact substring check
# against the one example string that actually appears in this prompt.

_EXAMPLE_ECHO_TEXTS = [
    "automatic sliding driveway gate stuck halfway open due to a dead "
    "motor and a jammed manual release lever",
]


def _looks_like_example_echo(problem_description: str) -> bool:
    """
    True if problem_description closely matches the worked example's own
    wording rather than describing what this specific customer said.
    """
    normalized = problem_description.strip().lower()
    return any(
        example in normalized or normalized in example
        for example in _EXAMPLE_ECHO_TEXTS
    )


def _call_extraction_model(
    messages: list[dict], model_name: str, temperature: float
) -> CustomerProblemSchema:
    """
    Shared call+parse logic used by both the primary extraction call and
    the echo-recovery retry in extract_final_json, so the request /
    fence-stripping / validation logic only lives in one place.
    """
    response = _nvidia_client.chat.completions.create(
        model=model_name,
        messages=messages,
        # json_object mode enforces valid JSON on every response; the extraction
        # prompt already specifies the exact fields, and Pydantic validates shape.
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=1024,
    )

    raw = response.choices[0].message.content.strip()

    # Small models sometimes emit markdown fences despite instructions
    if raw.startswith("```json"):
        raw = raw.split("```json", 1)[1].rsplit("```", 1)[0].strip()
    elif raw.startswith("```"):
        raw = raw.split("```", 1)[1].rsplit("```", 1)[0].strip()

    try:
        return CustomerProblemSchema.model_validate_json(raw)
    except ValueError as exc:
        raise ValueError(
            f"Extraction model returned invalid JSON it could not be parsed from: {raw!r}"
        ) from exc


def extract_final_json(
    chat_history: list[dict],
    model_name: str = "meta/llama-3.1-70b-instruct",
) -> CustomerProblemSchema:
    """
    Convert a completed interview history into a validated payload.

    SERVICE_REGISTRY is a bias toward known-good matches, never a filter
    that deletes the model's actual answer. Tag and category data the model
    produces is preserved as-is (after light normalisation); is_custom_category
    is purely an informational flag for downstream routing, not a gate that
    discards anything.

    Before calling the extraction model, the customer's own messages are
    embedded and matched against the registry to produce a shortlist of the
    most semantically relevant categories (see _shortlist_categories). This
    keeps the per-call classification prompt focused and reduces the chance
    of an unrelated category getting picked purely because it was sitting in
    a long list — the shortlist never blocks the model from going outside it.

    `categories` (1-3 entries, most central trade first) replaces the old
    single problem_category + secondary_categories + service_tags fields —
    each entry owns only the tags that trade would actually perform, so
    multi-trade jobs route to every relevant worker pool without tags
    bleeding into the wrong trade.

    problem_description is checked against _looks_like_example_echo after
    the first extraction call. If it matches, the model gets one retry at a
    higher temperature with an explicit correction nudge; if that retry
    still echoes (or fails outright), the original result is kept rather
    than blocking extraction on this defensive check.

    Outcomes:
      - Clean registry match: a category entry's name is an exact
        SERVICE_REGISTRY key and every one of its tags is an exact tag for
        that category. is_custom_category=False for that entry. Fully
        verified, cheapest to auto-route.
      - Registry category, novel tag(s): the category matches a registry key
        but at least one tag had to be invented. is_custom_category=True for
        that entry; category-level dispatch still works, the novel tag(s)
        may want a quick manual glance.
      - Fully custom: the category itself isn't a registry key.
        is_custom_category=True for that entry.
      - No job at all: is_job_request=False, categories=[] — nothing to
        dispatch.

    Strips the system prompt from history before sending so the extraction
    engine sees only the real dialogue.
    """
    cleaned = [msg for msg in chat_history if msg["role"] != "system"]

    # Plain-text version of what the customer described, used only to find
    # the semantic neighbourhood of categories for the shortlist — never
    # sent to the model as a leading question, and never overrides anything
    # the model itself decides.
    customer_text = " ".join(msg["content"] for msg in cleaned if msg["role"] == "user")
    candidate_categories = _shortlist_categories(customer_text)

    messages = [
        {"role": "system", "content": _build_extraction_prompt(candidate_categories)}
    ] + cleaned

    result = _call_extraction_model(messages, model_name, temperature=0.0)

    # Nothing dispatchable ever surfaced — don't fabricate a category/tags
    # just to fill the schema.
    if not getattr(result, "is_job_request", True):
        return _blank_non_job_result(result)

    result.categories = _sanitize_categories(result.categories)

    if _looks_like_example_echo(result.problem_description):
        logger.warning(
            "Extraction echoed the worked example's problem_description "
            "verbatim; retrying at a higher temperature."
        )
        retry_messages = messages + [
            {
                "role": "system",
                "content": (
                    "Your previous problem_description copied the worked "
                    "example's exact wording. That example illustrates "
                    "format only. Rewrite problem_description using only "
                    "details this specific customer actually said, in "
                    "different words."
                ),
            }
        ]
        try:
            retry_result = _call_extraction_model(retry_messages, model_name, temperature=0.2)
            if (
                getattr(retry_result, "is_job_request", True)
                and not _looks_like_example_echo(retry_result.problem_description)
            ):
                retry_result.categories = _sanitize_categories(retry_result.categories)
                result = retry_result
        except Exception as exc:
            logger.warning(
                "Retry after example echo failed, keeping original result: %s", exc
            )

    if not result.categories or not result.problem_description.strip():
        # Incomplete extraction despite is_job_request=True — treat as no job
        # rather than dispatching a half-empty request.
        return _blank_non_job_result(result)

    return result