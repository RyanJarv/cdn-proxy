import re
import typer

from cdn_proxy.cloudflare import CloudFlare

app = typer.Typer(
    name="cloudflare",
    help="Manage CloudFlare proxies",
    context_settings={"help_option_names": ["-h", "--help"]},
)

cloudflare: CloudFlare


@app.callback()
def session(
    token: str = typer.Option(..., help="Sets the AWS region.", metavar="REGION"),
    zone_name: str = typer.Option(..., help="Sets the AWS region.", metavar="REGION"),
):
    global cloudflare
    cloudflare = CloudFlare(token, zone_name)


@app.command()
def create(target: str = typer.Argument(..., help="The origin to target, can be an IP or hostname.")):
    """Create a new proxies CloudFlare DNS record targeting the specified origin."""

    with typer.progressbar(cloudflare.create(target), length=10, label=f"Creating {target}") as progress:
        for update in progress:
            progress.label = update
            progress.update(1)
    subdomain = re.sub(r'\.', '-', target)
    typer.echo(f"Created proxy for {target} -- {subdomain}.{cloudflare.zone_name}", color=typer.colors.GREEN)


@app.command()
def delete(id: str = typer.Argument(None, help="Optional device name to limit snapshots to.")):
    """
    Delete the delete the DNS record specified target.

    ID specifies the CloudFront distribution to delete, this can be found with the list command.
    """

    with typer.progressbar(
        cloudflare.delete(id), length=5, label=f"Destroying {id}"
    ) as progress:
        for update in progress:
            progress.label = update
            progress.update(1)


@app.command(name="list")
def _list():
    """
    List CloudFlare DNS records created with cdn-proxy.

    DNS records created with cdn-proxy will have a subdomain prefix of "cdn-proxy-". Records created with this tool
    will have a suffix of the target name, records created with the GoLang scanner will have a number as the suffix.
    """
    for (target, subdomain) in cloudflare.list():
        typer.echo(f"* {typer.style(target, fg=typer.colors.CYAN)} -- {subdomain}")
