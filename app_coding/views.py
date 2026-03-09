from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import ExamSession, Submission
from .question_loader import (
    load_questions,
    get_question_by_id,
    get_questions_for_exam,
    validate_answer,
    get_questions_by_difficulty,
)
import json
import subprocess
import tempfile
import os
import time
import random
import requests as http_requests


@csrf_exempt
def register_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    data = json.loads(request.body)

    name = data.get("name")
    department = data.get("department")
    year = data.get("year")

    if not all([name, department, year]):
        return JsonResponse({"error": "All fields required"}, status=400)

    # Prevent duplicate session
    if ExamSession.objects.filter(name=name).exists():
        return JsonResponse({"error": "User already registered"}, status=400)

    ExamSession.objects.create(
        name=name,
        department=department,
        year=year,
        question_order=[],
        current_index=0
    )

    return JsonResponse({"status": "Registered successfully"}, status=201)


@csrf_exempt
def login_view(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = data.get("name")

    if not name:
        return JsonResponse({"error": "name required"}, status=400)

    try:
        session = ExamSession.objects.get(name=name)
    except ExamSession.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    request.session["name"] = name

    now = timezone.now()

    if now < settings.CONTEST_START_TIME:
        return JsonResponse({
            "status": "not_started",
            "start_time": settings.CONTEST_START_TIME
        })

    if now >= settings.CONTEST_END_TIME:
        return JsonResponse({
            "status": "ended"
        })

    return JsonResponse({
        "status": "exam",
        "name": name
    })


@csrf_exempt
def generate_question_order(request):
    """
    Generate ALL 10 questions for the user in shuffled order.
    Uses questions.json instead of database.
    Users can choose which question to solve in any order.
    """
    name = request.session.get("name")

    if not name:
        return JsonResponse({"error": "session expired"}, status=400)

    try:
        session = ExamSession.objects.get(name=name)
    except ExamSession.DoesNotExist:
        return JsonResponse({"error": "session not found"}, status=404)

    now = timezone.now()

    # exam not started
    if now < settings.CONTEST_START_TIME:
        return JsonResponse({
            "status": "not_started",
            "start_time": settings.CONTEST_START_TIME
        })

    # exam ended
    if now >= settings.CONTEST_END_TIME:
        return JsonResponse({"status": "ended"})

    # Generate questions only once (from JSON file)
    if not session.question_order:
        # Load ALL questions from JSON
        all_questions = load_questions()
        all_ids = [q["id"] for q in all_questions]

        if len(all_ids) < 1:
            return JsonResponse({
                "error": "No questions found in questions.json"
            }, status=500)

        # Shuffle the question IDs for this user
        random.shuffle(all_ids)

        session.question_order = all_ids
        session.current_index = 0
        session.save()

    # Return ALL questions in shuffled order (without expected_answer)
    questions_data = get_questions_for_exam(session.question_order)

    # Get solved questions from Submission model
    solved_question_ids = list(
        Submission.objects.filter(
            question_id__in=session.question_order,
            is_correct=True
        ).values_list("question_id", flat=True)
    )

    return JsonResponse({
        "status": "exam",
        "questions": questions_data,
        "solved_question_ids": solved_question_ids,
        "total_score": session.score,
    })


@csrf_exempt
def submit_answer(request):
    """
    Submit answer for a specific question.
    Validates the answer using JSON data (exact match).
    Allows resubmission for wrong answers.
    
    Accepts: { "question_id": ..., "answer": "..." }
    Returns: { "status": "correct"|"wrong", "score": ... }
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = request.session.get("name")
    question_id = data.get("question_id")
    user_answer = data.get("answer")

    if not name:
        return JsonResponse({"error": "session expired"}, status=400)
    
    if question_id is None or user_answer is None:
        return JsonResponse({"error": "question_id and answer required"}, status=400)

    try:
        with transaction.atomic():
            # Lock this session row until transaction completes
            session = (
                ExamSession.objects
                .select_for_update()
                .get(name=name)
            )

            # Verify question is in user's question set
            if question_id not in session.question_order:
                return JsonResponse({"error": "Invalid question"}, status=400)

            # Get question from JSON
            question = get_question_by_id(question_id)
            if not question:
                return JsonResponse({"error": "Question not found in questions.json"}, status=404)

            # Check if already solved correctly
            existing_correct = Submission.objects.filter(
                question_id=question_id,
                is_correct=True
            ).exists()

            if existing_correct:
                return JsonResponse({
                    "status": "already_solved",
                    "message": "You have already solved this question correctly!",
                    "score": session.score,
                })

            # Validate answer using exact match
            validation = validate_answer(question_id, user_answer)
            is_correct = validation["is_correct"]

            # Create submission record
            Submission.objects.create(
                question_id=question_id,
                submitted_answer=str(user_answer).strip(),
                is_correct=is_correct,
                marks_awarded=question["marks"] if is_correct else 0,
            )

            if is_correct:
                session.score += question["marks"]
                session.save()

                # Check if all questions solved
                solved_count = Submission.objects.filter(
                    question_id__in=session.question_order,
                    is_correct=True
                ).values("question_id").distinct().count()

                all_solved = solved_count >= len(session.question_order)

                return JsonResponse({
                    "status": "correct",
                    "message": "Correct answer!",
                    "marks_awarded": question["marks"],
                    "score": session.score,
                    "all_solved": all_solved,
                })
            else:
                return JsonResponse({
                    "status": "wrong",
                    "message": "Wrong answer. Try again!",
                    "score": session.score,
                })

    except ExamSession.DoesNotExist:
        return JsonResponse({"error": "session not found"}, status=404)


# ─── CODE EXECUTION ENDPOINT ────────────────────────────────────────────────────

CODE_RUNNER_URL = os.environ.get("CODE_RUNNER_URL", "http://localhost:3001/run")
CODE_EXECUTION_TIMEOUT = 10  # seconds (for local fallback)
MAX_OUTPUT_LENGTH = 50000    # characters

@csrf_exempt
def run_code(request):
    """
    Execute user-submitted code.
    
    First tries the CodeSandbox-powered code-runner service (Node.js on port 3001).
    Falls back to local subprocess execution if the service is unavailable.
    
    Accepts: { "code": "...", "language": "python", "puzzleInput": "..." }
    Returns: { "status": "success"|"error", "stdout": "...", "stderr": "...", "executionTime": ... }
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    code = data.get("code", "")
    language = data.get("language", "python")
    puzzle_input = data.get("puzzleInput", "")

    if not code.strip():
        return JsonResponse({"error": "No code provided"}, status=400)

    # ─── Try CodeSandbox code-runner service first ───────────────────────────────
    try:
        response = http_requests.post(
            CODE_RUNNER_URL,
            json={
                "code": code,
                "language": language,
                "puzzleInput": puzzle_input,
            },
            timeout=60,  # Allow up to 60s for sandbox operations
        )
        
        if response.status_code == 200:
            result_data = response.json()
            # Check if code-runner returned an actual successful execution
            # If it returned an error (e.g., sandbox creation failed), fall back to local
            if result_data.get("status") == "success":
                stdout = result_data.get("stdout", "")
                # If code-runner returns "(no output)" or empty, and this is Python,
                # fall back to local execution as CodeSandbox may have issues
                if language == "python" and stdout in ("(no output)", ""):
                    print(f"[run_code] Code-runner returned empty output, falling back to local subprocess")
                else:
                    return JsonResponse(result_data)
            elif result_data.get("status") == "error":
                # Check if it's a sandbox/infrastructure error vs code error
                stderr = result_data.get("stderr", "")
                if "sandbox" in stderr.lower() or "unauthorized" in stderr.lower() or "failed to" in stderr.lower():
                    # Infrastructure error, fall back to local execution
                    print(f"[run_code] Code-runner infrastructure error, falling back to local: {stderr}")
                else:
                    # Actual code execution error, return it
                    return JsonResponse(result_data)
        else:
            # Service returned an error, fall through to local execution
            error_data = response.json()
            if "error" in error_data:
                print(f"[run_code] Code-runner HTTP error: {error_data}")
                
    except http_requests.exceptions.ConnectionError:
        # Code-runner service not running, fall back to local execution
        pass
    except http_requests.exceptions.Timeout:
        return JsonResponse({
            "status": "error",
            "stderr": "Code execution timed out (remote service).",
            "executionTime": 60000,
        })
    except Exception as e:
        # Log but continue to fallback
        print(f"[run_code] Code-runner service error: {e}")

    # ─── Fallback: Local subprocess execution (Python only) ──────────────────────
    if language != "python":
        return JsonResponse({
            "error": f"Language '{language}' requires the code-runner service. Please start it with: cd code-runner && npm start"
        }, status=503)

    start_time = time.time()
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir="/tmp"
        ) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        result = subprocess.run(
            ["python3", tmp_path],
            input=puzzle_input,
            capture_output=True,
            text=True,
            timeout=CODE_EXECUTION_TIMEOUT,
            cwd="/tmp",
        )

        execution_time = int((time.time() - start_time) * 1000)

        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if len(stdout) > MAX_OUTPUT_LENGTH:
            stdout = stdout[:MAX_OUTPUT_LENGTH] + "\n... (output truncated)"
        if len(stderr) > MAX_OUTPUT_LENGTH:
            stderr = stderr[:MAX_OUTPUT_LENGTH] + "\n... (output truncated)"

        if result.returncode != 0:
            return JsonResponse({
                "status": "error",
                "stdout": stdout,
                "stderr": stderr,
                "executionTime": execution_time,
            })

        return JsonResponse({
            "status": "success",
            "stdout": stdout if stdout else "(no output)",
            "stderr": stderr,
            "executionTime": execution_time,
        })

    except subprocess.TimeoutExpired:
        execution_time = int((time.time() - start_time) * 1000)
        return JsonResponse({
            "status": "error",
            "stderr": f"Execution timed out after {CODE_EXECUTION_TIMEOUT} seconds.",
            "executionTime": execution_time,
        })

    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        return JsonResponse({
            "status": "error",
            "stderr": f"Server error: {str(e)}",
            "executionTime": execution_time,
        })

    finally:
        # Clean up the temp file if it was created
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# ─── HEALTH CHECK ENDPOINT ────────────────────────────────────────────────────

def health_check(request):
    """
    Health check endpoint for Railway deployment.
    Returns 200 OK if the service is running.
    """
    return JsonResponse({
        "status": "healthy",
        "service": "codearena-backend",
    })
