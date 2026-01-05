import re
import time

user_message_times = {}

def behavior_score(message):
    score = 0
    content = message.content

    # Caps spam
    if content.isupper() and len(content) > 6:
        score += 2

    # Repeated characters
    if re.search(r"(.)\1{4,}", content):
        score += 2

    # Mention spam
    if content.count("@") >= 5:
        score += 2

    # Link spam
    if re.search(r"http[s]?://", content):
        score += 1

    # Flooding (messages too fast)
    now = time.time()
    uid = message.author.id
    last = user_message_times.get(uid, 0)
    if now - last < 1.2:
        score += 2
    user_message_times[uid] = now

    return score
