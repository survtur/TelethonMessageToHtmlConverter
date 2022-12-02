"""
Creates html-formatted text from telegram message with entitities.
For python3.8+.
Tested on Telethon 1.25.4.

It uses Telethon module just for type hinting. Feel free to delete it.

"""

from html import escape
from dataclasses import dataclass
from typing import List, Optional, Dict, NamedTuple, Callable, Union

from telethon.tl.types import TypeMessageEntity

_UTF_16 = 'utf-16-le'


class _Tag(NamedTuple):
    opening: str
    closing: str


@dataclass
class _PositionChange:
    to_open: List[_Tag]
    to_close: List[_Tag]
    br: bool


_TagMakerFunction = Callable[[TypeMessageEntity, str], _Tag]

def _url_conv(entity, s: str) -> _Tag:
    return _Tag(f'<a href="{escape(s)}">', '</a>')


# Main convertsion table.
# Each MessageEntiry can be converted to:
#   1) None - When entity should be ignored.
#   2) _Tag object - when required tag is simple.
#   3) Function that receives two arguments: entity and string it covers. Should return _Tag.
_ENTITIES_TO_TAG: Dict[str, Union[None, _Tag, _TagMakerFunction]] = {
    'MessageEntityItalic': _Tag('<i>', '</i>'),
    'MessageEntityBold': _Tag('<b>', '</b>'),
    'MessageEntityCode': _Tag('<pre>', '</pre>'),
    'MessageEntityStrike': _Tag('<s>', '</s>'),
    'MessageEntitySpoiler': _Tag('[', ']'),
    'MessageEntityUnderline': _Tag('<span style="text-decoration: underline">', '</span>'),
    'MessageEntityPhone': None,
    'MessageEntityHashtag': None,
    'MessageEntityUrl': _url_conv,
    'MessageEntityTextUrl': lambda e, s: _Tag(f'<a href="{escape(e.url)}">', '</a>'),
}
"""
Describes now start and end of entity should be represented in HTML
"""


class MessageToHtmlConverter:

    def __init__(self, message: str, entities: Optional[List[TypeMessageEntity]]):

        if not entities and '\n' not in message:
            self.html = message
            return

        self._message = message
        self.html = ''

        # Usage of UTF-16 helps to get correct entity position.
        # Pros: There is no need of calculating codepoints and bytes. Just multiply offset/length by 2
        #       and everything will be correct.
        # Cons: Many utf encode/decode operaions.
        self._message_b16 = message.encode(_UTF_16)

        # This dict contains list of positions in message, where tag should be opened or closed,
        # or where paragraph or line break should be inserted.
        self._positions: Dict[int, _PositionChange] = {}
        self._ensure_position_exists(0)
        self._ensure_position_exists(len(self._message_b16))
        self._prepare_entity_positions_utf16le(entities)
        self._prerape_br_positions()

        separations_points = list(sorted(self._positions.keys()))

        # Keep tracking of opened tags. It helps to decide should <br/> or </p><p> be user instead of "\n"
        # You may check that when we close tags, the last on is what should be closed.
        # An that in the end this list is empty.
        opened_tags: List[_Tag] = []

        for pos in range(len(separations_points)):
            index = separations_points[pos]
            if index == len(self._message_b16):
                next_index = None
            else:
                next_index = separations_points[pos + 1]

            unchanged_part = self._message_b16[index:next_index].decode(_UTF_16)

            for t in self._positions[index].to_close:
                opened_tags.pop()
                self.html += t.closing

            if self._positions[index].br:
                if _ENTITIES_TO_TAG['MessageEntityCode'] in opened_tags:
                    self.html += '<br/>'
                else:
                    self.html += "</p><p>"

            for t in self._positions[index].to_open:
                opened_tags.append(t)
                self.html += t.opening

            self.html += escape(unchanged_part.replace('\n', ''))

        self.html = '<p>' + self.html + '</p>'

    def _prerape_br_positions(self):
        for i in range(len(self._message)):
            if self._message[i] == '\n':
                i = len(self._message[0:i].encode(_UTF_16))
                self._ensure_position_exists(i)
                self._positions[i].br = True

    def _prepare_entity_positions_utf16le(self, entities) -> None:
        if not entities:
            return

        for e in entities:
            start = e.offset * 2
            end = (e.offset + e.length) * 2
            self._ensure_position_exists(start)
            self._ensure_position_exists(end)
            tag = _ENTITIES_TO_TAG[type(e).__name__]
            if tag:

                if callable(tag):
                    txt_bytes = self._message_b16[start:end]
                    txt = txt_bytes.decode(_UTF_16)
                    tag = tag(e, txt)

                self._positions[start].to_open.append(tag)
                self._positions[end].to_close.insert(0, tag)

    def _ensure_position_exists(self, i: int):
        if i not in self._positions:
            self._positions[i] = _PositionChange([], [], False)
