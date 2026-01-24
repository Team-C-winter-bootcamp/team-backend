from rest_framework import serializers


class CaseSerializer(serializers.Serializer):
    category = serializers.CharField()
    who = serializers.CharField()
    when = serializers.CharField()
    what = serializers.CharField()
    want = serializers.CharField()
    detail = serializers.CharField()


class CaseAnswerApiResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="success")
    data = serializers.JSONField()