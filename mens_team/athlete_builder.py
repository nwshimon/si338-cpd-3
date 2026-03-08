import csv
import glob
import os
import re
from html import escape

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

DEFAULT_TEAM_LABEL = "Ann Arbor Skyline Cross Country"

# If script is placed in repo root, it will look in these folders (if they exist).
DEFAULT_INPUT_DIRS = ["mens_team", "womens_team"]

OUTPUT_EXT = ".html"


# =========================
# Helpers
# =========================

def athletic_profile_url(athlete_id: str) -> str:
    athlete_id = athlete_id.strip()
    return f"https://www.athletic.net/athlete/{athlete_id}/cross-country/" if athlete_id else "#"


def hosted_profile_img_url(athlete_id: str) -> str:
    athlete_id = athlete_id.strip()
    return f"{BASE_URL}/images/profiles/{athlete_id}.jpg" if athlete_id else f"{BASE_URL}/images/profiles/default_image.jpg"


def ordinal(place_str: str) -> str:
    """Convert '23', '23.', '23 ' -> '23rd' etc. If not numeric, return original."""
    if place_str is None:
        return ""
    s = str(place_str).strip().rstrip(".")
    if not s.isdigit():
        return str(place_str).strip()
    n = int(s)
    if 10 <= (n % 100) <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def parse_time_to_seconds(t: str):
    """
    Parse times like '16:34.8PR', '17:55.6 SR', '21:08.4' into seconds (float).
    Returns None if parsing fails.
    """
    if not t:
        return None
    s = str(t).strip()
    # strip common annotations
    s = re.sub(r"(PR|\*|SR)", "", s, flags=re.IGNORECASE).strip()
    # keep only digits, colon, dot
    s = re.sub(r"[^0-9:\.]", "", s)
    if ":" not in s:
        return None
    parts = s.split(":")
    if len(parts) != 2:
        return None
    try:
        minutes = int(parts[0])
        seconds = float(parts[1])
        return minutes * 60 + seconds
    except ValueError:
        return None


def find_header_index(rows):
    """
    Find the header row that contains Meet / Meet URL.
    Returns (idx, header) or (-1, None).
    """
    for i, r in enumerate(rows):
        if not r:
            continue
        joined = ",".join([c.strip() for c in r]).lower()
        if "meet url" in joined and "overall place" in joined:
            return i, r
    return -1, None


def safe_get(d, key, default=""):
    v = d.get(key, default)
    return "" if v is None else str(v)

def safe_filename(path):
    """
    Replace spaces with underscores in the filename.
    """
    p_no_ext = os.path.splitext(path)[0]
    dir_part, file_part = os.path.split(p_no_ext)
    file_part = file_part.replace(" ", "_")
    return os.path.join(dir_part, file_part + OUTPUT_EXT)

# =========================
# Parsing athlete CSV
# =========================

def parse_athlete_csv(path: str):
    """
    Supports the athlete CSV format you showed:
      row 0: athlete name
      row 1: athlete id
      blank rows
      header row: Name, Overall Place, Grade, Time, Date, Meet, Meet URL, Comments, Photo
      then:
        - Season record rows: Overall Place is a YEAR (e.g., 2022) and Grade filled
        - Race rows: Meet + Meet URL filled (Grade sometimes blank)
    """
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    athlete_name = rows[0][0].strip() if len(rows) > 0 and rows[0] else ""
    athlete_id = rows[1][0].strip() if len(rows) > 1 and rows[1] else ""

    header_idx, header = find_header_index(rows)
    if header_idx == -1:
        raise ValueError(f"Could not find athlete data header row in {path}")

    data_rows = rows[header_idx + 1 :]

    # Normalize header keys
    header_keys = [h.strip() for h in header]
    dict_rows = []
    for r in data_rows:
        if not any(cell.strip() for cell in r):
            continue
        # pad short rows
        if len(r) < len(header_keys):
            r = r + [""] * (len(header_keys) - len(r))
        dict_rows.append(dict(zip(header_keys, r)))

    season_records = []  # [{year, grade, sr_time}]
    races = []           # [{grade, meet, url, time, place}]

    for dr in dict_rows:
        overall_place = safe_get(dr, "Overall Place").strip()
        grade = safe_get(dr, "Grade").strip()
        time = safe_get(dr, "Time").strip()
        meet = safe_get(dr, "Meet").strip()
        meet_url = safe_get(dr, "Meet URL").strip()

        # Season record row: overall_place looks like a year and grade is present
        if overall_place.isdigit() and len(overall_place) == 4 and grade:
            season_records.append({
                "year": overall_place,
                "grade": grade,
                "sr": time
            })
            continue

        # Race row: has a meet name (and usually URL)
        if meet:
            races.append({
                "grade": grade,         # may be blank in your current CSVs
                "meet": meet,
                "url": meet_url or "#",
                "time": time,
                "place": overall_place
            })

    # Determine "most recent grade" from season_records
    most_recent_grade = None
    if season_records:
        # pick the largest year, then its grade
        season_records_sorted = sorted(
            season_records,
            key=lambda x: int(x["year"]) if str(x["year"]).isdigit() else -1
        )
        most_recent_grade = season_records_sorted[-1]["grade"]

    # If race grade is missing, assign to most recent grade (so tables are not empty)
    if most_recent_grade:
        for r in races:
            if not r["grade"]:
                r["grade"] = most_recent_grade

    return {
        "name": athlete_name,
        "athlete_id": athlete_id,
        "season_records": season_records,
        "races": races,
        "most_recent_grade": most_recent_grade
    }


