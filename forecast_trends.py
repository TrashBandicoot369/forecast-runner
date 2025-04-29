import logging
from datetime import datetime, timedelta, timezone
from firebase_admin_setup import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_trending_memes(hours: int = 6):
    memes_ref = db.collection("memes")
    now_ts = datetime.now(timezone.utc).timestamp()
    cutoff_ts = now_ts - (hours * 3600)

    query = memes_ref.where("created_utc", ">", cutoff_ts)
    try:
        results = query.stream()
        memes = []
        for doc in results:
            meme = doc.to_dict()
            meme["id"] = doc.id
            memes.append(meme)
        logger.info(f"Fetched {len(memes)} memes from the last {hours} hours")
        return memes
    except Exception as e:
        logger.error(f"Error fetching memes: {e}")
        return []

def score_virality(meme: dict) -> float:
    upvotes = meme.get("upvotes", 0)
    ratio = meme.get("upvote_ratio", 1.0)
    comments = meme.get("comments", 0)
    created_utc = meme.get("created_utc")

    if not created_utc:
        return 0.0

    hours_since_post = (datetime.now(timezone.utc).timestamp() - created_utc) / 3600
    hours_since_post = max(hours_since_post, 0.1)

    score = (upvotes * ratio + comments * 2) / hours_since_post
    return round(score, 2)

def push_alert(meme_id: str, reason: str):
    try:
        db.collection("alerts").add({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "memeId": meme_id,
            "reason": reason
        })
        logger.info(f"🚨 Alert for {meme_id}: {reason}")
    except Exception as e:
        logger.error(f"Failed to push alert for {meme_id}: {e}")

def update_meme_forecast(meme_id: str, score: float, meme: dict):
    try:
        # Check last score before update
        prev_score = meme.get("forecastScore", 0)
        spike = prev_score > 0 and ((score - prev_score) / prev_score) >= 0.5
        threshold = score > 75

        if spike:
            push_alert(meme_id, f"Forecast score spiked {prev_score} → {score}")
        elif threshold:
            push_alert(meme_id, f"Forecast score exceeded 75: {score}")

        db.collection("memes").document(meme_id).update({"forecastScore": score})
    except Exception as e:
        logger.warning(f"Failed to update meme {meme_id}: {e}")

def snapshot_top_forecasts(memes: list, top_n: int = 5):
    if not memes:
        logger.warning("No memes to snapshot.")
        return

    sorted_memes = sorted(memes, key=lambda m: score_virality(m), reverse=True)
    top_memes = sorted_memes[:top_n]
    timestamp = datetime.now(timezone.utc).isoformat()

    snapshot_data = {
        "timestamp": timestamp,
        "memes": [
            {
                "id": m["id"],
                "title": m.get("title") or m.get("name") or "untitled",
                "forecastScore": score_virality(m),
                "lulzScore": m.get("lulzScore", 0),
                "vibeShift": m.get("vibeShift", 0),
                "image_url": m.get("image_url"),
                "link": m.get("link")
            }
            for m in top_memes
        ]
    }

    try:
        db.collection("trending_snapshots").add(snapshot_data)
        logger.info(f"📸 Snapshot saved with top {top_n} forecast memes.")
    except Exception as e:
        logger.error(f"Failed to save snapshot: {e}")

if __name__ == "__main__":
    memes = get_trending_memes()
    for meme in memes:
        score = score_virality(meme)
        update_meme_forecast(meme["id"], score, meme)
    snapshot_top_forecasts(memes)
