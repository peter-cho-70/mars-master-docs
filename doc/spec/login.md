# 로그인 기능 구현 가이드
### 1단계: 로컬 계정 → 2단계: 네이버 · 구글 · 카카오 소셜 로그인

**대상 스택**: Next.js + TypeScript + Supabase (Auth/DB) + Vercel
**버전**: v0.1
**작성 원칙**: 1단계(로컬 계정)를 먼저 완전히 검증한 뒤, 2단계(소셜 로그인)를 계정 하나씩 순차 추가한다. 각 provider 연동 후 반드시 수동 테스트를 거치고 다음 단계로 넘어간다.

---

## 0. 전체 로드맵

| 단계 | 내용 | 비고 |
|---|---|---|
| 0 | 사전 준비 (Supabase 프로젝트, 환경변수, DB 스키마) | 모든 단계의 전제조건 |
| 1 | 로컬 계정 (이메일/비밀번호) 로그인 | Supabase Auth 기본 기능 |
| 2-A | 구글 로그인 | Supabase 네이티브 지원 |
| 2-B | 카카오 로그인 | Supabase 네이티브 지원, 단 이메일 스코프 제약 있음 |
| 2-C | 네이버 로그인 | **Supabase 미지원** → Custom OAuth 직접 구현 필요 |
| 3 | 계정 연동/충돌 정책, 세션 통합, 보안 점검 | 전체 마무리 |

> 중요: Supabase Auth는 Google과 Kakao는 소셜 로그인 provider로 기본 제공하지만, Naver는 공식 지원 목록에 없다. 이 부분이 이번 작업에서 가장 손이 많이 가는 부분이므로 네이버는 별도 절차(4장)로 분리했다.

---

## 1. 사전 준비 (모든 단계 공통)

### 1.1 Supabase 프로젝트 설정 확인
- Supabase 프로젝트 생성 (또는 기존 3-repo 공유 DB 프로젝트 사용 — FinanceHub와 동일한 원칙으로 Auth도 공유 Supabase 인스턴스를 쓸지, 프로젝트별로 분리할지 먼저 결정)
- `Authentication > URL Configuration`에서 `Site URL`, `Redirect URLs` 등록 (로컬 개발용 `http://localhost:3000/**`, 배포용 Vercel 도메인 `https://yourapp.vercel.app/**` 둘 다 추가)
- `Authentication > Providers`에서 Email 활성화 확인 (기본값 On)

