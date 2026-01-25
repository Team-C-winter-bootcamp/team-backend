from rest_framework import serializers


class CaseSerializer(serializers.Serializer):
    category = serializers.CharField(required=False, allow_blank=True, default='일반')
    who = serializers.CharField()
    when = serializers.CharField()
    what = serializers.CharField()
    want = serializers.CharField()
    detail = serializers.CharField()


class PrecedentResultSerializer(serializers.Serializer):
    case_No = serializers.CharField()
    case_name = serializers.CharField()
    case_title = serializers.CharField()
    law_category = serializers.CharField()
    law_subcategory = serializers.CharField()
    court = serializers.CharField()
    judgment_date = serializers.CharField()
    similarity = serializers.FloatField()
    preview = serializers.CharField(required=False, allow_blank=True)


class CaseSearchResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    code = serializers.IntegerField()
    message = serializers.CharField()
    data = serializers.DictField()


class PrecedentDetailResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    data = serializers.DictField()


class CaseAnswerApiResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="success")
    data = serializers.JSONField()