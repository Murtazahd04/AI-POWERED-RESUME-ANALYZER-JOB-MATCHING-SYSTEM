# Profile feature implementation plan

## Goal

Replace the disabled **Profile** item in the sidebar with a protected profile page where a signed-in user can review and update their account details.

## Proposed first-release scope

- Show the signed-in user's name, email address, account role, and account creation date.
- Let the user update their name and email address.
- Let the user change their password after confirming their current password.
- Keep role and account creation date read-only. The profile API must never allow a user to change their role.
- Do not add an avatar, phone number, public profile, or account deletion in this release; those fields and flows are not currently part of the user model.

## Implementation tasks

### 1. Backend profile API

- [x] Add a request schema for profile updates with optional name and email fields, length/format validation, and rejection of unknown fields. Require at least one field.
- [x] Add a password-change request schema that requires the current password and a valid new password. Reuse the registration password-strength rules where possible.
- [x] Add an authenticated profile update endpoint under `PATCH /api/auth/me`. Update only fields explicitly allowed by the request schema; do not accept `role`, `created_at`, password hash, or arbitrary database fields.
- [x] Normalize email addresses consistently with registration and login. Return a clear conflict response if another account already uses the requested email, including uniqueness races.
- [x] Add an authenticated `POST /api/auth/me/password` endpoint. Verify the current password before hashing and saving the new password; never return or log either password or its hash.
- [x] Return the sanitized updated `UserOut` after profile updates, preserving the existing response contract and never exposing `password_hash`.
- [x] Confirm token behavior: access tokens contain the user ID and are checked against the current user record on each request, but have no password-version/revocation mechanism. They remain valid until expiration after a password change; password change does not claim to log out existing sessions.

**Existing backend references:** [auth routes](../backend/app/routes/auth_routes.py), [schemas](../backend/app/schemas.py), [authentication dependency](../backend/app/deps.py), [auth route tests](../backend/tests/test_auth_routes.py).

### 2. Frontend profile page and navigation

- [x] Add a protected `/profile` route and render it inside the shared application layout.
- [x] Create a profile page that loads and displays the current user's account data, with distinct loading, success, and error states.
- [x] Add an edit form for name and email, with client-side required/length/email validation that complements (but does not replace) server validation.
- [x] Add a separate password-change form with current password, new password, and confirmation fields. Clear password fields after success and display server validation errors.
- [x] Add API client functions for profile update and password change; reuse the existing API client and error-message conventions.
- [x] On a successful profile update, update the shared auth context so the header avatar/initials and any other user UI reflect the saved name immediately.
- [x] Enable the Profile sidebar item by removing its `soon` state. Active-link styling and responsive styles are provided.
- [x] Make forms keyboard accessible, associate labels with inputs, disable duplicate submissions while saving, and provide clear success/error feedback.

**Existing frontend references:** [routes](../frontend/src/App.jsx), [sidebar and header](../frontend/src/components/Layout.jsx), [auth context](../frontend/src/context/AuthContext.jsx), [API endpoints](../frontend/src/api/endpoints.js), [registration form patterns](../frontend/src/pages/RegisterPage.jsx), [theme styles](../frontend/src/theme.css).

### 3. Verification and release

- [x] Add backend tests for successful profile updates, omitted fields, invalid input, duplicate email, unauthenticated access, password mismatch/current-password failure, password strength, and response redaction.
- [x] Add frontend tests for loading, successful save, API errors, password confirmation, password success/field clearing, and updated header initials.
- [x] Run the relevant backend tests and available frontend build/test commands; fix regressions introduced by the feature. The frontend has no lint script.
- [ ] Manually verify profile navigation, refresh/session restoration, edits, error feedback, and password change with a normal user and an admin account.
- [ ] Confirm that role remains read-only and that one user's requests cannot access or modify another user's account.

## Acceptance criteria

- An authenticated user can open Profile and see their own current account details.
- A user can save a valid name and/or email update; the page and shared header show the saved values without requiring logout.
- A user can change their password only after providing the correct current password and a valid new password.
- Invalid or conflicting changes produce understandable errors and do not partially update the account.
- Profile and password endpoints require authentication, cannot modify privileged fields, and do not expose password data.
- The Profile navigation item is active and usable rather than marked “soon”; all unrelated navigation behavior remains unchanged.

## Suggested implementation order

1. Finalize the request/response contract and backend validation.
2. Implement and test the authenticated backend endpoints.
3. Add frontend API methods and the profile page/forms.
4. Wire the protected route, shared user-state refresh, and sidebar navigation.
5. Run automated and manual verification against the acceptance criteria.
