import json
import os
from typing import List

from pydantic import BaseModel, Field, ValidationError

class SubtaskItem(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    desc: str = ""


class TaskItem(BaseModel):
    id: int
    title: str = Field(min_length=1, max_length=200)
    completed: bool = False
    subtasks: List[SubtaskItem] = Field(default_factory=list)


class AppState(BaseModel):
    tasks: List[TaskItem] = Field(default_factory=list)


DATA_FILE = "ivynode_data.json"


def load_data() -> AppState:
    if not os.path.exists(DATA_FILE):
        return AppState()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return AppState(**data)

    except FileNotFoundError:
        return AppState()

    except json.JSONDecodeError:
        print("Error: The saved data file contains invalid JSON.")
        return AppState()

    except ValidationError:
        print("Error: The saved data contains invalid task information.")
        return AppState()

    except OSError as e:
        print(f"Error reading saved data: {e}")
        return AppState()


def save_data(state: AppState) -> bool:
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write(state.model_dump_json(indent=2))

        return True

    except OSError as e:
        print(f"Error saving data: {e}")
        return False