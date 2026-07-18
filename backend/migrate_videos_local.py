"""Migration one-shot : copie les vidéos fal.media existantes en local et met à jour les documents."""
import asyncio
import os
import sys

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))


async def main():
    import ai_media_service
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    jobs = await db.ai_video_jobs.find(
        {"status": "DONE", "video_url": {"$regex": "^https://"}}, {"_id": 0}
    ).to_list(50)
    print(f"{len(jobs)} vidéo(s) fal.media à migrer")
    for job in jobs:
        fal_url = job["video_url"]
        try:
            local_url = await ai_media_service.download_video_locally(fal_url, job["id"])
        except Exception as exc:
            print(f"ECHEC {job['id']}: {exc}")
            continue
        await db.ai_video_jobs.update_one(
            {"id": job["id"]}, {"$set": {"video_url": local_url, "fal_video_url": fal_url}}
        )
        await db.vendor_products.update_one(
            {"id": job["product_id"], "video_url": fal_url}, {"$set": {"video_url": local_url}}
        )
        await db.products.update_one(
            {"id": job["product_id"], "video_url": fal_url}, {"$set": {"video_url": local_url}}
        )
        print(f"OK {job['id']} -> {local_url}")


asyncio.run(main())
