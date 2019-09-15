import os
import inspect

from constants import *
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDS_PATH

from dsutils import *

from google.cloud import videointelligence
client = videointelligence.VideoIntelligenceServiceClient()

videos = [
    '/data/htn/videos/bedroom_1.mp4',
    '/data/htn/videos/city_1.mp4',
    '/data/htn/videos/country_1.mp4',
    '/data/htn/videos/festival_1.mp4',
    '/data/htn/videos/funeral_1.mp4',
    '/data/htn/videos/historical_1.mp4',
    '/data/htn/videos/mountains_1.mp4',
    '/data/htn/videos/railroad_1.mp4',
    '/data/htn/videos/school_1.mp4'
]

ds = GoogleDatastore()
for v in videos:
    print("Processing video", v)
    ds.upload(v, v.split('/')[-1])

    job = client.annotate_video(
        input_uri='gs://htn19videos/%s' % v.split('/')[-1],
        features=['LABEL_DETECTION'],
    )

    result = job.result()
    shot_labels = result.annotation_results[0].shot_label_annotations

    labels = []
    for shot in shot_labels:
        desc = shot.entity.description
        duration = 0

        for seg in shot.segments:
            seg = seg.segment
            if seg.end_time_offset.nanos == 0:
                duration += int(1e10) - seg.start_time_offset.nanos
            else:
                duration += seg.end_time_offset.nanos - seg.start_time_offset.nanos

        labels.append((duration, desc))

    labels.sort(reverse=True)
    print(labels)

