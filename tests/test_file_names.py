import os
from datetime import datetime, timezone
from unittest import mock

from blackboard_sync.content import base
from blackboard_sync.content.attachment import Attachment


def test_has_extension():
    assert base.has_extension("Table1.do")
    assert base.has_extension("kisDataFinal.dta")
    assert not base.has_extension("Clase 1.2 final")
    assert not base.has_extension("xid-24187548_1")


def test_attachment_keeps_stata_extension():
    att = mock.Mock(fileName="Table1.do", mimeType="application/octet-stream")
    a = Attachment(att, {}, mock.Mock())
    assert a.filename == "Table1.do"

    att = mock.Mock(fileName="Notas", mimeType="application/pdf")
    assert Attachment(att, {}, mock.Mock()).filename == "Notas.pdf"


def test_written_file_gets_blackboard_date_as_mtime(tmp_path):
    posted = datetime(2026, 11, 9, 15, 0, tzinfo=timezone.utc)
    stream = base.FStream()
    stream.posted = posted
    base.written.clear()

    path = tmp_path / "x.html"
    stream.write_base(path, mock.Mock(submit=lambda f: f()), "hola")

    assert os.stat(path).st_mtime == posted.timestamp()
    assert [p for p, _ in base.written] == [path]
