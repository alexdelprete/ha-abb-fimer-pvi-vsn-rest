"""VSN authentication."""
import aiohttp

async def detect_vsn_model(session: aiohttp.ClientSession, base_url: str) -> str:
    """Detect VSN300 or VSN700."""
    # TODO: Implement detection
    return "vsn700"
