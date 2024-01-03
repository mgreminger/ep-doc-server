import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_md_to_docx():
    files = {'request_file': ("input.md", open('./tests/input.md', 'rb'), "text/markdown")}
    response = client.post("/docgen/docx", files=files)
    assert response.status_code == 200

    assert len(response.content) > 700000

    # save output docx data to a file as an artifact
    # can be compared to ./tests/output_reference.docx
    # cannot use a bit-wise comparison since pandoc uses timestamp data
    os.makedirs('./tests/output', exist_ok=True)
    with open('./tests/output/output.docx', 'wb') as output_docx:
        output_docx.write(response.content)
    
    