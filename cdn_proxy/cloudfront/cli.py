import asyncio
from typing import List

import boto3

import typer

from cdn_proxy.cloudfront import CloudFront
from cdn_proxy.cloudfront.scanner import CloudFrontScanner
from cdn_proxy.lib import networks_to_hosts

app = typer.Typer(name="cloudfront", help="Manage CloudFront distributions")

sess: boto3.session.Session = boto3.session.Session()


@app.callback()
def session(
    region: str = typer.Option(
        default="us-east-1", help="Sets the AWS region.", metavar="REGION"
    ),
    profile: str = typer.Option(
        default=None, help="Shared credential profile to use.", metavar="PROFILE"
    ),
):
    global sess
    sess = boto3.session.Session(region_name=region, profile_name=profile)


@app.command()
def create():
    """
    Create a new CloudFront distribution and Lambda@Edge function targeting the specified origin.

    Requests that pass through this distribution will have their Host header rewritten by the Lambda@Edge function to
    specify the target domain.

    The X-Forwarded-For header will be also set to a random IP address by the Lambda@Edge function.
    """

    cloudfront = CloudFront(sess)
    with typer.progressbar(
        cloudfront.create(), length=20, label=f"Creating Proxy"
    ) as progress:
        for update in progress:
            progress.label = typer.style(update, fg=typer.colors.CYAN)
            progress.update(1)
    typer.echo(
        f"The new distribution is accessible at {cloudfront.domain_name}",
        color=typer.colors.GREEN,
    )


@app.command()
def scan(
    workers: int = typer.Option(20, help="Max concurrent workers."),
    host: str = typer.Option(None, help="Optional device name to limit snapshots to."),
    targets: List[str] = typer.Argument(
        ..., help="Optional device name to limit snapshots to."
    ),
):
    """
    Create a new CloudFront distribution and Lambda@Edge function targeting the specified origin.

    Requests that pass through this distribution will have their Host header rewritten by the Lambda@Edge function to
    specify the target domain.

    The X-Forwarded-For header will be also set to a random IP address by the Lambda@Edge function.
    """
    asyncio.run(_scan(host, targets, workers))


async def _scan(host, targets, workers):
    async with CloudFrontScanner(sess, workers=workers) as scan:
        tasks = []
        with typer.progressbar(list(networks_to_hosts(targets)), label=f"Scanning") as progress:
            for origin in progress:
                tasks.append(scan.scan(origin, host))

        await asyncio.gather(*tasks)


@app.command()
def delete():
    """
    Disable and delete the specified distribution.

    ID specifies the CloudFront distribution to delete, this can be found with the list command.
    """

    cloudfront = CloudFront(sess)
    with typer.progressbar(
        cloudfront.delete(), length=30, label=f"Destroying {id}"
    ) as progress:
        for update in progress:
            progress.label = typer.style(update, fg=typer.colors.CYAN)
            progress.update(1)


@app.command()
def status():
    """Get the status of the CloudFront deployment."""

    proxy = CloudFront.status(sess)
    if proxy:
        typer.echo(f"Status: {typer.style('Deployed', bold=True, fg=typer.colors.GREEN)}")
        typer.echo(f"DistributionID: {typer.style(proxy.id, bold=True)}")
        typer.echo(f"ProxyUrl: {typer.style(proxy.domain, bold=True)}")
    else:
        typer.echo(f"Status: {typer.style('Not Deployed', bold=True, fg=typer.colors.RED)}")
