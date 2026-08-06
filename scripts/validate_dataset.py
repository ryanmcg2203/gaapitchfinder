#!/usr/bin/env python3
"""Validate the canonical GAA Pitch Finder CSV before generating site output.

Directions coordinates may differ from the canonical Latitude/Longitude values by
at most 0.00001 degrees (roughly 1.1 metres of latitude). Small differences from
decimal precision are accepted; larger differences usually indicate stale links.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Collection, Iterable, Mapping, Sequence
from urllib.parse import parse_qs, urlparse


ROOT_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT_DIR / "gaapitchfinder_data.csv"

EXPECTED_HEADERS = (
    "File",
    "Club",
    "Pitch",
    "Code",
    "Latitude",
    "Longitude",
    "Province",
    "Country",
    "Division",
    "County",
    "Directions",
    "Twitter",
    "Elevation",
    "annual_rainfall",
    "rain_days",
    "Wikipedia",
)
REQUIRED_CORE_FIELDS = (
    "File",
    "Club",
    "Latitude",
    "Longitude",
    "Province",
    "Country",
    "Division",
    "County",
    "Directions",
)

ALLOWED_URL_SCHEMES = {"http", "https"}
ALLOWED_DIRECTIONS_HOSTS = {"maps.google.com"}
ALLOWED_TWITTER_HOSTS = {
    "twitter.com",
    "www.twitter.com",
    "x.com",
    "www.x.com",
    # A few clubs publish only an Instagram profile in the legacy Twitter column.
    "instagram.com",
    "www.instagram.com",
}
ALLOWED_WIKIPEDIA_HOSTS = {
    "wikipedia.org",
    "www.wikipedia.org",
    "*.wikipedia.org",
}

DIRECTIONS_COORDINATE_TOLERANCE = 0.00001


@dataclass(frozen=True)
class NumericRule:
    minimum: float
    maximum: float


OPTIONAL_NUMERIC_RULES = {
    "Elevation": NumericRule(-500, 9000),
    "annual_rainfall": NumericRule(0, 12000),
    "rain_days": NumericRule(0, 366),
}


@dataclass(frozen=True)
class Diagnostic:
    line_number: int
    message: str
    severity: str = "error"

    def format(self, path: Path) -> str:
        return f"{self.severity.upper()}: {path}:{self.line_number}: {self.message}"


@dataclass
class ValidationResult:
    row_count: int = 0
    errors: list[Diagnostic] = field(default_factory=list)
    information: list[Diagnostic] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class CsvRecord:
    line_number: int
    values: tuple[str, ...]
    row: Mapping[str, str]


def format_coordinate(value: float) -> str:
    """Format coordinates precisely enough to make small mismatches visible."""
    return f"{value:.12g}"


def validate_headers(headers: Sequence[str]) -> list[Diagnostic]:
    """Return an error unless headers exactly match the public CSV schema."""
    if tuple(headers) == EXPECTED_HEADERS:
        return []
    return [
        Diagnostic(
            1,
            f"headers must be {list(EXPECTED_HEADERS)!r}; found {list(headers)!r}",
        )
    ]


def parse_finite_number(value: str) -> float:
    """Parse a finite floating-point value, raising ValueError otherwise."""
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("not a number") from error
    if not math.isfinite(number):
        raise ValueError("not finite")
    return number


def host_is_allowed(hostname: str, allowed_hosts: Collection[str]) -> bool:
    """Match a hostname against exact names and ``*.example.com`` entries."""
    hostname = hostname.lower()
    for allowed_host in allowed_hosts:
        allowed_host = allowed_host.lower()
        if hostname == allowed_host:
            return True
        if allowed_host.startswith("*.") and hostname.endswith(allowed_host[1:]):
            return True
    return False


def validate_url(value: str, allowed_hosts: Collection[str]) -> str | None:
    """Return a reason when a URL does not use an allowed scheme and host."""
    try:
        parsed = urlparse(value)
    except ValueError as error:
        return f"is malformed ({error})"
    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_URL_SCHEMES:
        found = repr(parsed.scheme) if parsed.scheme else "no scheme"
        return f"scheme must be http or https; found {found}"

    try:
        hostname = (parsed.hostname or "").lower()
    except ValueError:
        hostname = ""
    if not hostname or not host_is_allowed(hostname, allowed_hosts):
        found = repr(hostname) if hostname else "no host"
        return f"host is not allowed; found {found}"
    return None


def parse_directions_coordinates(url: str) -> tuple[float, float]:
    """Extract a finite, world-bounded latitude/longitude pair from ``daddr``."""
    try:
        query = urlparse(url).query
    except ValueError as error:
        raise ValueError(f"is malformed ({error})") from error
    values = parse_qs(query).get("daddr", [])
    if len(values) != 1:
        raise ValueError("must contain exactly one daddr query parameter")

    parts = values[0].split(",")
    if len(parts) != 2:
        raise ValueError("daddr must contain latitude and longitude")
    try:
        latitude = parse_finite_number(parts[0])
        longitude = parse_finite_number(parts[1])
    except ValueError as error:
        raise ValueError(f"daddr coordinates are {error}") from error

    if not -90 <= latitude <= 90:
        raise ValueError("daddr latitude must be between -90 and 90")
    if not -180 <= longitude <= 180:
        raise ValueError("daddr longitude must be between -180 and 180")
    return latitude, longitude


def _validate_numeric_field(
    row: Mapping[str, str],
    field_name: str,
    line_number: int,
    rule: NumericRule,
) -> tuple[float | None, list[Diagnostic]]:
    raw_value = (row.get(field_name) or "").strip()
    if not raw_value:
        return None, []

    try:
        number = parse_finite_number(raw_value)
    except ValueError as error:
        return None, [
            Diagnostic(
                line_number,
                f"{field_name} must be a finite number; found {raw_value!r} ({error})",
            )
        ]

    if not rule.minimum <= number <= rule.maximum:
        return None, [
            Diagnostic(
                line_number,
                f"{field_name} must be between {rule.minimum:g} and "
                f"{rule.maximum:g}; found {raw_value!r}",
            )
        ]
    return number, []


def validate_row(row: Mapping[str, str], line_number: int) -> list[Diagnostic]:
    """Validate one schema-compatible CSV row."""
    errors = []
    for field_name in REQUIRED_CORE_FIELDS:
        if not (row.get(field_name) or "").strip():
            errors.append(Diagnostic(line_number, f"{field_name} is required"))

    latitude, latitude_errors = _validate_numeric_field(
        row, "Latitude", line_number, NumericRule(-90, 90)
    )
    longitude, longitude_errors = _validate_numeric_field(
        row, "Longitude", line_number, NumericRule(-180, 180)
    )
    errors.extend(latitude_errors)
    errors.extend(longitude_errors)

    for field_name, rule in OPTIONAL_NUMERIC_RULES.items():
        _value, numeric_errors = _validate_numeric_field(
            row, field_name, line_number, rule
        )
        errors.extend(numeric_errors)

    url_rules = (
        ("Directions", ALLOWED_DIRECTIONS_HOSTS),
        ("Twitter", ALLOWED_TWITTER_HOSTS),
        ("Wikipedia", ALLOWED_WIKIPEDIA_HOSTS),
    )
    directions_url_is_valid = False
    for field_name, allowed_hosts in url_rules:
        value = (row.get(field_name) or "").strip()
        if not value:
            continue
        url_error = validate_url(value, allowed_hosts)
        if url_error:
            errors.append(Diagnostic(line_number, f"{field_name} URL {url_error}"))
        elif field_name == "Directions":
            directions_url_is_valid = True

    if directions_url_is_valid:
        directions_url = (row.get("Directions") or "").strip()
        try:
            directions_latitude, directions_longitude = (
                parse_directions_coordinates(directions_url)
            )
        except ValueError as error:
            errors.append(Diagnostic(line_number, f"Directions URL {error}"))
        else:
            if latitude is not None and longitude is not None and (
                abs(directions_latitude - latitude)
                > DIRECTIONS_COORDINATE_TOLERANCE
                or abs(directions_longitude - longitude)
                > DIRECTIONS_COORDINATE_TOLERANCE
            ):
                errors.append(
                    Diagnostic(
                        line_number,
                        "Directions daddr coordinates "
                        f"({format_coordinate(directions_latitude)}, "
                        f"{format_coordinate(directions_longitude)}) do not "
                        "match Latitude/Longitude "
                        f"({format_coordinate(latitude)}, "
                        f"{format_coordinate(longitude)}) within "
                        f"{DIRECTIONS_COORDINATE_TOLERANCE:g} degrees",
                    )
                )

    return errors


def find_shared_coordinate_information(
    records: Iterable[CsvRecord],
) -> list[Diagnostic]:
    """Report shared coordinates without failing validation.

    Different clubs often legitimately share one ground, so these diagnostics are
    intended for human review and are kept separate from validation errors.
    """
    coordinate_records = defaultdict(list)
    for record in records:
        try:
            latitude = parse_finite_number(record.row["Latitude"].strip())
            longitude = parse_finite_number(record.row["Longitude"].strip())
        except (KeyError, AttributeError, ValueError):
            continue
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            continue
        coordinate_records[(latitude, longitude)].append(record)

    information = []
    for (latitude, longitude), matches in sorted(coordinate_records.items()):
        if len(matches) < 2:
            continue
        line_numbers = ", ".join(str(record.line_number) for record in matches)
        names = ", ".join(
            (record.row.get("Club") or "<unnamed>").strip() or "<unnamed>"
            for record in matches
        )
        information.append(
            Diagnostic(
                matches[0].line_number,
                f"coordinates {format_coordinate(latitude)},"
                f"{format_coordinate(longitude)} are shared by "
                f"CSV lines {line_numbers} ({names})",
                severity="info",
            )
        )
    return information


def validate_dataset(path: str | Path = DATASET_PATH) -> ValidationResult:
    """Validate a CSV file and return errors plus non-failing information."""
    dataset_path = Path(path)
    result = ValidationResult()
    records = []
    first_seen_rows: dict[tuple[str, ...], int] = {}

    try:
        dataset_file = dataset_path.open(encoding="utf-8", newline="")
    except OSError as error:
        result.errors.append(Diagnostic(1, f"cannot read dataset: {error}"))
        return result

    try:
        with dataset_file:
            reader = csv.reader(dataset_file, strict=True)
            try:
                headers = next(reader)
            except StopIteration:
                result.errors.append(Diagnostic(1, "dataset is empty"))
                return result
            except csv.Error as error:
                result.errors.append(Diagnostic(1, f"invalid CSV: {error}"))
                return result

            result.errors.extend(validate_headers(headers))
            headers_are_valid = tuple(headers) == EXPECTED_HEADERS

            while True:
                line_number = reader.line_num + 1
                try:
                    values = next(reader)
                except StopIteration:
                    break
                except csv.Error as error:
                    result.errors.append(
                        Diagnostic(
                            max(line_number, reader.line_num),
                            f"invalid CSV: {error}",
                        )
                    )
                    break

                result.row_count += 1
                row_values = tuple(values)
                if len(values) != len(EXPECTED_HEADERS):
                    result.errors.append(
                        Diagnostic(
                            line_number,
                            f"expected {len(EXPECTED_HEADERS)} columns; "
                            f"found {len(values)}",
                        )
                    )
                    continue

                first_line = first_seen_rows.setdefault(row_values, line_number)
                if first_line != line_number:
                    result.errors.append(
                        Diagnostic(
                            line_number,
                            f"exact duplicate of CSV line {first_line}",
                        )
                    )

                if not headers_are_valid:
                    continue
                row = dict(zip(EXPECTED_HEADERS, values))
                record = CsvRecord(line_number, row_values, row)
                records.append(record)
                result.errors.extend(validate_row(row, line_number))
    except UnicodeDecodeError as error:
        result.errors.append(
            Diagnostic(
                max(1, result.row_count + 2),
                f"dataset is not valid UTF-8: {error}",
            )
        )

    result.information.extend(find_shared_coordinate_information(records))
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DATASET_PATH,
        help=f"CSV to validate (default: {DATASET_PATH})",
    )
    args = parser.parse_args(argv)

    result = validate_dataset(args.path)
    for diagnostic in result.information:
        print(diagnostic.format(args.path))
    for diagnostic in result.errors:
        print(diagnostic.format(args.path), file=sys.stderr)

    if not result.is_valid:
        print(
            f"Dataset validation failed with {len(result.errors)} error(s) "
            f"across {result.row_count} data row(s)",
            file=sys.stderr,
        )
        return 1

    notice_suffix = ""
    if result.information:
        notice_suffix = f"; {len(result.information)} shared-coordinate notice(s)"
    print(f"Dataset validation passed: {result.row_count} data row(s){notice_suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
