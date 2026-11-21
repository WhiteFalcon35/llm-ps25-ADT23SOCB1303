# StudyPilot AI – Study Plan Generator

**Assigned problem:** Roll No. 25 – Study Plan Generator  
**Domain:** Education and Learning

## 1. Project overview
StudyPilot AI generates a day-wise study timetable using a student's subjects, syllabus topics, exam dates, topic difficulty and available study hours.

## 2. Features
- Subject and syllabus input
- Exam date and available-hours input
- Python-based subject priority score
- Gemini API timetable generation
- Rule-based fallback when Gemini is unavailable
- Validation of dates, topic coverage, daily hours and overlapping sessions
- CSV timetable export through Streamlit

## 3. Project structure
```text
StudyPilot-AI/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── data/
│   └── sample_subjects.txt
├── modules/
│   ├── __init__.py
│   ├── planner.py
│   ├── validator.py
│   └── exporter.py
└── tests/
    └── test_planner.py