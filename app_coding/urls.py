from sys import path

from rest_framework.routers import DefaultRouter
# from .views import QuestionViewSet

# router = DefaultRouter()
# router.register(r'questions', QuestionViewSet)

# urlpatterns = router.urls

# from .views import start_exam, current_question, submit_answer, total_score
from app_coding import views
from django.urls import path
urlpatterns = [
    path('register_url/',views.register_view,name='register_url'),
    path('login_url/',views.login_view,name='login_url'),
    # path('start/',views.start_exam,name='start_exam'),
    # path('current/',views.current_question,name='current_question'),
    path('submit/',views.submit_answer,name='submit_answer'),
    # path('score/',views.total_score,name='total_score'),
    path('generate_question_order/',views.generate_question_order,name='generate_question_order'),
    path('run_code/',views.run_code,name='run_code'),
    path('health/',views.health_check,name='health_check'),
]   