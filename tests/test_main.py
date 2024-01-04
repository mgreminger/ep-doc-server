import os, filecmp

from fastapi.testclient import TestClient

from app.main import app, Settings, get_settings

client = TestClient(app)

def get_test_settings():
    return Settings(testing=True)

app.dependency_overrides[get_settings] = get_test_settings

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
    
    assert filecmp.cmp('./tests/output/output.docx', './tests/output_reference.docx', shallow=False)

    assert False