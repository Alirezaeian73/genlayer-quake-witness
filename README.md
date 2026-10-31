# Quake Witness

Quake Witness is an experimental GenLayer Intelligent Contract that checks a claimed earthquake magnitude against the official USGS earthquake catalog.

## How it works

A caller submits a USGS event ID and a claimed magnitude. The contract fetches the corresponding CSV record from the official USGS FDSN Event Web Service, parses the event ID, magnitude, time, location, depth, place, and review status, and uses GenLayer's comparative equivalence principle to require validator agreement on those facts. Deterministic contract logic then compares the submitted magnitude with the catalog value and stores the result.

The contract uses the stable API retrieval method `gl.nondet.web.get()` and decodes the response body as UTF-8. It does not require PDF rendering, text conversion, or an API key.

## Results

- `SUPPORTED`: the USGS event ID was found and the submitted magnitude matches the catalog value.
- `CONTRADICTED`: the event ID was found, but the submitted magnitude differs from the catalog value.
- `NOT_FOUND`: the catalog returned no event row for the requested ID.
- `SOURCE_UNAVAILABLE`: the source could not be retrieved.
- `UNCLEAR`: the response could not be parsed or compared confidently.

The source may revise event data. This contract records agreement with one USGS catalog response. It is not an emergency alert and does not replace official safety guidance.

## Current live deployment

- Network: GenLayer Studio
- Contract: `0x3091C3ec7E74ECBaCB2796d03039ec7937028a02`
- Deployment transaction: [0x95fa09282c691812af4a60e112fe2f66631aa1dddef328491459edd3713e1bec](https://explorer-studio.genlayer.com/tx/0x95fa09282c691812af4a60e112fe2f66631aa1dddef328491459edd3713e1bec)
- Live assessment transaction: [0x81af84d74fafb319aa9d3e1940a4d5b4f018e8704c54fe99e90f212feafa2c69](https://explorer-studio.genlayer.com/tx/0x81af84d74fafb319aa9d3e1940a4d5b4f018e8704c54fe99e90f212feafa2c69)
- Stored assessment ID: `0`
- Stored result: `SUPPORTED`
- Event: `us7000tuhe`, magnitude `2.5`, reviewed status, `12 km NW of Junction, Utah`
- Source response SHA-256: `d0c748bc1a0952fabb44b40758cb7cce0fe4ecc68cd0fa8682bf76e41e60ee98`

The assessment stores the source URL, the source response digest, and the event details. This is one successful live result and does not guarantee that every future source request will be available or unchanged.

## Development

The project uses Python and pytest for local helper tests. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m py_compile contracts/quake_witness.py
pytest -q
