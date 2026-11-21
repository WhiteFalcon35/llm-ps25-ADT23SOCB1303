import pandas as pd


def schedule_to_dataframe(schedule):
    """Convert the complete schedule into a pandas DataFrame."""

    rows = []

    for day, blocks in sorted(schedule.items()):
        for block in sorted(
            blocks,
            key=lambda item: item["start"]
        ):
            rows.append({
                "Date": day,
                "Start": block.get("start_time", ""),
                "End": block.get("end_time", ""),
                "Duration (minutes)": block.get("duration", 0),
                "Activity": block.get("activity", ""),
                "Category": block.get("category", ""),
                "Subject": block.get("subject") or "",
                "Topic": block.get("topic") or ""
            })

    return pd.DataFrame(rows)


def export_schedule_csv(schedule):
    """Return the schedule as CSV bytes."""

    dataframe = schedule_to_dataframe(schedule)

    return dataframe.to_csv(index=False).encode("utf-8")