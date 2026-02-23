-- SignSimple.io - Audit Trail Database Schema
-- Migration: 001_audit_trail_schema
-- Compliant with: ESIGN Act, UETA, eIDAS
--
-- Run this migration to create the tables needed for
-- legally-binding Certificate of Completion functionality

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- DOCUMENTS TABLE
-- Core table for document envelopes
-- ============================================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    -- Status: draft, sent, in_progress, completed, voided, expired

    -- Document hashes for integrity verification
    original_hash VARCHAR(64) NOT NULL,       -- SHA-256 of original uploaded document
    current_hash VARCHAR(64),                  -- Current hash (updated with each signature)
    final_hash VARCHAR(64),                    -- SHA-256 of final signed document

    -- Ownership and timestamps
    created_by UUID NOT NULL,                  -- References users table
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    voided_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,

    -- File storage paths
    original_file_path VARCHAR(500) NOT NULL,
    signed_file_path VARCHAR(500),
    certificate_path VARCHAR(500),

    -- Document metadata
    page_count INTEGER DEFAULT 1,
    file_size_bytes BIGINT,
    mime_type VARCHAR(100) DEFAULT 'application/pdf',

    -- Settings
    reminder_frequency_days INTEGER DEFAULT 3,
    expiration_days INTEGER DEFAULT 30,

    -- Soft delete
    deleted_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT documents_valid_status CHECK (status IN (
        'draft', 'sent', 'in_progress', 'completed', 'voided', 'expired'
    ))
);

-- ============================================================
-- SIGNERS TABLE
-- Tracks all signing parties for each document
-- ============================================================
CREATE TABLE IF NOT EXISTS signers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Signer identity
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'signer',
    -- Role: signer, approver, cc, witness
    signing_order INTEGER NOT NULL DEFAULT 1,

    -- Current status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- Status: pending, sent, delivered, viewed, signed, declined

    -- ESIGN Consent tracking (CRITICAL for legal compliance)
    consent_given BOOLEAN DEFAULT FALSE,
    consent_timestamp TIMESTAMP WITH TIME ZONE,
    consent_ip_address INET,
    consent_user_agent TEXT,

    -- Signature tracking
    signed_at TIMESTAMP WITH TIME ZONE,
    signature_ip_address INET,
    signature_user_agent TEXT,
    signature_data JSONB,              -- Contains signature image, position, etc.

    -- Access management
    access_token VARCHAR(255) UNIQUE NOT NULL,
    access_token_expires_at TIMESTAMP WITH TIME ZONE,
    first_viewed_at TIMESTAMP WITH TIME ZONE,
    last_viewed_at TIMESTAMP WITH TIME ZONE,
    view_count INTEGER DEFAULT 0,

    -- Decline tracking
    declined_at TIMESTAMP WITH TIME ZONE,
    decline_reason TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT signers_valid_role CHECK (role IN ('signer', 'approver', 'cc', 'witness')),
    CONSTRAINT signers_valid_status CHECK (status IN (
        'pending', 'sent', 'delivered', 'viewed', 'signed', 'declined'
    ))
);

-- ============================================================
-- AUDIT_EVENTS TABLE
-- Core audit trail - THE HEART OF LEGAL COMPLIANCE
-- Every action is logged with full context
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    signer_id UUID REFERENCES signers(id) ON DELETE SET NULL,

    -- Event classification
    event_type VARCHAR(50) NOT NULL,
    event_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Actor information (who did this)
    actor_type VARCHAR(20) NOT NULL,   -- 'user', 'signer', 'system'
    actor_id UUID,                      -- User or signer ID
    actor_email VARCHAR(255),

    -- Network/Device information (where/how it happened)
    ip_address INET,
    user_agent TEXT,
    device_type VARCHAR(50),           -- 'desktop', 'mobile', 'tablet'
    browser VARCHAR(100),
    os VARCHAR(100),

    -- Geolocation (optional, from IP lookup)
    geo_country VARCHAR(100),
    geo_region VARCHAR(100),
    geo_city VARCHAR(100),

    -- Hash chain for tamper-evidence
    previous_hash VARCHAR(64),
    current_hash VARCHAR(64),

    -- Event-specific data (flexible JSON)
    event_data JSONB,

    -- Indexing timestamp
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT audit_events_valid_event_type CHECK (event_type IN (
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
    CONSTRAINT audit_events_valid_actor_type CHECK (actor_type IN ('user', 'signer', 'system'))
);

-- ============================================================
-- CERTIFICATES TABLE
-- Stores Certificate of Completion records
-- ============================================================
CREATE TABLE IF NOT EXISTS certificates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Certificate data
    certificate_hash VARCHAR(64) NOT NULL,    -- Hash of all certificate data
    certificate_data JSONB NOT NULL,          -- Complete certificate JSON
    pdf_path VARCHAR(500) NOT NULL,           -- Path to generated PDF

    -- Generation metadata
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    generated_by VARCHAR(20) NOT NULL DEFAULT 'system',

    -- Verification tracking
    verification_url VARCHAR(500) NOT NULL,
    verified_count INTEGER DEFAULT 0,
    last_verified_at TIMESTAMP WITH TIME ZONE,

    -- Unique constraint to prevent duplicate certificates
    CONSTRAINT certificates_unique_document UNIQUE (document_id)
);

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================

