def calculate_readiness(subjects, progress):
    """
    Estimate exam readiness using syllabus completion and quiz scores.

    This is a project-defined indicator, not a guaranteed prediction
    of actual exam performance.
    """

    total_topics = sum(
        len(subject.get("topics", []))
        for subject in subjects
    )

    if total_topics == 0:
        return {
            "readiness": 0,
            "completion": 0,
            "average_quiz_score": None
        }

    progress_lookup = {
        (item["subject"], item["topic"]): item
        for item in progress
    }

    completed = 0
    quiz_scores = []

    for subject in subjects:
        for topic in subject.get("topics", []):
            item = progress_lookup.get(
                (subject["name"], topic)
            )

            if item:
                if item["status"] == "Completed":
                    completed += 1

                if item["quiz_score"] is not None:
                    quiz_scores.append(float(item["quiz_score"]))

    completion = (completed / total_topics) * 100

    if quiz_scores:
        average_score = sum(quiz_scores) / len(quiz_scores)
        readiness = 0.60 * completion + 0.40 * average_score
    else:
        average_score = None
        readiness = completion

    return {
        "readiness": round(readiness, 1),
        "completion": round(completion, 1),
        "average_quiz_score": (
            round(average_score, 1)
            if average_score is not None
            else None
        )
    }


def find_weak_topics(progress, threshold=50):
    """Return topics with quiz scores below the threshold."""

    weak_topics = []

    for item in progress:
        score = item.get("quiz_score")

        if score is not None and float(score) < threshold:
            weak_topics.append({
                "subject": item["subject"],
                "topic": item["topic"],
                "quiz_score": float(score),
                "status": item["status"]
            })

    return sorted(
        weak_topics,
        key=lambda item: item["quiz_score"]
    )


def subject_completion(subjects, progress):
    """Calculate completion percentage for every subject."""

    lookup = {
        (item["subject"], item["topic"]): item
        for item in progress
    }

    result = []

    for subject in subjects:
        topics = subject.get("topics", [])
        total = len(topics)

        completed = sum(
            1
            for topic in topics
            if (
                (item := lookup.get((subject["name"], topic)))
                and item["status"] == "Completed"
            )
        )

        percentage = (
            (completed / total) * 100
            if total else 0
        )

        result.append({
            "subject": subject["name"],
            "completed": completed,
            "total": total,
            "completion": round(percentage, 1)
        })

    return result