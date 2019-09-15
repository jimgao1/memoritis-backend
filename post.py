
from constants import *
import word2vec
import json

model = word2vec.load(MODEL_PATH)

def semantic(p1, p2):
    if p1 not in model.vocab or p2 not in model.vocab:
        return 0

    wa, wb, match = model.distance(p1, p2)[0]
    return match

class Post:
    def __init__(self, post_id, username, filename):
        self.post_id = post_id
        self.username = username
        self.filename = filename
        self.tags = []
        self.cache = {}

    def get_dict(self):
        return {
                'post_id': self.post_id,
                'user': self.username,
                'tags': self.tags,
                'video_url': 'https://storage.googleapis.com/htn19videos/%s' % self.filename,
                'thumbnail_url': 'https://storage.googleapis.com/htn19videos/%s.png' % self.filename[:-4]
               }

    def compare(self, p):
        if p in self.cache:
            return self.cache[p]

        tags1 = self.tags[:10]
        tags2 = p.tags[:10]

        score = 0
        best_match_factor, best_match = 0, None
        for i, w1 in zip(range(len(tags1)), tags1):
            for j, w2 in zip(range(len(tags2)), tags2):
                s = semantic(w1, w2)
                if s > best_match_factor:
                    best_match_factor = s
                    best_match = w1
                score += MATCH_DECAY ** (i+j) * s

        self.cache[p] = (score, best_match)
        return (score, best_match)

    def __str__(self):
        return json.dumps({'post_id': self.post_id, 'tags': self.tags})
