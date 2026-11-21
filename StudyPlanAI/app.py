
import streamlit as st
import pandas as pd
import plotly.express as px

from datetime import date, time, datetime, timedelta

from modules.planner import (
    parse_subjects,
    calculate_priorities
)

from modules.scheduler import generate_exam_plan

from modules.validator import validate_schedule

from modules.database import (
    initialize_database,
    save_plan,
    load_latest_plan,
    update_topic,
    get_topic_progress
)

from modules.analytics import (
    calculate_readiness,
    find_weak_topics,
    subject_completion
)

from modules.exporter import (
    schedule_to_dataframe,
    export_schedule_csv
)

from modules.ai_assistant import get_study_recommendations


# ============================================================
# 1. APPLICATION CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="StudyPilot AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

initialize_database()


# ============================================================
# 2. SESSION STATE
# ============================================================

if "schedule" not in st.session_state:
    st.session_state.schedule = {}

if "subjects" not in st.session_state:
    st.session_state.subjects = []

if "settings" not in st.session_state:
    st.session_state.settings = {}

if "priorities" not in st.session_state:
    st.session_state.priorities = []

if "plan_loaded" not in st.session_state:
    st.session_state.plan_loaded = False


# ============================================================
# 3. LOAD SAVED PLAN
# ============================================================

def load_saved_plan():
    """Load the latest saved study plan from SQLite."""

    saved = load_latest_plan()

    if not saved:
        return False

    st.session_state.schedule = saved["schedule"]
    st.session_state.subjects = saved["subjects"]
    st.session_state.settings = saved.get("settings", {})

    planning_date_text = st.session_state.settings.get(
        "planning_date",
        date.today().isoformat()
    )

    planning_date = date.fromisoformat(planning_date_text)

    st.session_state.priorities = calculate_priorities(
        st.session_state.subjects,
        planning_date
    )

    st.session_state.plan_loaded = True

    return True


if not st.session_state.plan_loaded:
    saved_plan = load_latest_plan()

    if saved_plan:
        st.session_state.schedule = saved_plan["schedule"]
        st.session_state.subjects = saved_plan["subjects"]
        st.session_state.settings = saved_plan.get("settings", {})

        saved_planning_date = st.session_state.settings.get(
            "planning_date",
            date.today().isoformat()
        )

        st.session_state.priorities = calculate_priorities(
            st.session_state.subjects,
            date.fromisoformat(saved_planning_date)
        )

        st.session_state.plan_loaded = True


# ============================================================
# 4. HELPER FUNCTIONS
# ============================================================

def format_clock(value):
    """Convert a time object to HH:MM."""

    return value.strftime("%H:%M")


def format_session_time(offset, wake_time, planning_date):
    """
    Convert a minute offset from wake-up into a readable time.

    Offsets beyond 1440 represent the following day.
    """

    wake = datetime.strptime(
        wake_time,
        "%H:%M"
    ).time()

    start = datetime.combine(
        planning_date,
        wake
    )

    result = start + timedelta(
        minutes=int(offset)
    )

    return result.strftime("%d %b, %I:%M %p")


def make_dataframe(day_schedule, wake_time, planning_date):
    """Convert one day's timetable into a DataFrame."""

    rows = []

    for block in sorted(
        day_schedule,
        key=lambda item: item["start"]
    ):
        rows.append({
            "Start": format_session_time(
                block["start"],
                wake_time,
                planning_date
            ),
            "End": format_session_time(
                block["end"],
                wake_time,
                planning_date
            ),
            "Activity": block["activity"],
            "Category": block["category"],
            "Subject": block.get("subject") or "-",
            "Topic": block.get("topic") or "-",
            "Duration (minutes)": block["duration"]
        })

    return pd.DataFrame(rows)


def get_all_study_sessions(schedule):
    """Collect all academic study sessions."""

    academic_categories = {
        "Learning",
        "Revision",
        "Practice",
        "Mock Test"
    }

    sessions = []

    for day, blocks in schedule.items():
        for block in blocks:
            if block["category"] in academic_categories:
                sessions.append({
                    **block,
                    "date": day
                })

    return sessions


def get_planning_date():
    """Return the saved planning date."""

    value = st.session_state.settings.get(
        "planning_date",
        date.today().isoformat()
    )

    return date.fromisoformat(value)


