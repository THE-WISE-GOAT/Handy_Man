#!/usr/bin/env python3
"""
Generate a customer-side seed CSV for the Handy_Man `jobs` table
(core.model.Job).

Design point that matters most
------------------------------
Job descriptions are written in the CUSTOMER's voice — symptoms, complaints,
and consequences ("water is pooling under the sink and the cabinet floor has
gone soft") — while worker descriptions in workers_seed.csv are in the
PROVIDER's voice — capabilities ("traces hidden leaks behind walls and under
slabs, then repairs the failed section").

They deliberately share almost no vocabulary. If both sides used the same
phrasing, a cosine-similarity match would look excellent while actually only
measuring string overlap, and you would not learn whether the embedding
understands that "my sink is leaking" means "plumber". Keeping the vocabularies
disjoint is what makes this a real test of nv-embed-v1 + the Sigmoid score.

Every job's `categories` JSONB carries the same trade tags used by
workers_seed.csv, so each job has genuine candidates to match against, and
locations are drawn from the same Kathmandu Valley clusters so the 20 km
ST_DWithin filter behaves.

Output dialect: PostgreSQL `COPY ... WITH (FORMAT csv, HEADER true, NULL '')`
  * JSONB   -> compact JSON, CSV-quoted with doubled inner quotes
  * bool    -> true / false
  * NULL    -> unquoted empty field
  * ''      -> quoted empty field
  * location-> SRID=4326;POINT(lon lat)   (longitude first, PostGIS axis order)
  * description_vector -> NULL (backfill with nv-embed-v1, input_type="query")
"""

from __future__ import annotations

import csv
import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 20260804
N_ROWS = 220
OUT = Path(__file__).with_name("jobs_seed.csv")
WORKERS_CSV = Path(__file__).with_name("workers_seed.csv")

rng = random.Random(SEED)

# --------------------------------------------------------------------------
# Vocabulary matched to your live table:
#   status: PENDING / ASSIGNED / COMPLETED / CANCELLED   (uppercase)
#   mode:   express / regular
# NOTE: your production table currently holds BOTH 'PENDING' and 'pending'.
# That inconsistency will break any `status == "PENDING"` filter. This file
# emits uppercase only; consider a one-off UPDATE to normalise the live rows.
# --------------------------------------------------------------------------
STATUS_WEIGHTS = [
    ("PENDING",   40),   # posted, awaiting match/bid
    ("MATCHED",   14),   # candidates staged in job_worker_matches
    ("ASSIGNED",  18),   # worker accepted -> worker_id set
    ("COMPLETED", 20),   # finished -> worker_id set
    ("CANCELLED",  8),   # customer withdrew
]
MODES = [("express", 45), ("regular", 55)]

