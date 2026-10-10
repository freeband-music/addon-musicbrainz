set dotenv-load := true

default:
    @just --list

# Run the add-on (http://localhost:7001)
run:
    uv run uvicorn freeband_musicbrainz.app:app --port 7001

# Offline tests
test:
    uv run pytest -q tests

# Regenerate freeband_protocol/models.py from the protocol repository
gen:
    uvx --from datamodel-code-generator datamodel-codegen \
      --input "${FREEBAND_PROTOCOL:-../protocol}/openapi.yaml" --input-file-type openapi \
      --output freeband_protocol/models.py \
      --output-model-type pydantic_v2.BaseModel \
      --snake-case-field --allow-population-by-field-name \
      --target-python-version 3.12 --use-standard-collections --use-union-operator \
      --custom-file-header "# Generated from protocol/openapi.yaml by 'just gen'. Do not edit."
    touch freeband_protocol/__init__.py

# Validate the running add-on against the protocol
[positional-arguments]
conformance *args:
    uv run "${FREEBAND_PROTOCOL:-../protocol}/conformance/run.py" http://localhost:7001 "$@"
