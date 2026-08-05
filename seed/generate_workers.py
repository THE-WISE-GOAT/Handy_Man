#!/usr/bin/env python3
"""
Generate a large, realistic seed CSV for the Handy_Man `workers` table
(core.model.WorkerProfile).

Output is written in PostgreSQL CSV-COPY dialect:
  * text arrays  -> {a,b,c}   (curly-brace array literal, elements quoted when needed)
  * booleans     -> true / false
  * NULL         -> empty unquoted field  (\\COPY ... WITH (FORMAT csv, HEADER true))
  * empty string -> ""        (quoted, so NOT NULL text columns stay non-null)
  * location     -> SRID=4326;POINT(lon lat)   (EWKT, cast on load)
  * description_vector -> NULL (backfill with nvidia/nv-embed-v1, see backfill script)

Deterministic: fixed RNG seed, so re-running produces byte-identical output.
"""

from __future__ import annotations

import csv
import math
import random
from pathlib import Path

SEED = 20260727
N_ROWS = 1200
OUT = Path(__file__).with_name("workers_seed.csv")

rng = random.Random(SEED)

# --------------------------------------------------------------------------
# Trade taxonomy.
# Each entry: category_tag -> (job_category, [niches])
# A "niche" bundles specialities + tools + description fragments so that the
# generated job_description is semantically distinct per niche. This matters:
# the text is what nv-embed-v1 turns into the 4096-d vector, so near-duplicate
# descriptions would collapse the cosine-distance spread your Sigmoid relies on.
# --------------------------------------------------------------------------
TRADES: dict[str, tuple[str, list[dict]]] = {
    "plumbing": ("plumber", [
        {
            "name": "trenchless sewer rehabilitation",
            "specialities": ["trenchless-pipe-relining", "cured-in-place-pipe", "epoxy-liner"],
            "tools": ["hydro-jetter", "robotic-root-cutter", "sewer-push-camera", "cipp-inversion-drum"],
            "does": "repairs cracked underground sewer lines without excavating the yard or breaking the driveway",
            "then": "installs a new pipe inside the old one using CIPP inversion lining, clears root intrusion by hydro-jetting and mechanical cutting, then seals the host pipe with a custom-mixed epoxy liner",
        },
        {
            "name": "HDPE and live hot-tap work",
            "specialities": ["hdpe-electrofusion", "high-rise-commercial", "live-hot-tap"],
            "tools": ["electrofusion-welding-machine", "electrofusion-tapping-saddle", "liquid-nitrogen-jacket", "bypass-hose-line"],
            "does": "installs and repairs high-density polyethylene riser mains in multi-storey commercial buildings",
            "then": "performs live hot-tap bypasses and pipe-freezing isolation so damaged sections can be replaced without shutting water off to the whole block",
        },
        {
            "name": "residential repair and fixtures",
            "specialities": ["leak-detection", "tap-and-mixer-repair", "toilet-and-cistern"],
            "tools": ["acoustic-leak-detector", "pipe-wrench-set", "basin-wrench", "drain-auger"],
            "does": "traces hidden leaks behind walls and under slabs, then repairs or replaces the failed section",
            "then": "swaps worn taps, mixers, cisterns and float valves, re-seats toilets, and re-seals joints that have started weeping",
        },
        {
            "name": "water tank, pump and overhead supply",
            "specialities": ["overhead-tank-plumbing", "pressure-pump-install", "float-valve-automation"],
            "tools": ["pressure-gauge-kit", "pipe-threading-machine", "submersible-pump-puller", "level-sensor-tester"],
            "does": "sets up rooftop and underground tank plumbing with booster pumps for buildings on intermittent municipal supply",
            "then": "wires automatic float and level-sensor cutoffs, balances pressure across floors, and services pumps that are drawing air or running dry",
        },
        {
            "name": "solar hot water and geyser lines",
            "specialities": ["solar-water-heater-plumbing", "geyser-install", "thermostatic-mixing"],
            "tools": ["torque-wrench", "pipe-insulation-cutter", "expansion-vessel-charger", "infrared-thermometer"],
            "does": "installs and re-plumbs solar water heaters, electric geysers and their pressure-relief and expansion assemblies",
            "then": "fits thermostatic mixing valves to stop scalding, insulates hot runs to cut standby loss, and descales tanks fed by hard water",
        },
    ]),
    "electrical": ("electrician", [
        {
            "name": "domestic wiring and consumer units",
            "specialities": ["house-rewiring", "consumer-unit-upgrade", "earthing-and-bonding"],
            "tools": ["insulation-resistance-tester", "earth-loop-impedance-tester", "cable-conduit-bender", "clamp-meter"],
            "does": "rewires older homes and replaces fuse boards with modern RCBO consumer units",
            "then": "installs proper earthing and bonding, tests insulation resistance and loop impedance circuit by circuit, and issues a written test schedule",
        },
        {
            "name": "fault finding and emergency callout",
            "specialities": ["fault-diagnosis", "tripping-circuit-repair", "emergency-callout"],
            "tools": ["thermal-camera", "socket-tester", "cable-tracer", "digital-multimeter"],
            "does": "tracks down circuits that trip intermittently, sockets that go dead, and lights that flicker under load",
            "then": "uses a cable tracer and thermal camera to locate the failing joint or overloaded run, then repairs it and re-tests the whole circuit",
        },
        {
            "name": "inverter, battery and backup power",
            "specialities": ["inverter-install", "battery-bank-wiring", "changeover-switching"],
            "tools": ["hydrometer", "battery-load-tester", "crimping-tool-set", "busbar-torque-wrench"],
            "does": "sizes and installs inverter and battery backup systems for homes and small shops with unreliable grid supply",
            "then": "wires manual and automatic changeover switching, builds properly torqued battery banks, and diagnoses banks that no longer hold charge",
        },
        {
            "name": "lighting design and low voltage",
            "specialities": ["led-retrofit", "architectural-lighting", "low-voltage-track"],
            "tools": ["lux-meter", "dimmer-compatibility-tester", "driver-programmer", "laser-level"],
            "does": "designs and installs interior lighting layouts, from recessed LED ceilings to architectural cove and track lighting",
            "then": "retrofits old fittings to dimmable LED drivers, measures achieved lux against the design, and fixes flicker caused by mismatched dimmers",
        },
        {
            "name": "three-phase and light industrial",
            "specialities": ["three-phase-distribution", "motor-starter-wiring", "power-factor-correction"],
            "tools": ["phase-rotation-meter", "power-quality-analyser", "megger", "contactor-test-set"],
            "does": "installs and maintains three-phase distribution boards, motor starters and control panels for workshops and small factories",
            "then": "corrects phase imbalance, fits capacitor banks for power-factor correction, and logs power quality to find the source of nuisance trips",
        },
    ]),
    "carpentry": ("carpenter", [
        {
            "name": "bespoke furniture and joinery",
            "specialities": ["custom-furniture", "mortise-and-tenon", "hardwood-finishing"],
            "tools": ["mortiser", "thickness-planer", "router-table", "japanese-pull-saw"],
            "does": "builds made-to-measure tables, beds, wardrobes and shelving in solid hardwood",
            "then": "cuts traditional mortise-and-tenon and dovetail joinery, then hand-finishes with oil or lacquer to match existing pieces in the room",
        },
        {
            "name": "modular kitchen and wardrobe fitting",
            "specialities": ["modular-kitchen", "sliding-wardrobe", "soft-close-hardware"],
            "tools": ["edge-bander", "hinge-boring-machine", "cabinet-jig", "laser-level"],
            "does": "manufactures and installs modular kitchen carcasses, sliding wardrobes and loft storage",
            "then": "bores and aligns soft-close hinges and drawer runners, edge-bands exposed panels, and scribes units to walls that are out of plumb",
        },
        {
            "name": "doors, windows and frames",
            "specialities": ["door-hanging", "frame-repair", "window-shutter"],
            "tools": ["lock-mortiser", "chisel-set", "belt-sander", "door-jamb-saw"],
            "does": "hangs and rehangs internal and external doors, repairs rotted frames, and fits shutters",
            "then": "mortises locks and hinges, planes doors that bind after monsoon swelling, and replaces sills and thresholds that have gone soft",
        },
        {
            "name": "structural timber and roofing carpentry",
            "specialities": ["roof-truss", "floor-joist-repair", "timber-decking"],
            "tools": ["circular-saw", "framing-nailer", "moisture-meter", "post-level"],
            "does": "frames roof trusses, sisters failing floor joists, and builds outdoor decking and pergolas",
            "then": "checks timber moisture before fixing, ties new members into the existing structure, and treats all exposed end-grain against rot and borers",
        },
    ]),
    "painting": ("painter", [
        {
            "name": "interior finishing and putty work",
            "specialities": ["wall-putty", "emulsion-finish", "colour-matching"],
            "tools": ["putty-blade-set", "orbital-wall-sander", "airless-sprayer", "colour-fan-deck"],
            "does": "prepares and paints interior walls and ceilings to a smooth putty finish",
            "then": "fills and sands to a flat plane before priming, sprays or rolls two full coats, and mixes custom shades to match an existing wall",
        },
        {
            "name": "exterior weatherproof coating",
            "specialities": ["exterior-weathercoat", "elastomeric-coating", "anti-fungal-treatment"],
            "tools": ["pressure-washer", "swing-stage-rigging", "wet-film-gauge", "moisture-meter"],
            "does": "cleans, treats and recoats building exteriors that have chalked, cracked or grown algae",
            "then": "applies elastomeric crack-bridging coatings over hairline cracks, treats fungal growth at source, and checks wet-film thickness so the coat actually lasts the warranty",
        },
        {
            "name": "wood and metal protective finishing",
            "specialities": ["polyurethane-polish", "melamine-finish", "anti-corrosive-metal-paint"],
            "tools": ["hvlp-spray-gun", "spray-booth-extractor", "wire-brush-wheel", "viscosity-cup"],
            "does": "sprays PU and melamine finishes on furniture and joinery, and repaints grilles, gates and railings",
            "then": "strips old coatings back, treats rust with a converter and anti-corrosive primer, and lays down an even sprayed topcoat without runs",
        },
        {
            "name": "decorative and textured finishes",
            "specialities": ["texture-wall", "stencil-and-mural", "wallpaper-hanging"],
            "tools": ["texture-roller-set", "trowel-and-float", "seam-roller", "wallpaper-steamer"],
            "does": "creates decorative feature walls using textures, stencils, murals and wallpaper",
            "then": "builds up trowelled texture coats, aligns patterned wallpaper drops without visible seams, and strips failed old paper cleanly with steam",
        },
    ]),
    "masonry": ("mason", [
        {
            "name": "brick and block structural work",
            "specialities": ["brickwork", "block-masonry", "load-bearing-wall"],
            "tools": ["brick-trowel", "line-and-pins", "mortar-mixer", "spirit-level"],
            "does": "builds brick and block walls, piers and boundary walls to line and plumb",
            "then": "mixes mortar to the right grade for the load, ties new masonry into old, and cuts and props openings before forming lintels",
        },
        {
            "name": "plastering and rendering",
            "specialities": ["cement-plaster", "gypsum-plaster", "waterproof-render"],
            "tools": ["plastering-trowel", "aluminium-straight-edge", "hawk", "sponge-float"],
            "does": "plasters new masonry and re-renders walls where the old coat has hollowed or blown",
            "then": "hacks back the failed area, applies a bonding coat, and floats the finish flat enough that the painter needs minimal putty",
        },
        {
            "name": "concrete and RCC work",
            "specialities": ["rcc-slab", "concrete-repair", "rebar-tying"],
            "tools": ["concrete-vibrator", "rebar-bender", "power-float", "slump-cone"],
            "does": "casts RCC slabs, columns, beams and stairs, and repairs spalled concrete where rebar has begun to corrode",
            "then": "ties and spaces reinforcement to cover, checks slump before pouring, vibrates out honeycombing, and cures the pour properly instead of letting it dry out",
        },
        {
            "name": "stone cladding and heritage repointing",
            "specialities": ["stone-cladding", "lime-mortar-repointing", "heritage-restoration"],
            "tools": ["stone-cutter", "pointing-iron", "lime-mortar-mill", "diamond-blade-grinder"],
            "does": "fixes natural stone cladding and repoints old brick and stone buildings",
            "then": "rakes out cement pointing that is trapping damp in heritage walls, repoints in a breathable lime mortar, and matches the original joint profile",
        },
    ]),
    "hvac": ("hvac technician", [
        {
            "name": "split AC installation and service",
            "specialities": ["split-ac-install", "gas-charging", "coil-cleaning"],
            "tools": ["vacuum-pump", "manifold-gauge-set", "flaring-tool", "refrigerant-recovery-machine"],
            "does": "installs, relocates and services split and window air conditioners",
            "then": "vacuums and leak-tests the line set before charging, recovers rather than vents old refrigerant, and deep-cleans coils and blower wheels that have lost airflow",
        },
        {
            "name": "VRF and central systems",
            "specialities": ["vrf-commissioning", "ducted-system", "bms-integration"],
            "tools": ["nitrogen-purge-kit", "digital-anemometer", "brazing-torch", "vrf-service-laptop"],
            "does": "commissions VRF and ducted central systems for offices, hotels and larger homes",
            "then": "purges with nitrogen while brazing, balances air volumes duct by duct with an anemometer, and integrates the units with the building management system",
        },
        {
            "name": "refrigeration and cold storage",
            "specialities": ["walk-in-chiller", "deep-freezer-repair", "compressor-replacement"],
            "tools": ["refrigerant-leak-detector", "compressor-puller", "superheat-calculator", "data-logger"],
            "does": "maintains walk-in chillers, display cabinets and deep freezers for shops and restaurants",
            "then": "diagnoses compressors that short-cycle, sets superheat and subcooling correctly, and logs cabinet temperature over a full cycle to prove the fix held",
        },
        {
            "name": "ventilation and indoor air quality",
            "specialities": ["exhaust-ventilation", "kitchen-hood-ducting", "air-purification"],
            "tools": ["duct-crimper", "airflow-hood", "particle-counter", "sheet-metal-nibbler"],
            "does": "designs and installs exhaust ventilation, kitchen hood ducting and fresh-air systems",
            "then": "sizes ducts so extraction actually works at the far end, seals leaking joints, and measures particulate levels before and after to show the improvement",
        },
    ]),
    "appliance-repair": ("appliance repair technician", [
        {
            "name": "washing machine and dryer repair",
            "specialities": ["front-load-washer", "drum-bearing-replacement", "control-board-repair"],
            "tools": ["bearing-press", "esr-meter", "torx-driver-set", "appliance-diagnostic-reader"],
            "does": "repairs front and top load washing machines that leak, over-vibrate or stop mid-cycle",
            "then": "presses in new drum bearings and seals, reflows or replaces failed control boards, and clears drain pumps blocked by coins and lint",
        },
        {
            "name": "refrigerator repair",
            "specialities": ["fridge-gas-refill", "defrost-system-repair", "inverter-compressor"],
            "tools": ["pinch-off-tool", "brazing-torch", "clamp-ammeter", "vacuum-pump"],
            "does": "repairs refrigerators that are not cooling, icing up, or running constantly",
            "then": "locates and brazes leaks in the sealed system, recharges to the plate weight, and replaces failed defrost heaters, thermostats and inverter compressor boards",
        },
        {
            "name": "kitchen and small appliance repair",
            "specialities": ["microwave-repair", "induction-hob", "mixer-grinder-rewinding"],
            "tools": ["magnetron-tester", "armature-winding-jig", "hot-air-rework-station", "insulation-tester"],
            "does": "repairs microwaves, induction hobs, ovens, mixers and other small kitchen appliances",
            "then": "tests magnetrons and high-voltage diodes safely, rewinds burnt motor armatures, and reworks IGBT stages on induction boards rather than scrapping the unit",
        },
    ]),
    "locksmith": ("locksmith", [
        {
            "name": "emergency lockout and door opening",
            "specialities": ["non-destructive-entry", "lock-picking", "24hr-emergency"],
            "tools": ["pick-set", "electric-pick-gun", "letterbox-tool", "air-wedge"],
            "does": "opens homes, offices and cars for people locked out, without damaging the door",
            "then": "picks or bypasses the lock non-destructively wherever possible, and only drills as a last resort before fitting a like-for-like replacement on the spot",
        },
        {
            "name": "high-security lock and safe work",
            "specialities": ["safe-opening", "restricted-keyway", "master-key-system"],
            "tools": ["safe-scope", "key-cutting-machine", "code-generator", "drill-rig"],
            "does": "opens and services safes and strongrooms, and designs master-key suites for buildings with many tenants",
            "then": "manipulates or scopes safes shut by a failed lock, changes combinations, and cuts restricted keyways so keys cannot be copied at a corner shop",
        },
        {
            "name": "electronic and smart access",
            "specialities": ["digital-door-lock", "rfid-access-control", "biometric-lock"],
            "tools": ["rfid-encoder", "access-control-programmer", "crimping-tool", "door-closer-jig"],
            "does": "installs digital, RFID and biometric locks together with the access control behind them",
            "then": "enrols and revokes credentials, wires magnetic locks to fail-safe on fire alarm, and recovers systems where the admin credential has been lost",
        },
    ]),
    "roofing": ("roofer", [
        {
            "name": "flat roof waterproofing",
            "specialities": ["app-membrane", "liquid-waterproofing", "flat-roof-leak"],
            "tools": ["propane-torch-kit", "membrane-roller", "moisture-survey-meter", "heat-welder"],
            "does": "finds and fixes leaks on flat concrete roofs and terraces",
            "then": "torch-applies or heat-welds membrane over the failed area, forms proper upstands at parapets and drains, and re-falls ponding areas so water actually reaches the outlet",
        },
        {
            "name": "pitched roof and sheet roofing",
            "specialities": ["cgi-sheet-roofing", "tile-roof-repair", "ridge-and-flashing"],
            "tools": ["sheet-nibbler", "roofing-screw-gun", "safety-harness", "seaming-tool"],
            "does": "installs and repairs CGI sheet, tile and truss-supported pitched roofs",
            "then": "replaces corroded sheets and cracked tiles, re-beds ridges, and reworks flashings at chimneys and valleys where most leaks actually start",
        },
        {
            "name": "gutters, drainage and rainwater",
            "specialities": ["gutter-install", "downpipe-repair", "rainwater-harvesting"],
            "tools": ["gutter-crimper", "drain-camera", "pipe-cutter", "laser-fall-gauge"],
            "does": "installs and unblocks gutters, downpipes and rainwater harvesting connections",
            "then": "sets correct falls so gutters drain instead of overflowing at the joint, and diverts harvested water through a first-flush filter into storage",
        },
    ]),
    "tiling": ("tiler", [
        {
            "name": "bathroom and wet area tiling",
            "specialities": ["wet-area-waterproofing", "shower-tray-forming", "epoxy-grouting"],
            "tools": ["wet-tile-saw", "notched-trowel-set", "levelling-clip-system", "grout-float"],
            "does": "tiles bathrooms and wet areas over a properly detailed waterproof membrane",
            "then": "forms falls to the drain, bands the corners and penetrations before tiling, and finishes in epoxy grout where the area gets constant water",
        },
        {
            "name": "large format and stone tiling",
            "specialities": ["large-format-porcelain", "marble-laying", "stone-polishing"],
            "tools": ["rail-cutter", "vacuum-suction-lifter", "levelling-system", "floor-polisher"],
            "does": "lays large-format porcelain, marble and granite floors flat and lippage-free",
            "then": "back-butters and beats in every sheet, uses a levelling system across joints, and grinds and polishes stone in place where slabs meet unevenly",
        },
        {
            "name": "tile repair and regrouting",
            "specialities": ["hollow-tile-repair", "regrouting", "anti-skid-treatment"],
            "tools": ["grout-rake", "injection-resin-kit", "diamond-hole-saw", "tile-lifter"],
            "does": "fixes drummy or cracked tiles and refreshes stained, crumbling grout",
            "then": "injects resin under hollow tiles instead of ripping up the whole floor where possible, rakes and regrouts joints, and applies anti-skid treatment to slippery areas",
        },
    ]),
    "welding": ("welder", [
        {
            "name": "structural steel fabrication",
            "specialities": ["mig-welding", "structural-steel", "staircase-fabrication"],
            "tools": ["mig-welder", "plasma-cutter", "magnetic-square-set", "angle-grinder"],
            "does": "fabricates and erects steel staircases, mezzanines, canopies and support frames",
            "then": "cuts and fits members to drawing, lays full-penetration structural welds, and grinds and primes every joint before handover",
        },
        {
            "name": "gates, grilles and railings",
            "specialities": ["gate-fabrication", "window-grille", "ms-railing"],
            "tools": ["arc-welder", "pipe-bender", "bench-vice", "cutting-disc-set"],
            "does": "makes and installs mild steel gates, window grilles, balcony railings and security bars",
            "then": "measures the opening on site, fabricates to fit rather than to a standard size, and hangs gates so they swing true and latch without lifting",
        },
        {
            "name": "stainless and aluminium specialist welding",
            "specialities": ["tig-welding", "stainless-steel", "aluminium-welding"],
            "tools": ["tig-welder", "argon-purge-kit", "stainless-wire-brush", "pickling-paste-kit"],
            "does": "TIG welds stainless steel and aluminium for handrails, kitchen equipment and food-grade work",
            "then": "back-purges with argon to stop sugaring on the inside of the weld, and pickles and passivates stainless afterwards so it does not rust at the heat-affected zone",
        },
    ]),
    "pest-control": ("pest control technician", [
        {
            "name": "termite and wood borer treatment",
            "specialities": ["anti-termite-treatment", "wood-borer", "pre-construction-treatment"],
            "tools": ["soil-injection-rod", "power-sprayer", "termite-baiting-station", "moisture-meter"],
            "does": "treats active termite infestations in buildings and furniture, and does pre-construction soil treatment",
            "then": "drills and injects along the affected line, installs monitored bait stations for colony elimination, and identifies the moisture source that let them in",
        },
        {
            "name": "general pest and rodent management",
            "specialities": ["cockroach-gel-treatment", "rodent-proofing", "bed-bug-treatment"],
            "tools": ["gel-bait-applicator", "ulv-fogger", "rodent-tracking-station", "steam-treatment-unit"],
            "does": "manages cockroach, rodent, bed bug and ant problems in homes, kitchens and warehouses",
            "then": "uses targeted gel and bait rather than blanket spraying in food areas, proofs the entry routes rodents are using, and returns for a follow-up to break the breeding cycle",
        },
    ]),
    "cleaning": ("cleaner", [
        {
            "name": "deep cleaning and post-construction",
            "specialities": ["deep-cleaning", "post-construction-cleanup", "grout-and-stain-removal"],
            "tools": ["rotary-scrubber", "wet-dry-vacuum", "steam-cleaner", "single-disc-machine"],
            "does": "deep cleans homes and offices, including handover cleaning after construction or renovation",
            "then": "removes cement haze, paint spatter and adhesive residue from floors and glass, scrubs and reseals grout lines, and steam-treats areas that cannot take chemicals",
        },
        {
            "name": "water tank and sump cleaning",
            "specialities": ["water-tank-cleaning", "sump-disinfection", "sludge-removal"],
            "tools": ["submersible-sludge-pump", "high-pressure-washer", "uv-disinfection-wand", "confined-space-kit"],
            "does": "empties, scrubs and disinfects overhead tanks, underground sumps and reservoirs",
            "then": "removes accumulated sludge and biofilm, disinfects with a food-safe agent, and follows confined-space procedure with a second person on the surface",
        },
        {
            "name": "facade and glass cleaning",
            "specialities": ["facade-cleaning", "high-rise-glass", "rope-access"],
            "tools": ["rope-access-kit", "water-fed-pole-system", "squeegee-set", "deionised-water-unit"],
            "does": "cleans building facades and high-rise glazing from rope access or a water-fed pole",
            "then": "uses deionised water so glass dries spot-free, removes hard-water staining from the outside of the pane, and works to a documented rope access method statement",
        },
    ]),
    "landscaping": ("gardener", [
        {
            "name": "garden maintenance and planting",
            "specialities": ["garden-maintenance", "seasonal-planting", "organic-composting"],
            "tools": ["hedge-trimmer", "soil-ph-meter", "brush-cutter", "pruning-shear-set"],
            "does": "maintains gardens through the season: mowing, pruning, weeding and replanting",
            "then": "tests and amends soil rather than just adding fertiliser, sets up compost from garden waste, and plans planting so something is in flower most of the year",
        },
        {
            "name": "irrigation and lawn systems",
            "specialities": ["drip-irrigation", "sprinkler-system", "lawn-laying"],
            "tools": ["irrigation-controller", "trenching-spade", "flow-meter", "lawn-roller"],
            "does": "designs and installs drip and sprinkler irrigation and lays new lawn",
            "then": "zones the system so beds and lawn are watered differently, sets controller schedules to the season, and levels and rolls the base before turfing",
        },
        {
            "name": "tree work and hardscaping",
            "specialities": ["tree-pruning", "tree-felling", "paving-and-hardscape"],
            "tools": ["chainsaw", "climbing-harness", "stump-grinder", "plate-compactor"],
            "does": "prunes, reduces and safely fells trees, and builds paths, patios and retaining edges",
            "then": "sections down trees over structures with rigging rather than dropping them whole, grinds stumps out, and compacts sub-base properly so paving does not sink",
        },
    ]),
    "solar": ("solar technician", [
        {
            "name": "rooftop PV installation",
            "specialities": ["rooftop-pv-install", "string-inverter", "net-metering"],
            "tools": ["mc4-crimping-tool", "irradiance-meter", "iv-curve-tracer", "torque-wrench"],
            "does": "installs rooftop solar PV arrays with string inverters and net-metering connections",
            "then": "lays out strings to avoid shading losses, torques and weatherproofs every MC4 connection, and commissions with an IV curve trace to prove the array performs to spec",
        },
        {
            "name": "solar maintenance and fault finding",
            "specialities": ["pv-fault-diagnosis", "panel-cleaning", "hybrid-battery-storage"],
            "tools": ["thermal-drone", "insulation-tester", "clamp-meter-dc", "module-cleaning-kit"],
            "does": "diagnoses solar systems that are underproducing and services existing arrays",
            "then": "thermally images the array to find hot cells and failed bypass diodes, tests string insulation for water ingress, and retrofits hybrid battery storage where the tariff justifies it",
        },
    ]),
    "security-systems": ("cctv and security technician", [
        {
            "name": "CCTV and video surveillance",
            "specialities": ["ip-cctv-install", "nvr-configuration", "remote-viewing-setup"],
            "tools": ["poe-network-tester", "cctv-test-monitor", "rj45-crimper", "cable-fish-tape"],
            "does": "installs IP CCTV systems with NVR recording and phone-based remote viewing",
            "then": "plans camera positions for usable identification rather than just coverage, terminates and tests every PoE run, and configures retention and secure remote access without exposing the recorder to the open internet",
        },
        {
            "name": "alarms, intercom and gate automation",
            "specialities": ["burglar-alarm", "video-door-phone", "automatic-gate"],
            "tools": ["alarm-panel-programmer", "intercom-tester", "gate-motor-limit-jig", "multimeter"],
            "does": "installs burglar alarms, video door phones and automatic gate operators",
            "then": "zones the alarm so pets do not trigger it, wires intercoms to release the gate strike, and sets motor limits and obstruction sensing so a gate cannot close on someone",
        },
    ]),
    "flooring": ("flooring specialist", [
        {
            "name": "wood and laminate flooring",
            "specialities": ["laminate-flooring", "engineered-wood", "floor-sanding"],
            "tools": ["floor-sander", "flooring-nailer", "moisture-meter", "tapping-block"],
            "does": "lays laminate and engineered wood floors and refinishes existing timber floors",
            "then": "checks slab moisture and lays the right underlay before starting, leaves proper expansion gaps at the perimeter, and sands and re-coats old boards instead of replacing them where the wear layer allows",
        },
        {
            "name": "vinyl, epoxy and resin floors",
            "specialities": ["vinyl-sheet-welding", "epoxy-floor-coating", "self-levelling-screed"],
            "tools": ["hot-air-welder", "spiked-roller", "self-leveller-mixer", "concrete-grinder"],
            "does": "installs welded vinyl sheet, epoxy coatings and self-levelling screeds in homes, clinics and workshops",
            "then": "grinds and primes the substrate first, pours self-levelling screed to correct a floor that is out of level, and heat-welds vinyl seams so the finish is genuinely waterproof",
        },
    ]),
    "glazing": ("glazier", [
        {
            "name": "glass, mirror and shower screens",
            "specialities": ["toughened-glass", "mirror-fitting", "shower-enclosure"],
            "tools": ["glass-suction-lifter", "glass-cutter", "silicone-gun", "edge-polishing-machine"],
            "does": "measures, supplies and fits toughened glass partitions, mirrors and frameless shower enclosures",
            "then": "templates on site rather than working from a sketch, drills and polishes edges before toughening, and sets panels on proper packers so the weight sits where it should",
        },
        {
            "name": "aluminium and uPVC windows",
            "specialities": ["upvc-window-install", "aluminium-partition", "double-glazing"],
            "tools": ["mitre-saw", "glazing-shovel", "sealant-applicator", "window-hardware-jig"],
            "does": "fabricates and installs uPVC and aluminium windows, doors and office partitions",
            "then": "fits double-glazed units with correct drainage and ventilation of the rebate, adjusts hardware so sashes compress the seal evenly, and replaces blown units that have fogged internally",
        },
    ]),
    "generator": ("generator technician", [
        {
            "name": "diesel generator service",
            "specialities": ["diesel-genset-service", "amf-panel", "load-bank-testing"],
            "tools": ["load-bank", "injector-tester", "avr-tester", "insulation-tester"],
            "does": "installs, services and repairs standby diesel generator sets and their AMF panels",
            "then": "load-bank tests rather than just idling the set, services injectors and governors, and sets AMF changeover timing so the load transfers cleanly when the grid drops",
        },
    ]),
    "water-treatment": ("water treatment technician", [
        {
            "name": "RO and domestic water treatment",
            "specialities": ["ro-plant-install", "water-softener", "iron-removal-filter"],
            "tools": ["tds-meter", "membrane-flush-kit", "hardness-test-kit", "pressure-gauge"],
            "does": "installs and services RO plants, softeners and iron removal filters for homes and small buildings",
            "then": "tests raw water first and sizes media to the actual hardness and iron level, sets recovery ratio so membranes are not scaling, and schedules regeneration and membrane changes",
        },
    ]),
    "networking": ("network and internet technician", [
        {
            "name": "structured cabling and home networks",
            "specialities": ["structured-cabling", "wifi-mesh-setup", "fibre-splicing"],
            "tools": ["fusion-splicer", "otdr", "cable-certifier", "punch-down-tool"],
            "does": "runs structured cabling and sets up reliable Wi-Fi coverage in homes and offices",
            "then": "certifies every copper run rather than just checking it links up, splices and tests fibre drops with an OTDR, and places mesh nodes from an actual site survey instead of guessing",
        },
    ]),
    "interior-finishing": ("false ceiling and interior finisher", [
        {
            "name": "false ceiling and drywall",
            "specialities": ["gypsum-false-ceiling", "pop-cornice", "drywall-partition"],
            "tools": ["laser-level", "drywall-lifter", "screw-gun", "jointing-knife-set"],
            "does": "builds gypsum and POP false ceilings, cornices and drywall partitions",
            "then": "sets out a level grid from a laser line, coordinates openings with the electrician before boarding, and tapes and skims joints so no cracking shows through the paint",
        },
    ]),
}

