import logging
import sys

from flask import Flask, request, jsonify

import markov

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
LOG = logging.getLogger('markov:main')

app = Flask(__name__)


@app.route('/gen', methods=['POST'])
def generate():
    params = request.json
    if 'dictionary' not in params:
        return jsonify(ok=False, error='Dictionary identifier is required')
    text = markov.generate_sentences(params['dictionary'],
                                     t1=params.get('start', None),
                                     amount=params.get('num_sentences', None))
    return jsonify(ok=True, text=text)


@app.route('/train', methods=['POST'])
def train():
    params = request.json
    if 'dictionary' not in params:
        return jsonify(ok=False, error='Dictionary identifier is required')
    markov.train_model(params['dictionary'],
                       corpus=params.get('corpus', ''))
    return jsonify(ok=True)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