# =========================
# Build bio text
# =========================

def build_auto_bio(data) -> str:
    """
    Generates a simple, non-embarrassing paragraph from stats available.
    """
    name = data["name"]
    grade = data.get("most_recent_grade") or "?"
    races = data["races"]

    best_time = None
    best_time_str = None
    best_place = None
    best_place_str = None
    best_place_meet = None

    for r in races:
        # best place (lowest numeric)
        p = str(r.get("place", "")).strip().rstrip(".")
        if p.isdigit():
            p_int = int(p)
            if best_place is None or p_int < best_place:
                best_place = p_int
                best_place_str = ordinal(p)
                best_place_meet = r.get("meet", "")

        # best time (lowest seconds)
        secs = parse_time_to_seconds(r.get("time", ""))
        if secs is not None and (best_time is None or secs < best_time):
            best_time = secs
            best_time_str = r.get("time", "")

    parts = []
    parts.append(f"{name} is a Skyline runner currently listed as grade {grade}.")
    if best_place_str and best_place_meet:
        parts.append(f"The best placement in these results is {best_place_str} at {best_place_meet}.")
    if best_time_str:
        parts.append(f"The best recorded time in these results is {best_time_str}.")
    parts.append("This page is automatically generated from the team’s race CSV data.")

    return " ".join(parts)


# =========================
# HTML generation
# =========================

def build_grade_tables(races):
    """
    Returns HTML for one table per grade, sorted by grade descending, then by meet name.
    Each table has columns: Race | Time | Placement
    """
    # group by grade
    by_grade = {}
    for r in races:
        g = str(r.get("grade", "")).strip() or "Other"
        by_grade.setdefault(g, []).append(r)

    # sort grade keys as integers when possible, descending
    def grade_sort_key(g):
        return int(g) if str(g).isdigit() else -999

    grade_keys = sorted(by_grade.keys(), key=grade_sort_key, reverse=True)

    tables_html = []

    for g in grade_keys:
        caption = f"{g}th Grade" if str(g).isdigit() else str(g)

        # sort rows by numeric place when possible
        def place_key(r):
            p = str(r.get("place", "")).strip().rstrip(".")
            return int(p) if p.isdigit() else 999999

        rows = sorted(by_grade[g], key=place_key)

        row_html = ""
        for r in rows:
            meet = escape(r.get("meet", ""))
            url = escape(r.get("url", "#"))
            time = escape(r.get("time", ""))
            place = escape(ordinal(r.get("place", "")))

            row_html += f"""
    <tr>
      <td><a href="{url}">{meet}</a></td>
      <td>{time}</td>
      <td>{place}</td>
    </tr>"""

        tables_html.append(f"""
<table>
  <caption>{escape(caption)}</caption>
  <thead>
    <tr>
      <th scope="col">Race</th>
      <th scope="col">Time</th>
      <th scope="col">Placement</th>
    </tr>
  </thead>
  <tbody>
    {row_html}
  </tbody>
</table>
""")

    return "\n".join(tables_html)


def generate_runner_page(data) -> str:
    name = escape(data["name"])
    athlete_id = escape(data["athlete_id"])
    grade = escape(data.get("most_recent_grade") or "?")

    profile_url = athletic_profile_url(data["athlete_id"])
    profile_img = hosted_profile_img_url(data["athlete_id"])

    bio = escape(build_auto_bio(data))

    tables = build_grade_tables(data["races"])

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{name}</title>
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
      <h1>{name}</h1>
      <p>Grade: {grade} &nbsp; <a href="{profile_url}">Athletic.net Profile</a></p>
    </div>
  </div>
</header>

<main>
  <p>{bio}</p>
  <img src="{profile_img}" alt="{name} profile photo">
</main>

{tables}

<footer>
  <p>All data gathered from the team’s race spreadsheet.</p>
</footer>
</body>
</html>
"""
    return html


# =========================
# Main
# =========================

def find_input_dirs():
    """
    If script is in a team folder (mens_team or womens_team), process only that folder.
    If script is in repo root, process DEFAULT_INPUT_DIRS that exist.
    """
    here = os.path.abspath(os.getcwd())
    base = os.path.basename(here)

    if base in ("mens_team", "womens_team"):
        return ["."]
    else:
        existing = [d for d in DEFAULT_INPUT_DIRS if os.path.isdir(d)]
        return existing if existing else ["."]
    

def main():
    input_dirs = find_input_dirs()

    for d in input_dirs:
        pattern = os.path.join(d, "*.csv")
        csv_files = glob.glob(pattern)

        if not csv_files:
            print(f"No CSV files found in {d}")
            continue

        for csv_path in csv_files:
            try:
                data = parse_athlete_csv(csv_path)
                html = generate_runner_page(data)

                ###out_path = os.path.splitext(csv_path)[0] + OUTPUT_EXT
                out_path = safe_filename(csv_path)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(html)

                print(f"Generated {out_path}")

            except Exception as e:
                print(f"ERROR processing {csv_path}: {e}")


if __name__ == "__main__":
    main()
