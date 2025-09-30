# \# Automated Time-table Scheduling for IIIT Dharwad

# 

# This project aims to automate timetable scheduling for courses at IIIT Dharwad.

# 


# 

# Automated Time-Table Scheduling for IIIT Dharwad

## Team: Byte_Me

A robust, conflict-free scheduling system designed to automate the creation and management of academic timetables for the Indian Institute of Information Technology Dharwad.

---

## 📖 Table of Contents

-   [Problem Statement](#-problem-statement)
-   [Key Features](#-key-features)
-   [Tech Stack](#-tech-stack)
-   [Folder Structure](#-folder-structure)
-   [Getting Started](#-getting-started)
-   [Running Tests](#-running-tests)
-   [Team Members](#-team-members)

---

## 🎯 Problem Statement

[cite_start]In many educational institutions, timetable scheduling is performed manually, which is a time-consuming and error-prone process[cite: 35]. [cite_start]This often leads to issues like scheduling conflicts, overbooked classrooms, and uneven faculty workloads[cite: 36]. [cite_start]The existing system at IIIT Dharwad requires students and faculty to cross-reference multiple documents to understand their schedules, which is inefficient and inconvenient[cite: 58].

[cite_start]This project aims to develop a fully automated timetable software that generates optimized and conflict-free schedules, saving administrative time and providing a seamless, user-friendly experience for students and faculty[cite: 41].

## ✨ Key Features

The software is designed with the following features and capabilities:

-   [cite_start]**Automatic Timetable Generation:** Creates optimized and conflict-free timetables based on institutional rules and constraints[cite: 41].
-   [cite_start]**Role-Based Access Control:** Secure login system for different user roles such as Administrator, Faculty, and Student[cite: 168].
-   [cite_start]**Admin Management Panel:** Allows administrators to add, edit, or delete courses, subjects, faculty, and rooms[cite: 168].
-   [cite_start]**Faculty Availability:** Enables faculty members to log in and specify their unavailable time slots, which the system will consider during scheduling[cite: 168].
-   **Constraint Handling:**
    -   [cite_start]Prevents clashes for faculty, classrooms, and labs[cite: 168].
    -   [cite_start]Schedules a maximum of one lecture per subject per day[cite: 168].
    -   [cite_start]Ensures proper breaks between classes and a dedicated lunch break[cite: 168].
-   **Exam Scheduling:**
    -   [cite_start]Automatically generates conflict-free exam timetables[cite: 170].
    -   [cite_start]Allocates classrooms and generates seating plans for exams[cite: 170].
    -   [cite_start]Assigns invigilators fairly while respecting faculty workload[cite: 170].
-   **Custom Views & Export:**
    -   [cite_start]Generates separate, personalized timetables for students and faculty[cite: 170].
    -   [cite_start]Allows timetables to be downloaded in PDF or Excel formats[cite: 170].
-   [cite_start]**Google Calendar Integration:** Automatically syncs generated timetables with a student's Google Calendar and sets reminders for classes[cite: 170].
-   [cite_start]**Manual Adjustments:** Provides an option for the administrator to manually modify the auto-generated timetable if necessary[cite: 170].

## 🛠️ Tech Stack

-   **Backend:** Python 3.x
-   **Data Storage:** CSV / JSON for input data
-   **Testing:** `pytest` framework for unit testing
-   **Version Control:** Git & GitHub

## 📂 Folder Structure

The project is organized into the following directories:

# \- `data/` → contains sample input timetable (`classes.csv`)

# \- `src/` → core code (`scheduler.py`)

# \- `tests/` → basic unit tests

## 🚀 Getting Started

Follow these instructions to set up and run the project locally.

### Prerequisites

-   Python 3.8 or higher
-   pip (Python package installer)

### Installation

1.  **Clone the repository:**
    ```sh
    git clone <your-repository-url>
    ```
2.  **Navigate to the project directory:**
    ```sh
    cd Automated-Timetable-Scheduling
    ```
3.  **Install the required dependencies** (create a `requirements.txt` file first):
    ```sh
    pip install -r requirements.txt
    ```

### Usage

To run the scheduler and generate a timetable, execute the main script:

```sh
python src/scheduler.py
The generated timetable will be displayed in the console.

✅ Running Tests
To ensure the reliability of the code, run the unit tests using pytest:

Bash

pytest
All tests should pass, confirming that the core components are functioning correctly.
