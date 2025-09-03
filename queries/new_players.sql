WITH LAST_SEASON AS (
	SELECT ps.player_id AS player_id
	FROM core_playerstatus ps
	JOIN core_season s ON ps.season_id = s.id
	WHERE s.year = 2024
),
THIS_SEASON AS (
	SELECT ps.player_id AS player_id
	FROM core_playerstatus ps
	JOIN core_season s ON ps.season_id = s.id
	WHERE s.year = 2025
)

SELECT p.username, p.email
FROM THIS_SEASON ls
JOIN core_player p ON ls.player_id = p.id
WHERE ls.player_id NOT IN (
	SELECT player_id
	FROM LAST_SEASON
)
