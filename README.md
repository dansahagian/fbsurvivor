
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3111/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v1.json)](https://github.com/charliermarsh/ruff)

# FB Survivor
This project is used to run a family and friends NFL Survivor League. The league was originally managed using email and Excel. The first version of the application was written in Python, Flask, and used MongoDB. The second version switched to using Postgres and raw SQL queries, but continued to use Flask. This version, technically the third, but with the original name, is a ground up rewrite using Django and leveraging Django's ORM.  

On July 22, 2024, I restarted the git history for the public repo and archived the original repo.

## About the Deployment
- Runs on a single [Linode](https://www.linode.com/) running Debian Linux
- Deployed with a simple deploy script
