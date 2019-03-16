import logging
import sys
from random import choice

from google.cloud import datastore

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
LOG = logging.getLogger('markov:markov')

_client = datastore.Client()


def generate_sentences(dictionary_id: int, t1: str = None, amount: int = None) -> str:
    t1 = t1 or '$'
    amount = amount or 1
    sentences = []
    for i in range(amount):
        if i == 0:
            sentence = _generate_sentence(dictionary_id, t1)
        else:
            sentence = _generate_sentence(dictionary_id)
        sentences.append(sentence)
    return ' '.join(sentences)


def _generate_sentence(dictionary_id: int, t1: str = '$') -> str:
    phrase = ''
    t0 = '$'
    if t1 != '$':
        phrase += t1
    while True:
        key = _client.key('Db', 'markov',
                          'Dictionary', str(dictionary_id),
                          'Chain', t0,
                          'Chain', t1)
        q = _client.query(kind='Chain', ancestor=key)
        entities = q.fetch()
        seq = [e.key.name for e in entities]
        if not seq:
            phrase += "!"
            break
        t0, t1 = t1, choice(seq)
        if t1 == '$':
            break
        if t1 in '.!?,;:' or t0 == '$':
            phrase += t1
        else:
            phrase += ' ' + t1
    return phrase.capitalize()
