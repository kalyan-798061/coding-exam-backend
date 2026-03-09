"""
Question Loader Module
======================
Loads questions from questions.json file.
No database needed - pure JSON-based question management.

Data Format (questions.json):
{
  "questions": [
    {
      "id": 1,                          # Unique question ID
      "title": "Sum of Numbers",        # Question title
      "description": "...",             # Full problem description
      "difficulty": "easy",             # "easy" or "hard"
      "marks": 10,                      # Points for correct answer
      "examples": [                     # Example test cases (shown to user)
        {
          "input": "1\n2\n3",
          "output": "6",
          "explanation": "1 + 2 + 3 = 6"
        }
      ],
      "constraints": [                  # List of constraints
        "Each line contains one integer"
      ],
      "puzzle_input": "10\n20\n30",     # The actual input data for this question
      "expected_answer": "60"           # The correct answer (exact match)
    }
  ]
}
"""

import json
import os
from pathlib import Path

# Path to questions.json (same directory as this file's parent)
QUESTIONS_FILE = Path(__file__).parent.parent / "questions.json"


def load_questions():
    """
    Load all questions from questions.json.
    Returns a list of question dictionaries.
    """
    if not QUESTIONS_FILE.exists():
        raise FileNotFoundError(f"Questions file not found: {QUESTIONS_FILE}")
    
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return data.get("questions", [])


def get_question_by_id(question_id):
    """
    Get a single question by its ID.
    Returns None if not found.
    """
    questions = load_questions()
    for q in questions:
        if q["id"] == question_id:
            return q
    return None


def get_all_question_ids():
    """
    Get list of all question IDs.
    """
    questions = load_questions()
    return [q["id"] for q in questions]


def validate_answer(question_id, user_answer):
    """
    Validate user's answer against expected answer.
    Uses exact string match (after stripping whitespace).
    
    Returns:
        {
            "is_correct": True/False,
            "expected": "..." (only if wrong, for debugging)
        }
    """
    question = get_question_by_id(question_id)
    if not question:
        return {"is_correct": False, "error": "Question not found"}
    
    expected = str(question["expected_answer"]).strip()
    submitted = str(user_answer).strip()
    
    is_correct = (submitted == expected)
    
    result = {"is_correct": is_correct}
    if not is_correct:
        # Optionally include expected answer for debugging
        # Remove this in production if you don't want to leak answers
        # result["expected"] = expected
        pass
    
    return result


def get_questions_for_exam(question_ids=None):
    """
    Get questions formatted for the exam.
    Excludes expected_answer from the response (don't send to frontend).
    PRESERVES the order of question_ids (important for shuffled order).
    
    Args:
        question_ids: List of IDs to include (in order). If None, returns all.
    
    Returns:
        List of question dicts safe to send to frontend.
    """
    questions = load_questions()
    
    # Create a lookup dict for quick access
    questions_by_id = {q["id"]: q for q in questions}
    
    # If question_ids provided, return in that order
    if question_ids:
        ordered_questions = []
        for qid in question_ids:
            if qid in questions_by_id:
                ordered_questions.append(questions_by_id[qid])
        questions = ordered_questions
    
    # Remove expected_answer before sending to frontend
    safe_questions = []
    for q in questions:
        safe_q = {
            "question_id": q["id"],
            "title": q["title"],
            "description": q["description"],
            "difficulty": q["difficulty"],
            "marks": q["marks"],
            "examples": q.get("examples", []),
            "constraints": q.get("constraints", []),
            "puzzle_input": q["puzzle_input"],
        }
        safe_questions.append(safe_q)
    
    return safe_questions


def get_question_count():
    """Get total number of questions."""
    return len(load_questions())


def get_questions_by_difficulty(difficulty):
    """
    Get questions filtered by difficulty.
    
    Args:
        difficulty: "easy" or "hard"
    """
    questions = load_questions()
    return [q for q in questions if q["difficulty"] == difficulty]
