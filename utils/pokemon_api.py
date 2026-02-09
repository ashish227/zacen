import os
import requests

API_URL = os.getenv("POKEMON_API_URL")


def identify_pokemon(image_url: str) -> str | None:
    if not API_URL:
        print("[API ERROR] POKEMON_API_URL not set")
        return None

    payload = {"image_url": image_url}

    try:
        response = requests.post(API_URL, json=payload, timeout=15)

        if response.status_code != 200:
            print(f"[API ERROR] {response.status_code} {response.text}")
            return None

        data = response.json()
        return data.get("pokemon")

    except Exception as e:
        print("[API EXCEPTION]", e)
        return None
