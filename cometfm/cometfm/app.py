from itsdangerous import URLSafeSerializer
from flask import Flask, request, jsonify, render_template, abort
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('comet.html')

@app.route('/onair')
def onair():
    safe_serializer = URLSafeSerializer(secret_key=app.secret_key)
    safe, params = safe_serializer.loads_unsafe(request.args.get('channel'))
    if not safe:
        abort(400)

    station_id, stream_id, allowed_ip = params
    user_id = request.args.get('user_id', type=int)
    timeout = 25 if request.args.get('cursor') else None

    #if request.remote_addr != allowed_ip:
    #    abort(400)
    info = app.cometfm.get_info(station_id=station_id, stream_id=stream_id, user_id=user_id, timeout=timeout)
    return jsonify(info)

@app.route('/stats')
def stats():
    return jsonify({'stats': app.cometfm.stats})