# --------------------------------------------------------------------------
# Job templates, keyed by the SAME category_tag values as workers_seed.csv.
#
# Each template:
#   titles  - short customer-entered titles (often terse or lowercase, as real
#             users type them)
#   symptom - what the customer observes
#   impact  - why it matters to them / urgency
#   ask     - what they want done
#   tags    - speciality tags for the categories JSONB; these MUST exist in
#             the workers taxonomy or the job has no candidates
# --------------------------------------------------------------------------
TEMPLATES: dict[str, list[dict]] = {
    "plumbing": [
        {
            "titles": ["toilet leak", "Leaking toilet", "toilet keeps running"],
            "symptom": "The toilet cistern keeps running long after flushing and there is water seeping from the base onto the bathroom floor",
            "impact": "The floor is wet all day and it is the only toilet in the flat",
            "ask": "Need someone to stop the leak and replace the flush mechanism if it is worn out",
            "tags": ["toilet-and-cistern", "leak-detection"],
        },
        {
            "titles": ["Smelly dirt leakage", "sewer smell in bathroom", "drain blocked badly"],
            "symptom": "Waste water is backing up out of the bathroom floor drain and there is a strong sewage smell through the ground floor",
            "impact": "It has flooded twice this week and we cannot use the bathroom at all",
            "ask": "Want the line cleared and checked with a camera to see if the underground pipe is cracked",
            "tags": ["trenchless-pipe-relining", "cured-in-place-pipe"],
        },
        {
            "titles": ["solar water", "solar heater not heating", "geyser problem"],
            "symptom": "The 1000-litre rooftop tank feeds a solar heater but the water never gets properly hot, and one of the pipes on the roof is dripping",
            "impact": "We have been heating water on the stove for two weeks",
            "ask": "Need the solar hot water system checked, the leak fixed and the mixing valve set correctly",
            "tags": ["solar-water-heater-plumbing", "thermostatic-mixing"],
        },
        {
            "titles": ["no water pressure upstairs", "pump not working", "water pump issue"],
            "symptom": "The booster pump runs constantly but almost no water reaches the second and third floor taps, and the pump makes a rattling noise",
            "impact": "Two families upstairs have had no running water since Saturday",
            "ask": "Need the pump and overhead tank plumbing looked at, and the pressure balanced across all floors",
            "tags": ["pressure-pump-install", "overhead-tank-plumbing"],
        },
        {
            "titles": ["kitchen sink leaking", "tap dripping", "mixer tap replace"],
            "symptom": "Water is pooling in the cabinet under the kitchen sink and the mixer tap drips constantly even when closed tight",
            "impact": "The cabinet base has swollen and gone soft and I am worried about the wood",
            "ask": "Replace the mixer tap and fix whatever is leaking underneath",
            "tags": ["tap-and-mixer-repair", "leak-detection"],
        },
    ],
    "electrical": [
        {
            "titles": ["MCB keeps tripping", "power trips again and again", "fuse box problem"],
            "symptom": "The main breaker trips several times a day, usually when the water pump or iron is switched on, and the board makes a faint buzzing sound",
            "impact": "The fridge keeps losing power and food has spoiled twice",
            "ask": "Need someone to find what is overloading the circuit and fix it properly, not just reset it",
            "tags": ["tripping-circuit-repair", "fault-diagnosis"],
        },
        {
            "titles": ["house wiring old", "rewiring needed", "old wiring unsafe"],
            "symptom": "The house is about thirty years old, still on the original wiring with a ceramic fuse box, and some switches feel warm to the touch",
            "impact": "We have a newborn in the house and I am worried it is a fire risk",
            "ask": "Want a full assessment and rewiring with a modern breaker board and proper earthing",
            "tags": ["house-rewiring", "consumer-unit-upgrade", "earthing-and-bonding"],
        },
        {
            "titles": ["inverter not backing up", "battery backup dead", "inverter beeping"],
            "symptom": "The inverter beeps and cuts out within a few minutes of a power cut, and the batteries feel hot afterwards",
            "impact": "Load shedding is back and we are without light most evenings",
            "ask": "Need the batteries tested and the inverter wiring checked, replaced if the bank is finished",
            "tags": ["inverter-install", "battery-bank-wiring"],
        },
        {
            "titles": ["lights flickering", "need new lights fitted", "LED lights install"],
            "symptom": "Half the ceiling lights flicker and hum after we changed the bulbs to LED, and two of the dimmer switches no longer work at all",
            "impact": "It is giving everyone headaches in the living room",
            "ask": "Want the fittings and dimmers replaced with ones that actually work together",
            "tags": ["led-retrofit", "architectural-lighting"],
        },
        {
            "titles": ["3 phase connection workshop", "motor not starting", "workshop power problem"],
            "symptom": "The three-phase supply to my furniture workshop keeps dropping one phase and the big planer motor trips its starter on load",
            "impact": "Production has stopped and I am paying staff to sit idle",
            "ask": "Need the distribution board and motor starters checked and the imbalance sorted",
            "tags": ["three-phase-distribution", "motor-starter-wiring"],
        },
    ],
    "carpentry": [
        {
            "titles": ["wardrobe door broken", "almari door not closing", "cupboard repair"],
            "symptom": "The sliding wardrobe door has come off its bottom track and two of the soft-close hinges on the side cabinet are hanging loose",
            "impact": "The door cannot be closed and clothes are getting dusty",
            "ask": "Fix the track and replace the broken hinges",
            "tags": ["sliding-wardrobe", "soft-close-hardware"],
        },
        {
            "titles": ["Need bed made", "custom bed frame", "want wooden bed"],
            "symptom": "I want a solid wood queen bed with storage drawers underneath, made to fit a slightly narrow room",
            "impact": "Moving into the new flat next month and need it before then",
            "ask": "Looking for someone who can measure, build and finish it in matching wood",
            "tags": ["custom-furniture", "hardwood-finishing"],
        },
        {
            "titles": ["door not closing", "main door jam", "door frame rotted"],
            "symptom": "The main door has swollen and scrapes the frame badly since the monsoon, and the bottom of the frame has gone soft and crumbly",
            "impact": "The door cannot be locked properly which feels unsafe",
            "ask": "Need the door planed to fit and the rotted part of the frame replaced",
            "tags": ["door-hanging", "frame-repair"],
        },
        {
            "titles": ["modular kitchen fitting", "kitchen cabinets", "new kitchen setup"],
            "symptom": "We have a bare kitchen with only the counter slab in place and need cabinets above and below fitted around an awkward corner and the gas point",
            "impact": "Nothing has a place and we are cooking out of boxes",
            "ask": "Want modular units designed, made and installed with proper drawer hardware",
            "tags": ["modular-kitchen", "soft-close-hardware"],
        },
        {
            "titles": ["floor creaking badly", "wooden floor sagging", "floor joist problem"],
            "symptom": "The wooden floor in the upstairs bedroom flexes and creaks loudly in one area and feels slightly springy underfoot",
            "impact": "It feels unsafe walking across that part of the room",
            "ask": "Need the joists underneath inspected and strengthened",
            "tags": ["floor-joist-repair", "timber-decking"],
        },
    ],
    "painting": [
        {
            "titles": ["Room painting", "paint 2 rooms", "interior painting needed"],
            "symptom": "Two bedrooms need repainting; the current paint is patchy and there are hairline cracks and nail holes all over the walls",
            "impact": "Guests arriving for a wedding next month",
            "ask": "Want the walls puttied smooth and painted in a colour matched to the living room",
            "tags": ["wall-putty", "emulsion-finish", "colour-matching"],
        },
        {
            "titles": ["outside wall black", "exterior paint peeling", "wall fungus outside"],
            "symptom": "The north-facing outside wall has gone black and green with growth and the paint is flaking off in sheets",
            "impact": "It looks terrible from the street and neighbours have commented",
            "ask": "Need it cleaned, treated so the growth does not come back, and recoated with something weatherproof",
            "tags": ["exterior-weathercoat", "anti-fungal-treatment"],
        },
        {
            "titles": ["grill painting", "gate rusted", "railing paint"],
            "symptom": "The window grilles and the main gate have rust bubbling through the old paint, worst at the bottom where water collects",
            "impact": "Rust is starting to stain the wall below",
            "ask": "Want the rust treated and everything repainted so it lasts",
            "tags": ["anti-corrosive-metal-paint"],
        },
        {
            "titles": ["feature wall design", "texture wall living room", "wallpaper fitting"],
            "symptom": "We want one living room wall done as a feature — either a texture finish or patterned wallpaper, we are not sure which",
            "impact": "Renovating before Dashain",
            "ask": "Looking for someone who can advise and then do the finish properly",
            "tags": ["texture-wall", "wallpaper-hanging"],
        },
    ],
    "masonry": [
        {
            "titles": ["wall crack", "crack in wall widening", "plaster falling off"],
            "symptom": "There is a diagonal crack above the door frame that has widened noticeably since the last tremor, and plaster is hollow and falling in patches nearby",
            "impact": "I am worried about whether it is structural",
            "ask": "Need it assessed and the plaster and crack repaired properly",
            "tags": ["cement-plaster", "concrete-repair"],
        },
        {
            "titles": ["boundary wall build", "compound wall needed", "wall construction"],
            "symptom": "Need a boundary wall about 30 metres long and 6 feet high built along one side of the plot, with a gate opening left in it",
            "impact": "The plot is open and things have gone missing from the site",
            "ask": "Want brick or block wall built with a proper foundation",
            "tags": ["brickwork", "block-masonry"],
        },
        {
            "titles": ["Above-ground sewer pipe crack", "concrete slab leaking", "chhat leaking"],
            "symptom": "The concrete slab over the parking area is leaking through in several spots and there are rust stains with small pieces of concrete falling off",
            "impact": "Water drips onto the cars and the exposed steel worries me",
            "ask": "Need the spalled concrete repaired and the reinforcement treated before it gets worse",
            "tags": ["concrete-repair", "rebar-tying"],
        },
        {
            "titles": ["stone wall pointing", "old house repair", "heritage wall repair"],
            "symptom": "Our old family house has traditional brick walls where the joints are crumbling and someone previously patched them with grey cement which is now trapping damp inside",
            "impact": "The inside walls are damp and the plaster keeps blowing",
            "ask": "Need the wrong pointing removed and redone in a mortar that lets the wall breathe",
            "tags": ["lime-mortar-repointing", "heritage-restoration"],
        },
    ],
    "hvac": [
        {
            "titles": ["AC not cooling", "ac servicing", "AC gas problem"],
            "symptom": "The bedroom split AC runs but barely cools, the outdoor unit ices up, and there is a musty smell from the indoor unit",
            "impact": "It is unbearable to sleep in this heat",
            "ask": "Need it serviced, gas checked and the coils cleaned",
            "tags": ["split-ac-install", "gas-charging", "coil-cleaning"],
        },
        {
            "titles": ["new AC installation", "install 2 AC units", "AC fitting"],
            "symptom": "Two new split ACs need installing, one on the first floor and one on the second, with the outdoor units on the rear terrace",
            "impact": "Units are bought and sitting in boxes",
            "ask": "Want them installed with proper piping, vacuum and drainage",
            "tags": ["split-ac-install"],
        },
        {
            "titles": ["restaurant chiller not cold", "cold room problem", "freezer not freezing"],
            "symptom": "The walk-in chiller in my restaurant is holding at about 12 degrees instead of 4, and the compressor keeps switching on and off every few minutes",
            "impact": "I am losing stock daily and the health inspection is next week",
            "ask": "Need it diagnosed and repaired urgently",
            "tags": ["walk-in-chiller", "compressor-replacement"],
        },
        {
            "titles": ["kitchen smoke problem", "exhaust not working", "kitchen ventilation"],
            "symptom": "The commercial kitchen hood barely extracts and smoke fills the room whenever the tandoor is running; the duct rattles loudly",
            "impact": "Staff are complaining and customers can smell it in the dining area",
            "ask": "Want the hood and ducting checked and made to actually extract",
            "tags": ["kitchen-hood-ducting", "exhaust-ventilation"],
        },
    ],
    "appliance-repair": [
        {
            "titles": ["washing machine leaking", "washing machine noise", "washer not spinning"],
            "symptom": "The front-load washing machine makes a loud grinding noise on spin, shakes badly, and leaves a puddle of water underneath after each wash",
            "impact": "Cannot wash clothes for a family of five",
            "ask": "Need it repaired at home if possible rather than taken away",
            "tags": ["front-load-washer", "drum-bearing-replacement"],
        },
        {
            "titles": ["fridge not cooling", "refrigerator problem", "fridge ice buildup"],
            "symptom": "The fridge compartment is not cooling although the freezer works, and there is a thick block of ice at the back of the freezer",
            "impact": "Vegetables and milk are spoiling every other day",
            "ask": "Need the cooling and defrost system checked",
            "tags": ["fridge-gas-refill", "defrost-system-repair"],
        },
        {
            "titles": ["microwave not heating", "oven repair", "induction not working"],
            "symptom": "The microwave runs and the light comes on but food stays cold, and separately the induction hob shows an error code and shuts off",
            "impact": "Down to one gas burner for the whole household",
            "ask": "Want both looked at, repaired if it is worth it",
            "tags": ["microwave-repair", "induction-hob"],
        },
    ],
    "cleaning": [
        {
            "titles": ["Clean the dirty house", "deep cleaning needed", "house cleaning service"],
            "symptom": "The flat has been empty and locked for eight months and is thick with dust, with mould in the bathroom and grease still on the kitchen tiles",
            "impact": "Moving in this weekend",
            "ask": "Need a full deep clean including bathroom, kitchen and windows",
            "tags": ["deep-cleaning", "grout-and-stain-removal"],
        },
        {
            "titles": ["water tank cleaning", "tank dirty", "clean underground tank"],
            "symptom": "The underground water tank has not been cleaned in years and the water has started smelling and looking slightly cloudy",
            "impact": "The children have had stomach problems and I suspect the water",
            "ask": "Want the tank emptied, scrubbed and disinfected properly",
            "tags": ["water-tank-cleaning", "sump-disinfection"],
        },
        {
            "titles": ["after renovation cleaning", "post construction clean", "cement stains everywhere"],
            "symptom": "Construction just finished and there is cement haze on all the tiles, paint spots on the glass and fine dust over every surface",
            "impact": "Cannot hand the flat over to tenants like this",
            "ask": "Need a builders clean including the windows and floors",
            "tags": ["post-construction-cleanup", "grout-and-stain-removal"],
        },
        {
            "titles": ["building glass cleaning", "outside window cleaning", "facade wash"],
            "symptom": "The outside of the glass on our four-storey building has hard water staining and cannot be reached from inside",
            "impact": "The office frontage looks neglected to visiting clients",
            "ask": "Need someone with rope access or proper equipment to clean it",
            "tags": ["high-rise-glass", "facade-cleaning", "rope-access"],
        },
    ],
    "tiling": [
        {
            "titles": ["bathroom tiles", "bathroom leaking downstairs", "shower area leaking"],
            "symptom": "Water from the upstairs bathroom is coming through the ceiling below, and some floor tiles in the shower area sound hollow when tapped",
            "impact": "The ceiling below is stained and starting to sag",
            "ask": "Need the bathroom floor redone with proper waterproofing underneath",
            "tags": ["wet-area-waterproofing", "shower-tray-forming"],
        },
        {
            "titles": ["floor tiles cracked", "tile replacement", "tiles came loose"],
            "symptom": "Several large floor tiles in the hallway have cracked and a few have lifted at the corners where people walk most",
            "impact": "Someone has already tripped on the raised edge",
            "ask": "Want the loose and cracked tiles fixed or replaced to match",
            "tags": ["hollow-tile-repair", "large-format-porcelain"],
        },
        {
            "titles": ["grout dirty black", "regrouting bathroom", "tile joints stained"],
            "symptom": "The grout lines throughout the bathroom have gone black and crumbly and no amount of scrubbing helps",
            "impact": "It looks unhygienic even after cleaning",
            "ask": "Want the old grout raked out and redone in something that resists staining",
            "tags": ["regrouting", "epoxy-grouting"],
        },
        {
            "titles": ["marble floor dull", "marble polishing", "stone floor scratched"],
            "symptom": "The marble floor in the living and dining area has lost its shine, has visible scratches, and one slab sits slightly higher than its neighbour",
            "impact": "It was expensive and now looks worse than cheap tile",
            "ask": "Need it ground level and polished back",
            "tags": ["marble-laying", "stone-polishing"],
        },
    ],
    "roofing": [
        {
            "titles": ["roof leaking", "chhana leaking", "terrace water leaking"],
            "symptom": "The flat terrace roof leaks into the top floor bedroom during heavy rain, and water sits in a puddle near the parapet that never drains",
            "impact": "The bedroom ceiling is stained and we put buckets out every monsoon",
            "ask": "Need the leak found and the roof waterproofed properly",
            "tags": ["flat-roof-leak", "app-membrane", "liquid-waterproofing"],
        },
        {
            "titles": ["tin roof leaking", "CGI sheet replace", "roof sheet loose"],
            "symptom": "Two CGI sheets on the shed roof have corroded through and one has come loose and lifts in the wind",
            "impact": "Rain is getting into the store room and the noise is awful",
            "ask": "Want the bad sheets replaced and the ridge properly sealed",
            "tags": ["cgi-sheet-roofing", "ridge-and-flashing"],
        },
        {
            "titles": ["gutter overflowing", "downpipe broken", "rainwater pipe leaking"],
            "symptom": "The gutter overflows at one joint during every downpour and the downpipe has cracked, so water runs down the outside wall",
            "impact": "That wall is now permanently damp and the paint is peeling",
            "ask": "Need the gutter refixed with proper slope and the downpipe replaced",
            "tags": ["gutter-install", "downpipe-repair"],
        },
    ],
    "locksmith": [
        {
            "titles": ["locked out", "key lost urgent", "door locked cannot open"],
            "symptom": "I have lost the only key to my flat and I am standing outside; the lock is a standard mortise type",
            "impact": "Locked out with a small child and it is getting dark",
            "ask": "Need someone to open it without breaking the door and fit a new lock",
            "tags": ["non-destructive-entry", "24hr-emergency", "lock-picking"],
        },
        {
            "titles": ["safe locked", "almari safe not opening", "safe combination lost"],
            "symptom": "The office safe will not open; the dial turns but the handle does not release and the previous manager left without passing on the combination",
            "impact": "Documents and cash are locked inside and we need them for an audit",
            "ask": "Need it opened without destroying the safe and the combination reset",
            "tags": ["safe-opening", "master-key-system"],
        },
        {
            "titles": ["digital lock install", "smart lock fitting", "fingerprint lock"],
            "symptom": "We want to replace the main door lock with a fingerprint and PIN lock, and give separate access codes to family and the cleaner",
            "impact": "Too many keys in circulation after we changed tenants",
            "ask": "Want a digital lock supplied and fitted with codes set up",
            "tags": ["digital-door-lock", "biometric-lock"],
        },
    ],
    "welding": [
        {
            "titles": ["gate repair", "main gate broken", "gate not closing"],
            "symptom": "The steel main gate has sagged so it drags on the ground and will not latch, and one hinge weld has cracked right through",
            "impact": "The gate cannot be locked and it screeches loudly",
            "ask": "Need the hinge rewelded and the gate straightened so it closes",
            "tags": ["gate-fabrication", "mig-welding"],
        },
        {
            "titles": ["window grill needed", "security grill fitting", "balcony railing"],
            "symptom": "Need security grilles made and fitted to five ground floor windows, and a railing for the first floor balcony which currently has nothing",
            "impact": "There was a break-in attempt on the street last month",
            "ask": "Want them measured, fabricated and installed painted",
            "tags": ["window-grille", "ms-railing"],
        },
        {
            "titles": ["steel stairs needed", "spiral staircase", "staircase fabrication"],
            "symptom": "We need a steel staircase from the second floor to the roof terrace, currently reached only by a wooden ladder",
            "impact": "The ladder is dangerous for my parents",
            "ask": "Want a proper steel staircase designed, fabricated and installed",
            "tags": ["staircase-fabrication", "structural-steel"],
        },
    ],
    "pest-control": [
        {
            "titles": ["termite problem", "dhamira in wood", "termites in furniture"],
            "symptom": "There are mud tracks running up the wall behind the wardrobe and the wooden door frame sounds hollow and crumbles when pressed",
            "impact": "They have already destroyed one bookshelf",
            "ask": "Need the termites treated at the source, not just sprayed",
            "tags": ["anti-termite-treatment", "wood-borer"],
        },
        {
            "titles": ["cockroach problem kitchen", "rats in house", "bed bugs"],
            "symptom": "Cockroaches come out of the kitchen drain every night and we have started hearing rats in the ceiling; one bedroom also has bed bugs",
            "impact": "Nobody is sleeping properly and it is embarrassing with guests",
            "ask": "Want all three dealt with, safely since we have a cat and a toddler",
            "tags": ["cockroach-gel-treatment", "rodent-proofing", "bed-bug-treatment"],
        },
    ],
    "landscaping": [
        {
            "titles": ["garden maintenance", "garden overgrown", "need gardener"],
            "symptom": "The garden has been neglected for a year; grass is knee high, hedges are wild and several plants have died",
            "impact": "Snakes have been seen in the long grass",
            "ask": "Want it cleared, cut back and replanted, then maintained monthly",
            "tags": ["garden-maintenance", "seasonal-planting"],
        },
        {
            "titles": ["tree cutting", "big tree dangerous", "tree branch over roof"],
            "symptom": "A large tree at the edge of the plot leans towards the house and heavy branches now overhang the roof and the neighbour's wall",
            "impact": "I am afraid it will come down on the roof in a storm",
            "ask": "Need it safely pruned back or taken down in sections",
            "tags": ["tree-pruning", "tree-felling"],
        },
        {
            "titles": ["lawn and watering system", "sprinkler setup", "grass laying"],
            "symptom": "We want a proper lawn laid in the front garden with an automatic watering system, since hand watering is being forgotten",
            "impact": "The last lawn died from irregular watering",
            "ask": "Want the ground prepared, turf laid and irrigation installed on a timer",
            "tags": ["lawn-laying", "drip-irrigation", "sprinkler-system"],
        },
    ],
    "solar": [
        {
            "titles": ["solar panel install", "want solar power", "rooftop solar"],
            "symptom": "We want rooftop solar for a three-storey house with net metering, and the roof is partly shaded by a water tank in the afternoon",
            "impact": "Electricity bills have roughly doubled",
            "ask": "Need a system designed around the shading, installed and connected for net metering",
            "tags": ["rooftop-pv-install", "net-metering", "string-inverter"],
        },
        {
            "titles": ["solar output low", "solar not working properly", "panels dirty"],
            "symptom": "Our two-year-old solar array is generating noticeably less than it used to and the inverter logs an occasional fault in the afternoon",
            "impact": "We are drawing from the grid again despite paying for solar",
            "ask": "Want the array tested to find which part is underperforming",
            "tags": ["pv-fault-diagnosis", "panel-cleaning"],
        },
    ],
    "security-systems": [
        {
            "titles": ["CCTV install", "cctv camera fitting", "security camera needed"],
            "symptom": "We want six cameras covering the gate, parking and stairwell, with recording and the ability to view from a phone while travelling",
            "impact": "There have been thefts from the parking area twice",
            "ask": "Need cameras and a recorder installed and remote viewing set up securely",
            "tags": ["ip-cctv-install", "nvr-configuration", "remote-viewing-setup"],
        },
        {
            "titles": ["video door phone", "intercom not working", "gate automation"],
            "symptom": "The video door phone shows a blank screen and the buzzer does not release the gate, and we would like the gate motorised",
            "impact": "Someone has to walk down three floors every time the bell rings",
            "ask": "Want the intercom repaired and an automatic gate opener fitted",
            "tags": ["video-door-phone", "automatic-gate"],
        },
    ],
    "networking": [
        {
            "titles": ["wifi not reaching", "internet slow upstairs", "wifi dead zone"],
            "symptom": "The router is on the ground floor and there is almost no signal on the second floor or in the back bedroom, and video calls drop constantly",
            "impact": "Both of us work from home and calls keep failing",
            "ask": "Want proper cabling and access points so the whole house has coverage",
            "tags": ["structured-cabling", "wifi-mesh-setup"],
        },
        {
            "titles": ["office network setup", "LAN cabling office", "internet cabling"],
            "symptom": "New office with twelve desks needs wired network points, a small rack, and the fibre line brought in from the street box",
            "impact": "Staff move in at the start of next month",
            "ask": "Need the cabling installed, terminated and tested",
            "tags": ["structured-cabling", "fibre-splicing"],
        },
    ],
    "water-treatment": [
        {
            "titles": ["water tastes bad", "RO plant needed", "hard water problem"],
            "symptom": "The tap water leaves white scale on everything, tastes metallic, and stains the bathroom fittings brown",
            "impact": "We are buying jar water for drinking which is expensive",
            "ask": "Want the water tested and a treatment system installed for the whole house",
            "tags": ["ro-plant-install", "water-softener", "iron-removal-filter"],
        },
    ],
    "generator": [
        {
            "titles": ["generator not starting", "genset service", "generator problem"],
            "symptom": "The building's standby diesel generator cranks but will not start, and when it did run last month it produced black smoke and surged",
            "impact": "The building has no backup power at all right now",
            "ask": "Need it serviced and the changeover panel checked",
            "tags": ["diesel-genset-service", "amf-panel"],
        },
    ],
    "flooring": [
        {
            "titles": ["wooden flooring install", "laminate floor fitting", "new floor needed"],
            "symptom": "We want laminate or engineered wood laid in two bedrooms over the existing cement floor, which is slightly uneven in one corner",
            "impact": "Renovating before moving in next month",
            "ask": "Need the floor levelled and the new flooring supplied and laid",
            "tags": ["laminate-flooring", "engineered-wood", "self-levelling-screed"],
        },
        {
            "titles": ["epoxy floor workshop", "garage floor coating", "clinic flooring"],
            "symptom": "The clinic floor is bare concrete that stains easily and cannot be cleaned to a hygienic standard, with a slight slope towards the door",
            "impact": "We have an inspection for licensing coming up",
            "ask": "Want a seamless coated floor that can be properly disinfected",
            "tags": ["epoxy-floor-coating", "self-levelling-screed"],
        },
    ],
    "glazing": [
        {
            "titles": ["glass broken", "window glass replace", "mirror fitting"],
            "symptom": "A large window pane cracked across the middle and needs replacing, and we also want a full-length mirror fitted in the bedroom",
            "impact": "The cracked pane is taped up and letting in cold air",
            "ask": "Need the glass measured, supplied and fitted safely",
            "tags": ["toughened-glass", "mirror-fitting"],
        },
        {
            "titles": ["shower glass fitting", "shower cabin", "bathroom partition glass"],
            "symptom": "We want a frameless glass shower enclosure in the master bathroom where currently a curtain is used and water goes everywhere",
            "impact": "The bathroom floor is soaked after every shower",
            "ask": "Want it templated, made and installed",
            "tags": ["shower-enclosure", "toughened-glass"],
        },
        {
            "titles": ["uPVC windows", "window replacement", "noise from window"],
            "symptom": "The old aluminium windows facing the main road rattle, leak during rain, and traffic noise comes straight through",
            "impact": "Impossible to sleep with the road noise",
            "ask": "Want them replaced with double glazed uPVC units",
            "tags": ["upvc-window-install", "double-glazing"],
        },
    ],
    "interior-finishing": [
        {
            "titles": ["false ceiling", "ceiling design needed", "POP ceiling work"],
            "symptom": "We want a gypsum false ceiling in the living room with concealed lighting, and the existing ceiling has exposed conduit and an uneven surface",
            "impact": "Doing up the flat before a family function",
            "ask": "Need it designed and installed with the electrician's lighting coordinated",
            "tags": ["gypsum-false-ceiling", "pop-cornice"],
        },
        {
            "titles": ["partition wall needed", "divide room", "drywall partition"],
            "symptom": "We need to split one large bedroom into two smaller rooms with a partition, including a door and a socket on each side",
            "impact": "Two children now need separate rooms",
            "ask": "Want a partition built, finished and ready for paint",
            "tags": ["drywall-partition", "gypsum-false-ceiling"],
        },
    ],
    # ---- custom / rarer categories (is_custom_category equivalent) --------
    "seismic-retrofit": [
        {
            "titles": ["earthquake safety check", "building retrofit", "house strengthening"],
            "symptom": "Our four-storey house was built before the current code with a very open ground floor for parking, and cracks appeared at the column tops after the last tremor",
            "impact": "We are genuinely worried about the next big earthquake",
            "ask": "Want the building assessed for seismic vulnerability and strengthened where needed",
            "tags": ["seismic-vulnerability-survey", "jacketing-and-confinement", "wall-stitching"],
        },
    ],
    "swimming-pool": [
        {
            "titles": ["pool water green", "swimming pool cleaning", "pool pump problem"],
            "symptom": "The pool water has turned green and cloudy, the filter pressure reads high, and the level drops a few centimetres a day",
            "impact": "Guests at the guesthouse cannot use the pool",
            "ask": "Need the water balanced, the filter serviced and the leak traced",
            "tags": ["water-chemistry-balancing", "pool-filtration-plant", "pool-leak-detection"],
        },
    ],
    "septic-soakpit": [
        {
            "titles": ["septic tank full", "soak pit not draining", "septic overflow"],
            "symptom": "The septic tank is overflowing at the inspection cover and the soakpit no longer drains, so waste water is surfacing in the back yard",
            "impact": "The smell is unbearable and it is right beside the kitchen window",
            "ask": "Need the tank emptied and the soakpit rebuilt if it has silted up",
            "tags": ["septic-tank-desludging", "soakpit-construction", "drain-field-repair"],
        },
    ],
    "soundproofing": [
        {
            "titles": ["soundproofing room", "noise from neighbour", "studio acoustic treatment"],
            "symptom": "Noise from the neighbouring flat and the street comes straight through the shared wall, and my home studio recordings pick up a bad echo",
            "impact": "I cannot record client work from home",
            "ask": "Want the wall soundproofed and the room acoustically treated",
            "tags": ["acoustic-panel-install", "resilient-channel-isolation", "impact-noise-treatment"],
        },
    ],
    "chimney-flue": [
        {
            "titles": ["chimney smoke inside", "fireplace not drawing", "chimney cleaning"],
            "symptom": "Smoke blows back into the room when the fireplace is lit and there is a smell of soot upstairs even when it is not in use",
            "impact": "We stopped using the fireplace entirely because of the smoke",
            "ask": "Need the chimney swept, inspected and relined if it is leaking",
            "tags": ["chimney-sweeping", "flue-relining", "cowl-and-capping"],
        },
    ],
    "curtains-blinds": [
        {
            "titles": ["curtain fitting", "blinds installation", "curtain rod fixing"],
            "symptom": "We need curtain tracks and blinds fitted in five rooms; the previous rods pulled straight out of the plasterboard wall",
            "impact": "No privacy in the front-facing rooms",
            "ask": "Want tracks fixed properly this time and blinds cut to fit the windows",
            "tags": ["curtain-track-fitting", "roller-and-venetian-blinds", "motorised-shading"],
        },
    ],
    "furniture-restoration": [
        {
            "titles": ["old furniture repair", "antique table restore", "grandfather chair repair"],
            "symptom": "An inherited wooden table has lifting veneer on the top, wobbly legs where the joints have loosened, and water rings in the finish",
            "impact": "It is a family piece and I do not want it ruined by a rough repair",
            "ask": "Looking for someone who restores antiques properly rather than just repainting",
            "tags": ["veneer-repair", "french-polishing", "structural-joint-reglue"],
        },
    ],
    "elevator": [
        {
            "titles": ["lift not working", "elevator stuck", "lift door problem"],
            "symptom": "The building lift stops between floors intermittently and the doors sometimes close on people before reopening",
            "impact": "Elderly residents on the fifth floor are effectively trapped upstairs",
            "ask": "Need it serviced and the safety systems tested urgently",
            "tags": ["lift-servicing", "door-operator-alignment", "overspeed-governor-testing"],
        },
    ],
    "home-theatre": [
        {
            "titles": ["home theatre setup", "projector installation", "surround sound fitting"],
            "symptom": "We have bought a projector and a surround speaker set but need it installed properly, with cables hidden and the sound balanced",
            "impact": "Equipment has been sitting in boxes for a month",
            "ask": "Want it mounted, wired in-wall and calibrated",
            "tags": ["projector-installation", "surround-sound-calibration", "multi-room-audio"],
        },
    ],
    "bamboo-cane": [
        {
            "titles": ["bamboo work", "cane chair repair", "bamboo hut needed"],
            "symptom": "We want a bamboo shade structure built on the terrace, and four cane dining chairs have sagging, broken seat weaves",
            "impact": "Opening a small cafe on the terrace next season",
            "ask": "Need the structure built with treated bamboo and the chair seats rewoven",
            "tags": ["bamboo-structure-building", "cane-seat-weaving", "bamboo-treatment"],
        },
    ],
}

