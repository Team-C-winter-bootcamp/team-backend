from django.contrib import admin
from .models import (
    Category, SubCategory, Court, Outcome,
    Precedent, ReferenceCourtCase, ReferenceRule,
    Keyword, RelationOutcome, RelationCourtCase,
    RelationRule, RelationKeyword
)


# 1. 공통 설정을 위한 베이스 클래스
class BaseAdmin(admin.ModelAdmin):
    """
    IDE 경고 방지: 아래 필드들은 BaseModel을 상속받은 모델들에서 공통으로 사용됩니다.
    """
    readonly_fields = ('created_at', 'updated_at')
    list_display = ('id', 'is_deleted', 'created_at')
    list_filter = ('is_deleted',)


# 2. 메인 판례 관리 (중복 선언 해결)
@admin.register(Precedent)
class PrecedentAdmin(BaseAdmin):
    # 기존 list_display에 Precedent 전용 필드 추가
    list_display = ('case_no', 'case_title', 'court', 'judge_date') + BaseAdmin.list_display
    list_filter = ('court', 'decision_type', 'judge_date') + BaseAdmin.list_filter

    # [수정] 64번 라인 근처의 중복된 search_fields를 하나로 통합했습니다.
    search_fields = ('case_no', 'case_title', 'case_name')
    date_hierarchy = 'judge_date'
    
    # 긴 텍스트 필드들은 admin에서 제외 (판례내용 등은 S3에 저장되므로)
    exclude = (
        'judgment_content',  # 판결내용
        'judgment_summary',  # 판결요지
        'holdings',  # 판시사항
        'question',  # 질문
        'answer',  # 답변
        'summary_original',  # 요약원문
        'summary',  # 요약
    )
    
    # 이 판례를 다른 곳에서 검색할 때 사용할 필드 설정
    # (PrecedentAdmin 자체가 search_fields를 가지고 있어야 autocomplete가 작동함)


# 3. 관계 매핑 테이블 관리 (개별 관리 및 검색 최적화)
@admin.register(RelationOutcome)
class RelationOutcomeAdmin(BaseAdmin):
    list_display = ('precedent', 'outcome', 'outcome_value') + BaseAdmin.list_display
    autocomplete_fields = ['precedent', 'outcome']


@admin.register(RelationCourtCase)
class RelationCourtCaseAdmin(BaseAdmin):
    list_display = ('precedent', 'reference_court_case') + BaseAdmin.list_display
    autocomplete_fields = ['precedent', 'reference_court_case']


@admin.register(RelationRule)
class RelationRuleAdmin(BaseAdmin):
    list_display = ('precedent', 'reference_rule') + BaseAdmin.list_display
    autocomplete_fields = ['precedent', 'reference_rule']


@admin.register(RelationKeyword)
class RelationKeywordAdmin(BaseAdmin):
    list_display = ('precedent', 'keyword') + BaseAdmin.list_display
    autocomplete_fields = ['precedent', 'keyword']


# 4. 마스터 데이터 관리
@admin.register(Outcome)
class OutcomeAdmin(BaseAdmin):
    list_display = ('outcome_code', 'outcome_type') + BaseAdmin.list_display
    search_fields = ('outcome_type',)


@admin.register(Keyword)
class KeywordAdmin(BaseAdmin):
    list_display = ('name',) + BaseAdmin.list_display
    search_fields = ('name',)


@admin.register(ReferenceRule)
class ReferenceRuleAdmin(BaseAdmin):
    list_display = ('law_type', 'article_no') + BaseAdmin.list_display
    search_fields = ('law_type',)


@admin.register(ReferenceCourtCase)
class ReferenceCourtCaseAdmin(BaseAdmin):
    list_display = ('ref_case_no',) + BaseAdmin.list_display
    search_fields = ('ref_case_no',)


# 5. 기타 분류 데이터
@admin.register(Category)
class CategoryAdmin(BaseAdmin):
    list_display = ('category_code', 'category_name') + BaseAdmin.list_display
    search_fields = ('category_name',)


@admin.register(SubCategory)
class SubCategoryAdmin(BaseAdmin):
    list_display = ('subcategory_name', 'category') + BaseAdmin.list_display
    list_filter = ('category',) + BaseAdmin.list_filter
    search_fields = ('subcategory_name',)


@admin.register(Court)
class CourtAdmin(BaseAdmin):
    list_display = ('court_code', 'court_name', 'court_type') + BaseAdmin.list_display
    search_fields = ('court_name',)