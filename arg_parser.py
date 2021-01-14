import argparse
from iotscp.core.sccertificate import (
    DEFAULT_SEGMENTS,
    DEFAULT_SEGMENT_LENGTH
)

# LANG = "eng"

def parse_args():
    parser = argparse.ArgumentParser(
        description="Start the IOTSCP device defined in `userdevice.py`"
    )
    parser.add_argument(
        "action",
        help=(
            "The action you would like to perform "
            "`start` starts the device server "
            "`get_cert` creates a new certificate "
        ),
        choices=["start", "get_cert"]
    )
    parser.add_argument(
        "--certsize",
        default=[DEFAULT_SEGMENTS, DEFAULT_SEGMENT_LENGTH],
        nargs=2,
        type=int,
        help=(
            "The size of the certificate to be generated. "
            "--certsize 1000 1500 would create a certificate with 1000, 1500 "
            "character segments"
        )
    )
    parser.add_argument(
        "--port",
        default=8000,
        type=int,
        help=(
            "The port that the HTTP server should listen on. "
            "Defaults to 8000"
        ),
    )
    parser.add_argument(
        "--loglvl",
        default="INFO",
        help="The level to log at. Defaults to INFO",
        choices=["DEBUG", "INFO", "ERROR"]
    )
    parser.add_argument(
        "--logfile",
        default="",
        help="The file to log to. Defaults to stdout"
    )
    return parser.parse_args()