# Non-service job requests. Your live table has these with is_job_request=false
# and categories=null — event management, drivers, etc. Reproduced so the
# matching path is exercised against rows it must correctly ignore.
NON_SERVICE = [
    {
        "titles": ["event management", "need event help", "party organiser needed"],
        "symptom": "We need help organising a 150-guest engagement function including decoration, seating and catering coordination",
        "impact": "The date is fixed and nothing is arranged yet",
        "ask": "Looking for an event coordinator, not a repair service",
    },
    {
        "titles": ["driver needed", "need a driver", "driver for goods"],
        "symptom": "Need a driver with a licence to move household goods across the valley over two days",
        "impact": "Handing the old flat back at the end of the month",
        "ask": "Looking for a driver with a small truck",
    },
    {
        "titles": ["AUTOMOTIVE", "car problem", "bike servicing"],
        "symptom": "The car makes a grinding noise when braking and pulls to the left",
        "impact": "I do not feel safe driving the children in it",
        "ask": "Need a mechanic, ideally one who can come to the house",
    },
    {
        "titles": ["MOVING", "shifting house", "packers and movers"],
        "symptom": "Standard two-bedroom flat move within Lalitpur, including packing, a fridge and a washing machine",
        "impact": "Lease ends this month",
        "ask": "Want a moving team with a vehicle and packing material",
    },
    {
        "titles": ["tuition teacher", "home tutor needed", "maths tuition"],
        "symptom": "Need a tutor for a class 10 student in maths and science, twice a week at home",
        "impact": "Board exams are in a few months",
        "ask": "Looking for a tutor, not a tradesperson",
    },
]

