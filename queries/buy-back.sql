SELECT
	u.username,
	ps.can_buy_back,
	ps.did_buy_back
FROM
	core_playerstatus ps
	JOIN core_player p ON p.id = ps.player_id
	JOIN auth_user u ON u.id = p.user_id
	JOIN core_season s ON s.id = ps.season_id
WHERE
	s.is_current = TRUE
ORDER BY
	p.id