# ---- Kathmandu Valley geographic clusters -------------------------------
# (name, lat, lon, spread_km) — spread controls how far workers scatter from
# the cluster centre. Chosen so a 20 km ST_DWithin filter returns a varied,
# non-trivial subset rather than everything or nothing.
CLUSTERS = [
    ("Thamel, Kathmandu",              27.7154, 85.3123, 1.6),
    ("Baneshwor, Kathmandu",           27.6893, 85.3400, 2.0),
    ("Kalanki, Kathmandu",             27.6939, 85.2810, 2.0),
    ("Chabahil, Kathmandu",            27.7172, 85.3462, 1.8),
    ("Balaju, Kathmandu",              27.7357, 85.3020, 1.8),
    ("Budhanilkantha, Kathmandu",      27.7789, 85.3620, 2.4),
    ("Patan (Lalitpur)",               27.6766, 85.3240, 2.0),
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
    ("Nagarkot (outskirt)",            27.7150, 85.5200, 3.0),
    ("Dhulikhel (outskirt)",           27.6220, 85.5390, 3.0),
]

STREETS = [
    "Marg", "Sadak", "Galli", "Tole", "Chowk", "Height", "Colony", "Housing",
]
LOCALITY_WORDS = [
    "Naya", "Purano", "Shanti", "Milan", "Sundar", "Ganesh", "Buddha", "Krishna",
    "Nava", "Jhamsikhel", "Sanepa", "Bansbari", "Maharajgunj", "Baluwatar",
    "Gongabu", "Samakhusi", "Mitrapark", "Sinamangal", "Tinkune", "Lokanthali",
]