# Same clusters as workers_seed.csv, so the 20 km filter behaves comparably.
CLUSTERS = [
    ("Thamel, Kathmandu",              27.7154, 85.3123, 1.6),
    ("Baneshwor, Kathmandu",           27.6893, 85.3400, 2.0),
    ("Kalanki, Kathmandu",             27.6939, 85.2810, 2.0),
    ("Chabahil, Kathmandu",            27.7172, 85.3462, 1.8),
    ("Balaju, Kathmandu",              27.7357, 85.3020, 1.8),
    ("Budhanilkantha, Kathmandu",      27.7789, 85.3620, 2.4),
    ("Patan, Lalitpur",                27.6766, 85.3240, 2.0),
    ("Jawalakhel, Lalitpur",           27.6710, 85.3120, 1.6),
    ("Satdobato, Lalitpur",            27.6580, 85.3260, 2.0),
    ("Bhaktapur Durbar Square Area",   27.6710, 85.4298, 2.4),
    ("Suryabinayak, Bhaktapur",        27.6600, 85.4270, 2.2),
    ("Madhyapur Thimi",                27.6820, 85.3850, 2.0),
    ("Kirtipur",                       27.6790, 85.2774, 2.0),
    ("Tokha",                          27.7620, 85.3290, 2.2),
    ("Gokarneshwor",                   27.7480, 85.3900, 2.6),
    ("Sitapaila, Kathmandu",           27.7130, 85.2760, 1.8),
    ("Koteshwor, Kathmandu",           27.6780, 85.3490, 1.8),
    ("Dhapasi, Kathmandu",             27.7480, 85.3220, 1.8),
    ("Imadol, Lalitpur",               27.6620, 85.3420, 1.8),
    ("Godawari, Lalitpur",             27.5960, 85.3810, 3.0),
]

