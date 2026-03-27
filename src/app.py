"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import sqlite3

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# Default activity data used to seed the database on first run
default_activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    },
    "GitHub Skills": {
        "description": "Learn practical coding and collaboration using GitHub",
        "schedule": "Thursdays, 4:30 PM - 5:30 PM",
        "max_participants": 25,
        "participants": []
    }
}

db_path = current_dir / "activities.db"


def get_db_connection():
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with get_db_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS activities (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS registrations (
                activity_name TEXT NOT NULL,
                email TEXT NOT NULL,
                PRIMARY KEY (activity_name, email),
                FOREIGN KEY (activity_name) REFERENCES activities(name) ON DELETE CASCADE
            );
            """
        )

        existing_count = connection.execute(
            "SELECT COUNT(*) AS count FROM activities"
        ).fetchone()["count"]

        if existing_count == 0:
            for name, details in default_activities.items():
                connection.execute(
                    """
                    INSERT INTO activities (name, description, schedule, max_participants)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        name,
                        details["description"],
                        details["schedule"],
                        details["max_participants"],
                    ),
                )

                for email in details["participants"]:
                    connection.execute(
                        """
                        INSERT INTO registrations (activity_name, email)
                        VALUES (?, ?)
                        """,
                        (name, email),
                    )

        connection.commit()


def load_activities():
    activities = {}

    with get_db_connection() as connection:
        activity_rows = connection.execute(
            """
            SELECT name, description, schedule, max_participants
            FROM activities
            ORDER BY rowid
            """
        ).fetchall()

        for row in activity_rows:
            participant_rows = connection.execute(
                """
                SELECT email
                FROM registrations
                WHERE activity_name = ?
                ORDER BY rowid
                """,
                (row["name"],),
            ).fetchall()

            activities[row["name"]] = {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": [participant_row["email"] for participant_row in participant_rows],
            }

    return activities


@app.on_event("startup")
def startup():
    initialize_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return load_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with get_db_connection() as connection:
        activity = connection.execute(
            "SELECT name FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if activity is None:
            raise HTTPException(status_code=404, detail="Activity not found")

        existing_registration = connection.execute(
            """
            SELECT 1
            FROM registrations
            WHERE activity_name = ? AND email = ?
            """,
            (activity_name, email),
        ).fetchone()

        if existing_registration is not None:
            raise HTTPException(
                status_code=400,
                detail="Student is already signed up"
            )

        connection.execute(
            """
            INSERT INTO registrations (activity_name, email)
            VALUES (?, ?)
            """,
            (activity_name, email),
        )
        connection.commit()

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    with get_db_connection() as connection:
        activity = connection.execute(
            "SELECT name FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if activity is None:
            raise HTTPException(status_code=404, detail="Activity not found")

        existing_registration = connection.execute(
            """
            SELECT 1
            FROM registrations
            WHERE activity_name = ? AND email = ?
            """,
            (activity_name, email),
        ).fetchone()
        if existing_registration is None:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity"
            )

        connection.execute(
            """
            DELETE FROM registrations
            WHERE activity_name = ? AND email = ?
            """,
            (activity_name, email),
        )
        connection.commit()

    return {"message": f"Unregistered {email} from {activity_name}"}