### 1.2 환경변수 정리
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=       # 서버 전용, 클라이언트 노출 금지
```
네이버 커스텀 구현 시 추가로 필요:
```
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
NAVER_REDIRECT_URI=
```

### 1.3 DB 스키마 방향
- Supabase는 `auth.users`를 기본 인증 테이블로 자동 관리한다. 여기에 직접 컬럼을 추가하지 말고, `public.profiles` 테이블을 별도로 만들어 `id`를 `auth.users.id`에 FK로 연결하는 방식을 권장 (표준 패턴).
- `profiles` 컬럼 예시: `id (uuid, FK)`, `display_name`, `avatar_url`, `provider (local | google | kakao | naver)`, `created_at`
- Row Level Security(RLS) 정책을 처음부터 설정: 사용자는 본인 row만 read/update 가능하도록.

### 1.4 패키지 설치
```bash
npm install @supabase/supabase-js @supabase/ssr
```
`@supabase/ssr`는 Next.js App Router에서 서버/클라이언트 세션을 쿠키 기반으로 동기화하기 위해 필요.

---

## 2. 1단계: 로컬 계정(이메일/비밀번호) 로그인

### 2.1 목표
- 회원가입, 로그인, 로그아웃, 비밀번호 재설정, 이메일 인증까지 로컬 계정만으로 완결.
- 이후 소셜 로그인을 추가해도 세션 처리 로직이 그대로 재사용되도록 인증 레이어를 추상화.

### 2.2 Supabase 클라이언트 설정 (서버/클라이언트 분리)
- `lib/supabase/client.ts` : 브라우저용 클라이언트 (`createBrowserClient`)
- `lib/supabase/server.ts` : 서버 컴포넌트/라우트 핸들러용 클라이언트 (`createServerClient`, 쿠키 연동)
- `middleware.ts` : 모든 요청에서 세션 갱신 (`updateSession`) — 이게 없으면 서버에서 세션이 만료된 걸 못 감지함

### 2.3 회원가입/로그인 구현 순서
1. 회원가입 폼 → `supabase.auth.signUp({ email, password })`
2. 이메일 인증 메일 발송 확인 (Supabase 기본 템플릿 또는 커스텀 템플릿 — `Authentication > Email Templates`)
3. 로그인 폼 → `supabase.auth.signInWithPassword({ email, password })`
4. 로그아웃 → `supabase.auth.signOut()`
5. 비밀번호 재설정 → `resetPasswordForEmail()` → 재설정 페이지에서 `updateUser({ password })`
6. 로그인 성공 시 `profiles` 테이블에 row가 없으면 자동 생성하는 트리거(`on auth.users insert`)를 DB 함수로 걸어두면 이후 소셜 로그인 사용자와 동일한 방식으로 처리 가능

### 2.4 보호된 라우트 처리
- `middleware.ts`에서 세션 없으면 `/login`으로 리다이렉트하는 matcher 설정
- 서버 컴포넌트에서 `supabase.auth.getUser()`로 매번 실제 검증 (`getSession()`만 믿지 말 것 — 클라이언트에서 위조 가능한 값이므로 서버에서는 반드시 `getUser()`로 재검증)

### 2.5 1단계 완료 기준 (체크리스트)
- [ ] 회원가입 → 이메일 인증 → 로그인 전체 플로우 수동 테스트 완료
- [ ] 비밀번호 재설정 플로우 테스트 완료
- [ ] 잘못된 비밀번호/미인증 계정 로그인 시 에러 메시지 정상 표시
- [ ] 보호된 페이지 접근 시 미로그인 사용자가 정상적으로 리다이렉트됨
- [ ] `profiles` 테이블 자동 생성 트리거 동작 확인

---

## 3. 2단계-A/B: 구글 · 카카오 로그인 (Supabase 네이티브 지원)

### 3.1 공통 흐름
Supabase가 Google과 Kakao를 provider로 직접 지원하므로, 각 서비스 개발자 콘솔에서 앱 등록 → Supabase 대시보드에 client id/secret 입력 → 클라이언트에서 `signInWithOAuth({ provider })` 호출로 끝난다.

```ts
await supabase.auth.signInWithOAuth({
  provider: 'google', // 또는 'kakao'
  options: { redirectTo: `${origin}/auth/callback` }
})
```

콜백 라우트(`app/auth/callback/route.ts`)에서 인가 코드를 세션으로 교환:
```ts
const { searchParams } = new URL(request.url)
const code = searchParams.get('code')
if (code) {
  const supabase = createServerClient(...)
  await supabase.auth.exchangeCodeForSession(code)
}
```

### 3.2 구글 준비 절차
1. Google Cloud Console → 프로젝트 생성 → `OAuth 동의 화면` 설정 (외부/게시 상태로 전환해야 테스트 계정 외 사용자도 로그인 가능)
2. `사용자 인증 정보 > OAuth 클라이언트 ID` 생성 (유형: 웹 애플리케이션)
3. 승인된 리디렉션 URI에 Supabase 콜백 주소 등록: `https://[project-ref].supabase.co/auth/v1/callback`
4. 발급된 Client ID/Secret을 Supabase `Authentication > Providers > Google`에 입력

