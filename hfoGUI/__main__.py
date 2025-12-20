import sys

from .cli import build_parser, run_hilbert_batch
from .main import run

version = "1.0.8"


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == 'hilbert-batch':
        run_hilbert_batch(args)
    else:
        run()


if __name__ == '__main__':
    main(sys.argv[1:])
