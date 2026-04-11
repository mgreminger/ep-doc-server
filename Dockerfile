FROM pandoc/typst:3.9.0.2
 
ARG ENVIRONMENT=production

RUN apk add --no-cache python3 py3-pip
RUN apk add --no-cache poppler-utils
RUN apk add --no-cache font-noto-cjk font-noto-all font-noto-emoji ttf-dejavu fontconfig \
    && fc-cache -f

WORKDIR /code
 
COPY ./requirements.txt /code/requirements.txt
COPY ./requirements-dev.txt /code/requirements-dev.txt

RUN python3 -m venv /venv
ENV PATH=/venv/bin:$PATH

RUN if [ "$ENVIRONMENT" = "production" ]; then \
        pip install --no-cache-dir --upgrade -r /code/requirements.txt \
    ; else \
        pip install --no-cache-dir --upgrade -r /code/requirements.txt -r /code/requirements-dev.txt \
    ; fi
 
COPY ./app /code/app
COPY ./tests /code/tests

ENTRYPOINT ["/bin/sh", "-c"]
 
CMD ["uvicorn app.main:app --proxy-headers --host 0.0.0.0 --port 80"]
