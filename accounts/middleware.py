from django.shortcuts import redirect
from django.urls import reverse
from .models import SurveyQuestion, UserSurveyAnswer


class SurveyRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and not user.is_superuser:
            path = request.path
            survey_path = reverse('accounts:survey')
            allowed_prefixes = (
                survey_path,
                reverse('accounts:logout'),
                '/admin/',
                '/static/',
                '/media/',
            )
            if not any(path.startswith(p) for p in allowed_prefixes):
                if self._needs_survey(user):
                    return redirect(f"{survey_path}?next={path}")

        return self.get_response(request)

    def _needs_survey(self, user):
        required_questions = SurveyQuestion.objects.filter(is_active=True, is_required=True)
        if not required_questions.exists():
            return False
        for q in required_questions:
            if not UserSurveyAnswer.objects.filter(user=user, question=q).exists():
                return True
        return False
