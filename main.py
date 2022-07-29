from scan import scan_domain
import signatures
import output
import detection_enums
import domain_providers

from multiprocessing.pool import ThreadPool
import threading
from functools import partial

import logging
from sys import stderr, exit

import argparsing

print(argparsing.banner, file=stderr)
args = argparsing.parse_args()

###### verbosity

if args.verbose == 0:
    verbosity_level = logging.WARN
if args.verbose == 1:
    verbosity_level = logging.INFO
if args.verbose > 1:
    verbosity_level = logging.DEBUG

logging.basicConfig(format="%(message)s", level=verbosity_level)
logging.StreamHandler(stderr)
###### domain ingestion

if args.provider == "file":
    domains = domain_providers.from_file(args.filename)

if args.provider == "aws":
    domains = domain_providers.from_aws(
        args.aws_access_key_id, args.aws_access_key_secret
    )
###### signatures

signatures = [getattr(signatures, signature) for signature in signatures.__all__]

# replace name for each signature
for signature in signatures:
    signature.__name__ = signature.__name__.replace("signatures.", "")

if args.signature:
    signatures = [s for s in signatures if s.__name__ in args.signature]

if args.exclude_signature:
    signatures = [s for s in signatures if s.__name__ not in args.exclude_signature]

if args.disable_unlikely:
    signatures = [
        s for s in signatures if s.CONFIDENCE != detection_enums.CONFIDENCE.UNLIKELY
    ]

if args.disable_probable:
    signatures = [
        s for s in signatures if s.CONFIDENCE != detection_enums.CONFIDENCE.POTENTIAL
    ]

logging.info(f"Testing with {len(signatures)} signatures")


###### scanning

findings = []
lock = threading.Lock()
with output.Output(args.out_format, args.out) as o:
    scan = partial(
        scan_domain,
        signatures=signatures,
        output_handler=o,
        lock=lock,
        findings=findings,
    )
    pool = ThreadPool(processes=args.parallelism)
    pool.map(scan, domains)


###### exit

logging.warning(f"\n\nWe found {len(findings)} takeovers ☠️")
for finding in findings:
    logging.warning(f"-- DOMAIN '{finding.domain}' :: SIGNATURE '{finding.signature}'")
logging.warning(f"\n...Thats all folks!")

if args.pipeline:
    logging.debug(f"Pipeline flag set - Exit code: {len(findings)}")
    exit(len(findings))

# TOFO: test empire-alpha.integ.amazon.com , dipper-cts-gamma-tcp.aws.amazon.com
