from blackboard_sync.content.webdav import ContentParser


def test_content_parser_uses_iframe_title_as_filename():
    base_url = "https://aulavirtual.up.edu.pe"
    html = """
    <div>
      <iframe
        src="https://aulavirtual.up.edu.pe/bbcswebdav/pid-2564591-dt-content-rid-20751902_1/xid-20751902_1?locale=es_ES&isInlineRender=true&xythos-download=true&render=inline"
        title="Cronograma_actividades_RCE_2026_1_L.pdf">
      </iframe>
    </div>
    """

    parser = ContentParser(html, base_url)

    assert len(parser.links) == 1
    assert parser.links[0].text == "Cronograma_actividades_RCE_2026_1_L.pdf"
    assert parser.links[0].href.startswith(base_url)



def test_content_parser_reads_ultra_data_bbfile_name():
    # Ultra: empty <a> whose href ends in xid-...; real name lives in JSON
    base_url = "https://aulavirtual.up.edu.pe"
    html = (
        '<a data-bbfile=\'{"linkName":"Tarea 2 2026-II.pdf",'
        '"displayName":"Tarea 2 2026-II.pdf","mimeType":"application/pdf"}\' '
        'href="https://aulavirtual.up.edu.pe/bbcswebdav/pid-1-dt-content-'
        'rid-24187548_1/xid-24187548_1?x=1"></a>'
    )

    parser = ContentParser(html, base_url)

    assert [ln.text for ln in parser.links] == ["Tarea 2 2026-II.pdf"]
