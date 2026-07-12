# AI API 의존 테스트 명세

## 목적

현재 AI(LLM·이미지 생성) API 호출은 전부 mock으로 대체되어 있다. 이 문서는 **어떤 테스트가 AI API에 의존하는지**와 **mock을 실제 호출로 바꾸는 주입 지점(seam)**을 정리한 것으로, 추후 실제 AI API를 호출하는 live 테스트 티어를 구축할 때 기반 자료로 쓴다.

## AI API 의존 테스트 목록

### tests/analyzer/ — 텍스트 분석 (OpenAI chat)

| 테스트 | 의존 API | 현재 mock 지점 | live 전환 방법 |
|---|---|---|---|
| `test_daily_quote_analyzer.py::test_analyze_raw_content` | OpenAI (ChatOpenAI, structured output) | `analyzer._llm` 속성을 MagicMock + RunnableLambda로 교체 | `_llm` 교체 코드를 제거하면 실제 ChatOpenAI 호출 |
| `test_daily_quote_analyzer.py::test_reanalyze_content_field` | OpenAI (동적 create_model + structured output) | 동일 | 동일 |
| `test_meme_analyzer.py::test_analyze_raw_content` | OpenAI (멀티모달 — image_url 프롬프트 포함) | 동일 | 동일. 실제 접근 가능한 이미지 URL 필요 |
| `test_meme_analyzer.py::test_reanalyze_content_field` | OpenAI | 동일 | 동일 |

### tests/image_generator/test_diffusion_model.py — 이미지 생성 모델

| 테스트 | 의존 API | 현재 mock 지점 | live 전환 방법 |
|---|---|---|---|
| `test_nano_banana_create_image_parses_image_from_response` | Gemini (ChatGoogleGenerativeAI) | 모듈 레벨 `ChatGoogleGenerativeAI` patch + `_llm.ainvoke` mock | patch 제거 시 실제 Gemini 이미지 생성 |
| `test_nano_banana_reinforce_image_parses_image_from_response` | Gemini | 동일 | 동일 |
| `test_nano_banana_reinforce_image_raises_for_unsupported_format` | (호출 전 검증) | 동일 | AI 호출 전에 실패하므로 live 불필요 |
| `test_gpt_image2_create_image_parses_image_from_response` | OpenAI Images API (gpt-image-2) | 모듈 레벨 `AsyncOpenAI` patch + `images.generate` mock | patch 제거 시 실제 이미지 생성 (과금 큼) |
| `test_gpt_image2_reinforce_image_parses_image_from_response` | OpenAI Images API (edit) | `images.edit` mock | 동일 |
| `test_gpt_image2_reinforce_image_raises_for_unsupported_format` | (호출 전 검증) | 동일 | live 불필요 |
| `test_gpt_image2_create_image_raises_when_no_image_data` | (응답 파싱) | 동일 | live로 재현 불가한 에러 케이스 — mock 유지 |

### tests/image_generator/test_daily_quote_image_generator.py — 생성 파이프라인

| 테스트 | 의존 API | 현재 mock 지점 | live 전환 방법 |
|---|---|---|---|
| `test_generate_updates_image_url_and_status` | 이미지 모델 + S3 | 생성자 주입: `DailyQuoteImageGenerator(mock_model, mock_s3)` | 실제 `NanoBanana`/`GptImage2`와 `S3Client`를 생성자에 전달 |
| `test_regenerate_updates_image_url_and_status` | 이미지 모델 + S3 | 동일 | 동일 |

### tests/image_generator/test_factory.py — 배선 확인 (live 불필요)

| 테스트 | 비고 |
|---|---|
| `test_get_image_generator_with_nano_banana_model` 외 3개 | 클라이언트 생성만 patch하고 배선을 확인 — AI 호출 없음, live 티어 대상 아님 |

## 주입 seam 정리

live 전환 시 활용할 수 있는 주입 지점:

1. **`analyzer._llm` 속성** (`app/analyzer/daily_quote_analyzer.py`, `meme_analyzer.py`) — 생성자 주입이 아닌 속성 교체 방식. live 티어에서는 교체하지 않으면 됨. 필요 시 생성자 주입으로 리팩토링 여지 있음
2. **`DailyQuoteImageGenerator(model, s3_client)` 생성자** (`app/image_generator/daily_quote_image_generator.py`) — 가장 깨끗한 seam. 실제/가짜 모델을 자유롭게 조합 가능
3. **모듈 레벨 클라이언트 patch 지점** — `app.image_generator.diffusion_model.ChatGoogleGenerativeAI`, `AsyncOpenAI`, `app.image_generator.factory.S3Client`
4. **전역 `token_usage_handler`** (`app/usage/usage_tracking.py`) — `register_configure_hook`으로 전역 등록되므로, live LLM 호출 시 **실제 토큰 사용 기록이 발생**할 수 있음에 주의. `TokenUsageCallbackHandler(session_factory=...)`로 테스트 DB로 격리 가능

## 비-AI 외부 경계 (참고 — live AI 티어 대상 아님)

- **S3 (aioboto3)**: `tests/image_generator/test_s3_uploader.py` — AWS 자격증명 필요한 별도 live 대상
- **reddit (Playwright)**: `tests/scheduler/` 에서 `RedditClient` patch — 네트워크·차단 이슈로 비결정적
- **ZenQuotes**: `tests/client/test_zenquotes_client.py` — 무료 공개 API지만 응답 내용이 비결정적

## live 티어 구축 제안 (미구현)

- `@pytest.mark.ai_live` 마커 + pyproject `markers` 등록, 기본 실행에서 `-m "not ai_live"`로 deselect
- 필요 환경변수: 실제 `OPENAI_API_KEY`, `GEMINI_API_KEY` (현재 conftest는 가짜 키를 setdefault — live 실행 시 실제 키를 export하면 setdefault가 덮어쓰지 않음)
- 주의사항: 호출당 과금(특히 gpt-image-2), 응답 비결정성으로 인한 단언 완화 필요(정확한 텍스트 비교 대신 형식·필드 존재 검증), rate limit
