import json
import os

import click

from yt_archive.app import app

@click.group(name = 'yt_archive')
@click.version_option(version = '0.1',
                      prog_name = 'YouTube Archive')
@click.pass_context
def cli(ctx):
    ...

@cli.command(help = 'Run server.')
@click.option('--host', '-h', default = '127.0.0.1',
              help = 'The interface to bind to.')
@click.option('--port', '-p', default = 8090,
              help = 'The port to bind to.')
@click.option('--debug', '-d', is_flag = True,
              help = 'Turns on debug mode.')
@click.pass_context
def run(ctx, host, port, debug):
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # TODO: rm in production

    if not os.path.isfile('../db.json'):
        with open('../db.json', 'w') as f:
            json.dump({}, f, indent = 2, sort_keys = True)

    app.run(host = host, port = port, debug = debug)

def main():
    cli(obj = {})
