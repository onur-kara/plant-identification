"""
A small project to discover plant identification using AI.

For each plant in the plant_photo_dataset folder, send the three photos to the OpenAI agent. Each plant has its own folder.
If the name of the folder is "answers", skip it.
Record the responses in a JSON file.

"""

# Part 1: Plant Identification using OpenAI Assistants API

import os
import json
import asyncio
import httpx
import aiofiles
from pathlib import Path

# Set your OpenAI API key (ensure it's set in your environment)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ASSISTANT_ID = 'asst_y2zF37iRHlvBzopnnPaYg1q7'
BASE_URL = 'https://api.openai.com/v1'
HEADERS = {
    'Authorization': f'Bearer {OPENAI_API_KEY}',
    'OpenAI-Beta': 'assistants=v2',
}

DATASET_DIR = Path(__file__).parent / 'plant_photo_dataset'
OUTPUT_JSON = Path(__file__).parent / 'plant_id_results.json'

async def upload_image(file_path):
    url = f"{BASE_URL}/files"
    async with httpx.AsyncClient() as client:
        async with aiofiles.open(file_path, 'rb') as f:
            file_content = await f.read()
        files = {
            'file': (os.path.basename(file_path), file_content),
            'purpose': (None, 'vision'),
        }
        response = await client.post(url, headers=HEADERS, files=files)
        response.raise_for_status()
        return response.json()['id']

async def create_thread():
    url = f"{BASE_URL}/threads"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=HEADERS, json={})
        response.raise_for_status()
        return response.json()['id']

async def send_message(thread_id, file_ids):
    url = f"{BASE_URL}/threads/{thread_id}/messages"
    content = [
        {"type": "text", "text": "Please identify this plant from these three photos."},
        *[
            {"type": "image_file", "image_file": {"file_id": file_id, "detail": "auto"}}
            for file_id in file_ids
        ]
    ]
    body = {
        "role": "user",
        "content": content
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=HEADERS, json=body)
        response.raise_for_status()
        return response.json()['id']

async def run_assistant(thread_id):
    url = f"{BASE_URL}/threads/{thread_id}/runs"
    body = {
        "assistant_id": ASSISTANT_ID
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=HEADERS, json=body)
        response.raise_for_status()
        run = response.json()
        run_id = run['id']
        # Poll for completion
        while True:
            status_url = f"{BASE_URL}/threads/{thread_id}/runs/{run_id}"
            status_resp = await client.get(status_url, headers=HEADERS)
            status_resp.raise_for_status()
            status = status_resp.json()['status']
            if status in ['completed', 'failed', 'cancelled', 'expired']:  # terminal states
                break
            await asyncio.sleep(2)
        return status

async def get_latest_message(thread_id):
    url = f"{BASE_URL}/threads/{thread_id}/messages?order=desc&limit=1"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=HEADERS)
        response.raise_for_status()
        messages = response.json()['data']
        if messages:
            # Extract text content from the latest message
            for part in messages[0]['content']:
                if part['type'] == 'text':
                    return part['text']['value']
        return None

async def process_plant_folder(plant_folder):
    images = sorted(plant_folder.glob('*.jpg'))
    if len(images) != 3:
        print(f"Skipping {plant_folder.name}: expected 3 images, found {len(images)}")
        return plant_folder.name, "Error: Expected 3 images"
    # Upload images and get file IDs
    file_ids = []
    for img in images:
        try:
            file_id = await upload_image(str(img))
            file_ids.append(file_id)
        except Exception as e:
            print(f"Error uploading {img}: {e}")
            return plant_folder.name, f"Error uploading image: {e}"
    # Create thread, send message, run assistant, get response
    try:
        thread_id = await create_thread()
        await send_message(thread_id, file_ids)
        await run_assistant(thread_id)
        answer = await get_latest_message(thread_id)
        return plant_folder.name, answer
    except Exception as e:
        print(f"Error processing {plant_folder.name}: {e}")
        return plant_folder.name, f"Error: {e}"

async def main():
    results = {}
    tasks = []
    for plant_folder in DATASET_DIR.iterdir():
        if not plant_folder.is_dir() or plant_folder.name == 'answers':
            continue
        tasks.append(process_plant_folder(plant_folder))
    answers = await asyncio.gather(*tasks)
    for plant_name, answer in answers:
        results[plant_name] = answer
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results written to {OUTPUT_JSON}")

if __name__ == "__main__":
    asyncio.run(main())