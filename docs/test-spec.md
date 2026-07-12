# 테스트 명세

테스트 함수 65개(파라미터라이즈 포함 실행 케이스 75개)의 명세. 각 항목은 테스트 함수의 한글 docstring과 동일하다.

## 테스트 인프라

- **실제 DB 테스트**: DB를 만지는 테스트는 mock 없이 docker compose의 `meow-mysql` 컨테이너 안 전용 `meow_test` 데이터베이스에 대해 실행된다.
  - 테스트 세션 시작 시 `meow_test` DB를 자동 생성하고 스키마를 재생성한다 (`tests/conftest.py`의 `mysql_available`)
  - 각 테스트는 outer 트랜잭션 + SAVEPOINT(`join_transaction_mode="create_savepoint"`)로 격리되어, `@transactional`의 commit이 있어도 종료 시 전부 롤백된다 — 데이터가 남지 않는다
  - MySQL이 꺼져 있으면 DB 의존 테스트(30개)는 실패가 아니라 **skip** 처리된다
  - `TEST_MYSQL_URL` 환경변수로 대상 DB를 오버라이드할 수 있다
- **mock 경계**: 외부 API만 mock한다 — LLM(OpenAI/Gemini), reddit, ZenQuotes, S3(aioboto3). AI 의존 테스트 목록과 live 전환 방법은 [ai-test-spec.md](ai-test-spec.md) 참고.

## 분석기 — tests/analyzer/ (AI mock)

### test_daily_quote_analyzer.py
- `test_analyze_raw_content` — RAW 명언을 LLM으로 분석하면 번역·표현·배경이 채워지고 ANALYZED 상태가 된다
- `test_reanalyze_content_field` — 요청한 필드만 프롬프트 가이드에 따라 재분석되어 갱신된다

### test_meme_analyzer.py
- `test_analyze_raw_content` — RAW 밈을 LLM으로 분석하면 밈 텍스트·번역·배경이 채워지고 PENDING 상태가 된다
- `test_reanalyze_content_field` — 요청한 필드만 프롬프트 가이드에 따라 재분석되어 갱신된다

## 외부 클라이언트 — tests/client/ (HTTP mock)

### test_zenquotes_client.py
- `test_fetch_daily_quotes` — ZenQuotes API 응답(q/a)이 QUOTE 타입 NewContent 목록으로 매핑된다

## 이미지 생성 — tests/image_generator/ (AI·S3 mock)

### test_daily_quote_image_generator.py
- `test_generate_updates_image_url_and_status` — 이미지 생성 성공 시 S3 키 규칙에 맞는 image_url과 PENDING 상태로 갱신된다
- `test_regenerate_updates_image_url_and_status` — 이미지 재생성 시 기존 이미지를 내려받아 보강하고 edited 경로의 image_url로 갱신된다

### test_diffusion_model.py
- `test_nano_banana_create_image_parses_image_from_response` — Nano Banana(Gemini) 응답의 이미지 데이터를 PIL 이미지로 파싱한다
- `test_nano_banana_reinforce_image_parses_image_from_response` — Nano Banana 이미지 보강(reinforce) 응답을 PIL 이미지로 파싱한다
- `test_nano_banana_reinforce_image_raises_for_unsupported_format` — 지원하지 않는 포맷의 원본 이미지로 보강을 요청하면 예외가 발생한다
- `test_gpt_image2_create_image_parses_image_from_response` — GPT-Image-2 응답의 base64 이미지를 PIL 이미지로 파싱한다
- `test_gpt_image2_reinforce_image_parses_image_from_response` — GPT-Image-2 이미지 보강 응답을 PIL 이미지로 파싱한다
- `test_gpt_image2_reinforce_image_raises_for_unsupported_format` — 지원하지 않는 포맷의 원본 이미지로 보강을 요청하면 예외가 발생한다
- `test_gpt_image2_create_image_raises_when_no_image_data` — 응답에 이미지 데이터가 없으면 예외가 발생한다