LICENSE_BY_TIER = {
    "none": [None],
    "informal": [
        "on-the-job training, no formal license",
        "apprenticeship completed under a senior tradesperson",
        "employer-issued competency letter",
    ],
    "formal": [
        "CTEVT Level 1 Skill Test Certificate",
        "CTEVT Level 2 Skill Test Certificate",
        "CTEVT Level 3 Skill Test Certificate",
        "CTEVT Diploma, 3-year",
        "NSTB Skill Test Certificate",
        "Municipal trade license",
        "Manufacturer-authorised service certification",
        "Vocational training institute certificate",
        "Electrical Supervisor License (NEA recognised)",
        "Gas handling and refrigerant safety certificate",
    ],
}

REJECTION_REASONS = [
    "Scenario assessment score below the required threshold.",
    "Could not describe a safe isolation procedure for the given scenario.",
    "Stated years of experience inconsistent with the answers given during the interview.",
    "Declined to provide any verifiable license or training reference.",
    "Answers were copied verbatim from a public source; authenticity could not be established.",
    "Selected trade does not match the work described in the interview.",
    "Safety-critical step omitted in the practical scenario response.",
    "Unable to confirm a serviceable operating location within the coverage area.",
    "Interview abandoned before the practical scenario was completed.",
    "Provided contact number could not be verified.",
]