LANDMARKS = [
    "Newa Decor", "hotel Rupakot", "Pragya Sadan", "SASA Health Care",
    "Balumari Marg", "pure land tower", "Sunrise Apartment", "Gyan Jyoti School",
    "Annapurna Complex", "Himalaya Height", "Buddha Chowk", "Shanti Bhawan",
    "Nirvana Garden", "City Centre back gate", "Milan Tole", "Krishna Mandir side",
]

CONTACT_NAMES = [
    "Anup G", "Sita Sharma", "Ram Bahadur", "Client1", "Bikash Thapa",
    "Sunita Maharjan", "Deepak Shrestha", "Nirmala Rai", "Pemba Sherpa",
    "Kiran Adhikari", "Gita Tamang", "Rajesh Karki", "Manisha Gurung",
    "Suresh Basnet", "Laxmi Devkota", "Hari Prasad", "Anjali Joshi",
    "Binod Chaudhary", "Sarita KC", "Prakash Lama",
]

RELATION_NOTES = [
    "", "", "", "",
    " Please call my tenant on the number given, he is at the property.",
    " My mother is at home during the day, she does not speak much English.",
    " I am abroad, please coordinate with the caretaker on this number.",
    " Call before coming, the gate is usually locked.",
    " Best to come after 5pm when someone is home.",
]

