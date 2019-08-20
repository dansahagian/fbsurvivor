import db


def main():
    week = db.get_current_week()
    year = db.get_current_year()
    if week > 0:
        retired_players = db.get_retired_players()
        for player in retired_players:
            db.update_pick_result(player, year, week, "R")


if __name__ == "__main__":
    main()
