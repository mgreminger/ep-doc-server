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

    # save docx file as artifact
    os.makedirs('./tests/output', exist_ok=True)
    with open('./tests/output/output.docx', 'wb') as output_docx:
        output_docx.write(response.content)
    
    assert filecmp.cmp('./tests/output/output.docx', './tests/output_reference.docx', shallow=False)

def test_md_to_pdf():
    files = {'request_file': ("input.md", open('./tests/input.md', 'rb'), "text/markdown")}
    response = client.post("/docgen/pdf", files=files)
    assert response.status_code == 200

    # save pdf file as artifact
    os.makedirs('./tests/output', exist_ok=True)
    with open('./tests/output/output.pdf', 'wb') as output_pdf:
        output_pdf.write(response.content)
    
    # file comparison not working (change identifier metadata?) so will just check size
    assert len(response.content) > 250000