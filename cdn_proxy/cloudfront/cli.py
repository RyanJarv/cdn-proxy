from enum import Enum
import boto3

import typer

from cdn_proxy.cloudfront import CloudFront

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
def create(target: str = typer.Argument(..., help='Optional device name to limit snapshots to.')):
    """
    Create a new CloudFront distribution and Lambda@Edge function targeting the specified origin.

    Requests that pass through this distribution will have their Host header rewritten by the Lambda@Edge function to
    specify the target domain.

    The X-Forwarded-For header will be also set to a random IP address by the Lambda@Edge function.
    """

    cloudfront = CloudFront(sess, target)
    with typer.progressbar(cloudfront.create(), length=20, label=f"Creating {target}") as progress:
        for update in progress:
            progress.update(1)
            progress.label = typer.style(update, fg=typer.colors.CYAN)
    typer.echo(f"The new distribution is accessible at {cloudfront.domain_name}", color=typer.colors.GREEN)


@app.command()
def delete(target: str = typer.Argument(..., help='Optional device name to limit snapshots to.')):
    """
    Disable and delete the specified distribution.

    ID specifies the CloudFront distribution to delete, this can be found with the list command.
    """

    cloudfront = CloudFront(sess, target)
    with typer.progressbar(cloudfront.delete(), length=20, label=f"Destroying {id}") as progress:
        for update in progress:
            progress.update(1)
            progress.label = typer.style(update, fg=typer.colors.CYAN)


@app.command(name="list")
def list_distributions():
    """
    List CloudFront distributions IDs and targets created with cdn-proxy.

    Distributions created with cdn-proxy are marked by setting the cdn-proxy-target tag to the name of the target. This
    command will only list distributions with this tag key.
    """

    for (target, _id) in CloudFront.list(sess):
        typer.echo(f"* {typer.style(target, fg=typer.colors.CYAN)} -- {_id}")
