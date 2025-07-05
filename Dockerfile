FROM pandoc/typst:3.7.0.2-ubuntu
 
ARG ENVIRONMENT=production

# Install Python 3 and pip
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv

# Install fonts: Libertinus, Unifont, NewCMMath Book
RUN apt-get install -y --no-install-recommends \
        fonts-unifont \
        texlive-fonts-recommended \
        texlive-fonts-extra \
        fontconfig && \
    fc-cache -f && \
    rm -rf /var/lib/apt/lists/*

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