INCOMPLETE_STAGES = [
    "greeting",
    "category_selection",
    "specialities",
    "tools_and_equipment",
    "experience",
    "licensing",
    "description",
    "scenario",
    "location",
    "review",
]

DESC_OPENERS = [
    "{does_cap}.",
    "Regularly {does}.",
    "Day to day, {does}.",
    "Primarily {does}.",
]

DESC_CLOSERS = [
    "Works across {area} and nearby wards.",
    "Takes jobs across {area} and the surrounding area.",
    "Covers {area} and neighbouring localities.",
    "Based in {area}, travels within the valley for larger jobs.",
]

EXPERIENCE_LINES = {
    "junior": [
        "Has {yrs} years on the tools and works under a senior tradesperson on larger contracts.",
        "{yrs} years of hands-on experience, mostly on residential jobs.",
        "Around {yrs} years in the trade, still building a portfolio of larger commercial work.",
    ],
    "mid": [
        "{yrs} years in the trade, running jobs independently from quote to handover.",
        "Has {yrs} years of experience and handles both residential and small commercial contracts.",
        "{yrs} years on site, comfortable pricing and scheduling a job without supervision.",
    ],
    "senior": [
        "{yrs} years in the trade, and now supervises a small crew on multi-unit projects.",
        "With {yrs} years of experience, takes on complex remedial work other tradespeople have walked away from.",
        "{yrs} years in the field, regularly called in for second opinions and failure diagnosis.",
    ],
}

