import os
import aiohttp
import asyncio

API_URL = os.getenv("POKEMON_API_URL")


async def identify_pokemon(image_url: str) -> str | None:
    if not API_URL:
        print("[API ERROR] POKEMON_API_URL not set")
        return None

    payload = {"image_url": image_url}

    timeout = aiohttp.ClientTimeout(total=15)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(API_URL, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    print(f"[API ERROR] {response.status} {text}")
                    return None

                data = await response.json()
                return data.get("pokemon")

    except asyncio.TimeoutError:
        print("[API ERROR] Request timed out")
        return None

    except Exception as e:
        print("[API EXCEPTION]", e)
        return None
