
from datetime import date, datetime, timedelta


def to_minutes(time_text):
    parsed = datetime.strptime(time_text, "%H:%M")
    return parsed.hour * 60 + parsed.minute


def from_minutes(minutes):
    minutes %= 1440
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def make_block(start, end, activity, category, subject=None, topic=None):
    return {
        "start": int(start),
        "end": int(end),
        "start_time": from_minutes(start),
        "end_time": from_minutes(end),
        "activity": activity,
        "category": category,
        "subject": subject,
        "topic": topic,
        "duration": int(end - start)
    }


def create_routine(
    wake_time="06:00",
    sleep_time="23:00",
    college_day=False,
    college_start="09:00",
    college_end="16:00",
    breakfast_time="08:00",
    lunch_time="13:00",
    dinner_time="20:00"
):
    wake = to_minutes(wake_time)
    sleep = to_minutes(sleep_time)

    if wake >= sleep:
        raise ValueError(
            "Bedtime must be later than wake-up time."
        )

    blocks = []

    # Sleep outside the active planning period.
    blocks.append(
        make_block(0, wake, "Sleep", "Sleep")
    )
    blocks.append(
        make_block(sleep, 1440, "Sleep", "Sleep")
    )

    meals = [
        (breakfast_time, 45, "Breakfast"),
        (lunch_time, 60, "Lunch"),
        (dinner_time, 60, "Dinner")
    ]

    college_busy = None
    if college_day:
        college_start_absolute = to_minutes(college_start)
        college_end_absolute = to_minutes(college_end)

        if college_start_absolute >= college_end_absolute:
            raise ValueError("Invalid college timings.")

        college_busy = (
            max(0, college_start_absolute - 30),
            min(1440, college_end_absolute + 30)
        )

    for clock, duration, name in meals:
        start = to_minutes(clock)
        end = start + duration

        if end > 1440:
            raise ValueError(f"{name} crosses the planning-day boundary.")

        if college_busy and start < college_busy[1] and end > college_busy[0]:
            continue

        blocks.append(
            make_block(start, end, name, "Meal")
        )

    if college_day:
        blocks.append(
            make_block(
                college_busy[0],
                college_busy[1],
                "College and commute",
                "College"
            )
        )

    blocks.sort(key=lambda block: block["start"])

    return blocks


def validate_blocks(blocks):
    errors = []
    ordered = sorted(blocks, key=lambda item: item["start"])

    for block in ordered:
        if block["start"] < 0 or block["end"] > 1440:
            errors.append("Block is outside the planning day.")

        if block["end"] <= block["start"]:
            errors.append("Invalid block duration.")

    for previous, current in zip(ordered, ordered[1:]):
        if current["start"] < previous["end"]:
            errors.append(
                f"Overlap between {previous['activity']} "
                f"and {current['activity']}."
            )

    return errors


def calculate_free_slots(blocks):
    ordered = sorted(blocks, key=lambda item: item["start"])

    free_slots = []
    cursor = 0

    for block in ordered:
        if block["start"] > cursor:
            free_slots.append((cursor, block["start"]))

        cursor = max(cursor, block["end"])

    if cursor < 1440:
        free_slots.append((cursor, 1440))

    return free_slots


def make_tasks(priorities):
    tasks = []

    for subject in priorities:
        for topic in subject["topics"]:
            tasks.append({
                "subject": subject["name"],
                "topic": topic,
                "exam_date": subject["exam_date"],
                "priority": subject["priority"],
                "duration": 50
            })

    return sorted(
        tasks,
        key=lambda task: (
            task["exam_date"],
            -task["priority"]
        )
    )


def generate_exam_plan(
    subjects,
    planning_date,
    wake_time="06:00",
    sleep_time="23:00",
    breakfast_time="08:00",
    lunch_time="13:00",
    dinner_time="20:00",
    college_weekdays=None,
    college_start="09:00",
    college_end="16:00",
    daily_study_hours=5,
    revision_days=2
):
    if college_weekdays is None:
        college_weekdays = [0, 1, 2, 3, 4]

    if isinstance(planning_date, str):
        planning_date = date.fromisoformat(planning_date)

    if not subjects:
        raise ValueError("No subjects provided.")

    if not 1 <= daily_study_hours <= 16:
        raise ValueError("Daily study hours must be between 1 and 16.")

    if revision_days < 0:
        raise ValueError("Revision days cannot be negative.")

    last_exam = max(
        date.fromisoformat(subject["exam_date"])
        for subject in subjects
    )

    priorities = sorted(
        subjects,
        key=lambda subject: (
            subject["exam_date"],
            -subject.get("priority", 0)
        )
    )

    tasks = make_tasks(priorities)
    unscheduled_tasks = []
    schedule = {}

    current_date = planning_date

    while current_date <= last_exam:
        day_key = current_date.isoformat()

        is_college_day = (
            current_date.weekday() in college_weekdays
        )

        fixed_blocks = create_routine(
            wake_time=wake_time,
            sleep_time=sleep_time,
            college_day=is_college_day,
            college_start=college_start,
            college_end=college_end,
            breakfast_time=breakfast_time,
            lunch_time=lunch_time,
            dinner_time=dinner_time
        )

        errors = validate_blocks(fixed_blocks)

        if errors:
            raise ValueError(
                f"Invalid routine on {day_key}: {'; '.join(errors)}"
            )

        day_blocks = fixed_blocks.copy()
        study_minutes = 0
        maximum_minutes = daily_study_hours * 60

        free_slots = calculate_free_slots(day_blocks)

        for slot_start, slot_end in free_slots:
            cursor = slot_start

            while cursor + 50 <= slot_end and tasks:
                task = tasks[0]
                exam_date = date.fromisoformat(task["exam_date"])

                if current_date >= exam_date:
                    unscheduled_tasks.append(tasks.pop(0))
                    continue

                days_until_exam = (exam_date - current_date).days

                if days_until_exam <= revision_days:
                    unscheduled_tasks.append(tasks.pop(0))
                    continue

                if study_minutes + 50 > maximum_minutes:
                    break

                day_blocks.append(
                    make_block(
                        cursor,
                        cursor + 50,
                        f"Study: {task['topic']}",
                        "Learning",
                        task["subject"],
                        task["topic"]
                    )
                )

                cursor += 50
                study_minutes += 50
                tasks.pop(0)

            if study_minutes >= maximum_minutes:
                break

        # Add revision sessions for subjects with upcoming exams.
        for subject in priorities:
            exam_date = date.fromisoformat(subject["exam_date"])
            days_left = (exam_date - current_date).days

            if 0 <= days_left <= revision_days:
                if study_minutes + 40 > maximum_minutes:
                    continue

                for start, end in calculate_free_slots(day_blocks):
                    if end - start >= 40:
                        day_blocks.append(
                            make_block(
                                start,
                                start + 40,
                                f"Revision: {subject['name']}",
                                "Revision",
                                subject["name"]
                            )
                        )

                        study_minutes += 40
                        break

        day_blocks.sort(key=lambda block: block["start"])
        schedule[day_key] = day_blocks

        current_date += timedelta(days=1)

    unscheduled_tasks.extend(tasks)

    return schedule, unscheduled_tasks
