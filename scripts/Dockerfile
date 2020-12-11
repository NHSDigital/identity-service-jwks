FROM python:3

RUN pip install poetry

COPY ./make_jwk.py /make_jwk.py
COPY ./poetry.lock /poetry.lock
COPY ./pyproject.toml /pyproject.toml
COPY ./*.pub /public_keys/

RUN poetry install
RUN chmod +x make_jwk.py

ENTRYPOINT ["poetry", "run", "python", "./make_jwk.py"]
CMD []
