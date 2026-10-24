import re

from common import setup_state

state = setup_state()

with state.db.connect() as conn:
    rows = conn.execute(
        """
        SELECT id, type, resource_id, parameters, error, updated_at
        FROM Job
        WHERE status = 'failed'
        ORDER BY type, id
        """
    ).fetchall()

counts = {}
for row in rows:
    message = (row[4] or "").split(":", 1)[0]
    message = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}", "", message)
    message = re.sub(r"\(token [^)]*\)", "", message)
    message = " ".join(message.split())
    counts[message] = counts.get(message, 0) + 1
for message, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
    print(count, message)
print()

print(len(rows))
for job_id, job_type, resource_id, parameters, error, updated_at in rows:
    print(job_id, job_type, resource_id, updated_at)
    print(parameters)
    print(error)
    print()
