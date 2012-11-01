from ngram import NGram
import string
import unicodedata
import logging
from gevent import sleep
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
    return jsonify({'objects': result})

def build_index_in_background(collection, interval=30):
    global search
    while True:
        search = NGram(key=lambda x: x[0])
        for station in collection.find():
            search_str = string.join([station['title'], station.get('tag', u'')])
            search_str = normalize_str(search_str)
            search.add((search_str, station['id']))
            # copy only need keys
            stations[station['id']] = dict((key, val) for key, val in station.iteritems() if key in ('id', 'title', 'tag'))
        logging.info('index build, wait {} sec(s)'.format(interval))
        sleep(interval)
