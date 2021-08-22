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
        region: str = typer.Option(default='us-east-1', help="Sets the AWS region.", metavar="REGION"),
        profile: str = typer.Option(default=None, help="Shared credential profile to use.", metavar="PROFILE")
):
    global sess
    sess = boto3.session.Session(region_name=region, profile_name=profile)


@app.command()
def create(
        host: str = typer.Option(None, help='Value to set the Host header to set on requests to the origin.'),
        target: str = typer.Argument(..., help='Optional device name to limit snapshots to.'),
):
    """
    Create a new CloudFront distribution and Lambda@Edge function targeting the specified origin.

    Requests that pass through this distribution will have their Host header rewritten by the Lambda@Edge function to
    specify the target domain.

    The X-Forwarded-For header will be also set to a random IP address by the Lambda@Edge function.
    """

    cloudfront = CloudFront(sess, target, host)
    with typer.progressbar(cloudfront.create(), length=20, label=f"Creating {target}") as progress:
        for update in progress:
            progress.label = typer.style(update, fg=typer.colors.CYAN)
            progress.update(1)
    typer.echo(f"The new distribution is accessible at {cloudfront.domain_name}", color=typer.colors.GREEN)


@app.command()
def update(
        host: str = typer.Option(None, help='Value to set the Host header to set on requests to the origin.'),
        target: str = typer.Argument(..., help='Optional device name to limit snapshots to.'),
):
    """
    Create a new CloudFront distribution and Lambda@Edge function targeting the specified origin.

    Requests that pass through this distribution will have their Host header rewritten by the Lambda@Edge function to
    specify the target domain.

    The X-Forwarded-For header will be also set to a random IP address by the Lambda@Edge function.
    """

    cloudfront = CloudFront(sess, target, host)
    with typer.progressbar(cloudfront.update(), length=20, label=f"Creating {target}") as progress:
        for update in progress:
            progress.label = typer.style(update, fg=typer.colors.CYAN)
            progress.update(1)
    typer.echo(f"The new distribution is accessible at {cloudfront.domain_name}", color=typer.colors.GREEN)


@app.command()
def scan(
        workers: int = typer.Option(20, help='Max concurrent workers.'),
        host: str = typer.Option(None, help='Optional device name to limit snapshots to.'),
        targets: List[str] = typer.Argument(..., help='Optional device name to limit snapshots to.'),
):
    """
    Create a new CloudFront distribution and Lambda@Edge function targeting the specified origin.

    Requests that pass through this distribution will have their Host header rewritten by the Lambda@Edge function to
    specify the target domain.

    The X-Forwarded-For header will be also set to a random IP address by the Lambda@Edge function.
    """
    asyncio.run(_scan(host, targets, workers))


async def _scan(host, targets, workers):
    async with CloudFrontScanner(sess, max=workers) as scan:
        tasks = []
        with typer.progressbar(list(networks_to_hosts(targets)), label=f"Scanning") as progress:
            for origin in progress:
                tasks.append(scan.scan(str(origin), host))

        await asyncio.gather(*tasks)

@app.command()
def delete(target: str = typer.Argument(..., help='Optional device name to limit snapshots to.')):
    """
    Disable and delete the specified distribution.

    ID specifies the CloudFront distribution to delete, this can be found with the list command.
    """

    cloudfront = CloudFront(sess, target)
    with typer.progressbar(cloudfront.delete(), length=30, label=f"Destroying {id}") as progress:
        for update in progress:
            progress.label = typer.style(update, fg=typer.colors.CYAN)
            progress.update(1)


def status():
    """Get the status of the CloudFront deployment."""

    proxy = CloudFront.status(sess)
    typer.echo(f"* Target: {typer.style(proxy.target, fg=typer.colors.CYAN)} DistributionID: {proxy.id} "
               f"ProxyUrl: {proxy.domain}")