URGENCY_PREFIX = {
    "express": [
        "Urgent. ", "Need this today if possible. ", "As soon as possible please. ",
        "This is an emergency. ",
    ],
    "regular": ["", "", "", "No great rush. ", "Sometime this week is fine. "],
}

# `mode = express` is the customer paying for a faster dispatch, which they may
# well do for a planned renovation. But the strongest wording only makes sense
# for a fault that is actively causing harm — "This is an emergency" on a
# request to lay new laminate flooring reads as generated text, and that kind
# of tell is exactly what makes seed data useless for a demo. Trades not listed
# here get the softer express openers only.
EMERGENCY_TAGS = {
    "plumbing", "electrical", "locksmith", "hvac", "roofing", "appliance-repair",
    "generator", "elevator", "septic-soakpit", "pest-control", "glazing",
    "security-systems", "masonry",
}
SOFT_EXPRESS = ["Urgent. ", "As soon as possible please. ", "Need this done quickly. ",
                "Would like this sorted this week. "]

# --------------------------------------------------------------------------
# Trade-scoped detail sentences. Templates alone give ~65 distinct texts for
# 220 rows, so each would repeat 3-4 times verbatim — and duplicate text means
# duplicate embeddings, which flattens the cosine-distance spread the Sigmoid
# score depends on. These are phrased to apply to any job within the trade, so
# they add real variation without producing nonsense combinations.
# --------------------------------------------------------------------------
EXTRAS: dict[str, list[str]] = {
    "plumbing": [
        "The pipework is the old galvanised type, not PVC",
        "The shut-off valve is in the parking area if you need it",
        "A previous plumber patched this about six months ago and it has come back",
        "Water supply here is from the municipal line plus an underground tank",
        "The bathroom is on the second floor with tiled walls",
    ],
    "electrical": [
        "The distribution board is inside the stairwell cupboard",
        "Wiring is concealed in conduit so I do not know how it is routed",
        "We are on a 15 amp single-phase connection from NEA",
        "An electrician looked at it last year and said the load was too high",
        "There is an inverter in the circuit as well, in case that matters",
    ],
    "carpentry": [
        "The existing woodwork is sal wood, if you need to match it",
        "Room measurements are roughly 11 by 13 feet",
        "The last carpenter left the job unfinished and I do not want to call him back",
        "I would prefer a matte finish rather than high gloss",
        "The wall behind is plasterboard, not brick, so fixings may need care",
    ],
    "painting": [
        "Ceiling height is about nine feet so scaffolding may be needed",
        "The current paint is a distemper, I am not sure if it needs stripping",
        "We would like to keep the existing shade if it can be matched",
        "Furniture can be moved into the next room but not out of the house",
        "There is old wallpaper on one wall that would have to come off first",
    ],
    "masonry": [
        "The building is load bearing brick, about twenty-five years old",
        "There is a similar crack on the outside face of the same wall",
        "Access for a mixer is tight, the lane is barely wide enough for a bike",
        "We had this patched two monsoons ago and it opened up again",
        "I can arrange sand and cement locally if that is cheaper",
    ],
    "hvac": [
        "The unit is a 1.5 ton split, about four years old, out of warranty",
        "Outdoor unit sits on the rear terrace with a long pipe run",
        "It was last serviced roughly eighteen months ago",
        "The drain pipe also drips onto the neighbour's side",
        "The room gets full afternoon sun which may be part of the problem",
    ],
    "appliance-repair": [
        "It is a Samsung unit, roughly five years old, warranty finished",
        "It started making the noise gradually over about a month",
        "A technician came once and said a part had to be ordered, then never returned",
        "There is a power fluctuation problem in this area which may have damaged it",
        "I still have the original bill and manual if that helps",
    ],
    "cleaning": [
        "It is a three-bedroom flat, roughly 1200 square feet",
        "There is no lift, it is on the fourth floor",
        "Water supply is available but you would need to bring your own equipment",
        "We would like this done on a Saturday if possible",
        "There are two cats in the house so no strong chemicals please",
    ],
    "tiling": [
        "The tiles are 2 by 2 feet vitrified, and I have about ten spares left over",
        "The area is roughly 60 square feet",
        "I would rather not have the whole floor pulled up if it can be avoided",
        "The original tiling was done four years ago by the builder",
        "There is underfloor plumbing in that area so please be careful",
    ],
    "roofing": [
        "It is a flat RCC roof with a brick coba layer on top",
        "The problem only shows during heavy rain, not light drizzle",
        "The roof is also used for drying clothes so the finish needs to take foot traffic",
        "A waterproofing coat was applied about three years ago",
        "Access to the roof is by an external staircase",
    ],
    "locksmith": [
        "The lock is a Godrej mortise type",
        "The door itself is solid wood and I do not want it damaged",
        "There is a second lock on the same door that still works",
        "I have the original key for a different door of the same set",
        "I can show ownership documents if you need them before opening it",
    ],
    "welding": [
        "The existing metal is mild steel square tube, about 25mm",
        "Power is available at the site for your machine",
        "I want it primed and painted black to match the rest",
        "Total measurement is roughly 12 feet by 5 feet",
        "The previous welding was done badly and has cracked at the same joint before",
    ],
    "pest-control": [
        "We have a small child in the house so treatment must be safe",
        "This is the second time in two years, the last treatment did not hold",
        "The house has a lot of built-in wooden furniture",
        "There is a garden on two sides which may be where they are coming from",
        "We can vacate the house for a day if the treatment requires it",
    ],
    "landscaping": [
        "The garden is roughly 1800 square feet on two levels",
        "There is a water tap in the garden but no existing irrigation",
        "The soil is heavy clay and does not drain well",
        "We would like mostly local plants that survive without much care",
        "Waste will need to be carted away, there is no space to compost",
    ],
    "solar": [
        "Our average monthly consumption is around 300 units",
        "The roof is flat RCC with space for roughly ten panels",
        "We already have net metering approved from NEA",
        "The existing system is 3 kW with a string inverter",
        "There is a water tank on the roof that shades part of the area after 3pm",
    ],
    "security-systems": [
        "The building has four floors plus a basement parking",
        "Existing cabling from an old analogue system may be reusable",
        "There is a broadband connection in the ground floor office",
        "We want the recorder kept somewhere it cannot easily be taken",
        "Two of the camera positions are outdoors and exposed to rain",
    ],
    "networking": [
        "The house is three floors with concrete slabs between them",
        "The ISP router is a WorldLink unit in the ground floor hall",
        "We would prefer cables run in conduit rather than surface clipped",
        "About fifteen devices connect at once in the evening",
        "There is an existing conduit from the ground to first floor that may be usable",
    ],
    "water-treatment": [
        "We have both a boring and a municipal supply feeding the same tank",
        "A lab test last year showed high iron and hardness",
        "There is space for a plant beside the underground tank",
        "Daily consumption is roughly 1000 litres for two families",
        "We currently use a small RO unit in the kitchen only",
    ],
    "generator": [
        "It is a 25 kVA Kirloskar set, about eight years old",
        "There is an AMF panel but I am not sure it is working",
        "Diesel was last changed over a year ago and may have gone bad",
        "It powers the lift and common area lighting for eleven flats",
        "The generator room is in the basement with limited ventilation",
    ],
    "flooring": [
        "Total area is roughly 320 square feet across two rooms",
        "The existing surface is cement plaster, not tile",
        "There is a bathroom adjoining so a moisture barrier may be needed",
        "We want a mid-range finish, nothing imported",
        "Skirting also needs to be done to match",
    ],
    "glazing": [
        "The opening is roughly 5 feet by 4 feet",
        "It is on the third floor facing the road, so lifting glass up will be awkward",
        "The frame is aluminium and appears to be in reasonable condition",
        "We would like toughened glass this time since children play in that room",
        "There are four similar windows if the price works out for all of them",
    ],
    "interior-finishing": [
        "The room is about 14 by 16 feet with a nine foot ceiling",
        "We have a design reference photo I can share on WhatsApp",
        "Electrical work for the concealed lighting is not done yet",
        "We want gypsum rather than POP, for the finish",
        "The existing ceiling has exposed beams that we would like hidden",
    ],
    "seismic-retrofit": [
        "The house was built in 2062 BS without an engineer's drawing",
        "We have the original structural drawing, though it is hand drawn",
        "The ground floor is entirely open for parking with no infill walls",
        "Two neighbouring houses are attached on either side",
        "We would need a written engineer's report for the bank as well",
    ],
    "swimming-pool": [
        "The pool is roughly 8 by 4 metres and 1.5 metres deep",
        "The filtration plant room is behind the changing rooms",
        "It has not been drained fully in over two years",
        "We run it for guests so downtime needs to be minimal",
        "The pump was replaced last season but the sand filter is original",
    ],
    "septic-soakpit": [
        "The tank is roughly 8 by 5 feet, brick built, about fifteen years old",
        "There is no vehicle access to the back so hoses will need to run through the side gate",
        "It was last emptied about four years ago",
        "The soakpit is right beside the boundary wall so space is limited",
        "Six people live in the house full time",
    ],
    "soundproofing": [
        "The shared wall is a single brick partition, about 5 inches",
        "The room is roughly 12 by 10 feet with a wooden floor",
        "I record voice work so I need a low noise floor, not just less noise",
        "There is a window facing the road that is probably the weakest point",
        "We are renting, so nothing that permanently damages the structure",
    ],
    "chimney-flue": [
        "It is a masonry chimney serving a wood-burning stove",
        "The flue runs up through two floors to the roof",
        "It has not been swept in at least five years",
        "There is no cowl on top and birds have nested in it before",
        "The stove itself was installed by the previous owner",
    ],
    "curtains-blinds": [
        "The windows vary in size, the largest is about 7 feet wide",
        "Walls are drywall in three of the rooms and brick in the others",
        "We would like blackout fabric in the bedrooms",
        "One of the rooms has a curved bay window",
        "We can buy the fabric ourselves if you only do the fitting",
    ],
    "furniture-restoration": [
        "The piece is teak, at least fifty years old",
        "It was previously repaired with modern glue which has failed",
        "I would like the original patina kept rather than a fresh look",
        "There are three other pieces in the set in similar condition",
        "It is heavy and would be difficult to move out of the house",
    ],
    "elevator": [
        "It is a 6-passenger Kone lift, installed roughly nine years ago",
        "The annual maintenance contract lapsed last year",
        "The machine room is on the roof",
        "It serves seven floors including the basement",
        "The problem is worse when the building is busy in the morning",
    ],
    "home-theatre": [
        "The room is about 15 by 18 feet with a projector throw of roughly 4 metres",
        "It is a 5.1 set with a separate subwoofer",
        "We want the cables inside the wall, not in trunking",
        "There is a false ceiling already in place",
        "Power points are only on one side of the room at present",
    ],
    "bamboo-cane": [
        "We want treated bamboo since the last structure was eaten by borers",
        "The terrace area is roughly 20 by 15 feet",
        "It needs to survive the monsoon without a roof over it",
        "The chairs are old family pieces with cane seats",
        "We can source bamboo locally if you advise on the type",
    ],
}

