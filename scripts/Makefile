build:
	docker build -t make_jwk:latest .

# Usage:
#	make PK_FILE=jwtRS512.key.pub KID=example run
run:
	@docker run -it --rm make_jwk --pk-file=/public_keys/$(PK_FILE) --kid=$(KID)
