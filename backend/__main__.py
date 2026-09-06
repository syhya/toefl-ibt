import argparse
import uvicorn
from .app import create_app


def main():
    parser = argparse.ArgumentParser(description='Start the local TOEFL practice service.')
    parser.add_argument('--port', type=int, default=4173)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Choose a port between 1 and 65535.')
    uvicorn.run(create_app(), host='127.0.0.1', port=args.port, log_level='warning')


if __name__ == '__main__':
    main()
