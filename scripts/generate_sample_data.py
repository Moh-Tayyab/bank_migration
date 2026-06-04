#!/usr/bin/env python3
"""
Generate realistic WorldCheck sample data based on validation report statistics.
Produces 50 records that match the distribution in data/worldcheck_validation_report.json.
"""

import json
import csv
import random
from pathlib import Path
from datetime import date, timedelta

random.seed(42)  # Reproducible

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

# Distributions from validation report
CATEGORIES = [
    ("CRIME - TERROR", 4),
    ("NONCONVICTION TERROR", 3),
    ("CRIME - WAR", 3),
    ("CRIME - FINANCIAL", 3),
    ("POLITICAL INDIVIDUAL", 20),  # 40% PEP-leaning
    ("INDIVIDUAL", 17),  # 34% with first_name NULL = entities
]

# Sample first names (real, public-record style)
FIRST_NAMES = [
    "Sadi Tuma Abbas", "Humam abd-al-Khaliq", "Mahmud Dhiyab",
    "Yusuf Ibrahim", "Ahmad al-Rashid", "Khaled Mansour",
    "Omar Hassan", "Faisal Al-Sabah", "Tariq Aziz",
    "Nasser al-Kidwa", "Hassan Rouhani", "Mahmoud Abbas",
    "Ali Abdullah", "Saddam Hussein", "Muammar Gaddafi",
    "Bashar al-Assad", "Recep Erdogan", "Mohamed Morsi",
    "Hosni Mubarak", "Zine El Abidine", "Vladimir Putin",
    "Dmitry Medvedev", "Hugo Chavez", "Fidel Castro",
    "Raul Castro", "Kim Jong-un", "Xi Jinping",
    "Narendra Modi", "Imran Khan", "Sheikh Hasina",
    "Yoweri Museveni", "Paul Kagame", "Robert Mugabe",
]

# Sample last names (entity & person mix)
LAST_NAMES_PERSON = [
    "AL-JABBURI", "ABD-AL-GHAFUR", "AL-ASSAD", "AL-NASHIR",
    "HUSSEIN", "AL-DIN", "AL-QADHAFI", "AL-SABAH",
    "KHAN", "ABBAS", "MANSOUR", "HASSAN",
    "ROUHANI", "MORSI", "MUBARAK", "PUTIN",
    "CASTRO", "CHAVEZ", "MODI", "MUSEVENI",
    "KAGAME", "MUGABE", "XI", "KIM",
    "AL-RASHID", "AL-KIDWA", "AZIZ", "JABER",
    "AL-ZAWAHIRI", "AL-ZARQAWI", "BIN LADEN",
    "AL-SHABAAB", "AL-QAIDA", "TALIBAN",
]

# Entity names (no first_name)
ENTITY_NAMES = [
    "REVOLUTIONARY ORGANIZATION 17 NOVEMBER",
    "AL-QAIDA IN THE ARABIAN PENINSULA",
    "ISLAMIC STATE OF IRAQ AND SYRIA",
    "HEZBOLLAH MILITANT WING",
    "TALIBAN SUPREME COUNCIL",
    "HAMAS POLITICAL BUREAU",
    "BOKO HARAM SENIOR LEADERSHIP",
    "AL-SHABAAB INTELLIGENCE UNIT",
    "KURDISTAN WORKERS PARTY",
    "REAL IRA PROVISIONAL COUNCIL",
    "ETERNAL STRUGGLE MOVEMENT",
    "FATHERLAND LIBERATION FRONT",
    "GLOBAL RELIEF FOUNDATION",
    "BENEVOLENT INTERNATIONAL FOUNDATION",
    "HUMANITARIAN AID SOCIETY",
    "EASTERN DEVELOPMENT BANK",
    "NORTHERN OIL TRADING COMPANY",
    "GLOBAL INVESTMENT HOLDINGS",
    "INTERNATIONAL TRADE PARTNERS",
]

# Sample date pools (from validation report)
ENTERED_DATES = [
    "2000-11-10", "2000-10-16", "2000-10-16", "2000-11-10",
    "2001-03-22", "2001-05-15", "2001-09-08", "2002-01-12",
    "2002-06-30", "2003-04-18", "2003-08-25", "2004-02-14",
    "2004-07-09", "2005-11-03", "2006-05-20",
    "2007-09-14",
]

UPDATED_DATES = [
    "2022-11-15", "2022-08-30", "2023-04-06", "2023-01-22",
    "2022-06-18", "2022-12-10", "2023-05-14", "2023-02-28",
    "2022-09-05", "2022-10-20", "2023-03-15", "2022-07-12",
    "2022-11-30", "2023-01-08", "2022-05-25",
    "2022-04-10",
]

records = []
uid = 1

for category, count in CATEGORIES:
    for i in range(count):
        # 34% of records have first_name = NULL (mostly entities)
        is_entity = (category in ["CRIME - TERROR", "NONCONVICTION TERROR", "CRIME - WAR",
                                   "CRIME - FINANCIAL"]) or (random.random() < 0.34)

        if is_entity and category not in ["POLITICAL INDIVIDUAL", "INDIVIDUAL"]:
            # Pure entity record
            first_name = None
            last_name = random.choice(ENTITY_NAMES)
            ei = "E"
        elif is_entity:
            # Some POLITICAL INDIVIDUAL / INDIVIDUAL are stored as entities
            first_name = None
            last_name = random.choice(ENTITY_NAMES)
            ei = "E"
        else:
            # Person record
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES_PERSON)
            ei = random.choice(["M", "F"])

        # Sub-category: 66% have PEP for POLITICAL INDIVIDUAL, 0% for others
        if category == "POLITICAL INDIVIDUAL":
            sub_category = "PEP" if random.random() < 0.85 else None
        else:
            sub_category = None

        record = {
            "category": category,
            "editor": None,  # 100% NULL per validation report
            "entered": random.choice(ENTERED_DATES),
            "sub-category": sub_category,
            "uid": uid,
            "updated": random.choice(UPDATED_DATES),
            "entity_type": "person",
            "e-i": ei,
            "first_name": first_name,
            "last_name": last_name,
        }
        records.append(record)
        uid += 1

# Shuffle so categories are mixed (validation report showed mixed sample)
random.shuffle(records)

# Write JSON
json_path = OUTPUT_DIR / "worldcheck_raw.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(records, f, indent=2, ensure_ascii=False)

# Write CSV
csv_path = OUTPUT_DIR / "worldcheck_raw.csv"
with open(csv_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
    writer.writeheader()
    for rec in records:
        writer.writerow(rec)

# Stats
print(f"Generated {len(records)} records")
print(f"  JSON: {json_path}")
print(f"  CSV:  {csv_path}")
print(f"\nDistribution:")
from collections import Counter
cat_counts = Counter(r["category"] for r in records)
ei_counts = Counter(r["e-i"] for r in records)
null_fn = sum(1 for r in records if r["first_name"] is None)
null_subcat = sum(1 for r in records if r["sub-category"] is None)

print("  Categories:", dict(cat_counts))
print("  E/I:", dict(ei_counts))
print(f"  first_name NULL: {null_fn}/{len(records)} ({null_fn/len(records)*100:.0f}%)")
print(f"  sub-category NULL: {null_subcat}/{len(records)} ({null_subcat/len(records)*100:.0f}%)")
