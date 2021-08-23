from botocore.exceptions import NoCredentialsError, NoRegionError

from cdn_proxy.cli import app
import logging
import typer

from cdn_proxy.lib import CdnProxyException

logging.basicConfig(format="[%(levelname)s] %(message)s", level=logging.WARNING)

try:
    app(prog_name="cdn_proxy")
except CdnProxyException as e:
    typer.echo(typer.style(" ".join(e.args), fg=typer.colors.RED))
