import os
import csv
import re
from html import unescape
from datetime import datetime

# =========================
# Configuration
# =========================

BASE_URL = "https://umsicomplexwebdesign.github.io/xc_data"

CSS_RESET = f"{BASE_URL}/css/reset.css"
CSS_STYLE = f"../css/style.css"

SKYLINE_LOGO = (
    "https://resources.finalsite.net/images/f_auto,q_auto/"
    "v1695416665/a2schoolsorg/udbk8bxpqrgvjkwteeut/"
    "SkylineHighSchoolPrimaryThumbnailImage.jpg"
)

# OUTPUT_SUFFIX = "_race_page.html"
SKYLINE_TEAM_NAME = "Ann Arbor Skyline"

MEETS_DIR = "meets"

# =========================
# Helpers
# =========================

def strip_html(text: str) -> str:
    """Convert HTML-ish summary into plain text."""
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(text.split()).strip()


def ordinal(place_str: str) -> str:
    """Convert '23.' or '23' to '23rd' etc."""
    if not place_str:
        return ""
    s = str(place_str).strip()
    s = s.rstrip(".")
    if not s.isdigit():
        return place_str

    n = int(s)
    if 10 <= (n % 100) <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"

# def parse_date(date_str: str) -> datetime:
#     return datetime.strptime(date_str.strip(), "%b %d %Y")


def read_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return [line.rstrip("\n") for line in f]


# def find_line_index(lines: list[str], startswith: str) -> int:
#     """Return index of the first line that starts with 'startswith', else -1."""
#     for i, line in enumerate(lines):
#         if line.startswith(startswith):
#             return i
#     return -1

def find_line_index(lines: list[str], contains: str) -> int:
    for i, line in enumerate(lines):
        if contains in line:
            return i
    return -1


def parse_csv_block(block_lines: list[str]) -> list[list[str]]:
    """
    Parse a list of CSV lines into rows using csv.reader.
    This respects quoted commas.
    """
    reader = csv.reader(block_lines)
    return [row for row in reader if any(cell.strip() for cell in row)]


def safe_get(row_dict: dict, key: str, default: str = "") -> str:
    val = row_dict.get(key, default)
    return "" if val is None else str(val)

import re

def slugify_filename(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^\w\s-]", "", name)  # remove #, (), etc
    name = re.sub(r"\s+", "_", name)      # spaces → underscores
    return name


# =========================
# Main: process all CSVs in current folder
# =========================

# PROCESS RECENT RACES

recent_races = {} # a dictionary
# key = race name
# value = list of [meet_date (str), race_html_filename (str), skyline (list[dict[str, str]])]

for filename in os.listdir(MEETS_DIR):
    if not filename.lower().endswith(".csv"):
        continue
   
    if "womens" in filename.lower():
        continue

    path = os.path.join(MEETS_DIR, filename)
    lines = read_lines(path)
    
    if len(lines) < 6:
        print(f"Skipping {filename}: not enough lines to match expected format.")
        continue

    # ---- Meet metadata (first 4 lines) ----
    meet_name = lines[0].strip()
    meet_date = lines[1].strip() if len(lines) > 1 else ""
    # meet_link = lines[2].strip() if len(lines) > 2 else ""
    summary_html = lines[3].strip() if len(lines) > 3 else ""

    # ---- Locate blocks ----
    team_header_idx = find_line_index(lines, "Place,Team")
    indiv_header_idx = find_line_index(lines, "Place,Grade,Name")
    if team_header_idx == -1 or indiv_header_idx == -1:
        print(f"Skipping {filename}: could not find required CSV headers.")
        continue

        # ---- Individual results block ----
    indiv_block_lines = [line for line in lines[indiv_header_idx:] if line.strip() != ""]

    indiv_rows = parse_csv_block(indiv_block_lines)
    if len(indiv_rows) < 2:
        print(f"Skipping {filename}: no individual data rows found.")
        continue

    indiv_header = indiv_rows[0]
    indiv_data = indiv_rows[1:]

    # Build dicts for each athlete row
    indiv_dicts = []
    for row in indiv_data:
        # Pad short rows (in case a line is missing trailing columns)
        if len(row) < len(indiv_header):
            row = row + [""] * (len(indiv_header) - len(row))
        indiv_dicts.append(dict(zip(indiv_header, row)))

    # Filter Skyline runners
    skyline = [
        r for r in indiv_dicts
        if safe_get(r, "Team").strip() == SKYLINE_TEAM_NAME
    ]

    # If no Skyline rows, show a message but still build page
    skyline_rows_html = "" # we don't technically need this skyline_rows_html markup
    if skyline:
        # Sort by numeric place if possible
        def place_key(r):
            p = safe_get(r, "Place").strip().rstrip(".")
            return int(p) if p.isdigit() else 999999

        skyline.sort(key=place_key)

        for r in skyline:
            name = safe_get(r, "Name")
            time = safe_get(r, "Time")
            place = ordinal(safe_get(r, "Place"))

            skyline_rows_html += f"""
        <tr>
          <td>{name}</a></td>
          <td>{time}</td>
          <td>{place}</td>
        </tr>"""
    else:
        skyline_rows_html = """
        <tr>
          <td colspan="4">No Skyline runners found in this file (Team != "Ann Arbor Skyline").</td>
        </tr>"""

    base = filename.replace(".csv", "")
    #safe_name = slugify_filename(base)#
    race_html = f"{MEETS_DIR}/{base}_race_page.html"

    recent_races[meet_name] = [
        meet_date,
        skyline,
        race_html
    ]

