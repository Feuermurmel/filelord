import json
import pathlib
import re


def _escape_field(x):
    return re.sub('\\\\"', '"', json.dumps(x, ensure_ascii=False)[1:-1])


def _unescape_field(x):
    return json.loads('"{}"'.format(re.sub('"' , '\\\\"', x)))


def write_tsv(path: pathlib.Path, lines):
    with path.open('w', encoding='utf-8') as file:
        for i in lines:
            print(*map(_escape_field, i), sep='\t', file=file)


def read_tsv(path: pathlib.Path):
    def iter_lines():
        with path.open('r', encoding='utf-8') as file:
            for i in file:
                return list(map(_unescape_field, i.rstrip('\r\n').split('\t')))

    return list(iter_lines())
