from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q
from .models import Diploma
from .serializers import DiplomaSerializer, DiplomaSearchSerializer


class DiplomaSearchView(APIView):
    """
    GET /api/diplomacheck/search/?q=<query>
    Flexibele zoekfunctie: zoekt op elke combinatie van woorden in naam of CREBO.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response([])

        words = q.split()

        # AND-logica: elk woord moet ergens in naam of CREBO voorkomen
        word_filter = Q()
        for word in words:
            word_filter &= Q(name__icontains=word) | Q(crebo__icontains=word)

        # OR-fallback: als AND te weinig resultaten geeft, neem ook diploma's
        # die minstens één woord bevatten
        any_word_filter = Q()
        for word in words:
            any_word_filter |= Q(name__icontains=word) | Q(crebo__icontains=word)

        qs = Diploma.objects.filter(is_active=True)
        results = list(qs.filter(word_filter)[:10])
        if len(results) < 5:
            extra = qs.filter(any_word_filter).exclude(
                pk__in=[d.pk for d in results]
            )[:10 - len(results)]
            results += list(extra)

        return Response(DiplomaSearchSerializer(results, many=True).data)


class DiplomaDetailView(RetrieveAPIView):
    """
    GET /api/diplomacheck/<id>/
    Geeft volledige diploma-informatie inclusief kwalificerende functies.
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = DiplomaSerializer
    queryset = Diploma.objects.filter(is_active=True)
