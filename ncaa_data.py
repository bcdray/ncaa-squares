import requests
from datetime import datetime, timedelta

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"

# NCAA tournament round names by number of teams remaining
ROUND_MAP = {
    1: "Round of 64",
    2: "Round of 32",
    3: "Sweet 16",
    4: "Elite 8",
    5: "Final Four",
    6: "Championship",
}


def _parse_round(event):
    """Extract round name from ESPN event data."""
    # Check notes for round info
    for note in event.get("notes", []):
        headline = note.get("headline", "").lower()
        if "championship" in headline or "national championship" in headline:
            return "Championship"
        if "final four" in headline or "semifinal" in headline:
            return "Final Four"
        if "elite" in headline:
            return "Elite 8"
        if "sweet" in headline:
            return "Sweet 16"
        if "2nd round" in headline or "second round" in headline or "round of 32" in headline:
            return "Round of 32"
        if "1st round" in headline or "first round" in headline or "round of 64" in headline:
            return "Round of 64"

    # Fallback: check season type and round number
    season = event.get("season", {})
    slug = season.get("slug", "")
    if "post" in slug or "tournament" in slug:
        pass

    return "Tournament"


def _parse_game(event):
    """Parse a single ESPN event into a game dict."""
    competition = event.get("competitions", [{}])[0]
    competitors = competition.get("competitors", [])

    if len(competitors) < 2:
        return None

    status_obj = competition.get("status", event.get("status", {}))
    status_type = status_obj.get("type", {})
    state = status_type.get("state", "pre")  # pre, in, post
    status_detail = status_type.get("shortDetail", "")

    teams = []
    for comp in competitors:
        team_data = comp.get("team", {})
        teams.append({
            "name": team_data.get("shortDisplayName", team_data.get("displayName", "Unknown")),
            "abbreviation": team_data.get("abbreviation", ""),
            "seed": comp.get("curatedRank", {}).get("current", comp.get("seed", "")),
            "score": int(comp.get("score", 0)) if comp.get("score") else 0,
            "winner": comp.get("winner", False),
            "home_away": comp.get("homeAway", ""),
        })

    # Sort so higher score is first (winner)
    teams.sort(key=lambda t: t["score"], reverse=True)

    game_date = event.get("date", "")
    try:
        dt = datetime.fromisoformat(game_date.replace("Z", "+00:00"))
        display_date = dt.strftime("%-m/%-d")
    except (ValueError, AttributeError):
        display_date = game_date[:10] if game_date else ""

    round_name = _parse_round(event)

    return {
        "id": event.get("id", ""),
        "name": event.get("shortName", event.get("name", "")),
        "date": display_date,
        "state": state,
        "status": status_detail,
        "round": round_name,
        "winner": teams[0] if state == "post" else None,
        "loser": teams[1] if state == "post" else None,
        "teams": teams,
    }


def fetch_tournament_games(year=None):
    """Fetch NCAA tournament games from ESPN.

    Returns a list of game dicts sorted by date.
    Fetches multiple days covering the tournament window.
    """
    if year is None:
        year = datetime.now().year

    # NCAA tournament typically runs mid-March to early April
    start = datetime(year, 3, 17)
    end = datetime(year, 4, 8)

    all_games = {}
    current = start

    while current <= end:
        date_str = current.strftime("%Y%m%d")
        try:
            resp = requests.get(ESPN_URL, params={
                "dates": date_str,
                "groups": "100",
                "limit": "100",
            }, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            for event in data.get("events", []):
                game = _parse_game(event)
                if game and game["id"] not in all_games:
                    all_games[game["id"]] = game
        except requests.RequestException:
            pass

        current += timedelta(days=1)

    games = list(all_games.values())

    # Sort by round order then date
    round_order = {v: k for k, v in ROUND_MAP.items()}
    games.sort(key=lambda g: (round_order.get(g["round"], 99), g["date"]))

    return games
