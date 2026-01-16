from django.db import models


class BaseModel(models.Model):
    """모든 테이블 공통 필드"""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성 시각")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정 시각")
    is_deleted = models.BooleanField(default=False, verbose_name="논리적 삭제 플래그")

    class Meta:
        abstract = True


class Category(BaseModel):
    category_code = models.IntegerField(verbose_name="대분류 코드")
    category_name = models.CharField(max_length=50, verbose_name="대분류명")

    def __str__(self): return self.category_name


class SubCategory(BaseModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories',
                                 db_column='categories_id')
    subcategory_name = models.CharField(max_length=50, verbose_name="소분류명")

    def __str__(self): return self.subcategory_name


class Court(BaseModel):
    court_code = models.IntegerField(verbose_name="법원 코드")
    court_type = models.CharField(max_length=20, verbose_name="법원 타입")
    court_name = models.CharField(max_length=50, verbose_name="법원명")

    def __str__(self): return self.court_name


class Outcome(BaseModel):
    outcome_code = models.IntegerField(verbose_name="결과 코드")
    outcome_type = models.CharField(max_length=50, verbose_name="결과 이름")

    def __str__(self): return self.outcome_type


# --- 여기서부터 에러 발생했던 클래스들 시작 ---

class ReferenceCourtCase(BaseModel):
    ref_case_no = models.CharField(max_length=50, verbose_name="사건번호")

    def __str__(self): return self.ref_case_no


class ReferenceRule(BaseModel):
    law_type = models.CharField(max_length=50, verbose_name="법률명")
    article_no = models.IntegerField(verbose_name="조문")

    def __str__(self): return f"{self.law_type} {self.article_no}"


class Keyword(BaseModel):
    name = models.CharField(max_length=200, verbose_name="키워드")

    def __str__(self): return self.name


class Precedent(BaseModel):
    case_no = models.CharField(max_length=50, verbose_name="사건번호")
    case_name = models.CharField(max_length=50, verbose_name="사건명")
    case_title = models.CharField(max_length=100, verbose_name="사건제목")
    decision_type = models.CharField(max_length=20, verbose_name="심판유형")
    judge_date = models.DateField(verbose_name="판결선고일")
    court = models.ForeignKey(Court, on_delete=models.CASCADE, db_column='court_id')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, db_column='subcategories_id')

    # API 대응용 필드 추가
    judgment_content = models.TextField(blank=True, null=True, verbose_name="판결내용")
    judgment_summary = models.TextField(blank=True, null=True, verbose_name="판결요지")
    holdings = models.TextField(blank=True, null=True, verbose_name="판시사항")
    question = models.TextField(blank=True, null=True, verbose_name="질문")
    answer = models.TextField(blank=True, null=True, verbose_name="답변")
    summary_original = models.TextField(blank=True, null=True, verbose_name="요약원문")
    summary = models.TextField(blank=True, null=True, verbose_name="요약")


# --- 관계 테이블 ---

class RelationOutcome(BaseModel):
    precedent = models.OneToOneField(Precedent, on_delete=models.CASCADE, db_column='precedents_id', related_name='relationoutcome')
    outcome = models.ForeignKey(Outcome, on_delete=models.CASCADE, db_column='outcomes_id')
    outcome_value = models.IntegerField(null=True, blank=True)


class RelationCourtCase(BaseModel):
    reference_court_case = models.ForeignKey(ReferenceCourtCase, on_delete=models.CASCADE,
                                             db_column='reference_court_cases_id')
    precedent = models.ForeignKey(Precedent, on_delete=models.CASCADE, db_column='precedents_id')


class RelationRule(BaseModel):
    reference_rule = models.ForeignKey(ReferenceRule, on_delete=models.CASCADE, db_column='reference_rules_id')
    precedent = models.ForeignKey(Precedent, on_delete=models.CASCADE, db_column='precedents_id')


class RelationKeyword(BaseModel):
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, db_column='keywords_id')
    precedent = models.ForeignKey(Precedent, on_delete=models.CASCADE, db_column='precedents_id')