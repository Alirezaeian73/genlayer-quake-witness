# Quake Witness

An experimental GenLayer Intelligent Contract that checks a claimed earthquake magnitude against the official USGS earthquake catalog.

## How it works

Submit a USGS event ID and a claimed magnitude. The contract retrieves that event's CSV record, checks the event ID and magnitude, and uses GenLayer's comparative equivalence principle to require validator agreement on the event details. It stores the result with the source URL, event data, and a SHA-256 digest of the CSV response.

Results are `SUPPORTED`, `CONTRADICTED`, `NOT_FOUND`, `SOURCE_UNAVAILABLE`, or `UNCLEAR`. USGS may revise earthquake information. This is not an emergency alert or a replacement for official safety guidance.

## Live Studio assessment

- Contract: `0x3091C3ec7E74ECBaCB2796d03039ec7937028a02`
- Deployment: [0x95fa09282c691812af4a60e112fe2f66631aa1dddef328491459edd3713e1bec](https://explorer-studio.genlayer.com/tx/0x95fa09282c691812af4a60e112fe2f66631aa1dddef328491459edd3713e1bec)
- Assessment: [0x81af84d74fafb319aa9d3e1940a4d5b4f018e8704c54fe99e90f212feafa2c69](https://explorer-studio.genlayer.com/tx/0x81af84d74fafb319aa9d3e1940a4d5b4f018e8704c54fe99e90f212feafa2c69)
- Stored assessment: ID `0`, status `SUPPORTED`
- Event: `us7000tuhe`, magnitude `2.5`, reviewed, `12 km NW of Junction, Utah`
- CSV response SHA-256: `d0c748bc1a0952fabb44b40758cb7cce0fe4ecc68cd0fa8682bf76e41e60ee98`

## Development

Install the development dependency and run the helper tests:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m py_compile contracts/quake_witness.py
pytest -q
