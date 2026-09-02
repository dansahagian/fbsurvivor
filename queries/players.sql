WITH
	current_season AS (
		SELECT
			id
		FROM
			core_season
		WHERE
			is_current = TRUE
	),
	current_players AS (
		SELECT
			u.id AS user_id,
			u.email AS user_email
		FROM
			core_playerstatus ps
			JOIN core_player p ON ps.player_id = p.id
			JOIN auth_user u ON p.user_id = u.id
		WHERE
			season_id = (
				SELECT
					id
				FROM
					current_season
			)
	),
	missing_players AS (
		SELECT
			email AS user_email
		FROM
			auth_user
		WHERE
			id NOT IN (
				SELECT
					user_id
				FROM
					current_players
			)
			AND email != ''
	),
	all_players AS (
		SELECT
			email AS user_email
		FROM
			auth_user
		WHERE
			email != ''
	)

SELECT
	user_email
FROM
	current_players
