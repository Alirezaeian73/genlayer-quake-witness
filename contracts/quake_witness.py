# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import hashlib
import json
import re


MAX_EVENT_ID_LENGTH = 40
MAX_CSV_LENGTH = 16000
MAGNITUDE_SCALE_DIGITS = 3
MAGNITUDE_SCALE = 10 ** MAGNITUDE_SCALE_DIGITS


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _clean_event_id(value: str) -> str:
    if not isinstance(value, str):
        raise gl.vm.UserError("Event ID must be text")
    event_id = value.strip()
    if not event_id or len(event_id) > MAX_EVENT_ID_LENGTH:
        raise gl.vm.UserError("Event ID is empty or too long")
    if re.fullmatch(r"[A-Za-z0-9_-]+", event_id) is None:
        raise gl.vm.UserError(
            "Event ID may contain only letters, numbers, hyphens, and underscores"
        )
    return event_id


def _scaled_magnitude(value: str):
    if not isinstance(value, str) or not value or len(value) > 24:
        return None
    match = re.fullmatch(r"([+-]?)(\d+)(?:\.(\d{1,3}))?", value.strip())
    if match is None:
        return None
    whole = int(match.group(2))
    fraction = (match.group(3) or "").ljust(MAGNITUDE_SCALE_DIGITS, "0")
    scaled = whole * MAGNITUDE_SCALE + (int(fraction) if fraction else 0)
    if match.group(1) == "-":
        scaled = -scaled
    if scaled < -10000 or scaled > 10000:
        return None
    return scaled


def _split_csv_line(line: str):
    fields = []
    current = []
    in_quotes = False
    index = 0
    while index < len(line):
        character = line[index]
        if character == '"':
            if in_quotes and index + 1 < len(line) and line[index + 1] == '"':
                current.append('"')
                index += 2
                continue
            in_quotes = not in_quotes
        elif character == "," and not in_quotes:
            fields.append("".join(current).strip())
            current = []
        else:
            current.append(character)
        index += 1
    if in_quotes:
        return None
    fields.append("".join(current).strip())
    return fields


def _parse_event_csv(csv_text: str, requested_event_id: str):
    if (
        not isinstance(csv_text, str)
        or not csv_text.strip()
        or len(csv_text) > MAX_CSV_LENGTH
    ):
        return None

    lines = [line for line in csv_text.strip().splitlines() if line.strip()]
    if not lines:
        return None

    header = _split_csv_line(lines[0].lstrip("\ufeff"))
    if header is None:
        return None

    required = (
        "time",
        "latitude",
        "longitude",
        "depth",
        "mag",
        "id",
        "place",
        "status",
    )
    indexes = {}
    for name in required:
        if name not in header:
            return None
        indexes[name] = header.index(name)

    if len(lines) == 1:
        return {"status": "NOT_FOUND", "event_id": requested_event_id}
    if len(lines) != 2:
        return None

    row = _split_csv_line(lines[1])
    if row is None or len(row) != len(header):
        return None

    result = {}
    for name in required:
        result[name] = row[indexes[name]]

    if result["id"].lower() != requested_event_id.lower():
        return None
    if _scaled_magnitude(result["mag"]) is None:
        return None

    return {"status": "OK", "event": result}


