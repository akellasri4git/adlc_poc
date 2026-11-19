# ADLC-102: Login service design

## Description
As a security architect, I want only the design for a login service, so that the team can review the approach before anyone writes code.

No implementation is needed for this story.

## Acceptance Criteria
- Users log in with email and password
- Passwords are stored as salted hashes, never in plain text
- A successful login returns a session token that expires after 30 minutes
- The account is locked for 15 minutes after 5 failed attempts
- All login attempts are written to an audit log
