import typer
import cdn_bypass.cloudfront.cli
import cdn_bypass.cloudflare.cli

app = typer.Typer(name="cdn_proxy", help="Tool for bypassing IP restrictions in origins fronted by shared CDNs.")

app.add_typer(cdn_bypass.cloudfront.cli.app, name="cloudfront")
app.add_typer(cdn_bypass.cloudflare.cli.app, name="cloudflare")
