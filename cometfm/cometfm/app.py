from flask import Flask, request, jsonify, render_template, abort
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('comet.html')

@app.route('/1.0/onair')
def onair():
    station_id=request.args.get('station_id', type=int)
    stream_id=request.args.get('stream_id', type=int)
    if not (station_id and stream_id):
        abort(400)

    timeout = 25 if request.args.get('cursor') else None
    info = app.cometfm.get_info(station_id=station_id,
        stream_id=stream_id,
        user_id=request.args.get('user_id', type=int),
        timeout=timeout)
    return jsonify(info)
