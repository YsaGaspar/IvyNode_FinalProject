import json
import os
from typing import List
from pydantic import BaseModel, Field

class TaskItem(BaseModel):
    id: int
    title: str
    completed: bool = False

class AppState(BaseModel):
    tasks: List[TaskItem] = Field(default_factory=list)

DATA_FILE = "ivynode_data.json"

def load_data() -> AppState:
    if not os.path.exists(DATA_FILE):
        return AppState()
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return AppState(**data)
    except Exception:
        return AppState()

def save_data(state: AppState) -> None:
    with open(DATA_FILE, "w") as f:
        f.write(state.model_dump_json(indent=2))