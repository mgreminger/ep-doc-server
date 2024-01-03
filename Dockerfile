FROM pandoc/latex
 
RUN apk add --no-cache python3 py3-pip

WORKDIR /code
 
COPY ./requirements.txt /code/requirements.txt
 
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
 
COPY ./app /code/app

ENTRYPOINT ["/bin/sh", "-c"]
 
CMD ["uvicorn app.main:app --proxy-headers --host 0.0.0.0 --port 80"]
