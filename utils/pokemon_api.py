import aiohttp
import os

API_URL = os.getenv("POKEMON_API_URL")

async def identify_pokemon(image_url: str) -> str | None:
    if not API_URL:
        return None

    payload = {"image_url": image_url}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, timeout=15) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()
                return data.get("pokemon")

    except Exception:
        return None