EMERGENCY_LINES = [
    "Available for emergency callouts outside normal hours.",
    "Takes same-day emergency work, including nights and public holidays.",
    "Responds to urgent callouts, typically on site within a couple of hours.",
]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def jitter_point(lat: float, lon: float, spread_km: float) -> tuple[float, float]:
    """Scatter a point around (lat, lon) with a roughly gaussian spread."""
    # 1 deg latitude ~ 110.574 km; 1 deg longitude ~ 111.320*cos(lat) km
    dlat_km = rng.gauss(0.0, spread_km / 2.0)
    dlon_km = rng.gauss(0.0, spread_km / 2.0)
    lat2 = lat + dlat_km / 110.574
    lon2 = lon + dlon_km / (111.320 * math.cos(math.radians(lat)))
    return round(lat2, 6), round(lon2, 6)


def pg_array(values: list[str]) -> str:
    """Render a Python list as a PostgreSQL text[] literal: {a,b,"c d"}."""
    out = []
    for v in values:
        if v == "" or any(ch in v for ch in ',{}"\\ '):
            out.append('"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"')
        else:
            out.append(v)
    return "{" + ",".join(out) + "}"


def phone() -> str:
    prefix = rng.choice(["984", "985", "986", "980", "981", "982", "961", "962", "974", "975"])
    return f"+977-{prefix}{rng.randint(1000000, 9999999)}"


