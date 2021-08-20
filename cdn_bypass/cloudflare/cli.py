from enum import Enum
import boto3

import typer

from cdn_bypass.cloudflare import CloudFlare

app = typer.Typer(name="cloudflare", help="Manage CloudFlare distributions")

cloudflare: CloudFlare = None


@app.callback()
def session(
        token: str = typer.Option(..., help="Sets the AWS region.", metavar="REGION"),
        zone_name: str = typer.Option(..., help="Sets the AWS region.", metavar="REGION"),

):
    global cloudflare
    cloudflare = CloudFlare(token, zone_name)


@app.command()
def create(target: str = typer.Argument(..., help='Optional device name to limit snapshots to.')):
    """
    Create a new CloudFront distribution and Lambda@Edge function targeting the specified origin.

    Requests that pass through this distribution will have their Host header rewritten by the Lambda@Edge function to
    specify the target domain.

    The X-Forwarded-For header will be also set to a random IP address by the Lambda@Edge function.
    """

    with typer.progressbar(cloudflare.create(target), length=10, label=f"Creating {target}") as progress:
        for update in progress:
            progress.update(1)
            progress.label = update
    typer.echo(f"Created distribution {id}", color=typer.colors.GREEN)


@app.command()
def delete(id: str = typer.Argument(..., help='Optional device name to limit snapshots to.')):
    """
    Disable and delete the specified distribution.

    ID specifies the CloudFront distribution to delete, this can be found with the list command.
    """

    with typer.progressbar(cloudflare.delete(id), length=5, label=f"Destroying {id}") as progress:
        for update in progress:
            progress.update(1)
            progress.label = update


@app.command()
def list():
    """
    List CloudFront distributions IDs and targets created with cdn-proxy.

    Distributions created with cdn-proxy are marked by setting the cdn-proxy-target tag to the name of the target. This
    command will only list distributions with this tag key.
    """

    for (target, subdomain) in cloudflare.list():
        typer.echo(f"* {typer.style(target, fg=typer.colors.CYAN)} -- {subdomain}")
