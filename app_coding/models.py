from django.db import models


# Question model is no longer used - questions come from questions.json
# Keeping it here for reference/migration purposes
class Question(models.Model):
    """
    DEPRECATED: Questions are now loaded from questions.json
    This model is kept for backwards compatibility with existing migrations.
    """
    title = models.CharField(max_length=255)
    description = models.TextField()
    puzzle_input = models.TextField()
    expected_answer = models.CharField(max_length=255)
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
    """
    Tracks a user's exam session.
    - question_order: List of question IDs (from questions.json) assigned to this user
    - score: Total score accumulated
    """
    name = models.CharField(null=True, max_length=150, unique=True)
    department = models.TextField(null=True)
    year = models.TextField(null=True)
    question_order = models.JSONField(default=list)  # stores question IDs from JSON
    current_index = models.IntegerField(default=0)   # not used in new flow, kept for compatibility
    created_at = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(default=0)

    def __str__(self):
        return f"Session: {self.name}"


class Submission(models.Model):
    """
    Tracks individual answer submissions.
    - question_id: ID from questions.json (not a foreign key anymore)
    - Multiple submissions allowed per question (retry on wrong answers)
    """
    question_id = models.IntegerField(default=0)  # References ID in questions.json
    submitted_answer = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    marks_awarded = models.IntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Q{self.question_id}: {'Correct' if self.is_correct else 'Wrong'}"
