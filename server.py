from flask import Flask, request, abort, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from post import Post
from dsutils import GoogleDatastore
from imutils import write_first_frame
import json
import os
import random

from constants import *
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDS_PATH

app = Flask(__name__)
CORS(app)
ds = GoogleDatastore()
from google.cloud import videointelligence
gvclient = videointelligence.VideoIntelligenceServiceClient()

users = {}
posts = {}
tokens = {}
queue = []

def generate_token():
    return ''.join(['1234567890abcdef'[random.randint(0, 15)] for i in range(32)])

@app.route('/')
def hello():
    return b'Hello World'

@app.route('/login', methods=['POST'])
def login():
    if 'username' not in request.form or 'password' not in request.form:
        return b'Username/Password not present'

    username = request.form['username']
    password = request.form['password']

    if username in users and users[username] == password:
        while True:
            token = generate_token()
            if token not in tokens:
                tokens[token] = username

            return jsonify({'token': token})

    return b'Bad credentials'

@app.route('/register', methods=['POST'])
def register():
    if 'username' not in request.form or 'password' not in request.form:
        return b'Username/Password not present'

    username = request.form['username']
    password = request.form['password']

    if username in users:
        return b'Duplicate usernames'

    users[username] = password
    return b'OK'
    
@app.route('/newpost', methods=['POST'])
def new_post():
    if 'Authorization' not in request.headers or request.headers['Authorization'] not in tokens:
        abort(401)

    username = tokens[request.headers['Authorization']]

    if 'video' not in request.files:
        return b'No video found'

    video = request.files['video']
    if video == '':
        return b'No selected file'

    # Saving the video to local filesystem
    print("Saving video to local FS")
    filename = secure_filename(video.filename)
    print(filename)
    image_filename = '%s.png' % filename[:-4]
    abs_filename = os.path.join('uploads/', filename)
    abs_image_filename = os.path.join('uploads/', image_filename)
    video.save(abs_filename)
    write_first_frame(abs_filename, abs_image_filename)

    # Upload the video to Google filestore
    print("Uploading video to Google")
    ds.upload(abs_filename, filename)
    ds.upload(abs_image_filename, image_filename)
    post_id = len(posts.keys())
    posts[post_id] = Post(post_id, username, filename)
    
    # Process tags for the video
    print("Processing annotations")
    job = gvclient.annotate_video(
        input_uri='gs://htn19videos/%s' % filename,
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

    print("Detected %d tag(s)" % len(labels))
    posts[post_id].tags.extend([x[1] for x in labels])
    
    print("Done")

    return jsonify({'post_id': post_id})

@app.route('/upload')
def upload():
     return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action='/newpost' method=post enctype=multipart/form-data>
      <input type=file name=video>
      <input type=submit value=Upload>
    </form>
    '''

@app.route('/myposts')
def my_posts():
    if 'Authorization' not in request.headers or request.headers['Authorization'] not in tokens:
        abort(401)

    username = tokens[request.headers['Authorization']]

    ret = {}
    for i in posts.keys():
        if posts[i].username == username:
            ret[i] = posts[i].get_dict()

    return jsonify(ret)

@app.route('/posts')
def all_posts():
    return jsonify({posts[x].post_id: posts[x].get_dict() for x in posts.keys()})
    # return jsonify({'posts': list(posts.keys())})


@app.route('/search/<query>')
def search(query):
    tokens = query.split(' ')
    p = Post(-1, None, None)
    p.tags = tokens

    ret = []
    for post in posts:
        coef, bm = post.compare(p)
        ret.append((coef, post))

    ret.sort(reverse=True)
    return jsonify(ret)

@app.route('/post/<post_id>')
def get_post(post_id):
    try:
        post_id = int(post_id)
        if post_id not in posts:
            abort(404)

        return jsonify(posts[post_id].get_dict())
    except:
        abort(404)

@app.route('/post/<post_id>/compare')
def compare_all(post_id):
    post_id = int(post_id)
    if post_id not in posts:
        abort(404)

    ret = []
    cur = posts[post_id]
    for i, p in posts.items():
        if i != post_id:
            coef, bm = cur.compare(p)
            ret.append((i, coef))

    return jsonify(ret)

@app.route('/edges')
def edges():
    ret = []
    n = len(posts.keys())
    for i in range(n):
        for j in range(n):
            if i != j:
                coef, bm = posts[i].compare(posts[j])
                ret.append((i, j, coef, bm))

    return jsonify(ret)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
