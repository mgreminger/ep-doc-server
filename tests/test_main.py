import os, filecmp, asyncio, shutil, subprocess, time

import pytest
import httpx

@pytest.fixture(scope="session", autouse=True)
def start_server():
    testing_env = os.environ.copy()
    testing_env["TESTING"] = "1"

    server_process = subprocess.Popen(["uvicorn", "app.main:app", "--host",
                                       "127.0.0.1", "--port", "8000"],
                                       env=testing_env)
    time.sleep(5)

    yield

    server_process.terminate()


@pytest.fixture(scope="session", autouse=True)
def run_before_all_tests():
    shutil.rmtree('./tests/output', ignore_errors=True)
    os.makedirs('./tests/output')

@pytest.fixture
def client():
    yield httpx.Client(base_url="http://127.0.0.1:8000", timeout=40)

def test_md_to_docx(client):
    files = {'request_file': ("input.md", open('./tests/input.md', 'rb'), "text/markdown")}
    response = client.post("/docgen/docx", files=files)
    assert response.status_code == 200

    # save docx file as artifact
    with open('./tests/output/output.docx', 'wb') as output_docx:
        output_docx.write(response.content)
    
    assert filecmp.cmp('./tests/output/output.docx', './tests/output_reference.docx', shallow=False)

def test_md_to_docx_a4(client):
    files = {'request_file': ("input.md", open('./tests/input.md', 'rb'), "text/markdown")}
    response = client.post("/docgen/docx_a4", files=files)
    assert response.status_code == 200

    # save docx file as artifact
    with open('./tests/output/output_a4.docx', 'wb') as output_docx:
        output_docx.write(response.content)
    
    assert filecmp.cmp('./tests/output/output_a4.docx', './tests/output_reference_a4.docx', shallow=False)

def test_md_to_pdf(client):
    files = {'request_file': ("input.md", open('./tests/input_with_unicode.md', 'rb'), "text/markdown")}
    response = client.post("/docgen/pdf", files=files)
    assert response.status_code == 200

    # save pdf file as artifact
    with open('./tests/output/output.pdf', 'wb') as output_pdf:
        output_pdf.write(response.content)
    
    # file comparison not working (change identifier metadata?) so will just check size
    assert len(response.content) > 200000

    # Check paper size using pdfinfo
    pdfinfo_result = subprocess.run(['pdfinfo', './tests/output/output.pdf'], capture_output=True, text=True)
    assert pdfinfo_result.returncode == 0

    letter_size = False
    for line in pdfinfo_result.stdout.splitlines():
        if "letter" in line:
            letter_size = True
            break
  
    assert(letter_size)

def test_md_to_pdf_a4(client):
    files = {'request_file': ("input.md", open('./tests/input_with_unicode.md', 'rb'), "text/markdown")}
    response = client.post("/docgen/pdf_a4", files=files)
    assert response.status_code == 200

    # save pdf file as artifact
    with open('./tests/output/output.pdf', 'wb') as output_pdf:
        output_pdf.write(response.content)
    
    # file comparison not working (change identifier metadata?) so will just check size
    assert len(response.content) > 200000

    # Check paper size using pdfinfo
    pdfinfo_result = subprocess.run(['pdfinfo', './tests/output/output.pdf'], capture_output=True, text=True)
    assert pdfinfo_result.returncode == 0

    a4_size = False
    for line in pdfinfo_result.stdout.splitlines():
        if "A4" in line:
            a4_size = True
            break
  
    assert(a4_size)

def test_md_to_latex(client):
    files = {'request_file': ("input.md", open('./tests/input.md', 'rb'), "text/markdown")}
    response = client.post("/docgen/tex", files=files)
    assert response.status_code == 200

    # save md file as artifact
    with open('./tests/output/output.tex', 'wb') as output_pdf:
        output_pdf.write(response.content)

    assert filecmp.cmp('./tests/output/output.tex', './tests/output_reference.tex', shallow=False)

def test_md_to_latex_a4(client):
    files = {'request_file': ("input.md", open('./tests/input.md', 'rb'), "text/markdown")}
    response = client.post("/docgen/tex_a4", files=files)
    assert response.status_code == 200

    # save md file as artifact
    with open('./tests/output/output_a4.tex', 'wb') as output_pdf:
        output_pdf.write(response.content)

    assert filecmp.cmp('./tests/output/output_a4.tex', './tests/output_reference_a4.tex', shallow=False)

def test_error_on_binary_input(client):
    files = {'request_file': ("input.md", open('./tests/output_reference.docx', 'rb'), "text/markdown")}
    response = client.post("/docgen/docx", files=files)
    assert response.status_code == 415

@pytest.mark.anyio
async def test_simultaneous_requests():
    response_futures = []
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=120) as client:
        for i in range(20):
          files = {'request_file': ("input.md", open(f'./tests/input_{i}.md', 'rb'), "text/markdown")}
          response_futures.append(client.post("/docgen/docx", files=files))

        responses = await asyncio.gather(*response_futures)

    # save docx file as artifacts
    for i, response in enumerate(responses):     
      with open(f'./tests/output/output_{i}.docx', 'wb') as output_docx:
          output_docx.write(response.content)

    # check all of the files that have been created
    for i in range(20):
      assert filecmp.cmp(f'./tests/output/output_{i}.docx', f'./tests/output_reference_{i}.docx', shallow=False)

def test_health_check(client):
    response = client.get("/healthz")
    assert response.status_code == 200