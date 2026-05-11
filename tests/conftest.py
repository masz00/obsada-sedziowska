import io
import sys
from pathlib import Path

import pytest
import xlwt

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def make_xls(rows):
    """Build minimal XLS bytes with referee data starting at row 4.

    Each row: (klasa, home, away, date, time, referee, ass1, ass2)
    """
    book = xlwt.Workbook(encoding="cp1250")
    sheet = book.add_sheet("Sheet1")
    for i in range(4):
        sheet.write(i, 0, "")
    for i, (klasa, home, away, date, time_, referee, ass1, ass2) in enumerate(rows):
        r = i + 4
        sheet.write(r, 1, klasa)
        sheet.write(r, 2, home)
        sheet.write(r, 3, away)
        sheet.write(r, 4, date)
        sheet.write(r, 5, time_)
        sheet.write(r, 7, referee or " ")
        sheet.write(r, 8, ass1 or " ")
        sheet.write(r, 9, ass2 or " ")
    buf = io.BytesIO()
    book.save(buf)
    return buf.getvalue()