def address(area: str) -> str:
    return (
        f"{rng.choice(LOCALITY_WORDS)} {rng.choice(STREETS)}, "
        f"Ward {rng.randint(1, 32)}, {area}, Nepal"
    )


def build_description(niche: dict, yrs: int, area: str, emergency: bool,
                      specialities: list[str], tools: list[str]) -> str:
    does = niche["does"]
    opener_tpl = rng.choice(DESC_OPENERS)
    opener = opener_tpl.format(
        does=does,
        does_cap=does[0].upper() + does[1:],
        does_needed=does,
    )

    tier = "junior" if yrs <= 3 else ("mid" if yrs <= 9 else "senior")
    exp_line = rng.choice(EXPERIENCE_LINES[tier]).format(yrs=yrs)

    tool_sample = rng.sample(tools, k=min(len(tools), rng.randint(2, 3)))
    tool_line = "Works with " + ", ".join(t.replace("-", " ") for t in tool_sample) + "."

    spec_line = (
        "Core skills: "
        + ", ".join(s.replace("-", " ") for s in specialities)
        + "."
    )

    parts = [opener, niche["then"][0].upper() + niche["then"][1:] + ".", exp_line, spec_line, tool_line]
    if emergency:
        parts.append(rng.choice(EMERGENCY_LINES))
    parts.append(rng.choice(DESC_CLOSERS).format(area=area))

    # Vary sentence order slightly (keep opener first, closer last) so the
    # embeddings do not all share an identical structural fingerprint.
    middle = parts[1:-1]
    rng.shuffle(middle)
    return " ".join([parts[0], *middle, parts[-1]])


# --------------------------------------------------------------------------
# Row generation
# --------------------------------------------------------------------------
HEADER = [
    "id", "user_id", "worker_chat_id", "stage", "is_complete", "is_rejected",
    "rejection_reason", "job_category", "category_tag", "is_custom_category",
    "specialities", "specialized_tools_or_equipment", "years_experience",
    "license_or_certification", "job_description", "emergency_available",
    "has_verified_specialty", "scenario_passed", "scenario_score",
    "description_vector", "phone_number", "address_text", "latitude",
    "longitude", "location",
]

NULL = None          # -> empty unquoted field -> SQL NULL
EMPTY = ""           # -> quoted "" -> empty string (for NOT NULL text cols)

