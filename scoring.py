def score_game(game, grid, payouts):
    """Score a completed game against the grid.

    Returns a dict with game info plus square winner and payout,
    or None if the game isn't final.
    """
    if game["state"] != "post" or not game["winner"] or not game["loser"]:
        return None

    winner_score = game["winner"]["score"]
    loser_score = game["loser"]["score"]
    winner_digit = winner_score % 10
    loser_digit = loser_score % 10

    square_winner = grid.get((winner_digit, loser_digit), "???")
    payout = payouts.get(game["round"], 0)

    return {
        "game_id": game["id"],
        "date": game["date"],
        "round": game["round"],
        "winner_team": game["winner"]["name"],
        "winner_seed": game["winner"]["seed"],
        "winner_score": winner_score,
        "loser_team": game["loser"]["name"],
        "loser_seed": game["loser"]["seed"],
        "loser_score": loser_score,
        "winner_digit": winner_digit,
        "loser_digit": loser_digit,
        "square_winner": square_winner,
        "payout": payout,
    }


def build_leaderboard(scored_games):
    """Build leaderboard from scored games.

    Returns a list of dicts sorted by total winnings descending.
    """
    totals = {}
    for sg in scored_games:
        name = sg["square_winner"]
        if name not in totals:
            totals[name] = {"name": name, "total_winnings": 0, "wins": 0, "games_won": []}
        totals[name]["total_winnings"] += sg["payout"]
        totals[name]["wins"] += 1
        totals[name]["games_won"].append(
            f"{sg['winner_team']} {sg['winner_score']}-{sg['loser_score']} {sg['loser_team']}"
        )

    leaderboard = list(totals.values())
    leaderboard.sort(key=lambda x: x["total_winnings"], reverse=True)
    return leaderboard
