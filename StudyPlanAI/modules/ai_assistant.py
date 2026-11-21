import os
import requests

from dotenv import load_dotenv


load_dotenv()


def get_study_recommendations(
    subjects,
    progress,
    weak_topics,
    schedule
):
    """Generate exam-preparation recommendations using Gemini."""

    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash"
    )

    if not api_key or api_key == "YOUR_GEMINI_API_KEY":
        return (
            "Gemini API key is not configured. "
            "Add GEMINI_API_KEY to your .env file to enable "
            "AI-powered recommendations."
        )

    subject_summary = []

    for subject in subjects:
        subject_summary.append({
            "subject": subject["name"],
            "exam_date": subject["exam_date"],
            "difficulty": subject["difficulty"],
            "topics": subject["topics"]
        })

    schedule_summary = {}

    for day, blocks in schedule.items():
        schedule_summary[day] = [
            {
                "activity": block["activity"],
                "category": block["category"],
                "subject": block.get("subject"),
                "topic": block.get("topic"),
                "duration": block["duration"]
            }
            for block in blocks
            if block["category"] in {
                "Learning",
                "Revision",
                "Practice",
                "Mock Test"
            }
        ]

    prompt = f"""
You are an academic exam preparation assistant.

Analyze the following student information.

SUBJECTS:
{subject_summary}

TOPIC PROGRESS:
{progress}

WEAK TOPICS:
{weak_topics}

STUDY SCHEDULE:
{schedule_summary}

Give the student:
1. Three important preparation recommendations.
2. Which topics should be prioritized.
3. How to improve weak topics.
4. A practical revision strategy.
5. Advice for the upcoming examinations.

Be specific, concise and realistic.
Do not invent quiz scores or claim that the schedule has been changed.
"""

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model}:generateContent"
    )

    try:
        response = requests.post(
            url,
            params={"key": api_key},
            json={
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 1200
                }
            },
            timeout=45
        )

        response.raise_for_status()
        data = response.json()

        return (
            data["candidates"][0]["content"]["parts"][0]["text"]
        )

    except requests.exceptions.Timeout:
        return "Gemini request timed out. Please try again."

    except requests.exceptions.RequestException as error:
        return f"Gemini API request failed: {error}"

    except (KeyError, IndexError, TypeError):
        return "Gemini returned an unexpected response. Please try again."