# Rarer trades that workers enter as free text rather than picking from the
# standard list, so they land with is_custom_category = True. Each one still
# gets its OWN specialities/tools/description niche — borrowing them from an
# unrelated trade would put "lock-picking" on a chimney sweep and poison the
# semantic match results.
CUSTOM_TRADES: dict[str, tuple[str, list[dict]]] = {
    "chimney-flue": ("chimney and flue specialist", [
        {
            "name": "chimney sweeping and flue lining",
            "specialities": ["chimney-sweeping", "flue-relining", "cowl-and-capping"],
            "tools": ["rotary-sweeping-rod-set", "flue-camera", "smoke-pellet-kit", "draught-gauge"],
            "does": "sweeps and inspects chimneys and relines flues that have started leaking fumes into the room",
            "then": "camera-surveys the flue to find the breach, fits a stainless liner where the brickwork has failed, and pressure-tests the draught before signing the appliance off as safe to use",
        },
    ]),
    "swimming-pool": ("swimming pool technician", [
        {
            "name": "pool plant, filtration and water balance",
            "specialities": ["pool-filtration-plant", "water-chemistry-balancing", "pool-leak-detection"],
            "tools": ["sand-filter-media-vacuum", "photometer-test-kit", "pool-leak-dye-kit", "flow-meter"],
            "does": "services swimming pool circulation plant, filtration and dosing systems",
            "then": "backwashes and rebeds filter media, balances pH, chlorine and alkalinity to a measured reading rather than guesswork, and traces liner and pipework leaks that are dropping the water level",
        },
    ]),
    "home-theatre": ("home theatre installer", [
        {
            "name": "home cinema and multi-room audio",
            "specialities": ["surround-sound-calibration", "projector-installation", "multi-room-audio"],
            "tools": ["spl-meter", "hdmi-signal-analyser", "acoustic-measurement-mic", "cable-fish-tape"],
            "does": "installs home cinema systems, projectors and multi-room audio distribution",
            "then": "aligns and focuses the projector to the screen geometry, calibrates speaker levels and delays from measured SPL rather than by ear, and hides all cabling in-wall",
        },
    ]),
    "curtains-blinds": ("curtain and blinds fitter", [
        {
            "name": "curtain tracks, blinds and motorised shading",
            "specialities": ["curtain-track-fitting", "roller-and-venetian-blinds", "motorised-shading"],
            "tools": ["laser-level", "hollow-wall-anchor-set", "blind-cutting-bench", "cordless-hammer-drill"],
            "does": "measures, makes and fits curtain tracks, roller and venetian blinds and motorised shades",
            "then": "fixes brackets into the right substrate so heavy tracks do not pull out of plasterboard, cuts blinds to the measured opening, and wires and pairs motorised units to a remote or wall switch",
        },
    ]),
    "septic-soakpit": ("septic tank and soakpit specialist", [
        {
            "name": "septic tanks, soakpits and drain fields",
            "specialities": ["septic-tank-desludging", "soakpit-construction", "drain-field-repair"],
            "tools": ["vacuum-tanker-hose", "percolation-test-kit", "drain-rod-set", "confined-space-kit"],
            "does": "builds, empties and repairs septic tanks, soakpits and their drain fields",
            "then": "desludges the tank before it backs up into the house, runs a percolation test to size a new soakpit properly for the ground conditions, and rebuilds fields that have silted up and stopped draining",
        },
    ]),
    "furniture-restoration": ("antique furniture restorer", [
        {
            "name": "antique furniture restoration",
            "specialities": ["veneer-repair", "french-polishing", "structural-joint-reglue"],
            "tools": ["hide-glue-pot", "veneer-hammer", "cabinet-scraper-set", "shellac-polishing-mop"],
            "does": "restores antique and inherited furniture rather than replacing it",
            "then": "lifts and patches missing veneer with matched stock, re-glues loose joints in reversible hide glue so the piece can be worked on again in future, and builds up a French polish finish by hand",
        },
    ]),
    "bamboo-cane": ("bamboo and cane craftsman", [
        {
            "name": "bamboo construction and cane weaving",
            "specialities": ["bamboo-treatment", "cane-seat-weaving", "bamboo-structure-building"],
            "tools": ["bamboo-splitting-knife", "borax-treatment-tank", "cane-weaving-awl", "node-trimming-saw"],
            "does": "builds bamboo structures, screens and furniture, and reweaves cane seats and panels",
            "then": "borax-treats and seasons the bamboo first so borers do not destroy it within a season, splits and lashes members traditionally, and reweaves cane in the original pattern",
        },
    ]),
    "seismic-retrofit": ("earthquake retrofitting specialist", [
        {
            "name": "seismic strengthening of existing buildings",
            "specialities": ["jacketing-and-confinement", "wall-stitching", "seismic-vulnerability-survey"],
            "tools": ["rebar-locator", "core-drilling-rig", "epoxy-injection-pump", "crack-width-gauge"],
            "does": "assesses and strengthens existing masonry and RCC buildings against earthquake loading",
            "then": "surveys the structure for soft storeys and inadequate confinement, jackets weak columns, stitches cracked walls with helical ties, and injects structural epoxy into cracks that are still sound enough to bond",
        },
    ]),
    "soundproofing": ("acoustic and soundproofing installer", [
        {
            "name": "acoustic treatment and soundproofing",
            "specialities": ["acoustic-panel-install", "resilient-channel-isolation", "impact-noise-treatment"],
            "tools": ["sound-level-meter", "acoustic-sealant-gun", "resilient-clip-set", "reverberation-timer"],
            "does": "soundproofs rooms and treats acoustics in studios, clinics and apartments with noise complaints",
            "then": "measures the problem frequency before choosing a treatment, decouples partitions on resilient channels so structure-borne noise stops transmitting, and seals every flanking path since one gap undoes the whole build-up",
        },
    ]),
    "elevator": ("lift and elevator technician", [
        {
            "name": "lift servicing and safety testing",
            "specialities": ["lift-servicing", "door-operator-alignment", "overspeed-governor-testing"],
            "tools": ["lift-tachometer", "governor-test-rig", "door-force-gauge", "controller-programmer"],
            "does": "services and repairs passenger and goods lifts, including their controllers and door operators",
            "then": "aligns and adjusts door operators that are re-opening or trapping passengers, tests the overspeed governor and safety gear to the certification schedule, and diagnoses controller faults causing lifts to park out of service",
        },
    ]),
}



