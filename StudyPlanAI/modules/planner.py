from datetime import date, datetime


DIFFICULTY_SCORE = {
    "easy": 3,
    "medium": 6,
    "hard": 10
}


def parse_subjects(raw_text, planning_date=None):
    """
    Parse subject information from multiline text.

    Format:
    Subject | YYYY-MM-DD | difficulty | Topic 1, Topic 2
    """

    if planning_date is None:
        planning_date = date.today()

    if isinstance(planning_date, datetime):
        planning_date = planning_date.date()

    subjects = []
    seen_names = set()

    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        line = line.strip()

        if not line:
            continue

        parts = [part.strip() for part in line.split("|")]

        if len(parts) != 4:
            raise ValueError(
                f"Line {line_number}: Use the format "
                "'Subject | YYYY-MM-DD | difficulty | topics'."
            )

        name, exam_date_text, difficulty, topics_text = parts

        if not name:
            raise ValueError(f"Line {line_number}: Subject name is missing.")

        normalized_name = name.casefold()

        if normalized_name in seen_names:
            raise ValueError(f"Duplicate subject: {name}")

        seen_names.add(normalized_name)

        try:
            exam_date = datetime.strptime(
                exam_date_text, "%Y-%m-%d"
            ).date()
        except ValueError:
            raise ValueError(
                f"Line {line_number}: Exam date must be YYYY-MM-DD."
            )

        if exam_date < planning_date:
            raise ValueError(
                f"Line {line_number}: Exam date for {name} "
                "cannot be before the planning date."
            )

        difficulty = difficulty.lower()

        if difficulty not in DIFFICULTY_SCORE:
            raise ValueError(
                f"Line {line_number}: Difficulty must be easy, medium or hard."
            )

        topics = [
            topic.strip()
            for topic in topics_text.split(",")
            if topic.strip()
        ]

        if not topics:
            raise ValueError(f"Line {line_number}: Add at least one topic.")

        if len({topic.casefold() for topic in topics}) != len(topics):
            raise ValueError(
                f"Line {line_number}: Duplicate topics found in {name}."
            )

        subjects.append({
            "name": name,
            "exam_date": exam_date.isoformat(),
            "difficulty": difficulty,
            "topics": topics
        })

    if not subjects:
        raise ValueError("Please enter at least one subject.")

    return subjects


def calculate_priorities(subjects, planning_date=None):
    """
    Calculate a simple priority score for each subject.

    Higher difficulty, larger syllabus and closer exam dates
    increase priority.
    """

    if planning_date is None:
        planning_date = date.today()

    if isinstance(planning_date, datetime):
        planning_date = planning_date.date()

    result = []

    for subject in subjects:
        exam_date = date.fromisoformat(subject["exam_date"])
        days_left = (exam_date - planning_date).days

        difficulty = DIFFICULTY_SCORE[subject["difficulty"]] / 10
        workload = min(len(subject["topics"]) / 10, 1)
        urgency = max(0, min(1, 1 - days_left / 30))

        priority = 10 * (
            0.40 * difficulty
            + 0.30 * workload
            + 0.30 * urgency
        )

        item = subject.copy()
        item["days_left"] = days_left
        item["priority"] = round(priority, 2)

        result.append(item)

    return sorted(
        result,
        key=lambda item: (
            item["days_left"],
            -item["priority"]
        )
    )