import os
from flask import Flask, jsonify, render_template
from sheets import load_grid, load_payouts
from ncaa_data import fetch_tournament_games
from scoring import score_game, build_leaderboard

app = Flask(__name__)

SHEET_ID = os.environ.get("NCAA_SHEET_ID", "")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/board")
def api_board():
    try:
        grid = load_grid(SHEET_ID)
        payouts = load_payouts(SHEET_ID)
    except Exception as e:
        return jsonify({"error": f"Sheet error: {e}"}), 500

    try:
        games = fetch_tournament_games()
    except Exception as e:
        return jsonify({"error": f"ESPN error: {e}"}), 500

    # Score completed games
    scored_games = []
    for game in games:
        result = score_game(game, grid, payouts)
        if result:
            scored_games.append(result)

    leaderboard = build_leaderboard(scored_games)

    # Build grid as a serializable structure
    grid_data = []
    for r in range(10):
        row = []
        for c in range(10):
            row.append(grid.get((c, r), ""))
        grid_data.append(row)

    # Live games (in progress)
    live_games = []
    for game in games:
        if game["state"] == "in":
            teams = game["teams"]
            live_games.append({
                "name": game["name"],
                "status": game["status"],
                "round": game["round"],
                "teams": [
                    {"name": t["name"], "seed": t["seed"], "score": t["score"]}
                    for t in teams
                ],
            })

    # Upcoming games
    upcoming = []
    for game in games:
        if game["state"] == "pre":
            teams = game["teams"]
            upcoming.append({
                "name": game["name"],
                "status": game["status"],
                "round": game["round"],
                "date": game["date"],
                "teams": [
                    {"name": t["name"], "seed": t["seed"]}
                    for t in teams
                ],
            })

    return jsonify({
        "grid": grid_data,
        "scored_games": scored_games,
        "live_games": live_games,
        "upcoming": upcoming,
        "leaderboard": leaderboard,
        "payouts": payouts,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5001)
