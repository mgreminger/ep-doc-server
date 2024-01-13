FROM pandoc/latex
 
ARG ENVIRONMENT=production

RUN apk add --no-cache python3 py3-pip
RUN apk add --no-cache ttf-dejavu

WORKDIR /code
 
COPY ./requirements.txt /code/requirements.txt
COPY ./requirements-dev.txt /code/requirements-dev.txt

RUN if [ "$ENVIRONMENT" = "production" ]; then \
        pip install --no-cache-dir --upgrade -r /code/requirements.txt \
    ; else \
        pip install --no-cache-dir --upgrade -r /code/requirements.txt -r /code/requirements-dev.txt \
    ; fi
 
COPY ./app /code/app
COPY ./tests /code/tests

ENTRYPOINT ["/bin/sh", "-c"]
 
CMD ["uvicorn app.main:app --proxy-headers --host 0.0.0.0 --port 80"]
