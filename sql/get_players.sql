select email
from users u
join paid p ON p.user_id = u.id
where p.year = 2018