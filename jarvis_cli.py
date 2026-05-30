#!/usr/bin/env python3
"""
JARVIS CLI client — sends queries to the running daemon via named pipe.
"""
import argparse
import os
import sys
import time
import json

PIPE_PATH = os.path.expanduser('~/.jarvis_pipe')


def send_query(query):
    """Send a query to the JARVIS daemon via named pipe."""
    if not os.path.exists(PIPE_PATH):
        print('ERROR: JARVIS daemon is not running.', file=sys.stderr)
        print('Start it with: python3 setup_jarvis_daemon.py && launchctl load ~/Library/LaunchAgents/com.mehedi.jarvis.daemon.plist', file=sys.stderr)
        return False

    response_pipe = os.path.expanduser(f'~/.jarvis_response_{os.getpid()}')
    try:
        if os.path.exists(response_pipe):
            os.remove(response_pipe)
        os.mkfifo(response_pipe, 0o666)
    except Exception as exc:
        print(f'ERROR: Unable to create response pipe: {exc}', file=sys.stderr)
        return False

    request = {'query': query, 'response_pipe': response_pipe}
    try:
        with open(PIPE_PATH, 'w', encoding='utf-8') as pipe:
            pipe.write(json.dumps(request) + '\n')
            pipe.flush()
    except Exception as exc:
        print(f'ERROR: Failed to send query: {exc}', file=sys.stderr)
        try:
            os.remove(response_pipe)
        except Exception:
            pass
        return False

    try:
        with open(response_pipe, 'r', encoding='utf-8') as out_pipe:
            response = out_pipe.readline().strip()
            print(response)
            return True
    except Exception as exc:
        print(f'ERROR: Failed to read response: {exc}', file=sys.stderr)
        return False
    finally:
        try:
            os.remove(response_pipe)
        except Exception:
            pass

    try:
        with open(PIPE_PATH, 'w', encoding='utf-8') as pipe:
            pipe.write(query + '\n')
            pipe.flush()
        print(f'Query sent to JARVIS: {query}')
        return True
    except Exception as exc:
        print(f'ERROR: Failed to send query: {exc}', file=sys.stderr)
        return False


def build_parser():
    parser = argparse.ArgumentParser(description='Query JARVIS daemon.')
    parser.add_argument('query', nargs='?', help='Your question for JARVIS')
    parser.add_argument('-i', '--interactive', action='store_true', help='Interactive mode')
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.interactive:
        print('JARVIS CLI (interactive mode). Type "exit" to quit.')
        while True:
            try:
                query = input('Mehedi > ').strip()
            except (EOFError, KeyboardInterrupt):
                print('\nGoodbye.')
                break
            if not query:
                continue
            if query.lower() in ('exit', 'quit'):
                print('Goodbye.')
                break
            send_query(query)
    elif args.query:
        send_query(args.query)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

