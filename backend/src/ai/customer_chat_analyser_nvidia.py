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

problem_description contract
----------------------------
problem_description is the single field that downstream matching actually
embeds, so it is treated here as a first-class deliverable rather than a
one-line summary. It must be a 2–4 sentence, worker-facing job brief that
covers, in order: (1) the object/system and its type, (2) the observed
symptom or the work requested, (3) the location and physical context, and
(4) any concrete specifics the customer volunteered — material, size,
count, floor/level, access constraints, age, whether it's a repair vs a new
install. Anything the customer did not say is simply omitted; the field is
enriched by *using more of the conversation*, never by inventing detail.
Two guards enforce this after extraction: _looks_like_example_echo (the
model parroting the prompt's worked example) and
_description_needs_enrichment (a thin, vague, or first-person description).
Either one buys the model exactly one corrective retry.
"""

import json
import logging
import math
import os
import re
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

    "DETAIL CHECKLIST — what a good answer contains:\n"
    "A worker reading only the final summary should be able to picture the job and "
    "turn up with the right skills and tools. Before you finish, try to have learned "
    "as many of these as the job actually calls for:\n"
    "  - THE OBJECT: what exact thing is involved, and what kind it is (a geyser vs a "
    "solar water heater; a front-load vs top-load washing machine; a wooden vs metal "
    "gate).\n"
    "  - THE SYMPTOM OR THE ASK: what it's doing wrong (leaking, tripping, stuck, not "
    "heating, making noise) — or, for non-repair jobs, exactly what should be done "
    "(install, clean, move, paint, teach, cater).\n"
    "  - REPAIR vs INSTALL vs MAINTENANCE: whether an existing item is being fixed, a "
    "new one is being fitted, or something is being serviced/cleaned routinely. These "
    "look alike in words and are completely different jobs to staff.\n"
    "  - WHERE: which room, floor, or part of the property — kitchen, second-floor "
    "bathroom, rooftop tank, driveway, back garden.\n"
    "  - SCALE: how many, how big, how much area — one tap or five, a single room or "
    "the whole flat, a 2-seater sofa or a full lounge suite.\n"
    "  - ANYTHING THAT CHANGES THE APPROACH: material, rough age, whether it's been "
    "worked on before, or access limits (rooftop, locked shaft, third floor with no "
    "lift).\n"
    "Ask about a checklist item only when it is genuinely missing AND it would change "
    "what the worker does or brings. Never run through this list mechanically, never "
    "ask about something the customer already covered, and never ask for a detail that "
    "obviously doesn't apply to the job in front of you.\n\n"

    "STYLE RULES:\n"
    "- Keep every reply to 1–2 short sentences. Never write long paragraphs.\n"
    "- Always acknowledge what the customer just told you before asking anything. "
    "They should feel heard, not interrogated.\n"
    "- Ask about ONE missing piece at a time. Never stack two questions in one reply.\n"
    "- Prefer concrete, answerable questions over open ones: 'Is it the rooftop tank or "
    "an underground one?' beats 'Can you tell me more about the tank?'\n"
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
    "to in-home care, writing or coding something, general chit-chat, shopping requests, "
    "etc.). In that case, explain you can only help book hands-on service work and ask "
    "them to describe a job, instead of moving toward completion.\n\n"

    "ATTACHMENTS:\n"
    "- You are text-only. You cannot receive, view, or store photos, files, "
    "measurements-as-images, or any other attachment in this chat, even if the "
    "customer says they're sending one.\n"
    "- If a customer says they will send, attach, or share a photo, size, "
    "measurement, or any other file — do NOT say to go ahead and send it, do NOT "
    "imply you'll look at it or review it, and do NOT wait on it before continuing. "
    "Briefly note that attachments can be added in the attachment section when "
    "posting the job, then keep gathering the task description in words.\n"
    "  Good example:\n"
    "    Customer: 'Metal gate for entrance. I will send attachments for the "
    "size.'\n"
    "    You: 'Got it — a metal gate for the entrance. You can add the size "
    "photos in the attachment section when posting the job. Is this a repair "
    "or a new installation?'\n"
    "  Bad example (do not do this):\n"
    "    'You'll be sending attachments with the gate's size. Please go ahead "
    "and send them, and I'll make sure to get a clear picture of what's "
    "needed.'\n"
    "- A promised attachment never substitutes for a word description. Keep asking "
    "for the physical details you still need (what's wrong, what size/type in their "
    "own words, etc.) as normal.\n\n"

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
    "- If the customer has already sent 5 messages and the task still isn't fully "
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
        "  3. problem_description — THE MOST IMPORTANT FIELD. This is the job "
        "brief a worker will read to decide whether they can do this job, and "
        "it is the text that gets embedded and matched against worker "
        "capability profiles. A thin one-liner is a FAILURE even when it is "
        "technically accurate. Empty string only if is_job_request is false.\n\n"
        "     LENGTH AND SHAPE: write 2 to 4 complete sentences (roughly "
        "35–90 words) of flowing prose. Not a single clause, not bullet "
        "points, not a list of keywords, not a transcript. Longer than 4 "
        "sentences means you are padding — stop.\n\n"
        "     COVER THESE, IN THIS ORDER, using only what the conversation "
        "actually contains:\n"
        "       (a) THE OBJECT AND ITS TYPE — name the exact item, system, "
        "surface, vehicle, or person-facing service involved, with whatever "
        "type/model/material qualifier the customer gave (e.g. 'rooftop "
        "plastic water storage tank', 'front-load washing machine', "
        "'wall-mounted split AC unit', 'wooden main entrance door').\n"
        "       (b) THE SYMPTOM OR THE WORK REQUESTED — what is observably "
        "wrong (leaking, tripping, stuck, not heating, making noise, "
        "cracked, infested) or, for non-repair jobs, precisely what must be "
        "done (install, replace, clean, move, paint, coach, cater). State "
        "clearly whether this is a REPAIR of an existing item, a NEW "
        "INSTALLATION, or ROUTINE SERVICING/CLEANING — these read alike in "
        "words but are different jobs to staff.\n"
        "       (c) LOCATION AND CONTEXT — where on the property or vehicle "
        "the work happens: which room, floor, rooftop, exterior wall, "
        "driveway, or garden, plus property type (flat, house, office, shop) "
        "when the customer mentioned it.\n"
        "       (d) CONCRETE SPECIFICS THE CUSTOMER GAVE — quantity, "
        "dimensions, area, material, approximate age, prior repair attempts, "
        "and any access constraint (rooftop access, third floor without a "
        "lift, locked utility shaft, work must happen around furniture). "
        "Include the numbers and units exactly as stated.\n"
        "       (e) SCOPE PER TRADE — if categories lists more than one "
        "trade, make explicit which part of the work belongs to each, so a "
        "single-trade worker can tell what they'd be responsible for.\n\n"
        "     HARD RULES:\n"
        "       - NEVER invent, assume, or infer a detail the customer did "
        "not state. If the floor, size, material, or age never came up, "
        "simply do not mention it. Enrichment comes from using MORE of what "
        "was actually said, never from filling gaps with plausible guesses. "
        "A confidently wrong detail is far more damaging than a missing "
        "one, because it misroutes the job.\n"
        "       - Do NOT diagnose a root cause the customer did not "
        "themselves report. Describe the reported symptom. If the customer "
        "offered their own guess, attribute it as reported (e.g. 'customer "
        "reports the motor appears dead') rather than stating it as fact.\n"
        "       - Never use first person ('my sink is leaking') or "
        "customer framing ('the customer's sink is leaking'); the ONLY "
        "permitted use of the word 'customer' is attributing a reported "
        "guess as above. State the job directly: 'Water is leaking from the "
        "supply pipe under the kitchen sink.'\n"
        "       - Strip greetings, apologies, thanks, pleading and requests "
        "for help ('please help', 'can someone come fast'). Describe only "
        "the work.\n"
        "       - Do NOT mention urgency, danger, safety, scheduling "
        "preference, budget, or price — those are captured separately. "
        "Scheduling is only in-scope when it defines the job itself (e.g. "
        "'weekly recurring cleaning' vs a one-off).\n"
        "       - Use the plain, concrete vocabulary of TAG REGISTRY for "
        "the matched categories so the wording lines up with how worker "
        "capabilities are written in the same domain — but never bend the "
        "facts to fit a registry phrase.\n"
        "       - Write it so it stands alone. Someone who never saw this "
        "conversation must understand the whole job from this text only, "
        "with no pronouns pointing at things that were only mentioned in "
        "chat ('it', 'that one', 'the same as before').\n\n"
        "     QUALITY BAR — compare these:\n"
        "       WEAK (rejected): 'Water tank problem needs fixing.'\n"
        "       WEAK (rejected): 'Customer needs help with their tank and a "
        "timer.'\n"
        "       STRONG (accepted): 'A 1000-litre rooftop water storage tank "
        "on a two-storey house needs an automatic level-control timer "
        "fitted so the supply pump stops on its own. The work covers "
        "mounting the timer unit at the tank and adapting the existing tank "
        "inlet fittings, then wiring the timer into the pump's mains supply. "
        "The tank is reached by an external rooftop ladder.'\n"
        "     The strong version wins because every clause came from the "
        "conversation, the object is named with its type and size, the work "
        "type (new fitting, not repair) is explicit, and the two trades' "
        "portions are separable.\n\n"
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
        "open. It's the metal one at the street entrance of the house, "
        "about 12 feet wide, put in maybe six years ago. I think the "
        "motor's dead, and the manual release lever is jammed too so I "
        "can't push it by hand either.\"\n"
        "  Correct extraction:\n"
        "  {\n"
        "    \"is_job_request\": true,\n"
        "    \"categories\": [\n"
        "      {\"category\": \"construction\", \"tags\": [\"gate-repair\", "
        "\"manual-release-fixing\"], \"is_custom_category\": true},\n"
        "      {\"category\": \"electrical\", \"tags\": "
        "[\"electric-motor-replacement\", \"wiring-repair\"], "
        "\"is_custom_category\": true}\n"
        "    ],\n"
        "    \"problem_description\": \"An automatic sliding metal gate at "
        "the street entrance of a house, roughly 12 feet wide and about six "
        "years old, is stuck halfway open and cannot be moved by hand. The "
        "manual release lever is jammed, so the mechanical work covers "
        "freeing the release mechanism and checking the gate track and "
        "rollers it runs on. Separately, the drive motor is unresponsive and "
        "the customer reports it may be dead, so the motor and its supply "
        "wiring need diagnosing and likely replacing.\"\n"
        "  }\n"
        "  Note how the description names the object with its material, "
        "size and age exactly as stated, separates the mechanical scope "
        "from the electrical scope, and attributes the dead-motor guess as "
        "reported rather than asserting it.\n"
        "  This is NOT 'security', even though gates control access to a "
        "property. The job here is fixing stuck hardware — structural and "
        "electrical repair — not monitoring or protecting the property. "
        "'security' only applies when the job itself is about surveillance, "
        "alarms, or access-control systems (cameras, intercoms, alarm "
        "panels), not the physical mechanism of a gate, door, or lock.\n"
        "  STYLE NOTE: this example illustrates categorisation and "
        "description FORMAT only. Reuse its STRUCTURE, never its wording or "
        "its facts. If your own problem_description starts to mirror its "
        "phrasing for a different job, or mentions a gate, motor or release "
        "lever that this customer never brought up, you are echoing the "
        "example instead of describing the real conversation — rewrite "
        "using only this conversation's details, in your own words.\n\n"
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


# ── Description normalisation ────────────────────────────────────────────────
# Cheap, deterministic tidy-up applied to whatever the model returns, so the
# stored brief is always clean prose regardless of how the model formatted
# it. Strictly cosmetic — it never adds, removes, or reorders meaning, and
# never rewrites the job itself. Anything substantive is handled by the
# enrichment retry below, which asks the model to do the rewriting.

_MARKDOWN_BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.MULTILINE)
_WHITESPACE_RE = re.compile(r"\s+")


def _tidy_description(problem_description: str) -> str:
    """
    Flatten bullets/newlines into prose, collapse runs of whitespace, drop
    stray wrapping quotes, and make sure the text ends with a full stop.
    """
    text = problem_description.strip()
    if not text:
        return ""
    text = _MARKDOWN_BULLET_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()
    if text and text[-1] not in ".!?":
        text += "."
    return text


# ── Worked-example echo guard ────────────────────────────────────────────────
# Small models occasionally reproduce a prompt's own worked example almost
# verbatim instead of describing the real conversation, especially when the
# real job is topically close to the example. This is a targeted guard
# against that specific, observed failure mode — not a general plagiarism
# detector — so it's deliberately cheap: exact/near-exact substring checks
# against the distinctive phrases of the one example in this prompt.
#
# Keep these fragments in sync with the worked example in
# _build_extraction_prompt. If that example is reworded, the fragments here
# must be reworded with it or the guard silently stops firing.

_EXAMPLE_ECHO_TEXTS = [
    "an automatic sliding metal gate at the street entrance of a house",
    "roughly 12 feet wide and about six years old, is stuck halfway open",
    "the manual release lever is jammed, so the mechanical work covers",
    # Retained from the earlier, shorter worked example so histories or
    # cached prompts carrying the old wording are still caught.
    "automatic sliding driveway gate stuck halfway open due to a dead "
    "motor and a jammed manual release lever",
]


_MIN_ECHO_COMPARE_LEN = 40  # don't call a stub an "echo" just for being short


def _looks_like_example_echo(problem_description: str) -> bool:
    """
    True if problem_description closely matches the worked example's own
    wording rather than describing what this specific customer said.

    The reverse containment check (description inside an example fragment)
    only applies to text long enough for the overlap to be meaningful —
    otherwise a short, unrelated stub could coincidentally sit inside a
    fragment and get routed to the echo branch instead of the enrichment
    branch, which is the correction it actually needs.
    """
    normalized = _WHITESPACE_RE.sub(" ", problem_description.strip().lower())
    if not normalized:
        return False
    for example in _EXAMPLE_ECHO_TEXTS:
        if example in normalized:
            return True
        if len(normalized) >= _MIN_ECHO_COMPARE_LEN and normalized in example:
            return True
    return False


# ── Thin-description guard ───────────────────────────────────────────────────
# The whole point of this change is that problem_description must be a real
# job brief, not a label. Models under-deliver on that in a few predictable
# ways: they return one short clause, they hedge with placeholder nouns
# ('some issue with the tank'), they slip back into first person, or they
# compress a long, detail-rich conversation into a fraction of what was
# said. Each of those is detectable without another model call, so they're
# caught here and repaired with a single targeted retry rather than being
# stored and silently degrading match quality downstream.

_MIN_DESCRIPTION_WORDS = 18          # below this, it isn't a brief
_MIN_DESCRIPTION_SENTENCES = 2       # the prompt asks for 2–4
_DETAIL_RATIO = 0.22                 # vs. what the customer actually said
_DETAIL_RATIO_WORD_CAP = 45          # never demand more than this many words
_LONG_CONVERSATION_WORDS = 45        # only apply the ratio to real detail

# Phrases that signal the model hedged instead of describing the job. Kept
# deliberately narrow: each entry must be vague ON ITS OWN, so it can't fire
# on a detailed brief that merely happens to contain the words. "needs
# fixing" is excluded for exactly that reason — "the leaking mixer tap in
# the second-floor bathroom needs fixing" is a perfectly good brief.
_VAGUE_DESCRIPTION_MARKERS = (
    "something wrong",
    "something is wrong",
    "some issue",
    "some problem",
    "some kind of",
    "some work",
    "needs help",
    "general problem",
    "unspecified",
    "as described above",
    "as mentioned above",
    "see conversation",
    "details not provided",
    "no further details",
)

_FIRST_PERSON_RE = re.compile(r"\b(i|i'm|im|my|mine|we|we're|our|ours|me|us)\b")
_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+(?:\s|$)")


def _description_needs_enrichment(problem_description: str, customer_text: str = "") -> bool:
    """
    True when problem_description falls short of the brief contract and is
    worth one corrective retry.

    Fires on any of: empty/near-empty text, fewer than two sentences, a
    placeholder/hedging phrase, first-person voice, or a description that is
    disproportionately thin next to a detail-rich conversation. Deliberately
    conservative — a description that is merely concise but complete should
    pass, because a needless retry costs latency and risks the model
    padding with invented detail.
    """
    text = _tidy_description(problem_description)
    if not text:
        return True

    words = text.split()
    if len(words) < _MIN_DESCRIPTION_WORDS:
        return True

    sentences = [s for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    if len(sentences) < _MIN_DESCRIPTION_SENTENCES:
        return True

    lowered = text.lower()
    if any(marker in lowered for marker in _VAGUE_DESCRIPTION_MARKERS):
        return True

    if _FIRST_PERSON_RE.search(lowered):
        return True

    # The customer gave plenty of detail but almost none of it survived.
    customer_word_count = len(customer_text.split())
    if customer_word_count >= _LONG_CONVERSATION_WORDS:
        required = min(int(customer_word_count * _DETAIL_RATIO), _DETAIL_RATIO_WORD_CAP)
        if len(words) < required:
            return True

    return False


_ENRICHMENT_NUDGE = (
    "Your previous problem_description does not meet the required "
    "standard: it is too short, too vague, written in first person, or it "
    "dropped concrete details the customer actually provided. Produce the "
    "same JSON again with is_job_request and categories UNCHANGED, and "
    "rewrite problem_description as 2 to 4 full sentences (roughly 35–90 "
    "words) that state, in order: the exact object or service and its type "
    "or material, the observed symptom or the work requested and whether "
    "it is a repair, a new installation, or routine servicing/cleaning, "
    "where on the property or vehicle it is, and every concrete specific "
    "the customer gave — quantities, sizes, ages, access constraints — "
    "using their exact numbers. If more than one trade is involved, say "
    "which part of the work belongs to each. Use third-person, "
    "worker-facing prose with no first-person pronouns and no pleading or "
    "filler. Do NOT invent, assume, or infer anything the customer did not "
    "say: draw only on details actually present in the conversation above, "
    "and leave out anything that never came up."
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

    problem_description quality is enforced after the first extraction call,
    because it is the text downstream matching actually embeds:
      - _tidy_description flattens any bullets/newlines into clean prose.
      - _looks_like_example_echo catches the model parroting the prompt's
        worked example instead of this conversation.
      - _description_needs_enrichment catches briefs that are too short,
        single-sentence, hedging, first-person, or disproportionately thin
        next to a detail-rich conversation.
    Whichever fires first buys exactly ONE corrective retry at a slightly
    higher temperature with a targeted nudge. The retry is accepted only if
    it is genuinely better by the same checks; otherwise the original is
    kept. Extraction is never blocked on these defensive checks — a
    mediocre brief still dispatches, it just gets logged.

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
    # the semantic neighbourhood of categories for the shortlist and to
    # judge whether the returned brief used a fair share of the detail on
    # offer — never sent to the model as a leading question, and never
    # overrides anything the model itself decides.
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
    result.problem_description = _tidy_description(result.problem_description)

    # One retry budget, shared: whichever description problem shows up
    # first gets the correction. Echo is checked first because an echoed
    # description is wrong about the job itself, not merely thin.
    echoed = _looks_like_example_echo(result.problem_description)
    thin = False if echoed else _description_needs_enrichment(
        result.problem_description, customer_text
    )

    if echoed or thin:
        if echoed:
            logger.warning(
                "Extraction echoed the worked example's problem_description; "
                "retrying at a higher temperature."
            )
            nudge = (
                "Your previous problem_description reused the worked "
                "example's wording and details. That example illustrates "
                "STRUCTURE only, never content. Produce the same JSON again "
                "with is_job_request and categories UNCHANGED, and rewrite "
                "problem_description from scratch as 2 to 4 full sentences "
                "using only what this specific customer actually said, in "
                "your own words. Do not mention any object, fault, "
                "measurement or component that does not appear in the "
                "conversation above."
            )
        else:
            logger.info(
                "problem_description fell short of the job-brief standard "
                "(%d words); retrying for a richer description.",
                len(result.problem_description.split()),
            )
            nudge = _ENRICHMENT_NUDGE

        retry_messages = messages + [{"role": "system", "content": nudge}]
        try:
            retry_result = _call_extraction_model(retry_messages, model_name, temperature=0.2)
            retry_description = _tidy_description(retry_result.problem_description)
            improved = (
                getattr(retry_result, "is_job_request", True)
                and not _looks_like_example_echo(retry_description)
                and not _description_needs_enrichment(retry_description, customer_text)
                and bool(retry_result.categories)
            )
            if improved:
                retry_result.categories = _sanitize_categories(retry_result.categories)
                retry_result.problem_description = retry_description
                result = retry_result
            else:
                logger.warning(
                    "Description retry did not clear the quality checks; "
                    "keeping the original extraction."
                )
        except Exception as exc:
            logger.warning(
                "Retry after description quality check failed, keeping original result: %s",
                exc,
            )

    if not result.categories or not result.problem_description.strip():
        # Incomplete extraction despite is_job_request=True — treat as no job
        # rather than dispatching a half-empty request.
        return _blank_non_job_result(result)

    return result