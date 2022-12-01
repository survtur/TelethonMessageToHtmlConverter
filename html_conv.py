"""

Creates html-formatted text from telegram message with entitities.
It does not creates links. I just don't need it. The ides was to create correct visual formatting. 

For python3.8+.
Tested on Telethon 1.25.4.
"""


import html
from typing import List, Optional, Dict, NamedTuple

import telethon.tl.types


class _Tag(NamedTuple):
    opening: str
    closing: str


class _PositionChange(NamedTuple):
    to_open: List[_Tag]
    to_close: List[_Tag]
    br: bool

_PRE_TAG = _Tag('<pre>', '</pre>')


_ENTITIES_TO_TAG: Dict[str, Optional[_Tag]] = {
    'MessageEntityItalic': _Tag('<i>', '</i>'),
    'MessageEntityBold': _Tag('<b>', '</b>'),
    'MessageEntityCode': _PRE_TAG,
    'MessageEntityStrike': _Tag('<s>', '</s>'),
    'MessageEntitySpoiler': _Tag('[', ']'),
    'MessageEntityUnderline': _Tag('<span style="text-decoration: underline">', '</span>'),
    'MessageEntityPhone': None,
    'MessageEntityHashtag': None,
    'MessageEntityUrl': None,
    'MessageEntityTextUrl': None,
}
"""
Describes now start and end of entity should be represented in HTML
"""


class MessageToHtmlConverter:
    html: str

    def __init__(self, message: str, entities: Optional[List[telethon.tl.types.TypeMessageEntity]]):
        if not entities and '\n' not in message:
            self.html = message
            return

        b16 = message.encode('utf-16-le')
        positions: Dict[int, _PositionChange] = {
            0: _PositionChange([], [], False),
            len(b16): _PositionChange([], [], False)
        }
        positions.update(self._prepare_positions_utf16le(entities))

        for i in range(len(message)):
            if message[i] == '\n':
                i = len(message[0:i].encode('utf-16-le'))
                if i not in positions:
                    positions[i] = _PositionChange([], [], False)
                positions[i].br = True

        all_separations_set = set(positions.keys())
        separation_list = list(sorted(all_separations_set))
        out: str = ''
        opened_tags: List[_Tag] = []
        for pos in range(len(separation_list)):
            index = separation_list[pos]
            if index == len(b16):
                next_index = None
            else:
                next_index = separation_list[pos + 1]

            unchanged_part = b16[index:next_index].decode('utf-16-le')

            for t in positions[index].to_close:
                popped = opened_tags.pop()
                assert popped == t
                out += t.closing

            if positions[index].br:
                if _PRE_TAG in opened_tags:
                    out += '<br/>'
                else:
                    out += "</p><p>"

            for t in positions[index].to_open:
                opened_tags.append(t)
                out += t.opening

            out += html.escape(unchanged_part.replace('\n', ''))

        self.html = '<p>' + out + '</p>'

    @staticmethod
    def _prepare_positions_utf16le(entities):
        if not entities:
            return {}

        positions: Dict[int, _PositionChange] = {}
        for e in entities:
            start = e.offset * 2
            end = (e.offset + e.length) * 2
            if start not in positions:
                positions[start] = _PositionChange([], [], False)
            if end not in positions:
                positions[end] = _PositionChange([], [], False)
            tag = _ENTITIES_TO_TAG[type(e).__name__]
            if tag:
                positions[start].to_open.append(tag)
                positions[end].to_close.insert(0, tag)
        return positions

