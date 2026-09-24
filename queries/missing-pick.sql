SELECT
	u.username
FROM
	core_pick p
	JOIN core_player player ON p.player_id = player.id
	JOIN auth_user u ON player.user_id = u.id
	JOIN core_week w ON p.week_id = w.id
	JOIN core_season s ON w.season_id = s.id
WHERE
	s.is_current = True
	AND w.week_num = 2
	AND p.team_id IS NULL
