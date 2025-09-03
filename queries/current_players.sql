WITH
THIS_SEASON AS (
	SELECT ps.player_id AS player_id
	FROM core_playerstatus ps
	JOIN core_season s ON ps.season_id = s.id
	WHERE s.is_current = true
)

SELECT p.email
FROM THIS_SEASON ts
JOIN core_player p ON ts.player_id = p.id

