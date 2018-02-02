import logging
import mimetypes
from itertools import product
from pathlib import Path
from typing import Callable, Dict, Tuple, Any, List
from functools import partial

import json

import requests
from PIL import Image
# noinspection PyProtectedMember
from bs4 import Tag

logger = logging.getLogger(__name__)


class Cache:
    def __init__(self, func: Callable):
        self._func = func  # type: Callable
        self._cache = {}  # type: Dict[Tuple, Any]

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self._func
        return partial(self, obj)

    def __call__(self, *args, **kwargs):
        key = (self._func, args[1:], frozenset(kwargs.items()))
        if key in self._cache:
            return self._cache[key]
        result = self._func(*args, **kwargs)
        self._cache[key] = result
        return result


def table_to_2d(table_tag: Tag):
    """
    https://stackoverflow.com/a/48451104/3673259
    """
    row_spans = []  # track pending row_spans
    rows = table_tag.find_all("tr")

    # first scan, see how many columns we need
    col_count = 0
    for r, row in enumerate(rows):
        cells = row.select("> td,> th")
        # count columns (including spanned).
        # add active row_spans from preceding rows
        # we *ignore* the colspan value on the last cell, to prevent
        # creating "phantom" columns with no actual cells, only extended
        # colspans. This is achieved by hardcoding the last cell width as 1. 
        # a colspan of 0 means “fill until the end” but can really only apply
        # to the last cell; ignore it elsewhere. 
        col_count = max(
            col_count,
            sum(int(c.get("colspan", 1)) or 1 for c in cells[:-1]) + len(cells[-1:]) + len(row_spans))
        # update rowspan bookkeeping; 0 is a span to the bottom. 
        row_spans += [int(c.get("rowspan", 1)) or len(rows) - r for c in cells]
        row_spans = [s - 1 for s in row_spans if s > 1]

    # it doesn"t matter if there are still rowspan numbers "active"; no extra
    # rows to show in the table means the larger than 1 rowspan numbers in the
    # last table row are ignored.

    # build an empty matrix for all possible cells
    table = [[None] * col_count for row in rows]

    # fill matrix from row data
    row_spans = {}  # track pending row_spans, column number mapping to count
    for row, row_elem in enumerate(rows):
        span_offset = 0  # how many columns are skipped due to row and colspans 
        for col, cell in enumerate(row_elem.select("> td,> th")):
            # adjust for preceding row and colspans
            col += span_offset
            while row_spans.get(col, 0):
                span_offset += 1
                col += 1

            # fill table data
            rowspan = row_spans[col] = int(cell.get("rowspan", 1)) or len(rows) - row
            colspan = int(cell.get("colspan", 1)) or col_count - col
            # next column is offset by the colspan
            span_offset += colspan - 1
            value = cell.get_text()
            for drow, dcol in product(range(rowspan), range(colspan)):
                try:
                    table[row + drow][col + dcol] = value
                except IndexError:
                    # rowspan or colspan outside the confines of the table
                    pass

        # update rowspan bookkeeping
        row_spans = {c: s - 1 for c, s in row_spans.items() if s > 1}

    return table


def download_thumbnail(thumbnails: List[str], path: Path):
    for thumbnail in thumbnails:
        response = requests.get(thumbnail, stream=True)
        if response.status_code == 200:
            content_type = response.headers.get("content-type")
            ext = None
            if content_type is not None:
                ext = mimetypes.guess_extension(content_type)
                if ext in [".jpe", ".jpeg"]:
                    ext = ".jpg"
            if ext is None:
                ext = ".png"
            thumbnail_path = path.with_suffix(ext)
            response.raw.decode_content = True
            image = Image.open(response.raw)  # type: Image
            image.save(thumbnail_path)
            return


__all__ = [Cache, table_to_2d, download_thumbnail]