# Applies to any job. Kept generic so it never contradicts trade detail.
GENERIC_CONTEXT = [
    "It is a rented flat and the landlord has agreed to the work",
    "We are on the top floor with no lift",
    "Parking for a vehicle is available right outside",
    "The lane is narrow so a large vehicle will not reach the gate",
    "Someone is at home all day so timing is flexible",
    "The house is locked during office hours on weekdays",
    "This is a commercial premises so work would have to be after closing",
    "There is another small job at the same property we could discuss together",
]

CLOSERS = [
    "", "", "", "",
    "Please give me a rough estimate before starting.",
    "I would like a written quote first.",
    "Let me know when you could visit to look at it.",
    "Please bring whatever materials are needed, I will pay for them.",
    "I have a budget in mind so tell me if it is unrealistic.",
    "Photos are attached.",
    "Happy to pay a visit charge for an inspection.",
]

ATTACH_BASE = "https://res.cloudinary.com/handyman-demo/image/upload"


def jitter(lat: float, lon: float, spread_km: float) -> tuple[float, float]:
    dlat = rng.gauss(0.0, spread_km / 2.0)
    dlon = rng.gauss(0.0, spread_km / 2.0)
    return (
        round(lat + dlat / 110.574, 6),
        round(lon + dlon / (111.320 * math.cos(math.radians(lat))), 6),
    )


def phone() -> str:
    p = rng.choice(["984", "985", "986", "980", "981", "982", "974", "975"])
    return f"+977 {p}{rng.randint(1000000, 9999999)}"


def address(area: str) -> str:
    return (
        f"{rng.choice(LANDMARKS)}, Ward {rng.randint(1, 32)}, {area}, "
        f"{rng.choice(['बागमती प्रदेश', 'Bagmati Province'])}, "
        f"{rng.randint(44600, 44900)}, Nepal"
    )


def attachments(mode: str) -> list[dict]:
    """Customers attach photos more often for visible faults and urgent jobs."""
    n = rng.choices([0, 1, 2, 3], weights=[45, 28, 19, 8], k=1)[0]
    if mode == "express" and n == 0 and rng.random() < 0.3:
        n = 1
    out = []
    for _ in range(n):
        kind = rng.choices(["image", "video"], weights=[88, 12], k=1)[0]
        ext = "jpg" if kind == "image" else "mp4"
        out.append({
            "url": f"{ATTACH_BASE}/v{rng.randint(1700000000, 1799999999)}/"
                   f"job_{rng.randint(100000, 999999)}.{ext}",
            "type": kind,
        })
    return out