### 3.3 카카오 준비 절차
1. Kakao Developers 포털 → 애플리케이션 생성
2. `앱 설정 > 플랫폼`에서 REST API 키 확인 (= client_id)
3. `카카오 로그인 > 보안`에서 Client Secret 코드 발급 (= client_secret)
4. 리디렉션 URI에 Supabase 콜백 주소 등록
5. Supabase `Authentication > Providers > Kakao`에 client id/secret 입력
6. **주의**: Supabase의 카카오 연동은 `account_email`, `profile_image`, `profile_nickname` 동의항목을 자동으로 요청하는데, `account_email`은 카카오 비즈니스 인증 계정만 설정 가능한 항목이다. 개인/비즈니스 미인증 앱이면 로그인 시 이메일 동의 단계에서 막힐 수 있으니, 먼저 Kakao Developers에서 비즈니스 앱 전환 여부를 확인해야 한다.

### 3.4 완료 기준
- [ ] 구글 로그인 → 콜백 → 세션 생성 → `profiles` row 자동 생성 확인
- [ ] 카카오 로그인 동일하게 확인 (이메일 동의 이슈 발생 여부 별도 체크)
- [ ] 동일 브라우저에서 로컬 계정 로그아웃 후 소셜 로그인 전환이 매끄러운지 확인

---

## 4. 2단계-C: 네이버 로그인 (Supabase 미지원 — 직접 구현)

### 4.1 왜 별도 처리가 필요한가
Supabase Auth의 공식 provider 목록에 네이버가 없다. 따라서 두 가지 경로 중 하나를 선택해야 한다.

- **경로 A (권장, 표준 OAuth 방식)**: Supabase의 "Custom OAuth/OIDC Provider" 기능을 사용해 네이버를 OIDC 호환 provider로 등록. 단, 네이버가 완전한 OIDC 스펙을 지원하는지 사전에 검증 필요 (네이버는 OAuth 2.0 기반이며 OIDC id_token을 표준 방식으로 안 주는 경우가 있어, 이 부분은 반드시 네이버 개발자 문서로 재확인해야 함).
- **경로 B (직접 구현, 확실히 동작)**: 네이버 OAuth를 앱에서 직접 처리한 뒤, 검증된 네이버 사용자 정보를 가지고 Supabase의 Admin API(`auth.admin.createUser` / `generateLink`)로 세션을 발급하거나, 커스텀 JWT를 발급해 자체 세션 체계를 병행 운영.

이번 프로젝트는 "확실히 동작하는 것"이 우선이므로 **경로 B**를 기본안으로 하고, 경로 A는 선택적 개선 과제로 남겨둔다.