### test_factory.py
- `test_get_image_generator_with_nano_banana_model` — Nano Banana 모델 요청 시 NanoBanana 기반 생성기를 반환한다
- `test_get_image_generator_with_gpt_image_model` — GPT-Image 모델 요청 시 GptImage2 기반 생성기를 반환한다
- `test_get_image_generator_raises_for_unsupported_content_type` — 이미지 생성을 지원하지 않는 콘텐츠 타입이면 예외가 발생한다

### test_image_text_renderer.py
- `test_long_text_fits_within_two_lines` — 긴 텍스트가 이미지 위에 최대 줄 수(2줄) 이내로 줄바꿈되어 렌더링된다 ⚠️ 로컬 폰트 문제로 현재 실패
- `test_long_text_with_speaker_fits_within_three_lines` — 화자가 포함된 긴 텍스트가 본문+화자 합쳐 3줄 이내로 렌더링된다 ⚠️ 로컬 폰트 문제로 현재 실패

### test_s3_uploader.py
- `test_upload_png_returns_correct_url` — PNG 업로드 시 올바른 ContentType·Key로 저장하고 공개 URL을 반환한다
- `test_upload_jpeg_returns_correct_url` — JPEG 업로드 시 image/jpeg ContentType으로 저장하고 공개 URL을 반환한다
- `test_upload_unsupported_format_raises` — 지원하지 않는 이미지 포맷 업로드 요청은 예외가 발생한다
- `test_download_image_returns_pil_image` — S3 URL의 이미지를 내려받아 PIL 이미지로 반환한다
- `test_download_image_wrong_bucket_url_raises` — 다른 버킷의 URL로 다운로드를 요청하면 예외가 발생한다
- `test_download_image_non_s3_url_raises` — S3가 아닌 URL로 다운로드를 요청하면 예외가 발생한다

## 레포지토리 — tests/repository/mysql/ (실제 DB)

### test_content_repository.py
- `test_create_contents_adds_and_commits` — 새 콘텐츠 목록을 저장하면 저장 건수를 반환하고 실제 행이 생성된다
- `test_create_contents_skips_duplicates` — 이미 저장된 image_url·명언 텍스트와 중복되는 콘텐츠는 저장에서 제외된다
- `test_create_contents_truncates_long_fields` — author·title이 컬럼 최대 길이(200자)를 넘으면 잘라서 저장한다
- `test_update_status_rolls_back_for_missing_content` — 존재하지 않는 콘텐츠 상태 변경은 롤백되고 세션은 계속 사용할 수 있다

### test_usage_repository.py
- `test_record_adds_and_commits` — 토큰 사용량을 기록하면 token_usage 테이블에 실제 행이 생성된다
- `test_aggregate_by_maps_rows_to_usage_aggregate` — 기간 내 토큰 사용량을 일자·모델별로 집계하여 UsageAggregate로 반환한다 (실제 MySQL DATE_FORMAT 검증)
- `test_aggregate_by_excludes_out_of_range_rows` — 조회 기간 밖의 사용량은 집계에 포함되지 않는다

## 라우터 — tests/router/ (실제 DB, AI·S3 mock)

### test_admin.py
- `test_generate_image_for_content` — 이미지 생성 요청 시 생성기가 반환한 image_url·상태가 DB에 반영된다
- `test_generate_image_content_not_found` — 존재하지 않는 콘텐츠의 이미지 생성 요청은 404를 반환한다
- `test_regenerate_image_for_content` — 이미지 재생성 요청 시 프롬프트가 생성기에 전달되고 결과가 DB에 반영된다
- `test_regenerate_image_content_not_found` — 존재하지 않는 콘텐츠의 이미지 재생성 요청은 404를 반환한다
- `test_list_contents` — 상태·타입 필터에 맞는 콘텐츠 목록을 반환한다
- `test_list_contents_empty` — 조건에 맞는 콘텐츠가 없으면 빈 목록을 반환한다
- `test_analyze_content` — 콘텐츠 분석 요청 시 분석 결과 필드가 DB에 반영된다
- `test_analyze_content_not_found` — 존재하지 않는 콘텐츠의 분석 요청은 404를 반환한다
- `test_get_usage_cost` — 기간 내 실제 사용량 집계로 모델별 비용을 계산하고, 모르는 모델은 비용 없음으로 반환한다
- `test_get_usage_cost_applies_free_tier` — 무료 티어 적용 시 일일 무료 한도를 차감한 초과분만 과금된다
- `test_update_status_valid` — PENDING 콘텐츠 상태 변경 요청 시 DB의 상태가 APPROVED로 갱신된다
- `test_update_status_invalid_transition` — 허용되지 않는 상태 전이 요청은 422 검증 에러를 반환한다
- `test_reanalyze_fields` — 특정 필드 재분석 요청 시 재분석 결과가 DB에 반영된다
- `test_reanalyze_fields_not_found` — 존재하지 않는 콘텐츠의 재분석 요청은 404를 반환한다

