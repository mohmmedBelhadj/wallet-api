import os

import psycopg
from dotenv import load_dotenv

load_dotenv()
conn = psycopg.connect(os.environ["DATABASE_URL"])

user_id = 999


with conn.cursor() as cur:
    cur.execute(
        'SELECT id, full_name, email FROM users WHERE id = %s',
        (user_id,)
    )

    user = cur.fetchone()

    if user is None:
        print("User not found")
    else:
        print(user)

conn.close()