### 4.2 네이버 준비 절차
1. [네이버 개발자센터](https://developers.naver.com)에서 애플리케이션 등록
2. 사용 API에 "네아로(네이버 아이디로 로그인)" 추가
3. 서비스 URL, Callback URL 등록 (`https://yourapp.com/api/auth/naver/callback`)
4. Client ID / Client Secret 발급받아 환경변수에 저장

### 4.3 구현 절차 (경로 B, 개념 흐름)
1. `/api/auth/naver/login` : 네이버 인가 URL로 리다이렉트 (`https://nid.naver.com/oauth2.0/authorize?...`)
2. `/api/auth/naver/callback` :
   - 인가 코드 수신 → 네이버 토큰 엔드포인트(`https://nid.naver.com/oauth2.0/token`)에 code 교환 요청 → access_token 수신
   - access_token으로 네이버 프로필 API(`https://openapi.naver.com/v1/nid/me`) 호출 → 이메일, 닉네임 등 획득
   - 해당 이메일로 Supabase에 사용자가 있는지 조회 (`auth.admin.listUsers` 또는 `profiles` 테이블 조회)
   - 없으면 `auth.admin.createUser({ email, email_confirm: true, user_metadata: { provider: 'naver' } })`로 생성
   - 있으면 기존 계정 사용
   - Supabase의 `generateLink` (magic link 타입) 또는 세션 토큰 직접 발급 방식으로 클라이언트에 세션 쿠키 심기
3. 이 과정은 반드시 **서버 사이드**(Route Handler)에서만 처리 — `service_role` 키가 클라이언트에 노출되면 안 됨

### 4.4 완료 기준
- [ ] 네이버 인가 → 콜백 → 프로필 조회까지 수동 `curl` 테스트로 먼저 검증 (코드 작성 전에 raw HTTP 호출로 응답 구조 확인 — Master 프로젝트에서 Videohub를 `nc`로 먼저 찔러본 것과 동일한 원칙)
- [ ] 신규/기존 사용자 분기 로직 검증
- [ ] Supabase 세션이 정상 발급되어 로컬/구글/카카오와 동일한 미들웨어 보호 로직을 통과하는지 확인

---

## 5. 계정 연동 및 충돌 정책 (3단계)

여러 provider가 도입되면 "같은 이메일로 다른 방식으로 로그인"하는 상황이 반드시 발생한다. 정책을 미리 정해야 한다.

- **정책 A (자동 병합)**: 이메일이 같으면 자동으로 같은 계정으로 취급. 구현은 간단하지만, 이메일 소유권이 검증되지 않은 provider가 있으면 계정 탈취 위험이 생길 수 있음.
- **정책 B (수동 연동)**: 이메일이 같아도 별도 계정으로 만들고, 로그인 후 사용자가 "계정 연동" 버튼을 눌러야 병합. 안전하지만 UX 단계가 늘어남.
- 권장: 이메일 인증이 확실한 provider(구글, 인증된 로컬 계정)는 정책 A, 이메일 동의가 불확실한 카카오/네이버는 정책 B를 섞어 적용하는 것을 검토.

이 정책은 `profiles` 테이블의 `provider` 컬럼과 별도의 `linked_accounts` 테이블(1:N)로 관리하는 구조를 권장.

---

## 6. 보안 체크리스트 (배포 전 필수)

- [ ] `service_role` 키가 클라이언트 번들에 절대 포함되지 않았는지 확인 (`NEXT_PUBLIC_` 접두사 오사용 주의)
- [ ] 모든 서버 컴포넌트/API 라우트에서 `getUser()`로 재검증 (`getSession()` 신뢰 금지)
- [ ] Redirect URL 허용 목록이 와일드카드로 과도하게 열려있지 않은지 확인
- [ ] RLS 정책이 모든 사용자 데이터 테이블에 적용되어 있는지 확인 (특히 `profiles`, 향후 결제/구독 테이블)
- [ ] 네이버 커스텀 구현 부분은 CSRF 방지를 위한 `state` 파라미터 검증 로직이 들어갔는지 확인
- [ ] 비밀번호 재설정/이메일 변경 시 재인증(reauthentication) 요구 여부 결정

---

## 7. 테스트 절차 요약

1. 로컬 계정 전체 플로우 (회원가입~비밀번호 재설정) — 단독 테스트
2. 구글 로그인 — 단독 테스트 후 로컬 계정과의 상호작용 확인
3. 카카오 로그인 — 이메일 동의 이슈 여부 먼저 확인 후 진행
4. 네이버 로그인 — raw HTTP 호출로 API 응답 구조 먼저 검증 → 코드 구현 → 세션 발급 확인
5. 4개 provider 전체를 한 사용자가 이메일로 넘나들며 로그인했을 때의 연동/충돌 정책 동작 확인
6. 미들웨어 보호 라우트가 4개 provider 모두에 대해 동일하게 작동하는지 확인

---

## 8. 향후 확장 후보 (이번 범위 밖)

- 네이버 연동을 경로 A(Custom OIDC)로 전환해 유지보수 부담 축소
- 전화번호 기반 로그인 (Supabase Phone Auth)
- 2단계 인증(TOTP)
- 계정 삭제 시 GDPR/개인정보보호법 대응 절차