### test_content.py
- `test_get_daily_content` — 해당 날짜에 예약(USED)된 콘텐츠를 반환한다
- `test_get_daily_content_not_found` — 해당 날짜에 예약된 콘텐츠가 없으면 404를 반환한다

## 스케줄러 — tests/scheduler/ (실제 DB, 스크래퍼 mock)

### test_scheduler.py
- `test_daily_content_job_success` — 일일 잡이 승인된 콘텐츠 하나를 오늘 날짜(KST)로 예약(USED) 처리한다
- `test_daily_content_job_no_approved_raises` — 예약할 승인 콘텐츠가 없으면 NoApprovedContentError를 전파한다
- `test_weekly_scraping_job_inserts_all` — 주간 스크랩 잡이 reddit 밈과 명언을 수집해 RAW 상태로 저장한다
- `test_weekly_scraping_job_isolates_failures` — 한 스크래퍼가 실패해도 잡은 예외 없이 나머지 스크래퍼 결과를 저장한다

## 스키마 / 상태 전이 — tests/schema/ (순수 로직)

### test_content.py (파라미터라이즈, 12케이스)
- `test_valid_transitions` — 허용되는 상태 전이 요청은 검증을 통과한다
  - pending→approved, pending→rejected, raw/analyzed/approved/rejected→pending
- `test_invalid_transitions_raise` — 금지된 상태 전이 요청은 검증 에러가 발생한다
  - raw/analyzed→approved (PENDING이 아니면 승인 불가), raw/pending/approved/rejected→used (API로는 USED 전이 불가)

## 요금 / 사용량 추적 — tests/

### test_pricing.py (순수 로직)
- `test_compute_cost_known_model` — 단가가 등록된 모델은 토큰 수에 비례한 비용을 계산한다
- `test_compute_cost_unknown_model_returns_none` — 단가를 모르는 모델은 None을 반환한다
- `test_compute_cost_matches_dated_snapshot_name` — 날짜 스냅샷이 붙은 모델명도 기본 모델 단가에 매칭된다
- `test_compute_cost_free_tier_fully_covers_usage` — 무료 티어가 사용량을 전부 커버하면 비용은 0이다
- `test_compute_cost_free_tier_deducts_proportionally` — 무료 티어 초과분만 입력·출력 비율대로 과금된다
- `test_compute_cost_free_tier_scales_with_days` — 무료 티어 한도는 조회 기간(일수)에 비례해 늘어난다
- `test_compute_cost_free_tier_ignored_for_other_models` — 무료 티어는 해당 모델에만 적용되고 다른 모델에는 영향이 없다

### test_usage_tracking.py (실제 DB)
- `test_on_llm_end_records_usage` — LLM 응답의 usage_metadata가 token_usage 테이블에 실제로 기록된다
- `test_on_llm_end_skips_when_no_usage_metadata` — usage_metadata가 없는 LLM 응답은 기록하지 않는다
- `test_on_llm_end_skips_non_chat_generation` — chat 생성이 아닌 LLM 결과는 기록하지 않는다
- `test_on_llm_end_swallows_repository_errors` — 토큰 기록이 실패해도 예외를 전파하지 않고 LLM 응답 흐름을 막지 않는다
