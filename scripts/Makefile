build:
	docker build -t make_jwk:latest .

run:
	@docker run -it --rm make_jwk --pk-file=/public_keys/$(PK_FILE) --kid=$(KID)