def build_description(t: dict, mode: str, area: str, tag: str | None) -> str:
    """
    Assemble a customer-voice description in four layers:

      symptom  (always)  - what they observe
      impact   (usually) - why it matters, drives the urgency signal
      ask      (always)  - what they want done
      detail   (1-2)     - trade-scoped or generic context

    Sentence order is shuffled within the middle of the text so no two rows
    from the same template read identically. Without this layer, 65 templates
    across 220 rows would produce ~13 verbatim duplicates, and duplicate text
    means duplicate embeddings — which collapses the cosine-distance spread
    the Sigmoid score needs in order to rank anything.
    """
    lead = t["symptom"].rstrip(".") + "."
    middle: list[str] = []
    if rng.random() < 0.80:
        middle.append(t["impact"].rstrip(".") + ".")

    pool = list(EXTRAS.get(tag, [])) if tag else []
    n_detail = rng.choices([1, 2, 3], weights=[40, 45, 15], k=1)[0]
    picks: list[str] = []
    if pool:
        picks += rng.sample(pool, k=min(n_detail, len(pool)))
    if not pool or rng.random() < 0.45:
        picks.append(rng.choice(GENERIC_CONTEXT))
    middle += [p.rstrip(".") + "." for p in picks]

    if rng.random() < 0.25:
        middle.append(f"Property is in {area}.")
    rng.shuffle(middle)

    tail = [t["ask"].rstrip(".") + "."]
    closer = rng.choice(CLOSERS)
    if closer:
        tail.append(closer)

    body = " ".join([lead] + middle + tail)
    if mode == "express" and tag not in EMERGENCY_TAGS:
        return rng.choice(SOFT_EXPRESS) + body
    return rng.choice(URGENCY_PREFIX[mode]) + body


HEADER = [
    "id", "customer_id", "booking_chat_id", "worker_id", "title", "description",
    "status", "is_job_request", "categories", "contact_name", "contact_phone",
    "mode", "attachments", "address_text", "latitude", "longitude", "location",
    "description_vector", "created_at", "updated_at",
]

NULL = None


def load_worker_pool() -> tuple[dict[str, list[dict]], list[int]]:
    """
    Read workers_seed.csv so jobs can be assigned to a worker who actually
    does that trade. Assigning a plumbing job to an electrician would make
    the seed data self-inconsistent and useless for testing the match path.
    """
    by_tag: dict[str, list[dict]] = {}
    all_uids: list[int] = []
    if not WORKERS_CSV.exists():
        return by_tag, all_uids
    with WORKERS_CSV.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            all_uids.append(int(r["user_id"]))
            if (r["is_complete"] == "true" and r["scenario_passed"] == "true"
                    and r["is_rejected"] == "false"):
                by_tag.setdefault(r["category_tag"], []).append({
                    "user_id": int(r["user_id"]),
                    "lat": float(r["latitude"]),
                    "lon": float(r["longitude"]),
                })
    return by_tag, all_uids


def haversine_km(a: float, b: float, c: float, d: float) -> float:
    R = 6371.0088
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = p2 - p1, math.radians(d - b)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def make_rows(n: int) -> list[list]:
    workers_by_tag, worker_uids = load_worker_pool()
    max_worker_uid = max(worker_uids) if worker_uids else 968

    # Customer user ids live ABOVE the worker ids so the two seeds never
    # collide on users.id. Adjust CUSTOMER_ID_BASE if your users table differs.
    CUSTOMER_ID_BASE = max_worker_uid + 1
    n_customers = 85
    customer_ids = list(range(CUSTOMER_ID_BASE, CUSTOMER_ID_BASE + n_customers))

    tags = list(TEMPLATES.keys())
    common = {"plumbing", "electrical", "carpentry", "painting", "masonry",
              "hvac", "appliance-repair", "cleaning", "tiling"}
    weights = [10 if t in common else 4 for t in tags]

    rows: list[list] = []
    booking_chat_id = 1
    now = datetime(2026, 8, 4, 10, 30, 0)

    for i in range(1, n + 1):
        # ~7% are non-service requests (is_job_request = false, categories null)
        is_service = rng.random() >= 0.07

        mode = rng.choices([m for m, _ in MODES], weights=[w for _, w in MODES], k=1)[0]
        area, clat, clon, spread = rng.choice(CLUSTERS)
        lat, lon = jitter(clat, clon, spread)
        customer_id = rng.choice(customer_ids)

        if is_service:
            tag = rng.choices(tags, weights=weights, k=1)[0]
            tpl = rng.choice(TEMPLATES[tag])
            title = rng.choice(tpl["titles"])
            desc = build_description(tpl, mode, area, tag)
            # categories JSONB mirrors the shape in your live table
            cats = [{
                "tags": tpl["tags"],
                "category": tag,
                "is_custom_category": tag in {
                    "seismic-retrofit", "swimming-pool", "septic-soakpit",
                    "soundproofing", "chimney-flue", "curtains-blinds",
                    "furniture-restoration", "elevator", "home-theatre",
                    "bamboo-cane",
                },
            }]
        else:
            tag = None
            tpl = rng.choice(NON_SERVICE)
            title = rng.choice(tpl["titles"])
            desc = build_description(tpl, mode, area, None)
            # Empty list, NOT NULL. Your live table has NULL here on the
            # equivalent rows, but that data predates the constraint — the
            # actual DDL is `categories jsonb NOT NULL`, so a NULL would be
            # rejected on load. `[]` is the correct empty value and still
            # reads as "no trade" to the matcher.
            cats = []

        status = rng.choices(
            [s for s, _ in STATUS_WEIGHTS], weights=[w for _, w in STATUS_WEIGHTS], k=1
        )[0]

        # ASSIGNED/COMPLETED must have a worker; and that worker must do this
        # trade and be reasonably close, or the row contradicts the matcher.
        worker_id = NULL
        if status in ("ASSIGNED", "COMPLETED") and is_service:
            pool = workers_by_tag.get(tag, [])
            near = [w for w in pool if haversine_km(lat, lon, w["lat"], w["lon"]) <= 20.0]
            chosen = rng.choice(near) if near else (rng.choice(pool) if pool else None)
            if chosen:
                worker_id = chosen["user_id"]
            else:
                status = "PENDING"        # no credible worker -> leave unassigned
        elif status in ("ASSIGNED", "COMPLETED") and not is_service:
            status = "PENDING"            # non-service jobs are never matched

        # Every job originates from a dispatch chat, except a few created
        # directly (booking_chat_id is nullable and UNIQUE).
        if rng.random() < 0.92:
            bcid = booking_chat_id
            booking_chat_id += rng.randint(1, 3)   # gaps: not all chats become jobs
        else:
            bcid = NULL

        created = now - timedelta(
            days=rng.randint(0, 60), hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59), seconds=rng.randint(0, 59),
        )
        if status == "PENDING":
            updated = created + timedelta(minutes=rng.randint(0, 90))
        else:
            updated = created + timedelta(
                hours=rng.randint(1, 240), minutes=rng.randint(0, 59)
            )
        if updated > now:
            updated = now

        rows.append([
            i, customer_id, bcid, worker_id, title, desc, status,
            is_service, cats,
            rng.choice(CONTACT_NAMES),
            phone(), mode, attachments(mode),
            address(area) + rng.choice(RELATION_NOTES),
            lat, lon, f"SRID=4326;POINT({lon} {lat})",
            NULL,                                  # description_vector
            created.strftime("%Y-%m-%d %H:%M:%S.%f"),
            updated.strftime("%Y-%m-%d %H:%M:%S.%f"),
        ])

    return rows


def fmt(v) -> str:
    """
    One field, PostgreSQL CSV rules.
      None            -> unquoted empty  -> NULL
      ''              -> quoted ""       -> empty string
      list/dict       -> compact JSON, quoted (JSONB)
    """
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, dict)):
        v = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    s = str(v)
    if s == "":
        return '""'
    if any(ch in s for ch in [',', '"', '\n', '\r']):
        return '"' + s.replace('"', '""') + '"'
    return s


def main() -> None:
    rows = make_rows(N_ROWS)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        fh.write(",".join(HEADER) + "\n")
        for r in rows:
            fh.write(",".join(fmt(v) for v in r) + "\n")
    print(f"wrote {len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    main()
