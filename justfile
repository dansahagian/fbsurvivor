PROJECT   := "fbsurvivor"
DB_NAME   := "fbsurvivor2"
DB_USER   := "fbsurvivor2"
DEV_HOST  := "onryo"
PROD_HOST := "oyuki"
GROUPS    := "check django dev prod tooling"

import 'just-django.just'

# Grouped recipe listing in GROUPS order. The project justfile must declare
_list:
    @echo "Available recipes:"
    @first=1; for g in {{GROUPS}}; do [ $first = 1 ] || echo; first=0; just --list --unsorted --group "$g" --list-heading ""; done