-- Documents indexes
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_created_by ON documents(created_by);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_completed_at ON documents(completed_at DESC);

-- Signers indexes
CREATE INDEX IF NOT EXISTS idx_signers_document ON signers(document_id);
CREATE INDEX IF NOT EXISTS idx_signers_email ON signers(email);
CREATE INDEX IF NOT EXISTS idx_signers_status ON signers(status);
CREATE INDEX IF NOT EXISTS idx_signers_access_token ON signers(access_token);

-- Audit events indexes (critical for certificate generation)
CREATE INDEX IF NOT EXISTS idx_audit_events_document ON audit_events(document_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_actor_email ON audit_events(actor_email);
CREATE INDEX IF NOT EXISTS idx_audit_events_document_timestamp ON audit_events(document_id, event_timestamp ASC);

-- Certificates indexes
CREATE INDEX IF NOT EXISTS idx_certificates_document ON certificates(document_id);
CREATE INDEX IF NOT EXISTS idx_certificates_generated_at ON certificates(generated_at DESC);

-- ============================================================
-- TRIGGERS FOR AUTOMATIC TIMESTAMPS
-- ============================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to signers table
DROP TRIGGER IF EXISTS update_signers_updated_at ON signers;
CREATE TRIGGER update_signers_updated_at
    BEFORE UPDATE ON signers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- DATA RETENTION POLICY VIEW
-- Identifies records due for anonymization/deletion
-- ============================================================

CREATE OR REPLACE VIEW documents_for_retention_review AS
SELECT
    d.id,
    d.title,
    d.status,
    d.created_at,
    d.completed_at,
    EXTRACT(YEAR FROM AGE(NOW(), COALESCE(d.completed_at, d.created_at))) as years_old,
    CASE
        WHEN EXTRACT(YEAR FROM AGE(NOW(), COALESCE(d.completed_at, d.created_at))) >= 7
        THEN 'REVIEW_REQUIRED'
        ELSE 'RETAIN'
    END as retention_status
FROM documents d
WHERE d.deleted_at IS NULL
ORDER BY d.created_at ASC;

-- ============================================================
-- SAMPLE QUERIES FOR CERTIFICATE GENERATION
-- ============================================================

-- Query to get all data needed for certificate generation
-- (This is for reference - actual implementation in code)
/*
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
        d.signed_file_path
    FROM documents d
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
*/

-- ============================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================

COMMENT ON TABLE documents IS 'Document envelopes for electronic signature. Contains hash chain for integrity verification.';
COMMENT ON TABLE signers IS 'Signing parties for each document. Tracks consent and signature status for ESIGN compliance.';
COMMENT ON TABLE audit_events IS 'Complete audit trail for legal compliance. Every action logged with IP, device, timestamp.';
COMMENT ON TABLE certificates IS 'Certificate of Completion records. Links to generated PDF and contains verification data.';

COMMENT ON COLUMN signers.consent_given IS 'CRITICAL: Must be TRUE before signature is valid under ESIGN Act';
COMMENT ON COLUMN signers.consent_timestamp IS 'When ESIGN disclosure was accepted - required for legal validity';
COMMENT ON COLUMN signers.consent_ip_address IS 'IP address when consent given - part of audit trail';

COMMENT ON COLUMN audit_events.previous_hash IS 'Hash of previous event - creates tamper-evident chain';
COMMENT ON COLUMN audit_events.current_hash IS 'Hash of this event including previous_hash - verifiable integrity';

-- Migration complete
-- Version: 001
-- Date: 2026-01-10
