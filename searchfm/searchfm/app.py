import gevent
import string
import unicodedata
import logging
from ngram import NGram
from flask import Flask, jsonify

app = Flask(__name__)
search = NGram(key=lambda x: x[0])
stations = {}

def normalize_str(value):
    value = value.strip()[:256]
    value = unicodedata.normalize('NFKD', value)
    value = value.lower()
    return value

@app.route('/search/<query>')
def search_by_query(query):
    result = search.search(normalize_str(query), threshold=0.08)
    result = [(search_data[1], score) for search_data, score in result]
    result = [(index, item[0]) for index, item in enumerate(result)]
    result = [stations[station_id] for index, station_id in result if station_id in stations]
    result = sorted(result, key=lambda station: station['is_online'], reverse=True)
    return jsonify({'objects': result})

def build_index_in_background(collection, interval=30):
    global search
    while True:
        search = NGram(key=lambda x: x[0])
        for station in collection.find({'status': {'$ne': 0}, 'deleted_at': 0}, sort=[('status', 1)]):
            search_str = string.join([station['title'], station.get('tag', u'')])
            search_str = normalize_str(search_str)
            search.add((search_str, station['id']))
            stations[station['id']] = dict(
                id=station['id'],
                title=station['title'],
                is_online=(station['status'] == 1))
        logging.info('index build, wait {} sec(s)'.format(interval))
        gevent.sleep(interval)