home_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <link rel="stylesheet" href="css/style.css">
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Skyline Cross Country Home Page</title>
</head>

<body>
<header>
  <div class="header-content">
    <img src="https://resources.finalsite.net/images/f_auto,q_auto/v1695416665/a2schoolsorg/udbk8bxpqrgvjkwteeut/SkylineHighSchoolPrimaryThumbnailImage.jpg" alt="Skyline High School logo">
    <div class="header-text">
      <h1>Ann Arbor Skyline Cross Country</h1>
      <p>Welcome to the home for Ann Arbor Skyline Cross Country. Find information on recent races, individual stats, and more.</p>
    </div>
  </div>
</header>

<main>
  <h2>Recent Races</h2>
  <ul class="timeline">
"""

sorted_keys = sorted(
    recent_races,
    key=lambda race: datetime.strptime(
        recent_races[race][0], "%a %b %d %Y"
    )
)

for meet in sorted_keys:
    race_info = recent_races[meet]
    meet_date = race_info[0]
    skyline_runners = race_info[1]
    race_html_file = race_info[2]

    home_html += f"""
    <li class="timeline-event">
        <span class="timeline-event-icon"></span>
        <div class="timeline-event-copy">
        <p class="timeline-event-thumbnail">{meet_date}</p>

    <details class="race-card">
    <summary>
        <h3>{meet}</h3>
    </summary>
    <div class="race-card-content">
        <h4>Top Skyline Runners</h4>
        <dl>
"""
    for r in skyline_runners[:4]:
        name = safe_get(r, "Name")
        time = safe_get(r, "Time")
        athlete_id = safe_get(r, "Profile Pic").replace('.jpg', '').replace('.jpeg', '')

        if name and athlete_id:
            athlete_page_link = f"mens_team/{name}{athlete_id}.html"
            home_html += f"""
            <dt><a href="{athlete_page_link}">{name}</a></dt><dd>{time}</dd>
            """
        else:
            home_html += f"""
            <dt>{name}</dt><dd>{time}</dd>
            """
        # print(name, time)
        #home_html += f"""
            #<dt>{name}</dt><dd>{time}</dd>
        #"""
    home_html += f"""
        </dl>
        
        <p><a href={race_html_file}>Meet Results</a></p>
        </div>
    </details>
    </div>
    </li>
    """
home_html += f"""
</ul>
</main>

<section class="roster-section">
<h2>Team Roster</h2>
  <button class="roster-toggle" aria-expanded="false" aria-controls="roster-list">
    Show/Hide Roster
  </button>

    <ul id="roster-list" class="roster-list" hidden>
"""

roster = {}
# key = runner name
# value = full athlete page path

for meet_name, (meet_date, skyline, race_html) in recent_races.items():
    for r in skyline:
        name = safe_get(r, "Name")
        athlete_id = safe_get(r, "Profile Pic").replace(".jpg", "").replace(".jpeg", "")

        if name and athlete_id and name not in roster:
            roster[name] = f"mens_team/{name}{athlete_id}.html"

for name in sorted(roster):
    link = roster[name]
    home_html += f"""
    <li>
      <a href="{link}">{name}</a>
    </li>
    """

home_html += """
  </ul>
</section>


<script>
  const toggleButton = document.querySelector('.roster-toggle');
  const rosterList = document.getElementById('roster-list');

  toggleButton.addEventListener('click', () => {
    const isHidden = rosterList.hasAttribute('hidden');

    if (isHidden) {
      rosterList.removeAttribute('hidden');
      toggleButton.setAttribute('aria-expanded', 'true');
    } else {
      rosterList.setAttribute('hidden', '');
      toggleButton.setAttribute('aria-expanded', 'false');
    }
  });
</script>

</main>
<footer>
    <p>All data gathered from Garrett's race spreadsheet. Thanks Garrett!</p>
</footer>
</body>
</html>
"""


with open("index.html", "w", encoding="utf-8") as f:
    f.write(home_html)

print(f"Generated index.html with {len(recent_races)} races")