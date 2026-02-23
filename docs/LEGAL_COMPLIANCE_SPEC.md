# SignSimple.io Legal Compliance Specification
## Certificate of Completion & Audit Trail Implementation

**Version:** 1.0.0
**Last Updated:** 2026-01-10
**Status:** DRAFT - Requires Legal Review
**Applicable Laws:** ESIGN Act (US), UETA (US), eIDAS (EU), GDPR (EU)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Certificate of Completion PDF Template](#2-certificate-of-completion-pdf-template)
3. [SHA-256 Implementation](#3-sha-256-implementation)
4. [Audit Trail Database Schema](#4-audit-trail-database-schema)
5. [Audit Events Specification](#5-audit-events-specification)
6. [Timestamp Requirements](#6-timestamp-requirements)
7. [IP Address Capture](#7-ip-address-capture)
8. [Consent Flow](#8-consent-flow)
9. [Legal Disclaimers](#9-legal-disclaimers)
10. [eIDAS Compliance (EU)](#10-eidas-compliance-eu)
11. [Certificate Generation Code](#11-certificate-generation-code)
12. [Implementation Checklist](#12-implementation-checklist)

---

## 1. Executive Summary

This specification defines the technical and legal requirements for generating legally-binding Certificates of Completion for electronic signatures on SignSimple.io. The certificate serves as the "paper trail" required under:

- **ESIGN Act** (Electronic Signatures in Global and National Commerce Act, 15 U.S.C. 7001-7031)
- **UETA** (Uniform Electronic Transactions Act, adopted by 47+ US states)
- **eIDAS** (EU Regulation 910/2014 on electronic identification and trust services)

### What Makes a Signature Legally Binding?

Under ESIGN/UETA, an electronic signature is legally binding when:
1. **Intent to sign** - The signer intended to sign the document
2. **Consent to do business electronically** - Explicit consent was given
3. **Association of signature with record** - The signature is logically associated with the document
4. **Record retention** - The signed record can be accurately reproduced

The Certificate of Completion provides evidence of all four elements.

---

## 2. Certificate of Completion PDF Template

### 2.1 Layout Specification

```
+------------------------------------------------------------------+
|                    [SIGNSIMPLE.IO LOGO]                          |
|                                                                  |
|              CERTIFICATE OF COMPLETION                           |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Document Title: [DOCUMENT_NAME]                                 |
|  Document ID: [ENVELOPE_UUID]                                    |
|  Status: COMPLETED                                               |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  DOCUMENT INTEGRITY                                              |
|  ----------------------------------------------------------------|
|  Original Document Hash (SHA-256):                               |
|  [64-CHARACTER HASH - UPPERCASE]                                 |
|                                                                  |
|  Signed Document Hash (SHA-256):                                 |
|  [64-CHARACTER HASH - UPPERCASE]                                 |
|                                                                  |
|  Certificate Generated: [TIMESTAMP UTC]                          |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  SIGNING PARTIES                                                 |
|  ----------------------------------------------------------------|
|                                                                  |
|  Signer 1: [FULL_NAME]                                          |
|  Email: [EMAIL_ADDRESS]                                          |
|  Role: [SIGNER/APPROVER/CC]                                      |
|  Signature Status: SIGNED                                        |
|  Signed At: [TIMESTAMP UTC]                                      |
|  IP Address: [IP_ADDRESS]                                        |
|  Device: [BROWSER/OS SUMMARY]                                    |
|  Consent Given: Yes, at [CONSENT_TIMESTAMP UTC]                  |
|  ----------------------------------------------------------------|
|                                                                  |
|  Signer 2: [FULL_NAME]                                          |
|  [...repeat for each signer...]                                  |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  AUDIT TRAIL                                                     |
|  ----------------------------------------------------------------|
|  [TIMESTAMP] - Document created by [EMAIL]                       |
|  [TIMESTAMP] - Document sent to [EMAIL]                          |
|  [TIMESTAMP] - Email delivered to [EMAIL]                        |
|  [TIMESTAMP] - Document viewed by [EMAIL] from [IP]              |
|  [TIMESTAMP] - Signature completed by [EMAIL] from [IP]          |
|  [TIMESTAMP] - All signatures complete                           |
|  [TIMESTAMP] - Certificate generated                             |
|  [...chronological list of all events...]                        |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  LEGAL NOTICE                                                    |
|  ----------------------------------------------------------------|
|  This document was signed electronically using SignSimple.io.    |
|  Electronic signatures are legally binding under the ESIGN Act   |
|  (15 U.S.C. 7001 et seq.), UETA, and eIDAS Regulation            |
|  (EU 910/2014). All signers consented to use electronic          |
|  signatures before signing.                                      |
|                                                                  |
|  This certificate is tamper-evident. Any modification to the     |
|  signed document will invalidate the document hash above.        |
|                                                                  |
|  To verify this document: https://signsimple.io/verify/[UUID]    |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Certificate ID: [CERTIFICATE_UUID]                              |
|  Generated: [GENERATION_TIMESTAMP UTC]                           |
|  SignSimple.io - https://signsimple.io                          |
|                                                                  |
+------------------------------------------------------------------+
```

### 2.2 Required Fields

| Field | Source | Format | Required |
|-------|--------|--------|----------|
| Document Title | User input | String, max 255 chars | Yes |
| Document ID | System generated | UUID v4 | Yes |
| Original Document Hash | Computed at upload | SHA-256, 64 hex chars | Yes |
| Signed Document Hash | Computed at completion | SHA-256, 64 hex chars | Yes |
| Signer Full Name | User input | String | Yes |
| Signer Email | User input | Valid email | Yes |
| Signer Role | System | Enum: SIGNER, APPROVER, CC | Yes |
| Signature Timestamp | System | ISO 8601 UTC | Yes |
| Signer IP Address | Captured | IPv4 or IPv6 | Yes |
| Device/Browser | User Agent | Parsed string | Yes |
| Consent Timestamp | System | ISO 8601 UTC | Yes |
| Audit Events | System | Chronological list | Yes |
| Certificate ID | System generated | UUID v4 | Yes |
| Generation Timestamp | System | ISO 8601 UTC | Yes |

### 2.3 Tamper-Evidence Mechanisms

1. **Document Hash Verification**
   - The SHA-256 hash of the signed document is immutable
   - Any change to the document content will produce a different hash
   - Users can independently verify by computing the hash themselves

2. **Certificate Hash Chain**
   - The certificate itself should include a hash of all audit trail data
   - This prevents retroactive modification of the audit trail

3. **Digital Signature on Certificate (Optional Enhancement)**
   - Sign the certificate PDF with a code-signing certificate
   - Provides cryptographic proof of authenticity

4. **Verification URL**
   - Provide a unique URL where the certificate can be verified online
   - Store the certificate hash server-side for comparison

### 2.4 Example Certificate (Text Representation)

```
================================================================================
                              SIGNSIMPLE.IO
                       CERTIFICATE OF COMPLETION
================================================================================

Document Title: Employment Agreement - John Smith
Document ID: 8f14e45f-ceea-367a-a714-3c5e4c5f7b29
Status: COMPLETED

--------------------------------------------------------------------------------
                           DOCUMENT INTEGRITY
--------------------------------------------------------------------------------

Original Document Hash (SHA-256):
A3B2C1D4E5F6789012345678901234567890ABCDEF1234567890ABCDEF123456

Signed Document Hash (SHA-256):
B4C3D2E1F6789012345678901234567890ABCDEF5678901234567890ABCDEF78

Certificate Generated: 2026-01-10T15:30:45.123Z

--------------------------------------------------------------------------------
                            SIGNING PARTIES
--------------------------------------------------------------------------------

Signer 1: John Smith
  Email: john.smith@example.com
  Role: SIGNER
  Signature Status: SIGNED
  Signed At: 2026-01-10T14:22:33.456Z
  IP Address: 192.168.1.100
  Device: Chrome 120.0 on Windows 11
  Consent Given: Yes, at 2026-01-10T14:20:15.789Z

--------------------------------------------------------------------------------

Signer 2: Jane Doe (HR Manager)
  Email: jane.doe@company.com
  Role: SIGNER
  Signature Status: SIGNED
  Signed At: 2026-01-10T15:15:22.789Z
  IP Address: 10.0.0.50
  Device: Safari 17.2 on macOS Sonoma
  Consent Given: Yes, at 2026-01-10T15:12:05.123Z

--------------------------------------------------------------------------------
                             AUDIT TRAIL
--------------------------------------------------------------------------------

2026-01-10T10:00:00.000Z - Document created by hr@company.com
2026-01-10T10:00:05.123Z - Document sent to john.smith@example.com
2026-01-10T10:00:05.456Z - Document sent to jane.doe@company.com
2026-01-10T10:00:12.789Z - Email delivered to john.smith@example.com
2026-01-10T10:00:14.012Z - Email delivered to jane.doe@company.com
2026-01-10T14:20:00.345Z - Document viewed by john.smith@example.com (192.168.1.100)
2026-01-10T14:20:15.789Z - ESIGN consent given by john.smith@example.com
2026-01-10T14:22:33.456Z - Signature completed by john.smith@example.com
2026-01-10T15:12:00.678Z - Document viewed by jane.doe@company.com (10.0.0.50)
2026-01-10T15:12:05.123Z - ESIGN consent given by jane.doe@company.com
2026-01-10T15:15:22.789Z - Signature completed by jane.doe@company.com
2026-01-10T15:15:22.800Z - All signatures complete - Document COMPLETED
2026-01-10T15:30:45.123Z - Certificate of Completion generated

--------------------------------------------------------------------------------
                            LEGAL NOTICE
--------------------------------------------------------------------------------

This document was signed electronically using SignSimple.io. Electronic
signatures are legally binding under the ESIGN Act (15 U.S.C. 7001 et seq.),
UETA, and eIDAS Regulation (EU 910/2014). All signers consented to use
electronic signatures before signing.

This certificate is tamper-evident. Any modification to the signed document
will invalidate the document hash above.

To verify this document: https://signsimple.io/verify/8f14e45f-ceea-367a-a714-3c5e4c5f7b29

--------------------------------------------------------------------------------

Certificate ID: c9d8e7f6-5432-1098-7654-fedcba098765
Generated: 2026-01-10T15:30:45.123Z
SignSimple.io - https://signsimple.io

================================================================================
```

---

## 3. SHA-256 Implementation

### 3.1 When to Generate Hashes

| Event | Hash Type | Purpose |
|-------|-----------|---------|
| Document Upload | Original Document Hash | Proves the original document has not been modified |
| Each Signature Applied | Intermediate Hash | Creates hash chain for multi-signer documents |
| All Signatures Complete | Final Signed Document Hash | Proves final document integrity |
| Certificate Generation | Certificate Hash | Proves certificate has not been modified |

### 3.2 Hash Generation Workflow

```
1. UPLOAD
   OriginalHash = SHA256(original_pdf_bytes)
   Store: document.original_hash = OriginalHash

2. EACH SIGNATURE
   SignatureData = {
     signer_id,
     timestamp,
     signature_image_base64,
     position: {page, x, y}
   }
   PreviousHash = document.current_hash || document.original_hash
   NewHash = SHA256(PreviousHash + JSON.stringify(SignatureData))
   Store: document.current_hash = NewHash
   Store: audit_event.hash_before = PreviousHash
   Store: audit_event.hash_after = NewHash

3. COMPLETION
   FinalHash = SHA256(signed_pdf_bytes)
   Store: document.final_hash = FinalHash

4. CERTIFICATE
   CertificateData = {
     document_id,
     original_hash,
     final_hash,
     signers: [...],
     audit_trail: [...]
   }
   CertHash = SHA256(JSON.stringify(CertificateData))
   Store: certificate.hash = CertHash
```

### 3.3 Hash Display Format

```
Display Format: UPPERCASE, 64 characters, no spaces
Example: A3B2C1D4E5F6789012345678901234567890ABCDEF1234567890ABCDEF123456

For readability in UI, may break into groups:
A3B2C1D4 E5F67890 12345678 90123456 7890ABCD EF123456 7890ABCD EF123456
```

### 3.4 Hash Chain for Multi-Signer Documents

```
Document Created:
  H0 = SHA256(original_document)

Signer 1 Signs:
  H1 = SHA256(H0 || signature_data_1)

Signer 2 Signs:
  H2 = SHA256(H1 || signature_data_2)

Signer 3 Signs:
  H3 = SHA256(H2 || signature_data_3)

Final Hash:
  H_final = SHA256(completed_pdf_with_all_signatures)
```

This creates an immutable chain where each signature depends on all previous signatures.

### 3.5 JavaScript Implementation

```javascript
// hash-utils.js

/**
 * Generate SHA-256 hash of a file or buffer
 * Works in both Node.js and browser environments
 */

// Browser implementation using Web Crypto API
async function sha256Browser(data) {
  let buffer;

  if (data instanceof File) {
    buffer = await data.arrayBuffer();
  } else if (data instanceof ArrayBuffer) {
    buffer = data;
  } else if (typeof data === 'string') {
    buffer = new TextEncoder().encode(data);
  } else if (data instanceof Uint8Array) {
    buffer = data.buffer;
  } else {
    throw new Error('Unsupported data type for hashing');
  }

  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

  return hashHex.toUpperCase();
}

// Node.js implementation
const crypto = require('crypto');
const fs = require('fs');

function sha256Node(data) {
  const hash = crypto.createHash('sha256');

  if (Buffer.isBuffer(data)) {
    hash.update(data);
  } else if (typeof data === 'string') {
    hash.update(data, 'utf8');
  } else {
    throw new Error('Unsupported data type for hashing');
  }

  return hash.digest('hex').toUpperCase();
}

async function sha256File(filePath) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256');
    const stream = fs.createReadStream(filePath);

    stream.on('data', (chunk) => hash.update(chunk));
    stream.on('end', () => resolve(hash.digest('hex').toUpperCase()));
    stream.on('error', reject);
  });
}

/**
 * Generate hash chain for multi-signer documents
 */
function generateHashChain(previousHash, signatureData) {
  const dataToHash = previousHash + JSON.stringify(signatureData);
  return sha256Node(dataToHash);
}

/**
 * Verify document integrity
 */
async function verifyDocumentHash(documentPath, expectedHash) {
  const actualHash = await sha256File(documentPath);
  return {
    valid: actualHash === expectedHash.toUpperCase(),
    actualHash,
    expectedHash: expectedHash.toUpperCase()
  };
}

/**
 * Generate certificate hash for tamper-evidence
 */
function generateCertificateHash(certificateData) {
  // Sort keys for consistent hashing
  const sortedData = JSON.stringify(certificateData, Object.keys(certificateData).sort());
  return sha256Node(sortedData);
}

module.exports = {
  sha256Browser,
  sha256Node,
  sha256File,
  generateHashChain,
  verifyDocumentHash,
  generateCertificateHash
};
```

---

## 4. Audit Trail Database Schema

### 4.1 Core Tables

```sql
-- Documents table
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    -- Status: draft, sent, in_progress, completed, voided, expired

    -- Document hashes
    original_hash VARCHAR(64) NOT NULL,
    current_hash VARCHAR(64),
    final_hash VARCHAR(64),

    -- Metadata
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    voided_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,

    -- File storage
    original_file_path VARCHAR(500) NOT NULL,
    signed_file_path VARCHAR(500),
    certificate_path VARCHAR(500),

    -- Settings
    reminder_frequency_days INTEGER DEFAULT 3,
    expiration_days INTEGER DEFAULT 30,

    CONSTRAINT valid_status CHECK (status IN (
        'draft', 'sent', 'in_progress', 'completed', 'voided', 'expired'
    ))
);

-- Signers table
CREATE TABLE signers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Signer info
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'signer',
    -- Role: signer, approver, cc, witness
    signing_order INTEGER NOT NULL DEFAULT 1,

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- Status: pending, sent, delivered, viewed, signed, declined

    -- Consent tracking (CRITICAL for ESIGN compliance)
    consent_given BOOLEAN DEFAULT FALSE,
    consent_timestamp TIMESTAMP WITH TIME ZONE,
    consent_ip_address INET,
    consent_user_agent TEXT,

    -- Signature tracking
    signed_at TIMESTAMP WITH TIME ZONE,
    signature_ip_address INET,
    signature_user_agent TEXT,
    signature_data JSONB, -- Contains signature image, position, etc.

    -- Access tracking
    access_token VARCHAR(255) UNIQUE NOT NULL,
    first_viewed_at TIMESTAMP WITH TIME ZONE,
    last_viewed_at TIMESTAMP WITH TIME ZONE,
    view_count INTEGER DEFAULT 0,

    -- Decline info
    declined_at TIMESTAMP WITH TIME ZONE,
    decline_reason TEXT,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_role CHECK (role IN ('signer', 'approver', 'cc', 'witness')),
    CONSTRAINT valid_status CHECK (status IN (
        'pending', 'sent', 'delivered', 'viewed', 'signed', 'declined'
    ))
);

-- Audit Events table (THE CORE OF LEGAL COMPLIANCE)
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    signer_id UUID REFERENCES signers(id) ON DELETE SET NULL,

    -- Event details
    event_type VARCHAR(50) NOT NULL,
    event_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Actor information
    actor_type VARCHAR(20) NOT NULL, -- 'user', 'signer', 'system'
    actor_id UUID,
    actor_email VARCHAR(255),

    -- Network/Device information
    ip_address INET,
    user_agent TEXT,
    device_type VARCHAR(50), -- 'desktop', 'mobile', 'tablet'
    browser VARCHAR(100),
    os VARCHAR(100),

    -- Geolocation (optional, requires IP lookup service)
    geo_country VARCHAR(100),
    geo_region VARCHAR(100),
    geo_city VARCHAR(100),

    -- Hash chain
    previous_hash VARCHAR(64),
    current_hash VARCHAR(64),

    -- Additional event data
    event_data JSONB,

    -- Indexing
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_event_type CHECK (event_type IN (
        'document.created',
        'document.uploaded',
        'document.sent',
        'document.viewed',
        'document.downloaded',
        'document.completed',
        'document.voided',
        'document.expired',
        'email.sent',
        'email.delivered',
        'email.opened',
        'email.bounced',
        'signer.added',
        'signer.removed',
        'signer.reminded',
        'consent.given',
        'consent.withdrawn',
        'signature.started',
        'signature.completed',
        'signature.declined',
        'certificate.generated',
        'certificate.downloaded',
        'verification.success',
        'verification.failed'
    )),
    CONSTRAINT valid_actor_type CHECK (actor_type IN ('user', 'signer', 'system'))
);

-- Certificates table
CREATE TABLE certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Certificate data
    certificate_hash VARCHAR(64) NOT NULL,
    certificate_data JSONB NOT NULL,
    pdf_path VARCHAR(500) NOT NULL,

    -- Generation info
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    generated_by VARCHAR(20) NOT NULL DEFAULT 'system',

    -- Verification
    verification_url VARCHAR(500) NOT NULL,
    verified_count INTEGER DEFAULT 0,
    last_verified_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance
CREATE INDEX idx_audit_events_document ON audit_events(document_id);
CREATE INDEX idx_audit_events_timestamp ON audit_events(event_timestamp);
CREATE INDEX idx_audit_events_type ON audit_events(event_type);
CREATE INDEX idx_signers_document ON signers(document_id);
CREATE INDEX idx_signers_email ON signers(email);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_created_by ON documents(created_by);
```

### 4.2 Retention Requirements

| Data Type | Minimum Retention | Recommended | Legal Basis |
|-----------|-------------------|-------------|-------------|
| Signed Documents | 7 years | 10 years | ESIGN, SOX, various state laws |
| Audit Trail | 7 years | 10 years | ESIGN, eIDAS |
| Certificates | 7 years | 10 years | Same as documents |
| Consent Records | 7 years | 10 years | ESIGN, GDPR |
| IP Addresses | 7 years | See GDPR notes | May require anonymization under GDPR |

**GDPR Considerations:**
- IP addresses are personal data under GDPR
- Consider anonymizing after document expires + 30 days if no legal hold
- Retain full IP for active documents and those under legal hold

### 4.3 Query Patterns for Certificate Generation

```sql
-- Get all data needed for certificate generation
WITH document_info AS (
    SELECT
        d.id,
        d.title,
        d.status,
        d.original_hash,
        d.final_hash,
        d.created_at,
        d.completed_at,
        d.original_file_path,
        d.signed_file_path,
        u.email as created_by_email,
        u.name as created_by_name
    FROM documents d
    JOIN users u ON d.created_by = u.id
    WHERE d.id = :document_id
),
signers_info AS (
    SELECT
        s.id,
        s.email,
        s.name,
        s.role,
        s.signing_order,
        s.status,
        s.consent_given,
        s.consent_timestamp,
        s.consent_ip_address,
        s.consent_user_agent,
        s.signed_at,
        s.signature_ip_address,
        s.signature_user_agent
    FROM signers s
    WHERE s.document_id = :document_id
    ORDER BY s.signing_order
),
audit_info AS (
    SELECT
        ae.event_type,
        ae.event_timestamp,
        ae.actor_email,
        ae.ip_address,
        ae.browser,
        ae.os,
        ae.event_data
    FROM audit_events ae
    WHERE ae.document_id = :document_id
    ORDER BY ae.event_timestamp ASC
)
SELECT
    (SELECT row_to_json(d) FROM document_info d) as document,
    (SELECT json_agg(s) FROM signers_info s) as signers,
    (SELECT json_agg(a) FROM audit_info a) as audit_trail;
```

---

## 5. Audit Events Specification

### 5.1 Complete Event Catalog

#### Document Lifecycle Events

| Event | Description | Required Data |
|-------|-------------|---------------|
| `document.created` | Document envelope created | document_id, title, created_by, timestamp |
| `document.uploaded` | PDF file uploaded | document_id, file_hash, file_size, file_name |
| `document.sent` | Document sent for signing | document_id, recipients[], timestamp |
| `document.viewed` | Document viewed by signer | document_id, signer_id, ip, user_agent |
| `document.downloaded` | Signed document downloaded | document_id, downloaded_by, ip |
| `document.completed` | All signatures collected | document_id, final_hash, timestamp |
| `document.voided` | Document cancelled | document_id, voided_by, reason, timestamp |
| `document.expired` | Document expired without completion | document_id, expiration_timestamp |

#### Email Events

| Event | Description | Required Data |
|-------|-------------|---------------|
| `email.sent` | Signing request email sent | document_id, signer_id, recipient_email, message_id |
| `email.delivered` | Email delivered to server | document_id, signer_id, message_id, timestamp |
| `email.opened` | Email opened (tracking pixel) | document_id, signer_id, ip, user_agent, timestamp |
| `email.bounced` | Email bounced | document_id, signer_id, bounce_type, bounce_message |

#### Signer Events

| Event | Description | Required Data |
|-------|-------------|---------------|
| `signer.added` | Signer added to document | document_id, signer_id, email, name, role |
| `signer.removed` | Signer removed from document | document_id, signer_id, removed_by |
| `signer.reminded` | Reminder sent to signer | document_id, signer_id, reminder_number |

#### Consent Events (CRITICAL for ESIGN)

| Event | Description | Required Data |
|-------|-------------|---------------|
| `consent.given` | ESIGN consent accepted | signer_id, ip, user_agent, consent_version, timestamp |
| `consent.withdrawn` | Consent withdrawn | signer_id, ip, timestamp |

#### Signature Events

| Event | Description | Required Data |
|-------|-------------|---------------|
| `signature.started` | Signer began signing process | document_id, signer_id, ip, user_agent, timestamp |
| `signature.completed` | Signature successfully applied | document_id, signer_id, signature_hash, ip, timestamp |
| `signature.declined` | Signer declined to sign | document_id, signer_id, decline_reason, ip, timestamp |

#### Certificate Events

| Event | Description | Required Data |
|-------|-------------|---------------|
| `certificate.generated` | Certificate PDF created | document_id, certificate_id, certificate_hash |
| `certificate.downloaded` | Certificate downloaded | document_id, certificate_id, downloaded_by, ip |

#### Verification Events

| Event | Description | Required Data |
|-------|-------------|---------------|
| `verification.success` | Document verified successfully | document_id, verified_hash, verifier_ip |
| `verification.failed` | Verification failed (hash mismatch) | document_id, expected_hash, actual_hash, verifier_ip |

### 5.2 Event Data Schema

```typescript
interface AuditEvent {
  id: string;                    // UUID
  document_id: string;           // UUID
  signer_id?: string;            // UUID, if applicable

  event_type: EventType;
  event_timestamp: string;       // ISO 8601 UTC

  actor: {
    type: 'user' | 'signer' | 'system';
    id?: string;
    email?: string;
  };

  network: {
    ip_address: string;
    user_agent: string;
    device_type?: 'desktop' | 'mobile' | 'tablet';
    browser?: string;
    browser_version?: string;
    os?: string;
    os_version?: string;
  };

  geo?: {
    country?: string;
    country_code?: string;
    region?: string;
    city?: string;
    timezone?: string;
  };

  hash_chain?: {
    previous_hash: string;
    current_hash: string;
  };

  event_data: Record<string, any>;  // Event-specific data
}
```

### 5.3 Event Data Examples

```json
// document.created
{
  "event_type": "document.created",
  "event_data": {
    "title": "Employment Agreement",
    "page_count": 5,
    "file_size_bytes": 245678,
    "signers_count": 2
  }
}

// consent.given
{
  "event_type": "consent.given",
  "event_data": {
    "consent_version": "1.2",
    "consent_text_hash": "ABC123...",
    "disclosure_acknowledged": true,
    "hardware_software_requirements_acknowledged": true,
    "right_to_paper_copy_acknowledged": true
  }
}

// signature.completed
{
  "event_type": "signature.completed",
  "event_data": {
    "signature_type": "draw",  // draw, type, upload
    "signature_hash": "DEF456...",
    "fields_signed": [
      {"field_id": "sig1", "page": 3, "x": 100, "y": 500},
      {"field_id": "initial1", "page": 1, "x": 450, "y": 700}
    ],
    "time_spent_seconds": 45
  }
}
```

---

## 6. Timestamp Requirements

### 6.1 UTC Format Specification

All timestamps MUST be stored and displayed in ISO 8601 format with UTC timezone:

```
Format: YYYY-MM-DDTHH:mm:ss.sssZ

Examples:
2026-01-10T15:30:45.123Z
2026-01-10T00:00:00.000Z

Components:
- YYYY: 4-digit year
- MM: 2-digit month (01-12)
- DD: 2-digit day (01-31)
- T: Date/time separator
- HH: 2-digit hour (00-23)
- mm: 2-digit minute (00-59)
- ss: 2-digit second (00-59)
- sss: 3-digit millisecond (000-999)
- Z: UTC timezone indicator
```

### 6.2 Timestamp Storage Rules

```javascript
// ALWAYS store as UTC
const timestamp = new Date().toISOString();

// Database column type
// PostgreSQL: TIMESTAMP WITH TIME ZONE
// MySQL: DATETIME(3) with UTC conversion
// MongoDB: ISODate

// NEVER store local time
// NEVER store Unix timestamp without timezone context
```

### 6.3 NTP Synchronization Requirements

Servers generating timestamps MUST be synchronized via NTP:

```bash
# Linux server configuration (/etc/ntp.conf or /etc/chrony.conf)

# Use multiple NTP servers for redundancy
server 0.pool.ntp.org iburst
server 1.pool.ntp.org iburst
server 2.pool.ntp.org iburst
server 3.pool.ntp.org iburst

# Maximum allowed drift: 100ms
# Alert if drift exceeds 50ms
```

**Verification:**
```bash
# Check NTP sync status
timedatectl status
chronyc tracking
ntpq -p
```

**Application-level validation:**
```javascript
// Check if server time is synchronized
async function validateServerTime() {
  const ntpTime = await fetchNTPTime('pool.ntp.org');
  const serverTime = Date.now();
  const drift = Math.abs(ntpTime - serverTime);

  if (drift > 1000) { // More than 1 second drift
    throw new Error(`Server time drift detected: ${drift}ms`);
  }

  return true;
}
```

### 6.4 Proving Timestamp Authenticity

#### Option 1: Internal Hash Chain (Standard)

```javascript
// Each event includes hash of previous event + timestamp
const event = {
  timestamp: new Date().toISOString(),
  previousEventHash: 'ABC123...',
  // ... other data
};
event.hash = sha256(JSON.stringify(event));
```

#### Option 2: Third-Party Timestamping (RFC 3161)

For high-value documents, use a Trusted Timestamp Authority (TSA):

```javascript
// Using RFC 3161 Timestamp Protocol
const crypto = require('crypto');
const axios = require('axios');

async function getTimestampToken(dataHash) {
  // Create timestamp request
  const tsRequest = createTimestampRequest(dataHash);

  // Send to TSA (example: FreeTSA, DigiCert, etc.)
  const response = await axios.post(
    'https://freetsa.org/tsr',
    tsRequest,
    {
      headers: { 'Content-Type': 'application/timestamp-query' },
      responseType: 'arraybuffer'
    }
  );

  // Parse and store timestamp token
  const timestampToken = parseTimestampResponse(response.data);

  return {
    timestamp: timestampToken.genTime,
    token: timestampToken.encoded,
    tsa: 'freetsa.org',
    serialNumber: timestampToken.serialNumber
  };
}
```

#### Option 3: Blockchain Anchoring (Premium)

For maximum non-repudiation:

```javascript
// Anchor document hash to Bitcoin/Ethereum blockchain
async function anchorToBlockchain(documentHash) {
  // Use a service like OpenTimestamps, Chainpoint, or custom solution
  const anchor = await opentimestamps.stamp(documentHash);

  return {
    hash: documentHash,
    anchor: anchor,
    blockchain: 'bitcoin',
    pending: true  // Will be confirmed after block is mined
  };
}
```

### 6.5 Timestamp Display Guidelines

```javascript
// On Certificate: Always show UTC
"Signed At: 2026-01-10T15:30:45.123Z"

// In UI: Show local time with UTC reference
function formatForDisplay(isoTimestamp, userTimezone) {
  const date = new Date(isoTimestamp);

  // Local format for readability
  const local = date.toLocaleString('en-US', {
    timeZone: userTimezone,
    dateStyle: 'long',
    timeStyle: 'long'
  });

  // Always include UTC
  const utc = date.toISOString();

  return `${local} (${utc})`;
}
// Output: "January 10, 2026 at 10:30:45 AM EST (2026-01-10T15:30:45.123Z)"
```

---

## 7. IP Address Capture

### 7.1 Getting Real IP Behind Proxies/CDN

When using reverse proxies, load balancers, or CDNs, the direct connection IP is the proxy, not the user. Use these headers (in order of preference):

```javascript
// ip-capture.js

function getRealClientIP(request) {
  // Priority order for IP extraction
  const ipSources = [
    // 1. Cloudflare (if using Cloudflare)
    request.headers['cf-connecting-ip'],

    // 2. True-Client-IP (Akamai, Cloudflare Enterprise)
    request.headers['true-client-ip'],

    // 3. X-Real-IP (Nginx default)
    request.headers['x-real-ip'],

    // 4. X-Forwarded-For (standard, but can be spoofed)
    // Take the FIRST (leftmost) IP, which is the original client
    getFirstForwardedIP(request.headers['x-forwarded-for']),

    // 5. Direct connection (fallback)
    request.connection?.remoteAddress,
    request.socket?.remoteAddress,
    request.ip  // Express.js
  ];

  for (const ip of ipSources) {
    if (ip && isValidIP(ip)) {
      return normalizeIP(ip);
    }
  }

  return null;
}

function getFirstForwardedIP(forwardedFor) {
  if (!forwardedFor) return null;

  // X-Forwarded-For format: "client, proxy1, proxy2"
  const ips = forwardedFor.split(',').map(ip => ip.trim());
  return ips[0];
}

function isValidIP(ip) {
  // Basic validation for IPv4 and IPv6
  const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
  const ipv6Regex = /^(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}$/i;

  // Handle IPv6-mapped IPv4 addresses
  const cleanIP = ip.replace(/^::ffff:/, '');

  return ipv4Regex.test(cleanIP) || ipv6Regex.test(ip);
}

function normalizeIP(ip) {
  // Remove IPv6 prefix for IPv4-mapped addresses
  return ip.replace(/^::ffff:/, '');
}

module.exports = { getRealClientIP };
```

### 7.2 Cloudflare Headers

When using Cloudflare, these headers are available:

| Header | Description | Example |
|--------|-------------|---------|
| `CF-Connecting-IP` | Original visitor IP | `192.168.1.1` |
| `CF-IPCountry` | 2-letter country code | `US` |
| `CF-Ray` | Cloudflare request ID | `7a8b9c0d1e2f-LAX` |
| `X-Forwarded-For` | Full proxy chain | `192.168.1.1, 172.16.0.1` |
| `CF-Visitor` | Scheme info | `{"scheme":"https"}` |

```javascript
// Cloudflare-specific IP capture
function getCloudflareClientInfo(request) {
  return {
    ip: request.headers['cf-connecting-ip'],
    country: request.headers['cf-ipcountry'],
    ray: request.headers['cf-ray'],
    scheme: JSON.parse(request.headers['cf-visitor'] || '{}').scheme
  };
}
```

### 7.3 GDPR Privacy Considerations

IP addresses are **personal data** under GDPR. Requirements:

1. **Legal Basis**: Legitimate interest (fraud prevention, legal compliance)

2. **Purpose Limitation**: Only use for:
   - Signature verification
   - Fraud prevention
   - Legal compliance
   - Audit trail

3. **Data Minimization**:
   - Don't collect more than necessary
   - Consider hashing or partial anonymization after document completion

4. **Retention Limits**:
   - Retain full IP only as long as legally required
   - Anonymize after retention period

5. **Privacy Policy Disclosure**:
   ```
   We collect your IP address when you sign documents to:
   - Verify your identity
   - Prevent fraud
   - Comply with electronic signature laws (ESIGN, eIDAS)

   IP addresses are retained for [X] years as required by law,
   then anonymized or deleted.
   ```

6. **Data Subject Rights**:
   - Right to access: Provide IP in data export
   - Right to erasure: May be limited by legal retention requirements
   - Document the exemption for legal compliance

```javascript
// GDPR-compliant IP anonymization (after retention period)
function anonymizeIP(ip) {
  if (ip.includes(':')) {
    // IPv6: Zero out last 80 bits
    const parts = ip.split(':');
    return parts.slice(0, 3).join(':') + ':0:0:0:0:0';
  } else {
    // IPv4: Zero out last octet
    const parts = ip.split('.');
    parts[3] = '0';
    return parts.join('.');
  }
  // 192.168.1.100 -> 192.168.1.0
  // 2001:0db8:85a3::8a2e -> 2001:0db8:85a3:0:0:0:0:0
}
```

### 7.4 Geolocation Enrichment (Optional)

```javascript
// Using a geolocation service (e.g., MaxMind, IP-API)
const geoip = require('geoip-lite');

function enrichWithGeolocation(ip) {
  const geo = geoip.lookup(ip);

  if (!geo) {
    return null;
  }

  return {
    country: geo.country,      // "US"
    region: geo.region,        // "CA"
    city: geo.city,           // "San Francisco"
    timezone: geo.timezone,    // "America/Los_Angeles"
    coordinates: {
      latitude: geo.ll[0],
      longitude: geo.ll[1]
    }
  };
}

// Store with audit event
const auditEvent = {
  ip_address: clientIP,
  geo_country: geoData?.country,
  geo_region: geoData?.region,
  geo_city: geoData?.city,
  // Note: Don't store coordinates - too precise for privacy
};
```

---

## 8. Consent Flow

### 8.1 ESIGN Act Disclosure (EXACT COPY)

The following disclosure MUST be presented to signers before they can sign:

```
ELECTRONIC SIGNATURE DISCLOSURE AND CONSENT

Before you proceed to sign electronically, please read this disclosure carefully.

CONSENT TO USE ELECTRONIC SIGNATURES

By clicking "I Agree" below, you consent to:

1. Signing documents electronically using SignSimple.io
2. Receiving documents and notices electronically
3. Using electronic signatures in place of handwritten signatures

LEGAL EFFECT OF ELECTRONIC SIGNATURES

Under the federal Electronic Signatures in Global and National Commerce Act
(ESIGN Act, 15 U.S.C. 7001 et seq.) and applicable state law (Uniform Electronic
Transactions Act), electronic signatures have the same legal effect as handwritten
signatures when all parties consent to conduct business electronically.

By signing electronically, you agree that your electronic signature is the legal
equivalent of your manual/handwritten signature.

YOUR RIGHT TO OBTAIN PAPER COPIES

You have the right to receive a paper copy of any document you sign electronically.
To request a paper copy, you may:

- Download and print the document from your SignSimple.io account
- Contact [SENDER_EMAIL] to request a paper copy
- Email support@signsimple.io for assistance

There is no fee for requesting paper copies.

YOUR RIGHT TO WITHDRAW CONSENT

You may withdraw your consent to receive documents electronically at any time.
To withdraw consent:

- Do not sign the document
- Close this window and contact the sender directly
- Email support@signsimple.io

Withdrawing consent will not affect the validity of any documents you have
already signed electronically.

HARDWARE AND SOFTWARE REQUIREMENTS

To access and retain electronic documents, you need:

- A computer or mobile device with internet access
- A current web browser (Chrome, Firefox, Safari, or Edge)
- Software to view PDF documents (e.g., Adobe Reader)
- A printer or storage device to retain copies
- A valid email address to receive notifications

You confirm that you meet these requirements by proceeding.

UPDATING YOUR CONTACT INFORMATION

You are responsible for keeping your email address current. If your email
changes, please update it in your account settings or contact the sender.

ACKNOWLEDGMENT

By clicking "I Agree" below, you confirm that:

[ ] I have read and understand this Electronic Signature Disclosure
[ ] I agree to use electronic signatures
[ ] I meet the hardware and software requirements listed above
[ ] I understand my right to receive paper copies
[ ] I understand my right to withdraw consent

[I AGREE - PROCEED TO SIGN]          [I DO NOT AGREE - CANCEL]
```

### 8.2 Consent Checkbox Wording

The checkbox(es) before the "I Agree" button:

```html
<label>
  <input type="checkbox" id="consent-esign" required>
  I have read and agree to the <a href="#disclosure" target="_blank">Electronic Signature Disclosure</a>.
  I consent to use electronic signatures and understand that my electronic signature has the same
  legal effect as a handwritten signature.
</label>

<label>
  <input type="checkbox" id="consent-requirements" required>
  I confirm that I have access to the required hardware and software to view, sign, and retain
  electronic documents.
</label>

<label>
  <input type="checkbox" id="consent-paper-rights" required>
  I understand my right to receive paper copies and my right to withdraw consent.
</label>
```

### 8.3 Right to Paper Copy Disclosure

```
YOUR RIGHT TO PAPER COPIES

At any time, you may request a paper copy of any document you have signed
electronically. To obtain a paper copy:

Option 1: Self-Service
- Log into your SignSimple.io account
- Navigate to "My Documents"
- Click "Download" on any document
- Print the downloaded PDF

Option 2: Request from Sender
- Contact [SENDER_NAME] at [SENDER_EMAIL]
- Request a paper copy of the signed document
- The sender may mail or email you a copy

Option 3: Contact Support
- Email support@signsimple.io
- Subject: Paper Copy Request
- Include the document name and your email address

Cost: There is no charge for paper copies.

Timeframe: Paper copies will be provided within 5 business days of request.
```

### 8.4 Hardware/Software Requirements Disclosure

```
HARDWARE AND SOFTWARE REQUIREMENTS

To sign documents electronically with SignSimple.io, you need:

MINIMUM REQUIREMENTS:

Device:
- Desktop computer, laptop, tablet, or smartphone
- Screen resolution of at least 1024x768 (desktop) or 320x480 (mobile)

Internet Connection:
- Broadband internet connection
- Stable connection to complete signing process

Web Browser (any of the following):
- Google Chrome version 90 or later
- Mozilla Firefox version 88 or later
- Apple Safari version 14 or later
- Microsoft Edge version 90 or later
- JavaScript must be enabled

For Viewing Documents:
- PDF viewer (most browsers have built-in PDF support)
- Adobe Acrobat Reader (free) for advanced PDF features

For Retaining Copies:
- Printer (optional, for paper copies)
- Sufficient storage space for downloaded documents

Email:
- Valid email address to receive signing requests and notifications
- Access to email to verify your identity

RECOMMENDED:
- Updated operating system with latest security patches
- Antivirus software
- Secure, private internet connection (avoid public Wi-Fi)

By proceeding, you confirm that you currently have access to the hardware
and software listed above and will be able to access and retain the
documents you sign.
```

### 8.5 Consent Recording

```javascript
// consent-handler.js

async function recordConsent(signerId, request) {
  const consentRecord = {
    signer_id: signerId,
    consent_given: true,
    consent_timestamp: new Date().toISOString(),
    consent_ip_address: getRealClientIP(request),
    consent_user_agent: request.headers['user-agent'],
    consent_version: '1.0',  // Version of disclosure shown

    // Individual consent items
    consents: {
      esign_disclosure: true,
      hardware_software: true,
      paper_copy_rights: true
    },

    // Hash of the exact disclosure text shown
    disclosure_text_hash: await sha256(ESIGN_DISCLOSURE_TEXT),

    // Browser/device info
    device_info: parseUserAgent(request.headers['user-agent'])
  };

  // Update signer record
  await db.signers.update(signerId, {
    consent_given: true,
    consent_timestamp: consentRecord.consent_timestamp,
    consent_ip_address: consentRecord.consent_ip_address,
    consent_user_agent: consentRecord.consent_user_agent
  });

  // Create audit event
  await createAuditEvent({
    document_id: signer.document_id,
    signer_id: signerId,
    event_type: 'consent.given',
    ip_address: consentRecord.consent_ip_address,
    user_agent: consentRecord.consent_user_agent,
    event_data: consentRecord.consents
  });

  return consentRecord;
}
```

---

## 9. Legal Disclaimers

### 9.1 Terms of Service - Electronic Signature Section

```
ELECTRONIC SIGNATURES

9.1 Consent to Electronic Transactions

By using SignSimple.io, you consent to conduct transactions electronically,
including signing documents using electronic signatures. You agree that your
electronic signature has the same legal effect and enforceability as a
handwritten signature.

9.2 ESIGN Act Compliance

SignSimple.io is designed to comply with the Electronic Signatures in Global
and National Commerce Act (ESIGN Act, 15 U.S.C. 7001 et seq.) and the Uniform
Electronic Transactions Act (UETA) as adopted by individual U.S. states.
Electronic signatures created using our Service are intended to be legally
binding under these laws.

9.3 Your Responsibilities

When using electronic signatures, you agree to:

a) Verify the identity of all signers on your documents
b) Ensure all signers have consented to electronic signatures
c) Provide signers with access to the documents they sign
d) Retain copies of signed documents and Certificates of Completion
e) Not use the Service for documents that legally require notarization,
   witnessed signatures, or other formalities not supported by electronic
   signatures

9.4 Authentication

You are responsible for maintaining the security of your account credentials.
Electronic signatures made using your account are presumed to be authorized by
you. You must immediately notify us of any unauthorized access to your account.

9.5 Audit Trail

SignSimple.io maintains detailed audit trails for all documents, including
timestamps, IP addresses, and signer actions. This information is included in
the Certificate of Completion and may be used as evidence of the signing process.

9.6 No Legal Advice

SignSimple.io provides an electronic signature platform and does not provide
legal advice. We make no representations about whether electronic signatures
are appropriate for your specific use case. You should consult with a qualified
attorney regarding the legal requirements for your documents and jurisdiction.
```

### 9.2 Limitation of Liability Language

```
LIMITATION OF LIABILITY

10.1 Exclusion of Certain Damages

TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, IN NO EVENT SHALL
SIGNSIMPLE.IO, ITS AFFILIATES, DIRECTORS, OFFICERS, EMPLOYEES, AGENTS,
OR LICENSORS BE LIABLE FOR:

a) Any indirect, incidental, special, consequential, or punitive damages;
b) Any loss of profits, revenue, data, or business opportunities;
c) Any damages arising from your use or inability to use the Service;
d) Any damages arising from unauthorized access to or alteration of your
   documents or data;
e) Any claims related to the legal validity or enforceability of electronic
   signatures in your jurisdiction.

10.2 Limitation of Total Liability

OUR TOTAL AGGREGATE LIABILITY FOR ALL CLAIMS ARISING FROM OR RELATED TO
THE SERVICE SHALL NOT EXCEED THE GREATER OF (A) THE AMOUNTS PAID BY YOU
TO SIGNSIMPLE.IO IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM, OR (B)
ONE HUNDRED DOLLARS ($100).

10.3 Electronic Signature Validity

WHILE SIGNSIMPLE.IO IS DESIGNED TO CREATE LEGALLY BINDING ELECTRONIC
SIGNATURES UNDER APPLICABLE LAW, WE DO NOT GUARANTEE THAT ANY COURT OR
GOVERNMENT AUTHORITY WILL ACCEPT OR ENFORCE DOCUMENTS SIGNED USING OUR
SERVICE. THE LEGAL VALIDITY OF ELECTRONIC SIGNATURES MAY DEPEND ON
FACTORS OUTSIDE OUR CONTROL, INCLUDING THE NATURE OF THE DOCUMENT,
APPLICABLE LAWS, AND JUDICIAL INTERPRETATION.

10.4 Third-Party Claims

We are not responsible for any third-party claims arising from your use
of electronic signatures, including claims from signers, recipients, or
other parties regarding the validity or authenticity of signatures.

10.5 Basis of Bargain

THE LIMITATIONS SET FORTH IN THIS SECTION ARE FUNDAMENTAL ELEMENTS OF
THE BASIS OF THE BARGAIN BETWEEN YOU AND SIGNSIMPLE.IO.
```

### 9.3 Excluded Document Types Warning

```
EXCLUDED DOCUMENT TYPES

IMPORTANT: Electronic signatures may not be legally valid for certain
types of documents. The following documents are EXCLUDED from use with
SignSimple.io and may require handwritten signatures, notarization, or
other formalities:

FEDERALLY EXCLUDED (under ESIGN Act 15 U.S.C. 7003):
- Wills, codicils, and testamentary trusts
- Family law matters (adoption, divorce, custody orders)
- Court orders and official court documents
- Notices of default, foreclosure, or eviction related to primary residence
- Cancellation of utility services
- Cancellation of health or life insurance benefits
- Product recall notices affecting health or safety
- Documents required to accompany hazardous materials transport

STATE-SPECIFIC EXCLUSIONS (vary by jurisdiction):
- Real estate deeds and title transfers (some states)
- Powers of attorney (some states)
- Healthcare directives (some states)
- UCC filings (some states)

OTHER DOCUMENTS THAT MAY REQUIRE SPECIAL HANDLING:
- Documents requiring notarization
- Documents requiring witness signatures
- Government forms requiring original signatures
- Documents involving minors
- Documents for regulated industries with specific signature requirements

SIGNSIMPLE.IO DOES NOT PROVIDE LEGAL ADVICE. If you are unsure whether
electronic signatures are appropriate for your document, consult with a
qualified attorney in your jurisdiction.

By using SignSimple.io, you represent that your document is not one of
the excluded types listed above and that you have verified electronic
signatures are appropriate for your use case.
```

### 9.4 Jurisdiction Statement

```
GOVERNING LAW AND JURISDICTION

11.1 Governing Law

This Agreement and your use of SignSimple.io shall be governed by and
construed in accordance with the laws of the State of Delaware, United
States, without regard to its conflict of law provisions.

11.2 Jurisdiction

Any legal action or proceeding arising out of or relating to this Agreement
or the Service shall be brought exclusively in the federal or state courts
located in Wilmington, Delaware. You consent to the personal jurisdiction
of such courts and waive any objection to venue in such courts.

11.3 International Users

If you access the Service from outside the United States, you do so at your
own risk and are responsible for compliance with local laws. The Service is
operated from the United States, and we make no representation that the
Service is appropriate or available for use in other locations.

11.4 Electronic Signature Laws

While SignSimple.io is designed to comply with U.S. federal electronic
signature laws (ESIGN Act) and the EU eIDAS Regulation, the legal validity
of electronic signatures varies by jurisdiction. Users outside the United
States and European Union should verify that electronic signatures are
legally recognized in their jurisdiction before use.

11.5 Dispute Resolution

Before initiating any legal proceeding, you agree to attempt to resolve
any dispute informally by contacting us at legal@signsimple.io. If the
dispute is not resolved within 30 days, either party may proceed with
formal legal action.

11.6 Class Action Waiver

TO THE EXTENT PERMITTED BY LAW, YOU AGREE THAT ANY DISPUTE RESOLUTION
PROCEEDINGS WILL BE CONDUCTED ON AN INDIVIDUAL BASIS AND NOT AS A CLASS,
CONSOLIDATED, OR REPRESENTATIVE ACTION.
```

---

## 10. eIDAS Compliance (EU)

### 10.1 eIDAS Overview

The eIDAS Regulation (EU) No 910/2014 establishes three levels of electronic signatures:

| Level | Name | Requirements | Legal Effect |
|-------|------|--------------|--------------|
| 1 | Simple Electronic Signature (SES) | Any electronic data attached to or associated with other electronic data | Admissible as evidence; court determines weight |
| 2 | Advanced Electronic Signature (AES) | Uniquely linked to signer, capable of identifying signer, under signer's sole control, detects changes | Admissible as evidence; stronger presumption |
| 3 | Qualified Electronic Signature (QES) | AES + created by qualified device + based on qualified certificate | Equivalent to handwritten signature |

### 10.2 Simple Electronic Signature (SES) Requirements

SignSimple.io, as initially implemented, provides Simple Electronic Signatures. Requirements:

1. **Electronic Form**
   - Signature must be in electronic form (drawing, typed name, uploaded image)

2. **Association with Document**
   - Signature must be logically attached to the document
   - Clear visual indication of what was signed

3. **Intent to Sign**
   - Clear user action to sign (clicking "Sign" button)
   - Consent to electronic signing

4. **Audit Trail**
   - Records of when, where, and how the signature was applied
   - Certificate of Completion

**Our Implementation Provides:**
- Draw/Type/Upload signature options
- Embedded signature in PDF
- Timestamped audit trail
- Certificate of Completion
- IP address and device tracking

### 10.3 Advanced Electronic Signature (AES) Requirements

To upgrade to AES level (future enhancement):

1. **Uniquely Linked to Signatory**
   - Strong identity verification (ID document check, video verification)
   - Authentication before each signature

2. **Capable of Identifying the Signatory**
   - Store verified identity information
   - Link signature cryptographically to signer

3. **Under Sole Control of Signatory**
   - Two-factor authentication
   - Signature keys not shared
   - Device binding

4. **Detects Subsequent Changes**
   - Digital signature using PKI
   - Hash verification

**Implementation Path for AES:**
```
Phase 1: Strong Authentication
- Add SMS/email OTP verification
- Implement 2FA for all signers
- Track authentication events

Phase 2: Identity Verification
- Integrate ID verification service (Onfido, Jumio, etc.)
- Video verification option
- Store verified identity with signature

Phase 3: Digital Signatures
- Implement PKI-based signatures
- Generate signing certificates per signer
- Use timestamping authority

Phase 4: Tamper Detection
- Apply digital signature to PDF
- Implement hash chain verification
- Third-party timestamping
```

### 10.4 Qualified Electronic Signature (QES) Partnership Path

QES requires:
1. Qualified signature creation device (QSCD)
2. Qualified certificate from EU Trust Service Provider
3. Face-to-face or equivalent identity verification

**Partnership Options:**

| Partner Type | Examples | What They Provide |
|--------------|----------|-------------------|
| Trust Service Provider | DocuSign (EU), Swisscom, Namirial | Qualified certificates, QSCD |
| Identity Verification | IDnow, Veriff, Onfido | Video identification meeting eIDAS requirements |
| Remote Signing Service | Entrust, DigiCert | Cloud-based QSCD and certificates |

**Integration Architecture:**
```
SignSimple.io (SES)
       |
       v
Partner API Integration
       |
       +-- Identity Verification (IDnow, Veriff)
       |         |
       |         v
       |   Verified Identity
       |
       +-- Trust Service Provider (Swisscom, Namirial)
                 |
                 v
           QES Certificate + Remote Signing
                 |
                 v
         Qualified Electronic Signature
```

**Implementation Cost/Timeline:**
- Identity verification integration: 2-4 weeks, ~$10K setup
- TSP integration: 4-8 weeks, ~$25K setup
- Per-signature costs: $0.50-$2.00 for identity verification + $1-5 for QES
- Compliance audit: 4-6 weeks, ~$15K
- Total initial investment: ~$50-75K
- Timeline: 3-6 months

### 10.5 eIDAS-Specific Certificate Requirements

When serving EU customers, the Certificate of Completion should include:

```
EU ELECTRONIC SIGNATURE NOTICE

This document was signed using a Simple Electronic Signature (SES) as
defined by Regulation (EU) No 910/2014 (eIDAS).

Under Article 25(1) of the eIDAS Regulation, an electronic signature
shall not be denied legal effect and admissibility as evidence in legal
proceedings solely on the grounds that it is in an electronic form or
that it does not meet the requirements for qualified electronic signatures.

This Certificate of Completion provides evidence of:
- The identity of signers (as provided, not verified)
- The timestamp of each signature
- The integrity of the document (via SHA-256 hash)
- Consent to electronic signing

For documents requiring a higher level of assurance, please contact
support@signsimple.io about our Advanced and Qualified Electronic
Signature options.
```

---

## 11. Certificate Generation Code

### 11.1 Data Gathering

```javascript
// certificate-data.js

async function gatherCertificateData(documentId) {
  // Fetch all required data in parallel
  const [document, signers, auditEvents] = await Promise.all([
    db.documents.findById(documentId),
    db.signers.findByDocumentId(documentId),
    db.auditEvents.findByDocumentId(documentId)
  ]);

  if (!document || document.status !== 'completed') {
    throw new Error('Document not found or not completed');
  }

  // Get the sender (document creator)
  const sender = await db.users.findById(document.created_by);

  // Parse device info for each signer
  const signersWithDeviceInfo = signers.map(signer => ({
    ...signer,
    deviceInfo: parseUserAgent(signer.signature_user_agent)
  }));

  // Format audit events
  const formattedEvents = auditEvents.map(event => ({
    timestamp: event.event_timestamp,
    type: event.event_type,
    actor: event.actor_email,
    ip: event.ip_address,
    description: formatEventDescription(event)
  }));

  // Generate certificate ID
  const certificateId = generateUUID();
  const generatedAt = new Date().toISOString();

  // Build certificate data object
  const certificateData = {
    certificate: {
      id: certificateId,
      generated_at: generatedAt,
      verification_url: `https://signsimple.io/verify/${document.id}`
    },
    document: {
      id: document.id,
      title: document.title,
      status: document.status,
      original_hash: document.original_hash,
      final_hash: document.final_hash,
      created_at: document.created_at,
      completed_at: document.completed_at,
      page_count: document.page_count,
      sender: {
        name: sender.name,
        email: sender.email
      }
    },
    signers: signersWithDeviceInfo.map(signer => ({
      name: signer.name,
      email: signer.email,
      role: signer.role,
      status: signer.status,
      consent: {
        given: signer.consent_given,
        timestamp: signer.consent_timestamp,
        ip_address: signer.consent_ip_address
      },
      signature: {
        timestamp: signer.signed_at,
        ip_address: signer.signature_ip_address,
        device: signer.deviceInfo
      }
    })),
    audit_trail: formattedEvents
  };

  // Generate hash of certificate data for tamper-evidence
  certificateData.certificate.hash = generateCertificateHash(certificateData);

  return certificateData;
}

function parseUserAgent(userAgent) {
  if (!userAgent) return { browser: 'Unknown', os: 'Unknown' };

  const UAParser = require('ua-parser-js');
  const parser = new UAParser(userAgent);
  const result = parser.getResult();

  return {
    browser: `${result.browser.name || 'Unknown'} ${result.browser.version || ''}`.trim(),
    os: `${result.os.name || 'Unknown'} ${result.os.version || ''}`.trim(),
    device: result.device.type || 'desktop'
  };
}

function formatEventDescription(event) {
  const descriptions = {
    'document.created': `Document created by ${event.actor_email}`,
    'document.sent': `Document sent to signers`,
    'document.viewed': `Document viewed by ${event.actor_email}`,
    'document.completed': `All signatures complete - Document COMPLETED`,
    'email.delivered': `Email delivered to ${event.actor_email}`,
    'email.opened': `Email opened by ${event.actor_email}`,
    'consent.given': `ESIGN consent given by ${event.actor_email}`,
    'signature.completed': `Signature completed by ${event.actor_email}`,
    'signature.declined': `Signature declined by ${event.actor_email}`,
    'certificate.generated': `Certificate of Completion generated`
  };

  let description = descriptions[event.event_type] || event.event_type;

  if (event.ip_address) {
    description += ` (${event.ip_address})`;
  }

  return description;
}

module.exports = { gatherCertificateData };
```

### 11.2 PDF Generation with pdf-lib

```javascript
// generate-certificate.js

const { PDFDocument, StandardFonts, rgb } = require('pdf-lib');
const fs = require('fs').promises;

async function generateCertificatePDF(certificateData) {
  // Create a new PDF document
  const pdfDoc = await PDFDocument.create();

  // Embed fonts
  const helvetica = await pdfDoc.embedFont(StandardFonts.Helvetica);
  const helveticaBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
  const courier = await pdfDoc.embedFont(StandardFonts.Courier);

  // Add first page
  let page = pdfDoc.addPage([612, 792]); // Letter size
  const { width, height } = page.getSize();

  // Colors
  const black = rgb(0, 0, 0);
  const gray = rgb(0.4, 0.4, 0.4);
  const darkGray = rgb(0.2, 0.2, 0.2);
  const lineColor = rgb(0.8, 0.8, 0.8);

  // Margins and positioning
  const margin = 50;
  let y = height - margin;

  // Helper functions
  const drawText = (text, x, yPos, options = {}) => {
    page.drawText(text, {
      x,
      y: yPos,
      size: options.size || 10,
      font: options.font || helvetica,
      color: options.color || black
    });
  };

  const drawLine = (y) => {
    page.drawLine({
      start: { x: margin, y },
      end: { x: width - margin, y },
      thickness: 0.5,
      color: lineColor
    });
  };

  const drawSectionHeader = (title, yPos) => {
    drawText(title, margin, yPos, { font: helveticaBold, size: 12 });
    drawLine(yPos - 5);
    return yPos - 25;
  };

  // ========== HEADER ==========
  drawText('SIGNSIMPLE.IO', width / 2 - 45, y, { font: helveticaBold, size: 14 });
  y -= 25;
  drawText('CERTIFICATE OF COMPLETION', width / 2 - 85, y, { font: helveticaBold, size: 16 });
  y -= 15;
  drawLine(y);
  y -= 30;

  // ========== DOCUMENT INFO ==========
  const doc = certificateData.document;
  drawText(`Document Title: ${doc.title}`, margin, y, { font: helveticaBold, size: 11 });
  y -= 15;
  drawText(`Document ID: ${doc.id}`, margin, y, { size: 10, color: gray });
  y -= 15;
  drawText(`Status: ${doc.status.toUpperCase()}`, margin, y, { font: helveticaBold, size: 10 });
  y -= 25;

  // ========== DOCUMENT INTEGRITY ==========
  y = drawSectionHeader('DOCUMENT INTEGRITY', y);

  drawText('Original Document Hash (SHA-256):', margin, y, { size: 9 });
  y -= 12;
  drawText(doc.original_hash, margin, y, { font: courier, size: 8, color: darkGray });
  y -= 18;

  drawText('Signed Document Hash (SHA-256):', margin, y, { size: 9 });
  y -= 12;
  drawText(doc.final_hash, margin, y, { font: courier, size: 8, color: darkGray });
  y -= 18;

  drawText(`Certificate Generated: ${certificateData.certificate.generated_at}`, margin, y, { size: 9 });
  y -= 30;

  // ========== SIGNING PARTIES ==========
  y = drawSectionHeader('SIGNING PARTIES', y);

  for (const signer of certificateData.signers) {
    // Check if we need a new page
    if (y < 200) {
      page = pdfDoc.addPage([612, 792]);
      y = height - margin;
    }

    drawText(`${signer.name}`, margin, y, { font: helveticaBold, size: 10 });
    y -= 14;
    drawText(`Email: ${signer.email}`, margin + 15, y, { size: 9 });
    y -= 12;
    drawText(`Role: ${signer.role.toUpperCase()}`, margin + 15, y, { size: 9 });
    y -= 12;
    drawText(`Status: ${signer.status.toUpperCase()}`, margin + 15, y, { size: 9 });
    y -= 12;

    if (signer.signature.timestamp) {
      drawText(`Signed At: ${signer.signature.timestamp}`, margin + 15, y, { size: 9 });
      y -= 12;
      drawText(`IP Address: ${signer.signature.ip_address || 'N/A'}`, margin + 15, y, { size: 9 });
      y -= 12;
      drawText(`Device: ${signer.signature.device?.browser || 'Unknown'} on ${signer.signature.device?.os || 'Unknown'}`, margin + 15, y, { size: 9 });
      y -= 12;
    }

    if (signer.consent.given) {
      drawText(`Consent Given: Yes, at ${signer.consent.timestamp}`, margin + 15, y, { size: 9 });
      y -= 12;
    }

    y -= 10;
    drawLine(y);
    y -= 15;
  }

  // ========== AUDIT TRAIL ==========
  // New page for audit trail if needed
  if (y < 300) {
    page = pdfDoc.addPage([612, 792]);
    y = height - margin;
  }

  y = drawSectionHeader('AUDIT TRAIL', y);

  for (const event of certificateData.audit_trail) {
    if (y < 100) {
      page = pdfDoc.addPage([612, 792]);
      y = height - margin;
    }

    const timestamp = event.timestamp.replace('T', ' ').replace('Z', ' UTC');
    drawText(`${timestamp} - ${event.description}`, margin, y, { size: 8 });
    y -= 12;
  }

  y -= 20;

  // ========== LEGAL NOTICE ==========
  if (y < 200) {
    page = pdfDoc.addPage([612, 792]);
    y = height - margin;
  }

  y = drawSectionHeader('LEGAL NOTICE', y);

  const legalText = [
    'This document was signed electronically using SignSimple.io. Electronic signatures are',
    'legally binding under the ESIGN Act (15 U.S.C. 7001 et seq.), UETA, and eIDAS Regulation',
    '(EU 910/2014). All signers consented to use electronic signatures before signing.',
    '',
    'This certificate is tamper-evident. Any modification to the signed document will',
    'invalidate the document hash above.',
    '',
    `To verify this document: ${certificateData.certificate.verification_url}`
  ];

  for (const line of legalText) {
    drawText(line, margin, y, { size: 9 });
    y -= 12;
  }

  y -= 20;
  drawLine(y);
  y -= 20;

  // ========== FOOTER ==========
  drawText(`Certificate ID: ${certificateData.certificate.id}`, margin, y, { size: 9, color: gray });
  y -= 12;
  drawText(`Generated: ${certificateData.certificate.generated_at}`, margin, y, { size: 9, color: gray });
  y -= 12;
  drawText('SignSimple.io - https://signsimple.io', margin, y, { size: 9, color: gray });

  // Save PDF
  const pdfBytes = await pdfDoc.save();

  return pdfBytes;
}

// Save certificate and update database
async function createAndSaveCertificate(documentId) {
  // Gather data
  const certificateData = await gatherCertificateData(documentId);

  // Generate PDF
  const pdfBytes = await generateCertificatePDF(certificateData);

  // Save to file system
  const filePath = `certificates/${certificateData.certificate.id}.pdf`;
  await fs.writeFile(filePath, pdfBytes);

  // Save to database
  await db.certificates.create({
    id: certificateData.certificate.id,
    document_id: documentId,
    certificate_hash: certificateData.certificate.hash,
    certificate_data: certificateData,
    pdf_path: filePath,
    generated_at: certificateData.certificate.generated_at,
    verification_url: certificateData.certificate.verification_url
  });

  // Create audit event
  await createAuditEvent({
    document_id: documentId,
    event_type: 'certificate.generated',
    event_data: {
      certificate_id: certificateData.certificate.id,
      certificate_hash: certificateData.certificate.hash
    }
  });

  // Update document record
  await db.documents.update(documentId, {
    certificate_path: filePath
  });

  return {
    certificateId: certificateData.certificate.id,
    pdfPath: filePath,
    pdfBytes
  };
}

module.exports = { generateCertificatePDF, createAndSaveCertificate };
```

### 11.3 Attaching Certificate to Signed Document

**Option A: Append Certificate as Last Page(s)**
```javascript
async function appendCertificateToDocument(signedDocPath, certificatePdfBytes) {
  // Load the signed document
  const signedDocBytes = await fs.readFile(signedDocPath);
  const signedDoc = await PDFDocument.load(signedDocBytes);

  // Load the certificate
  const certificateDoc = await PDFDocument.load(certificatePdfBytes);

  // Copy certificate pages to signed document
  const certificatePages = await signedDoc.copyPages(
    certificateDoc,
    certificateDoc.getPageIndices()
  );

  for (const page of certificatePages) {
    signedDoc.addPage(page);
  }

  // Save combined document
  const combinedBytes = await signedDoc.save();

  return combinedBytes;
}
```

**Option B: Separate Certificate (Recommended)**
```javascript
// Keep certificate as separate file
// Advantages:
// - Document hash remains unchanged
// - Certificate can be regenerated if needed
// - Cleaner separation of concerns

async function saveSeparateCertificate(documentId) {
  const { pdfBytes, certificateId } = await createAndSaveCertificate(documentId);

  // Paths
  const signedDocPath = `documents/${documentId}/signed.pdf`;
  const certificatePath = `documents/${documentId}/certificate.pdf`;

  await fs.writeFile(certificatePath, pdfBytes);

  // Create a summary/manifest file
  const manifest = {
    document_id: documentId,
    signed_document: 'signed.pdf',
    certificate: 'certificate.pdf',
    generated_at: new Date().toISOString()
  };

  await fs.writeFile(
    `documents/${documentId}/manifest.json`,
    JSON.stringify(manifest, null, 2)
  );

  return { signedDocPath, certificatePath };
}
```

**Recommendation:** Use Option B (Separate Certificate) because:
1. The signed document hash remains stable
2. Certificates can be updated/regenerated without affecting the document
3. Easier to provide just the document or just the certificate as needed
4. Cleaner for long-term archival

---

## 12. Implementation Checklist

### Phase 1: Foundation (Week 1-2)

- [ ] **Database Schema**
  - [ ] Create `documents` table with hash fields
  - [ ] Create `signers` table with consent tracking
  - [ ] Create `audit_events` table with all fields
  - [ ] Create `certificates` table
  - [ ] Set up indexes for performance
  - [ ] Configure retention policies

- [ ] **Hash Implementation**
  - [ ] Implement SHA-256 for browser (Web Crypto API)
  - [ ] Implement SHA-256 for server (Node.js crypto)
  - [ ] Test hash generation for various file types
  - [ ] Implement hash chain for multi-signer documents

### Phase 2: Audit Trail (Week 2-3)

- [ ] **Event Tracking**
  - [ ] Implement all 20+ event types
  - [ ] Capture IP addresses correctly (CDN/proxy handling)
  - [ ] Parse and store user agent information
  - [ ] Test event creation for each workflow step

- [ ] **IP Capture**
  - [ ] Configure Cloudflare headers (if applicable)
  - [ ] Implement fallback chain for IP detection
  - [ ] Add geolocation enrichment (optional)
  - [ ] Document GDPR compliance measures

### Phase 3: Consent Flow (Week 3-4)

- [ ] **ESIGN Disclosure**
  - [ ] Create disclosure page with all required text
  - [ ] Implement consent checkboxes
  - [ ] Store consent version and hash
  - [ ] Record consent event with all metadata

- [ ] **User Interface**
  - [ ] Design consent modal/page
  - [ ] Add "I Agree" / "I Do Not Agree" buttons
  - [ ] Prevent signing without consent
  - [ ] Test consent flow on mobile devices

### Phase 4: Certificate Generation (Week 4-5)

- [ ] **Data Gathering**
  - [ ] Query all required data efficiently
  - [ ] Format data for certificate
  - [ ] Generate certificate hash

- [ ] **PDF Generation**
  - [ ] Install and configure pdf-lib
  - [ ] Implement certificate template
  - [ ] Test with various document/signer combinations
  - [ ] Generate sample certificates for review

- [ ] **Storage & Delivery**
  - [ ] Save certificate to file system/cloud storage
  - [ ] Update database with certificate reference
  - [ ] Implement certificate download endpoint
  - [ ] Test certificate generation at scale

### Phase 5: Verification (Week 5-6)

- [ ] **Verification Endpoint**
  - [ ] Create `/verify/:documentId` page
  - [ ] Display certificate data
  - [ ] Allow hash verification
  - [ ] Log verification attempts

- [ ] **Tamper Detection**
  - [ ] Implement document re-hash and compare
  - [ ] Display verification status
  - [ ] Handle failed verification gracefully

### Phase 6: Legal Review & Testing (Week 6-7)

- [ ] **Legal Review**
  - [ ] Have attorney review all disclosure text
  - [ ] Review Terms of Service updates
  - [ ] Confirm excluded document types list
  - [ ] Verify GDPR compliance measures

- [ ] **Testing**
  - [ ] End-to-end testing of complete workflow
  - [ ] Test with multiple signers
  - [ ] Test consent withdrawal
  - [ ] Test certificate generation
  - [ ] Test verification
  - [ ] Load testing for performance

### Phase 7: Documentation & Launch (Week 7-8)

- [ ] **Documentation**
  - [ ] API documentation for certificate endpoints
  - [ ] User guide for certificate verification
  - [ ] Internal documentation for support team

- [ ] **Launch**
  - [ ] Deploy to staging environment
  - [ ] Final QA
  - [ ] Deploy to production
  - [ ] Monitor for issues

---

## Appendix A: Sample API Endpoints

```javascript
// Certificate endpoints
POST   /api/documents/:id/certificate     // Generate certificate
GET    /api/documents/:id/certificate     // Download certificate PDF
GET    /api/verify/:documentId            // Public verification page
POST   /api/verify                        // Verify document hash

// Audit endpoints
GET    /api/documents/:id/audit-trail     // Get audit events
GET    /api/documents/:id/audit-trail/export  // Export as CSV

// Consent endpoints
POST   /api/signing/:token/consent        // Record consent
GET    /api/signing/:token/disclosure     // Get disclosure text
```

## Appendix B: Environment Variables

```bash
# Server
NODE_ENV=production
PORT=3000

# Database
DATABASE_URL=postgresql://user:pass@host:5432/signsimple

# Storage
STORAGE_TYPE=s3  # or 'local'
S3_BUCKET=signsimple-documents
S3_REGION=us-east-1

# Timestamps
NTP_SERVERS=pool.ntp.org
TIMESTAMP_DRIFT_TOLERANCE_MS=1000

# Geolocation (optional)
GEOIP_DATABASE_PATH=/path/to/GeoLite2-City.mmdb
# Or use API
GEOIP_API_KEY=your_api_key

# Third-party Timestamping (optional)
TSA_URL=https://freetsa.org/tsr
TSA_ENABLED=false

# Certificate Settings
CERTIFICATE_RETENTION_YEARS=10
HASH_ALGORITHM=SHA-256
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-10 | Legal Compliance Team | Initial specification |

---

**DISCLAIMER**: This document provides technical guidance for implementing electronic signature compliance features. It does not constitute legal advice. Consult with qualified legal counsel to ensure compliance with applicable laws in your jurisdiction.
