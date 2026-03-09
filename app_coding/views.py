from aiohttp import request
from django.shortcuts import redirect, render
from requests import session
from rest_framework import viewsets
from .models import *
from .serializers import QuestionSerializer
import random
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serializers import QuestionSerializer
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
import random

from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


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


import json
import random
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from .models import ExamSession, Question



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

    # generate questions only once
    if not session.question_order:

        easy_ids = list(
            Question.objects.filter(difficulty="easy")
            .values_list("id", flat=True)
        )

        hard_ids = list(
            Question.objects.filter(difficulty="hard")
            .values_list("id", flat=True)
        )

        if len(easy_ids) < 2 or len(hard_ids) < 3:
            return JsonResponse({"error": "Not enough questions in database"})

        selected_questions = random.sample(easy_ids, 2) + random.sample(hard_ids, 3)
        random.shuffle(selected_questions)

        session.question_order = selected_questions
        session.current_index = 0
        session.save()

    question_id = session.question_order[session.current_index]
    question = Question.objects.get(id=question_id)

    return JsonResponse({
        "status": "exam",
        "question_id": question.id,
        "title": question.title,
        "description": question.description,
        "puzzle_input": question.puzzle_input,
        "marks": question.marks,
    })

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ExamSession, Question


import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from .models import ExamSession, Question


@csrf_exempt
def submit_answer(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    data = json.loads(request.body)

    name = request.session.get("name")
    user_answer = data.get("answer")

    if not name or user_answer is None:
        return JsonResponse({"error": "name and answer required"}, status=400)

    try:
        with transaction.atomic():

            # lock this session row until transaction completes
            session = (
                ExamSession.objects
                .select_for_update()
                .get(name=name)
            )

            # exam already finished
            if session.current_index >= len(session.question_order):
                return JsonResponse({
                    "status": "finished",
                    "final_score": session.score
                })

            question_id = session.question_order[session.current_index]

            try:
                question = Question.objects.get(id=question_id)
            except Question.DoesNotExist:
                return JsonResponse({"error": "question missing"}, status=404)

            # check answer
            correct = str(user_answer).strip().upper() == str(question.expected_answer).strip().upper()

            if correct:
                session.score += question.marks

            session.current_index += 1
            session.save()

            # exam finished
            if session.current_index >= len(session.question_order):

                return JsonResponse({
                    "status": "finished",
                    "final_score": session.score
                })

            next_question_id = session.question_order[session.current_index]

            try:
                next_question = Question.objects.get(id=next_question_id)
            except Question.DoesNotExist:
                return JsonResponse({"error": "next question missing"}, status=404)

            return JsonResponse({
                "status": "next_question",
                "question_id": next_question.id,
                "title": next_question.title,
                "description": next_question.description,
                "puzzle_input": next_question.puzzle_input,
                "marks": next_question.marks
            })

    except ExamSession.DoesNotExist:
        return JsonResponse({"error": "session not found"}, status=404)

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def submit_answer(request):
#     user = request.user
#     submitted_answer = request.data.get("answer", "").strip()

#     try:
#         session = ExamSession.objects.get(user=user)
#     except ExamSession.DoesNotExist:
#         return Response({"error": "Exam not started"}, status=400)

#     total_questions = len(session.question_order)

#     if session.current_index >= total_questions:
#         return Response({
#             "exam_finished": True,
#             "message": "All questions already submitted"
#         })

#     question_id = session.question_order[session.current_index]
#     question = Question.objects.get(id=question_id)

#     # Prevent duplicate submission
#     if Submission.objects.filter(user=user, question=question).exists():
#         return Response({"error": "Already answered"}, status=400)

#     is_correct = submitted_answer == question.expected_answer.strip()
#     marks_awarded = question.marks if is_correct else 0

#     Submission.objects.create(
#         user=user,
#         question=question,
#         submitted_answer=submitted_answer,
#         is_correct=is_correct,
#         marks_awarded=marks_awarded
#     )

#     # Move to next question
#     session.current_index += 1
#     session.save()

#     # 🔥 Check if this was last question
#     if session.current_index >= total_questions:
#         return Response({
#             "correct": is_correct,
#             "marks_awarded": marks_awarded,
#             "exam_finished": True,
#             "message": "All questions submitted"
#         })

#     return Response({
#         "correct": is_correct,
#         "marks_awarded": marks_awarded,
#         "exam_finished": False
#     })




# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def total_score(request):
#     user = request.user

#     total = Submission.objects.filter(user=user).aggregate(
#         total=models.Sum('marks_awarded')
#     )['total'] or 0

#     return Response({"total_score": total})
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def start_exam(request):

#     # ✅ Calculate remaining time
#     # remaining_seconds = (settings.CONTEST_END_TIME - now).total_seconds()

#     question_ids = list(Question.objects.values_list('id', flat=True))
#     random.shuffle(question_ids)

#     ExamSession.objects.create(
#         user=user,
#         question_order=question_ids,
#         current_index=0,
#         end_time=settings.CONTEST_END_TIME  # important
#     )
    
#     question_id = session.question_order[session.current_index]
#     question = Question.objects.get(id=question_id)

#     remaining_seconds = int((session.end_time - timezone.now()).total_seconds())

#     return Response({
#         "question_id": question.id,
#         "title": question.title,
#         "description": question.description,
#         "puzzle_input": question.puzzle_input,
#         "current_index": session.current_index,
#         "total_questions": len(session.question_order),
#         "is_last_question": session.current_index == len(session.question_order) - 1,
#         "remaining_seconds": remaining_seconds
#     })

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def current_question(request):
#     user = request.user

#     try:
#         session = ExamSession.objects.get(user=user)
#     except ExamSession.DoesNotExist:
#         return Response({"error": "Exam not started"}, status=400)

#     if session.current_index >= len(session.question_order):
#         return Response({"message": "Exam finished"})

#     question_id = session.question_order[session.current_index]
#     question = Question.objects.get(id=question_id)

#     serializer = QuestionSerializer(question)
#     return Response(serializer.data)



# import json
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from .services.code_executor import execute_code

# @csrf_exempt
# def execute_view(request):

#     if request.method != "POST":
#         return JsonResponse({"error": "POST required"}, status=405)

#     try:
#         body = json.loads(request.body)

#         code = body.get("code")
#         language = body.get("language")
#         puzzle_input = body.get("puzzleInput", "")

#         result = execute_code(code, language, puzzle_input)

#         return JsonResponse(result)

#     except Exception as e:
#         return JsonResponse({
#             "status": "error",
#             "stderr": str(e)
#         })