def make_rows(n: int) -> list[list]:
    rows: list[list] = []
    tags = list(TRADES.keys())
    # Weight common trades more heavily than niche ones.
    weights = []
    common = {"plumbing", "electrical", "carpentry", "painting", "masonry",
              "hvac", "appliance-repair", "cleaning", "tiling"}
    for t in tags:
        weights.append(9 if t in common else 4)

    next_worker_chat_id = 1
    user_ids_in_use: list[int] = []
    next_user_id = 1

    for i in range(1, n + 1):
        # --- identity -----------------------------------------------------
        # 18% of rows reuse an existing user_id: one user, several trades.
        # user_id is deliberately NOT unique on this table.
        if user_ids_in_use and rng.random() < 0.18:
            user_id = rng.choice(user_ids_in_use[-400:])
        else:
            user_id = next_user_id
            next_user_id += 1
            user_ids_in_use.append(user_id)

        worker_chat_id = next_worker_chat_id
        next_worker_chat_id += 1

        # --- outcome mix --------------------------------------------------
        roll = rng.random()
        if roll < 0.80:
            outcome = "approved"      # complete, passed the scenario gate
        elif roll < 0.90:
            outcome = "rejected"      # complete but failed
        else:
            outcome = "in_progress"   # interview not finished

        # --- geography ----------------------------------------------------
        area, clat, clon, spread = rng.choice(CLUSTERS)
        lat, lon = jitter_point(clat, clon, spread)

        # --- in-progress rows --------------------------------------------
        if outcome == "in_progress":
            stage = rng.choice(INCOMPLETE_STAGES)
            reached = INCOMPLETE_STAGES.index(stage)
            has_cat = reached >= 1
            is_custom_ip = False
            if has_cat:
                if rng.random() < 0.04:
                    is_custom_ip = True
                    tag = rng.choice(list(CUSTOM_TRADES.keys()))
                    job_category, niches = CUSTOM_TRADES[tag]
                else:
                    tag = rng.choices(tags, weights=weights, k=1)[0]
                    job_category, niches = TRADES[tag]
                niche = rng.choice(niches)
            else:
                tag, job_category, niche = EMPTY, EMPTY, None

            specs = niche["specialities"] if (niche and reached >= 2) else []
            tls = niche["tools"] if (niche and reached >= 3) else []
            yrs = rng.randint(1, 20) if reached >= 4 else 0
            lic = rng.choice(LICENSE_BY_TIER["formal"]) if reached >= 5 else NULL
            desc = (
                build_description(niche, max(yrs, 1), area, False, specs, tls)
                if (niche and reached >= 6 and specs and tls) else EMPTY
            )
            has_loc = reached >= 8
            rows.append([
                i, user_id, worker_chat_id, stage, False, False, NULL,
                job_category, tag, is_custom_ip,
                pg_array(specs), pg_array(tls), yrs, lic, desc,
                False, False, False, 0,
                NULL,
                phone() if reached >= 8 else NULL,
                address(area) if has_loc else NULL,
                lat if has_loc else NULL,
                lon if has_loc else NULL,
                f"SRID=4326;POINT({lon} {lat})" if has_loc else NULL,
            ])
            continue

        # --- completed rows -----------------------------------------------
        # 10%, not 4%. At 4% the ten rare trades ended up with 1-3 matchable
        # workers each, which is realistic but useless: a customer job in those
        # trades has almost no bench to rank, and with only one worker holding
        # the trade, the speciality-trim below could erase a speciality from
        # the dataset entirely. 10% gives roughly 10-14 workers per rare trade
        # while keeping them clearly rarer than plumbing or electrical.
        is_custom = rng.random() < 0.10
        if is_custom:
            tag = rng.choice(list(CUSTOM_TRADES.keys()))
            job_category, niches = CUSTOM_TRADES[tag]
            niche = rng.choice(niches)
        else:
            tag = rng.choices(tags, weights=weights, k=1)[0]
            job_category, niches = TRADES[tag]
            niche = rng.choice(niches)

        # specialities: the niche set, sometimes trimmed or extended.
        # Trimming only for standard trades. Rare trades have so few workers
        # that dropping a speciality can remove it from the whole dataset, and
        # then a customer job asking for it has literally nobody to match.
        specs = list(niche["specialities"])
        if len(specs) > 2 and not is_custom and rng.random() < 0.25:
            specs = rng.sample(specs, k=len(specs) - 1)
        if rng.random() < 0.30:
            # Extra specialities may only come from OTHER niches of the SAME
            # trade. Pulling from a different trade is what previously put
            # "lock-picking" on a chimney specialist.
            source = CUSTOM_TRADES if is_custom else TRADES
            extra_pool = [s for nn in source[tag][1] for s in nn["specialities"]]
            extra = [s for s in extra_pool if s not in specs]
            if extra:
                specs.append(rng.choice(extra))
        rng.shuffle(specs)

        tls = list(niche["tools"])
        if len(tls) > 2:
            tls = rng.sample(tls, k=rng.randint(2, len(tls)))
        rng.shuffle(tls)

        yrs = rng.choices(
            [rng.randint(1, 3), rng.randint(4, 9), rng.randint(10, 18), rng.randint(19, 32)],
            weights=[25, 40, 27, 8], k=1,
        )[0]

        # license tier correlates with experience, but not perfectly
        lic_roll = rng.random()
        if yrs <= 3:
            tier = "formal" if lic_roll < 0.35 else ("informal" if lic_roll < 0.75 else "none")
        elif yrs <= 9:
            tier = "formal" if lic_roll < 0.60 else ("informal" if lic_roll < 0.90 else "none")
        else:
            tier = "formal" if lic_roll < 0.75 else ("informal" if lic_roll < 0.95 else "none")
        lic = rng.choice(LICENSE_BY_TIER[tier])
        lic = NULL if lic is None else lic

        emergency = rng.random() < (0.45 if tag in {"plumbing", "electrical", "locksmith", "hvac"} else 0.18)

        if outcome == "approved":
            # Scenario gate: passes strictly above 75 (see worker_chat_analyser).
            scenario_score = rng.choices(
                [rng.randint(76, 82), rng.randint(83, 90), rng.randint(91, 97), rng.randint(98, 100)],
                weights=[30, 38, 26, 6], k=1,
            )[0]
            scenario_passed = True
            is_rejected = False
            rejection_reason = NULL
            stage = "complete"
            # verified specialty correlates with a formal license and experience
            p_verified = 0.20 + (0.35 if tier == "formal" else 0.0) + min(yrs, 20) * 0.012
            has_verified = rng.random() < min(p_verified, 0.92)
        else:  # rejected
            scenario_score = rng.choices(
                [rng.randint(0, 30), rng.randint(31, 55), rng.randint(56, 70), rng.randint(71, 75)],
                weights=[12, 30, 38, 20], k=1,
            )[0]
            scenario_passed = False
            is_rejected = True
            rejection_reason = rng.choice(REJECTION_REASONS)
            stage = "complete"
            has_verified = rng.random() < 0.10

        desc = build_description(niche, yrs, area, emergency, specs, tls)

        rows.append([
            i, user_id, worker_chat_id, stage, True, is_rejected, rejection_reason,
            job_category, tag, is_custom,
            pg_array(specs), pg_array(tls), yrs, lic, desc,
            emergency, has_verified, scenario_passed, scenario_score,
            NULL,                       # description_vector — backfilled later
            phone(), address(area), lat, lon,
            f"SRID=4326;POINT({lon} {lat})",
        ])

    return rows


def fmt(v) -> str:
    """
    Render one value as a PostgreSQL-CSV field.

    The critical distinction Postgres makes under FORMAT csv:
      unquoted empty field  ->  NULL
      quoted empty field "" ->  empty string ''
    Python's csv.writer cannot express that difference, so fields are
    formatted by hand here.
    """
    if v is None:
        return ""                       # -> SQL NULL
    if isinstance(v, bool):
        return "true" if v else "false"
    if v == "":
        return '""'                     # -> empty string, for NOT NULL text cols

    s = str(v)
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
