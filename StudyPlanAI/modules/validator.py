from .scheduler import validate_blocks


STUDY_CATEGORIES = {
    "Learning",
    "Revision",
    "Practice",
    "Mock Test"
}


def validate_schedule(schedule, subjects, daily_study_hours):
    """
    Validate a generated schedule.

    Checks overlaps, invalid durations, subject names and
    the maximum daily study-time limit.
    """

    errors = []
    valid_subjects = {subject["name"] for subject in subjects}

    for day, blocks in schedule.items():
        errors.extend(
            f"{day}: {error}"
            for error in validate_blocks(blocks)
        )

        total_study_minutes = 0

        for block in blocks:
            if block["category"] in STUDY_CATEGORIES:
                total_study_minutes += block["duration"]

            subject = block.get("subject")

            if subject and subject not in valid_subjects:
                errors.append(
                    f"{day}: Unknown subject '{subject}'."
                )

        maximum = daily_study_hours * 60

        if total_study_minutes > maximum:
            errors.append(
                f"{day}: Study time exceeds the daily limit "
                f"({total_study_minutes} > {maximum} minutes)."
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }