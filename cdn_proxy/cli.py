import typer
import cdn_proxy.cloudfront.cli
import cdn_proxy.cloudflare.cli

app = typer.Typer(
    name="cdn_proxy",
    help="Tool for bypassing IP restrictions in origins fronted by shared CDNs.",
    context_settings={"help_option_names": ["-h", "--help"]},
)

app.add_typer(cdn_proxy.cloudfront.cli.app, name="cloudfront")
app.add_typer(cdn_proxy.cloudflare.cli.app, name="cloudflare")
