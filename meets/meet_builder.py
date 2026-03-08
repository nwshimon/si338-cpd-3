import os
import csv
import re
from html import unescape

# =========================
# Configuration
# =========================

BASE_URL = "https://umsicomplexwebdesign.github.io/xc_data"

CSS_RESET = f"{BASE_URL}/css/reset.css"
CSS_STYLE = f"{BASE_URL}/css/style.css"

SKYLINE_LOGO = (
    "https://resources.finalsite.net/images/f_auto,q_auto/"
    "v1695416665/a2schoolsorg/udbk8bxpqrgvjkwteeut/"
    "SkylineHighSchoolPrimaryThumbnailImage.jpg"
)

OUTPUT_SUFFIX = "_race_page.html"
SKYLINE_TEAM_NAME = "Ann Arbor Skyline"


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


def read_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return [line.rstrip("\n") for line in f]


def find_line_index(lines: list[str], startswith: str) -> int:
    """Return index of the first line that starts with 'startswith', else -1."""
    for i, line in enumerate(lines):
        if line.startswith(startswith):
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

def underscore_name(name: str) -> str:
    """
    Convert a name like 'Matthew Guikema' or 'Lila Edison' to 'Matthew_Guikema'.
    For names with more than two parts (e.g., 'Mary Jane Smith'), joins all parts with underscores.
    """
    parts = name.split()
    return "_".join(parts)

# =========================
# Main: process all CSVs in current folder
# =========================

for filename in os.listdir("."):
    if not filename.lower().endswith(".csv"):
        continue

    lines = read_lines(filename)
    if len(lines) < 6:
        print(f"Skipping {filename}: not enough lines to match expected format.")
        continue

    # ---- Meet metadata (first 4 lines) ----
    meet_name = lines[0].strip()
    meet_date = lines[1].strip() if len(lines) > 1 else ""
    meet_link = lines[2].strip() if len(lines) > 2 else ""
    summary_html = lines[3].strip() if len(lines) > 3 else ""
    summary_text = strip_html(summary_html)

    # ---- Locate blocks ----
    team_header_idx = find_line_index(lines, "Place,Team,Score")
    indiv_header_idx = find_line_index(lines, "Place,Grade,Name,")

    if team_header_idx == -1 or indiv_header_idx == -1:
        print(f"Skipping {filename}: could not find required CSV headers.")
        continue

    # # ---- Team results block (optional for this output, but we parse safely) ----
    # # Team block lines start at team_header_idx and go up to the blank line before indiv_header_idx
    # team_block_lines = []
    # for i in range(team_header_idx, indiv_header_idx):
    #     if lines[i].strip() == "" and i > team_header_idx:
    #         break
    #     team_block_lines.append(lines[i])

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
    skyline_rows_html = ""
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
            grade = safe_get(r, "Grade")
            athlete_id = safe_get(r, "Profile Pic").replace('.jpg', '').replace('.jpeg', '')

            if name and athlete_id:
                underscored_name = underscore_name(name)
                athlete_page_link = f"../mens_team/{underscored_name}{athlete_id}.html"
            else:
                athlete_page_link = "#"

            skyline_rows_html += f"""
        <tr>
          <td><a href="{athlete_page_link}">{name}</a></td>
          <td>{time}</td>
          <td>{place}</td>
          <td>{grade}</td>
        </tr>"""
    else:
        skyline_rows_html = """
        <tr>
          <td colspan="4">No Skyline runners found in this file (Team != "Ann Arbor Skyline").</td>
        </tr>"""

    # 

    # ---- Build HTML (race_page format) ----
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{meet_name}</title>
  <link rel="stylesheet" href="reset.css">
  <link rel="stylesheet" href="../css/style.css">
</head>

<body>

<header>
  <div class="header-content">
    <a href="../index.html">
        <img src="{SKYLINE_LOGO}" alt="Skyline High School logo">
    </a>
    <div class="header-text">
      <h1>{meet_name}</h1>
      <p>{meet_date} &nbsp; <a href="{meet_link}">Meet results</a></p>
    </div>
  </div>
</header>

<main>
  <p>{summary_text}</p>
</main>

<table>
  <caption>Skyline Results</caption>
  <thead>
    <tr>
      <th scope="col">Name</th>
      <th scope="col">Time</th>
      <th scope="col">Placement</th>
      <th scope="col">Grade</th>
    </tr>
  </thead>
  <tbody>
    {skyline_rows_html}
  </tbody>
</table>

<footer>
  <p>All data gathered from team race records.</p>
</footer>

</body>
</html>
"""

    output_file = filename[:-4] + OUTPUT_SUFFIX
    with open(output_file, "w", encoding="utf-8") as out:
        out.write(html)

    print(f"Generated {output_file} ({len(skyline)} Skyline runners)")
