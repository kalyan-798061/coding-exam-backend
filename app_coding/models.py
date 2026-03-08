from django.db import models


class Question(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    puzzle_input = models.TextField()
    expected_answer = models.CharField(max_length=255)  # single line answer
    marks = models.IntegerField(default=10)
    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("hard", "Hard"),
    ]
    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default='easy'
    )

    def __str__(self):
        return self.title


class ExamSession(models.Model):
    name=models.CharField(null=True, max_length=150, unique=True)  # Assuming one session per user
    department=models.TextField(null=True)  # e.g., CSE, ECE, etc.
    year=models.TextField(null=True)  # e.g., 1st Year, 2nd Year, etc.
    question_order = models.JSONField(default=list)  # stores shuffled question IDs
    current_index = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(default=0)


class Submission(models.Model):
    
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    submitted_answer = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    marks_awarded = models.IntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    # class Meta:
    #     unique_together = ('user', 'question')