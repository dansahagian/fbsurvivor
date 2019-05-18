SELECT u.email,pk.team
FROM users u
JOIN paid pd ON pd.user_id=u.id
JOIN picks pk ON pk.user_id=u.id
WHERE pd.year=(SELECT year FROM current)
AND pk.year=(SELECT year FROM current)
AND pk.week=(SELECT min(week)
			 FROM locks
			 WHERE lock_date>CURRENT_TIMESTAMP)
AND pk.team='--'