# ============================================================
# 5. CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    @import url(
        'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap'
    );

    .stApp {
        background:
            radial-gradient(
                circle at 80% 0%,
                rgba(95, 75, 220, 0.18),
                transparent 30%
            ),
            #0b1020;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    h1, h2, h3 {
        font-family: 'Space Grotesk', sans-serif;
    }

    [data-testid="stSidebar"] {
        background: #111a30;
        border-right: 1px solid rgba(255,255,255,0.08);
    }

    .block-container {
        max-width: 1500px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    div[data-testid="stMetric"] {
        background: #141e34;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 15px;
        padding: 18px;
    }

    .hero {
        background: linear-gradient(
            110deg,
            rgba(101,82,230,0.28),
            rgba(27,158,205,0.12)
        );
        border: 1px solid rgba(139,130,255,0.25);
        border-radius: 20px;
        padding: 30px;
        margin-bottom: 25px;
    }

    .hero h1 {
        color: white;
        font-size: 34px;
    }

    .hero p {
        color: #dbeafe;
        font-size: 17px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 6. SIDEBAR NAVIGATION
# ============================================================

with st.sidebar:

    st.markdown("## 🎓 StudyPilot AI")

    st.caption(
        "Intelligent Exam Preparation Planner"
    )

    st.divider()

    page = st.radio(
        "WORKSPACE",
        [
            "Dashboard",
            "Create Study Plan",
            "My Timetable",
            "Syllabus Tracker",
            "Analytics",
            "AI Study Assistant"
        ]
    )

    st.divider()

    if st.button(
        "Load Latest Saved Plan",
        use_container_width=True
    ):
        if load_saved_plan():
            st.success("Saved plan loaded.")
            st.rerun()
        else:
            st.warning("No saved plan found.")

    st.divider()

    st.caption(
        "Prepare smarter. Revise better. Perform confidently."
    )


# ============================================================
# 7. COMMON DATA
# ============================================================

schedule = st.session_state.schedule
subjects = st.session_state.subjects
settings = st.session_state.settings

progress = get_topic_progress()
weak_topics = find_weak_topics(progress)


# ============================================================
# 8. HERO SECTION
# ============================================================

st.markdown(
    """
    <div class="hero">
        <h1>Prepare smarter. Score better.</h1>
        <p>
            Your personal AI-powered examination preparation
            and syllabus management platform.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 9. DASHBOARD
# ============================================================

if page == "Dashboard":

    st.subheader("Your exam preparation overview")

    if not schedule or not subjects:

        st.info(
            "You haven't generated a study plan yet. "
            "Open Create Study Plan to begin."
        )

    else:

        readiness_data = calculate_readiness(
            subjects,
            progress
        )

        readiness = readiness_data["readiness"]

        total_topics = sum(
            len(subject["topics"])
            for subject in subjects
        )

        completion_data = subject_completion(
            subjects,
            progress
        )

        completed_topics = sum(
            item["completed"]
            for item in completion_data
        )

        upcoming_exams = sorted(
            subjects,
            key=lambda item: item["exam_date"]
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Subjects",
            len(subjects)
        )

        c2.metric(
            "Total syllabus topics",
            total_topics
        )

        c3.metric(
            "Completed topics",
            f"{completed_topics}/{total_topics}"
        )

        c4.metric(
            "Exam readiness",
            f"{readiness}%"
        )

        st.progress(readiness / 100)

        left, right = st.columns([1.3, 1])

        with left:

            st.markdown("### Upcoming examinations")

            exam_rows = []

            for subject in upcoming_exams:

                exam_date = date.fromisoformat(
                    subject["exam_date"]
                )

                exam_rows.append({
                    "Subject": subject["name"],
                    "Exam date": subject["exam_date"],
                    "Difficulty": subject["difficulty"].title(),
                    "Days remaining": (
                        exam_date - date.today()
                    ).days
                })

            exam_df = pd.DataFrame(exam_rows)

            st.dataframe(
                exam_df,
                use_container_width=True,
                hide_index=True
            )

        with right:

            st.markdown("### Weak topics")

            if weak_topics:

                for item in weak_topics:

                    st.warning(
                        f"{item['subject']} — "
                        f"{item['topic']} "
                        f"({item['quiz_score']}%)"
                    )

            else:

                st.success(
                    "No weak topics detected from recorded quiz scores."
                )

        st.markdown("### Your preparation workload")

        academic_categories = {
            "Learning",
            "Revision",
            "Practice",
            "Mock Test"
        }

        workload_rows = []

        for day, blocks in schedule.items():

            count = sum(
                1
                for block in blocks
                if block["category"] in academic_categories
            )

            workload_rows.append({
                "Date": day,
                "Study sessions": count
            })

        workload = pd.DataFrame(workload_rows)

        fig = px.bar(
            workload,
            x="Date",
            y="Study sessions",
            title="Planned academic sessions"
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ============================================================
# 10. CREATE STUDY PLAN
# ============================================================

elif page == "Create Study Plan":

    st.subheader("Create your personalized exam timetable")

    st.write(
        "Enter your examination details and weekly routine. "
        "StudyPilot will distribute your syllabus across "
        "the preparation period."
    )

    default_subject_text = """High Performance Computing | 2026-12-05 | hard | Parallel architectures, Amdahl's Law, OpenMP, MPI
Data Analytics | 2026-12-07 | medium | Data preprocessing, NumPy, Pandas, Visualization
Advanced Database | 2026-12-09 | hard | Transactions, Normalization, Indexing, Query optimization"""

    with st.form("study_plan_form"):

        st.markdown("### 1. Examination details")

        planning_date = st.date_input(
            "Preparation start date",
            value=date.today()
        )

        subject_text = st.text_area(
            "Subjects and syllabus",
            height=180,
            value=default_subject_text
        )

        st.caption(
            "Format: Subject | YYYY-MM-DD | difficulty | topic1, topic2"
        )

        st.divider()

        st.markdown("### 2. Your daily routine")

        col1, col2 = st.columns(2)

        with col1:

            wake_time = st.time_input(
                "Wake-up time",
                value=time(6, 30)
            )

            sleep_time = st.time_input(
                "Sleep time",
                value=time(23, 0)
            )

            breakfast_time = st.time_input(
                "Breakfast time",
                value=time(8, 0)
            )

        with col2:

            lunch_time = st.time_input(
                "Lunch time",
                value=time(13, 0)
            )

            dinner_time = st.time_input(
                "Dinner time",
                value=time(20, 0)
            )

            daily_study_hours = st.slider(
                "Maximum focused study hours per day",
                min_value=1,
                max_value=12,
                value=5
            )

        st.divider()

        st.markdown("### 3. College and weekly routine")

        college_weekdays = st.multiselect(
            "Select your college days",
            [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday"
            ],
            default=[
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday"
            ]
        )

        col1, col2 = st.columns(2)

        with col1:

            college_start = st.time_input(
                "College start",
                value=time(9, 0)
            )

        with col2:

            college_end = st.time_input(
                "College end",
                value=time(16, 0)
            )

        st.divider()

        st.markdown("### 4. Revision strategy")

        revision_days = st.slider(
            "Days reserved for revision before each exam",
            min_value=0,
            max_value=7,
            value=2
        )

        submit = st.form_submit_button(
            "✨ Generate my exam preparation plan",
            type="primary",
            use_container_width=True
        )

    if submit:

        try:

            if planning_date < date.today():
                raise ValueError(
                    "Preparation start date cannot be in the past."
                )

            if sleep_time <= wake_time:
                raise ValueError(
                    "For this version, bedtime must be later "
                    "than wake-up time on the same day."
                )

            if college_weekdays and college_end <= college_start:
                raise ValueError(
                    "College end time must be after college start."
                )

            parsed_subjects = parse_subjects(
                subject_text,
                planning_date
            )

            priorities = calculate_priorities(
                parsed_subjects,
                planning_date
            )

            weekday_numbers = {
                "Monday": 0,
                "Tuesday": 1,
                "Wednesday": 2,
                "Thursday": 3,
                "Friday": 4,
                "Saturday": 5,
                "Sunday": 6
            }

            selected_weekdays = [
                weekday_numbers[day]
                for day in college_weekdays
            ]

            with st.spinner(
                "StudyPilot is building your multi-day timetable..."
            ):

                new_schedule, remaining_tasks = generate_exam_plan(
                    subjects=priorities,
                    planning_date=planning_date,
                    college_weekdays=selected_weekdays,
                    wake_time=format_clock(wake_time),
                    sleep_time=format_clock(sleep_time),
                    college_start=format_clock(college_start),
                    college_end=format_clock(college_end),
                    breakfast_time=format_clock(breakfast_time),
                    lunch_time=format_clock(lunch_time),
                    dinner_time=format_clock(dinner_time),
                    daily_study_hours=daily_study_hours,
                    revision_days=revision_days
                )

            validation = validate_schedule(
                new_schedule,
                parsed_subjects,
                daily_study_hours
            )

            if not validation["valid"]:

                st.error(
                    "The generated timetable did not pass validation."
                )

                for error in validation["errors"]:
                    st.write(f"• {error}")

            else:

                new_settings = {
                    "planning_date": planning_date.isoformat(),
                    "wake_time": format_clock(wake_time),
                    "sleep_time": format_clock(sleep_time),
                    "breakfast_time": format_clock(breakfast_time),
                    "lunch_time": format_clock(lunch_time),
                    "dinner_time": format_clock(dinner_time),
                    "daily_study_hours": daily_study_hours,
                    "college_weekdays": selected_weekdays,
                    "college_start": format_clock(college_start),
                    "college_end": format_clock(college_end),
                    "revision_days": revision_days
                }

                st.session_state.schedule = new_schedule
                st.session_state.subjects = parsed_subjects
                st.session_state.priorities = priorities
                st.session_state.settings = new_settings
                st.session_state.plan_loaded = True

                save_plan(
                    new_schedule,
                    parsed_subjects,
                    new_settings
                )

                st.success(
                    "Your exam preparation timetable is ready!"
                )

                st.metric(
                    "Scheduled days",
                    len(new_schedule)
                )

                if remaining_tasks:

                    st.warning(
                        f"{len(remaining_tasks)} learning topic(s) "
                        "could not be scheduled. Consider increasing "
                        "daily study hours or starting earlier."
                    )

                    st.dataframe(
                        pd.DataFrame(remaining_tasks),
                        use_container_width=True,
                        hide_index=True
                    )

                st.balloons()

                st.info(
                    "Open My Timetable to view your complete plan."
                )

        except Exception as error:

            st.error(str(error))


# ============================================================
# 11. MY TIMETABLE
# ============================================================

elif page == "My Timetable":

    st.subheader("Your complete exam preparation timetable")

    if not schedule:

        st.info("Generate your study plan first.")

    else:

        dates = sorted(schedule.keys())

        selected_date = st.selectbox(
            "Select preparation date",
            dates
        )

        day_schedule = schedule[selected_date]

        wake_time = settings.get(
            "wake_time",
            "06:30"
        )

        selected_day = date.fromisoformat(
            selected_date
        )

        df = make_dataframe(
            day_schedule,
            wake_time,
            selected_day
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### Visual daily timeline")

        timeline_rows = []

        day_start = datetime.combine(
            selected_day,
            datetime.strptime(
                wake_time,
                "%H:%M"
            ).time()
        )

        for block in day_schedule:

            timeline_rows.append({
                "Activity": block["activity"],
                "Category": block["category"],
                "Start": day_start + timedelta(
                    minutes=block["start"]
                ),
                "End": day_start + timedelta(
                    minutes=block["end"]
                )
            })

        timeline = pd.DataFrame(timeline_rows)

        fig = px.timeline(
            timeline,
            x_start="Start",
            x_end="End",
            y="Category",
            color="Category",
            hover_name="Activity",
            title="Your preparation-day timeline"
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.download_button(
            "⬇ Download this day's timetable",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"studypilot_{selected_date}.csv",
            mime="text/csv"
        )

        st.divider()

        st.markdown("### Download complete exam timetable")

        all_df = schedule_to_dataframe(schedule)

        st.download_button(
            "⬇ Download complete exam timetable",
            data=export_schedule_csv(schedule),
            file_name="studypilot_complete_exam_plan.csv",
            mime="text/csv",
            type="primary"
        )


# ============================================================
# 12. SYLLABUS TRACKER
# ============================================================

elif page == "Syllabus Tracker":

    st.subheader("Track your syllabus completion")

    if not subjects:

        st.info("Generate a study plan first.")

    else:

        for subject in subjects:

            st.markdown(
                f"### {subject['name']}"
            )

            for topic in subject["topics"]:

                existing = next(
                    (
                        item
                        for item in progress
                        if item["subject"] == subject["name"]
                        and item["topic"] == topic
                    ),
                    None
                )

                default_status = (
                    existing["status"]
                    if existing
                    else "Pending"
                )

                default_score = (
                    float(existing["quiz_score"])
                    if existing
                    and existing["quiz_score"] is not None
                    else 0.0
                )

                col1, col2, col3 = st.columns([3, 2, 2])

                with col1:

                    st.write(topic)

                with col2:

                    status_options = [
                        "Pending",
                        "In Progress",
                        "Completed",
                        "Needs Revision"
                    ]

                    status = st.selectbox(
                        "Status",
                        status_options,
                        index=status_options.index(default_status),
                        key=f"status_{subject['name']}_{topic}"
                    )

                with col3:

                    score = st.number_input(
                        "Quiz score (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=default_score,
                        step=1.0,
                        key=f"score_{subject['name']}_{topic}"
                    )

                if st.button(
                    "Save topic",
                    key=f"save_{subject['name']}_{topic}"
                ):

                    update_topic(
                        subject["name"],
                        topic,
                        status,
                        score
                    )

                    st.success(
                        f"Saved: {topic}"
                    )

            st.divider()


# ============================================================
# 13. ANALYTICS
# ============================================================

elif page == "Analytics":

    st.subheader("Exam preparation analytics")

    if not schedule:

        st.info("Generate a study plan first.")

    else:

        readiness_data = calculate_readiness(
            subjects,
            progress
        )

        readiness = readiness_data["readiness"]

        st.metric(
            "Exam readiness estimate",
            f"{readiness}%"
        )

        st.progress(readiness / 100)

        st.caption(
            "This is a project-defined estimate based on syllabus "
            "completion and quiz scores, not a guaranteed exam result."
        )

        completion = subject_completion(
            subjects,
            progress
        )

        total_topics = sum(
            item["total"]
            for item in completion
        )

        completed = sum(
            item["completed"]
            for item in completion
        )

        pending = max(
            total_topics - completed,
            0
        )

        left, right = st.columns(2)

        with left:

            fig = px.pie(
                names=["Completed", "Remaining"],
                values=[completed, pending],
                hole=0.55,
                title="Syllabus completion"
            )

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        with right:

            if weak_topics:

                weak_df = pd.DataFrame(weak_topics)

                fig = px.bar(
                    weak_df,
                    x="topic",
                    y="quiz_score",
                    color="subject",
                    title="Topics needing attention",
                    labels={
                        "topic": "Topic",
                        "quiz_score": "Quiz score (%)"
                    }
                )

                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            else:

                st.success(
                    "No weak topics detected yet. "
                    "Record quiz scores to identify them."
                )

        st.markdown("### Subject-wise completion")

        completion_df = pd.DataFrame(completion)

        st.dataframe(
            completion_df,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### Subject priorities")

        planning_date = get_planning_date()

        priorities = calculate_priorities(
            subjects,
            planning_date
        )

        priority_df = pd.DataFrame([
            {
                "Subject": item["name"],
                "Priority score": item["priority"],
                "Difficulty": item["difficulty"],
                "Days left": item["days_left"]
            }
            for item in priorities
        ])

        st.dataframe(
            priority_df,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# 14. AI STUDY ASSISTANT
# ============================================================

elif page == "AI Study Assistant":

    st.subheader("Your AI examination preparation assistant")

    st.write(
        "Get recommendations based on your subjects, "
        "syllabus progress, quiz scores and timetable."
    )

    if not subjects or not schedule:

        st.info(
            "Generate your exam preparation plan first."
        )

    else:

        st.markdown("### Your preparation summary")

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Subjects",
            len(subjects)
        )

        c2.metric(
            "Scheduled days",
            len(schedule)
        )

        c3.metric(
            "Weak topics",
            len(weak_topics)
        )

        if st.button(
            "✨ Analyze my preparation",
            type="primary",
            use_container_width=True
        ):

            with st.spinner(
                "Gemini is analyzing your preparation..."
            ):

                advice = get_study_recommendations(
                    subjects,
                    progress,
                    weak_topics,
                    schedule
                )

            st.markdown("### Your AI study recommendations")

            st.markdown(advice)

        st.caption(
            "AI recommendations are advisory. The current scheduler "
            "does not automatically modify your timetable based "
            "on AI recommendations or quiz scores."
        )


# ============================================================
# 15. FOOTER
# ============================================================

st.divider()

st.caption(
    "StudyPilot AI · Intelligent Exam Preparation Planner · "
    "GenAI Mini Project · Roll No. 25"
)