class QuakeWitness(gl.Contract):
    assessment_count: u256
    assessments: TreeMap[u256, str]

    def __init__(self):
        self.assessment_count = 0
        self.assessments = TreeMap()

    @gl.public.write
    def verify_event(self, event_id: str, claimed_magnitude: str) -> u256:
        event_id = _clean_event_id(event_id)
        claimed_value = _scaled_magnitude(claimed_magnitude)
        if claimed_value is None:
            raise gl.vm.UserError(
                "Magnitude must be a decimal with at most three places"
            )

        source_url = (
            "https://earthquake.usgs.gov/fdsnws/event/1/query"
            "?format=csv&eventid=" + event_id
        )

        def evaluate_source() -> str:
            try:
                response = gl.nondet.web.get(source_url)
                csv_text = response.body.decode("utf-8")
            except Exception:
                return _json({"status": "SOURCE_UNAVAILABLE"})

            parsed = _parse_event_csv(csv_text, event_id)
            if parsed is None:
                return _json({"status": "EXTRACTION_UNCLEAR"})
            if parsed.get("status") == "NOT_FOUND":
                return _json(parsed)

            return _json({
                "status": "OK",
                "source_url": source_url,
                "rendered_csv_sha256": hashlib.sha256(
                    csv_text.encode("utf-8")
                ).hexdigest(),
                "event": parsed["event"],
            })

        principle = (
            "Independently check both results against the returned official USGS CSV data. "
            "The results must agree on status. For status OK, require exact agreement on the "
            "event ID, magnitude, origin time, latitude, longitude, depth, place, and review "
            "status. Ignore differences in the CSV text hash only if these fields agree. "
            "Do not infer values or accept unsupported event data."
        )
        consensus_output = gl.eq_principle.prompt_comparative(
            evaluate_source,
            principle=principle,
        )

        try:
            if isinstance(consensus_output, str):
                observed = json.loads(consensus_output)
            elif isinstance(consensus_output, dict):
                observed = consensus_output
            else:
                observed = {"status": "EXTRACTION_UNCLEAR"}
        except Exception:
            observed = {"status": "EXTRACTION_UNCLEAR"}

        status = "UNCLEAR"
        event = observed.get("event", {}) if isinstance(observed, dict) else {}
        rendered_csv_sha256 = (
            observed.get("rendered_csv_sha256", "")
            if isinstance(observed, dict)
            else ""
        )
        observed_source_url = (
            observed.get("source_url", "")
            if isinstance(observed, dict)
            else ""
        )

        if (
            isinstance(observed, dict)
            and observed.get("status") == "SOURCE_UNAVAILABLE"
        ):
            status = "SOURCE_UNAVAILABLE"
        elif (
            isinstance(observed, dict)
            and observed.get("status") == "NOT_FOUND"
        ):
            status = "NOT_FOUND"
        elif (
            isinstance(observed, dict)
            and observed.get("status") == "OK"
            and isinstance(event, dict)
        ):
            source_event_id = event.get("id", "")
            source_magnitude = _scaled_magnitude(event.get("mag", ""))
            if (
                isinstance(source_event_id, str)
                and source_event_id.lower() == event_id.lower()
                and source_magnitude is not None
            ):
                status = (
                    "SUPPORTED"
                    if source_magnitude == claimed_value
                    else "CONTRADICTED"
                )

        record_id = self.assessment_count
        record = {
            "id": int(record_id),
            "status": status,
            "event_id_claim": event_id,
            "claimed_magnitude": claimed_magnitude.strip(),
            "source_url": observed_source_url or source_url,
            "rendered_csv_sha256": rendered_csv_sha256,
            "source_event_id": (
                event.get("id", "") if isinstance(event, dict) else ""
            ),
            "source_magnitude": (
                event.get("mag", "") if isinstance(event, dict) else ""
            ),
            "source_time": (
                event.get("time", "") if isinstance(event, dict) else ""
            ),
            "source_latitude": (
                event.get("latitude", "") if isinstance(event, dict) else ""
            ),
            "source_longitude": (
                event.get("longitude", "") if isinstance(event, dict) else ""
            ),
            "source_depth_km": (
                event.get("depth", "") if isinstance(event, dict) else ""
            ),
            "source_place": (
                event.get("place", "") if isinstance(event, dict) else ""
            ),
            "source_review_status": (
                event.get("status", "") if isinstance(event, dict) else ""
            ),
            "notice": (
                "This records agreement with one USGS earthquake catalog response. "
                "Magnitude and event details may be revised by the source. "
                "It is not an emergency alert or a substitute for official safety guidance."
            ),
        }
        self.assessments[record_id] = _json(record)
        self.assessment_count += 1
        return record_id

    @gl.public.view
    def get_assessment(self, assessment_id: u256) -> str:
        return self.assessments.get(assessment_id, "")

    @gl.public.view
    def get_assessment_count(self) -> u256:
        return self.assessment_count
