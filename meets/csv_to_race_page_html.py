import csv
import html
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

# Hosted site root (used for CSS + image links in the generated HTML)
BASE_URL = "https://umsicomplexwebdesign.github.io/xc_data/"

# External logo used in the race_page.html example
SKYLINE_LOGO_URL = (
    "https://resources.finalsite.net/images/f_auto,q_auto/v1695416665/"
    "a2schoolsorg/udbk8bxpqrgvjkwteeut/SkylineHighSchoolPrimaryThumbnailImage.jpg"
)


def strip_html_tags(s: str) -> str:
    """Convert a small HTML snippet into plain text (keeps line breaks)."""
    s = re.sub(r"<\s*br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()


def extract_meet_id(url: str) -> Optional[str]:
    """Extract the numeric meet id from an Athletic.net URL."""
    m = re.search(r"/meet/(\d+)", url)
    return m.group(1) if m else None


def ordinal(place: str) -> str:
    """Convert '23.' -> '23rd'. If not numeric, return original."""
    place = place.strip().rstrip(".")
    if not place.isdigit():
        return place
    n = int(place)
    if 11 <= (n % 100) <= 13:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def parse_custom_meet_csv(csv_filename: str) -> Dict:
    """
    Parse the custom meet CSV format used by the existing builder.

    Expected layout:
      Row 0: Meet name (single cell)
      Row 1: Meet date (single cell)
      Row 2: Meet results URL (single cell)
      Row 3: Summary HTML (single cell)
      Row 4..N: Team Results table (3 cols) until a blank row
      Next: Individual Results header (8 cols), then data rows to EOF
    """
    with open(csv_filename, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if len(rows) < 5:
        raise ValueError("CSV file must have at least 5 rows.")

    meet_name = rows[0][0].strip()
    meet_date = rows[1][0].strip()
    meet_url = rows[2][0].strip()

    summary_raw = rows[3][0].strip()
    if (summary_raw.startswith('"') and summary_raw.endswith('"')) or (
        summary_raw.startswith("'") and summary_raw.endswith("'")
    ):
        summary_raw = summary_raw[1:-1]
    summary_text = strip_html_tags(summary_raw)

    # Team results
    team_results: List[Dict[str, str]] = []
    i = 4
    while i < len(rows):
        row = rows[i]
        if len(row) == 0 or all(c.strip() == "" for c in row):
            i += 1
            break
        if len(row) >= 3 and row[0].strip() != "Place":
            team_results.append(
                {"place": row[0].strip(), "team": row[1].strip(), "score": row[2].strip()}
            )
        i += 1

    # Individual results
    individual_results: List[Dict[str, str]] = []
    if i < len(rows) and len(rows[i]) >= 8 and rows[i][0].strip() == "Place":
        i += 1

    for j in range(i, len(rows)):
        row = rows[j]
        if len(row) == 0 or all(c.strip() == "" for c in row):
            continue
        if len(row) < 8:
            continue

        individual_results.append(
            {
                "place": row[0].strip(),
                "grade": row[1].strip(),
                "name": row[2].strip(),
                "athlete_link": row[3].strip(),
                "time": row[4].strip(),
                "team": row[5].strip(),
                "team_link": row[6].strip(),
                "profile_pic": row[7].strip(),
            }
        )

    return {
        "meet_name": meet_name,
        "meet_date": meet_date,
        "meet_url": meet_url,
        "summary_text": summary_text,
        "team_results": team_results,
        "individual_results": individual_results,
        "meet_id": extract_meet_id(meet_url),
    }


def pick_meet_photo_local(repo_root: str, meet_id: Optional[str]) -> Optional[str]:
    """
    If the repo has images/meets/<meet_id>/, return one image filename to use as the hero image.
    (We output a *hosted* URL, but we pick based on local repo contents so generation is deterministic.)
    """
    if not meet_id:
        return None

    folder = Path(repo_root) / "images" / "meets" / meet_id
    if not folder.exists() or not folder.is_dir():
        return None

    imgs = [p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}]
    if not imgs:
        return None

    imgs = sorted(imgs, key=lambda p: p.name.lower())
    return imgs[0].name


def build_race_page_html(meet: Dict, repo_root: Optional[str] = None, include_team_table: bool = False) -> str:
    """Generate HTML in the 'race_page.html' style (header hero + summary + Skyline results table)."""
    include_team_table = False
    css_reset = f"{BASE_URL}css/reset.css"
    css_style = f"{BASE_URL}css/style.css"

    meet_photo_url = None
    if repo_root:
        photo_name = pick_meet_photo_local(repo_root, meet.get("meet_id"))
        if photo_name:
            meet_photo_url = f'{BASE_URL}images/meets/{meet.get("meet_id")}/{photo_name}'

    # Filter to Skyline only (fallback to all runners if none match)
    skyline = [r for r in meet["individual_results"] if r["team"].strip().lower() == "ann arbor skyline"]
    runners = skyline if skyline else meet["individual_results"]

    summary_html = html.escape(meet["summary_text"]).replace("\n", "<br>\n")

    parts: List[str] = []
    parts.append(f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(meet["meet_name"])}</title>
  <link rel="stylesheet" href="{css_reset}">
  <link rel="stylesheet" href="{css_style}">
</head>

<body>
<a class="skip-link" href="#main">Skip to Main Content</a>

<header>
  <div class="header-content">
    <img src="{SKYLINE_LOGO_URL}" alt="Skyline High School logo">
    <div class="header-text">
      <h1>{html.escape(meet["meet_name"])}</h1>
      <p>{html.escape(meet["meet_date"])} <a href="{html.escape(meet["meet_url"])}">Meet results</a></p>
    </div>
  </div>
</header>

<main id="main">
  <p>
    {summary_html}
  </p>
""")

    if meet_photo_url:
        parts.append(f'  <img src="{meet_photo_url}" alt="{html.escape(meet["meet_name"])} photo">\n')

    parts.append("""  <table>
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
""")

    for r in runners:
        name_text = html.escape(r["name"])
        athlete_link = r.get("athlete_link", "").strip()
        name_cell = f'<a href="{html.escape(athlete_link)}">{name_text}</a>' if athlete_link else name_text

        time_cell = html.escape(r["time"])
        placement_cell = html.escape(ordinal(r["place"]))
        grade_cell = html.escape(r["grade"])

        parts.append(
            f"      <tr><td>{name_cell}</td><td>{time_cell}</td>"
            f"<td>{placement_cell}</td><td>{grade_cell}</td></tr>\n"
        )

    parts.append("    </tbody>\n  </table>\n")

    if include_team_table and meet.get("team_results"):
        parts.append("""  <table>
    <caption>Team Results</caption>
    <thead>
      <tr>
        <th scope="col">Place</th>
        <th scope="col">Team</th>
        <th scope="col">Score</th>
      </tr>
    </thead>
    <tbody>
""")
        for t in meet["team_results"]:
            parts.append(
                f'      <tr><td>{html.escape(t["place"])}</td>'
                f'<td>{html.escape(t["team"])}</td>'
                f'<td>{html.escape(t["score"])}</td></tr>\n'
            )
        parts.append("    </tbody>\n  </table>\n")

    parts.append("""</main>

<footer>
  <p>Data from the team race spreadsheet and Athletic.net.</p>
</footer>

</body>
</html>
""")
    return "".join(parts)


def csv_to_race_page(csv_filename: str, output_folder: str, repo_root: Optional[str] = None) -> str:
    """Read one CSV and write one race_page-style HTML file in output_folder."""
    meet = parse_custom_meet_csv(csv_filename)

    output_folder_path = Path(output_folder)
    output_folder_path.mkdir(parents=True, exist_ok=True)

    out_file = output_folder_path / (Path(csv_filename).stem + ".html")
    html_content = build_race_page_html(meet, repo_root=repo_root)

    out_file.write_text(html_content, encoding="utf-8")
    return str(out_file)


def process_meet_files(meets_folder: Optional[str] = None, repo_root: Optional[str] = None) -> None:
    """
    Convert every .csv in a meets folder into a race_page-style .html file.

    Typical usage (run from repo root):
      python csv_to_race_page_html.py
    """
    if meets_folder is None:
        meets_folder = os.path.join(os.getcwd(), "meets")

    csv_files = [f for f in os.listdir(meets_folder) if f.lower().endswith(".csv")]
    if not csv_files:
        print(f"No CSV files found in folder: {meets_folder}")
        return

    for csv_file in csv_files:
        csv_path = os.path.join(meets_folder, csv_file)
        out = csv_to_race_page(csv_path, meets_folder, repo_root=repo_root)
        print(f"Wrote {out}")


if __name__ == "__main__":
    # If you run this script from the repo root, repo_root=os.getcwd() will allow the script
    # to look for a local images/meets/<meet_id>/ folder (to choose a hero image filename).
    # Links in HTML will still point to the hosted BASE_URL.
    process_meet_files(repo_root=os.getcwd())
