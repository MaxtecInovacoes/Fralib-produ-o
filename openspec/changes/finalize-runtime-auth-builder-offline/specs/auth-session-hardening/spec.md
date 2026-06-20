## ADDED Requirements

### Requirement: TOTP-enabled users must satisfy second factor
FraLib auth SHALL require a valid TOTP code at login for users whose account has TOTP enabled.

#### Scenario: Enabled user logs in without TOTP
- **WHEN** a user with `totp_enabled=true` submits only email and password
- **THEN** the login endpoint rejects the session and reports that a second factor is required

#### Scenario: Enabled user logs in with valid TOTP
- **WHEN** a user with `totp_enabled=true` submits email, password and a valid current TOTP code
- **THEN** the login endpoint issues a session through the approved session mechanism

### Requirement: Browser sessions migrate to HttpOnly cookie with CSRF
FraLib SHALL migrate browser authentication from frontend-stored bearer tokens to an HttpOnly session cookie protected by CSRF for unsafe methods.

#### Scenario: Cookie session uses CSRF on mutation
- **WHEN** a browser request uses the session cookie for POST, PUT, PATCH or DELETE
- **THEN** the API requires a matching CSRF token from a readable CSRF cookie or header

#### Scenario: Bearer token compatibility remains during rollout
- **WHEN** an existing API client sends an Authorization bearer token during the migration window
- **THEN** the API continues to authenticate it until the frontend migration is complete and the compatibility path is explicitly removed

### Requirement: Auth migration is isolated from Builder publication fixes
FraLib SHALL keep 2FA and cookie migration as a separate implementation change from offline Builder publication hardening.

#### Scenario: Publication fix ships before auth migration
- **WHEN** the Builder offline contract fix is deployed
- **THEN** current login flows remain behaviorally compatible and auth hardening remains tracked by this OpenSpec capability
