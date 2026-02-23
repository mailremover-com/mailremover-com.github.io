/**
 * SignSimple.io - Audit Events System
 * Creates and manages audit trail for document signing
 *
 * Compliant with:
 * - ESIGN Act (15 U.S.C. 7001 et seq.)
 * - UETA
 * - eIDAS Regulation (EU 910/2014)
 */

const { v4: uuidv4 } = require('uuid');
const { generateAuditEventHash } = require('./hash-utils');
const { getRealClientIP, parseUserAgent, getClientInfo } = require('./ip-capture');

/**
 * All supported audit event types
 */
const EVENT_TYPES = {
  // Document lifecycle
  DOCUMENT_CREATED: 'document.created',
  DOCUMENT_UPLOADED: 'document.uploaded',
  DOCUMENT_SENT: 'document.sent',
  DOCUMENT_VIEWED: 'document.viewed',
  DOCUMENT_DOWNLOADED: 'document.downloaded',
  DOCUMENT_COMPLETED: 'document.completed',
  DOCUMENT_VOIDED: 'document.voided',
  DOCUMENT_EXPIRED: 'document.expired',

  // Email events
  EMAIL_SENT: 'email.sent',
  EMAIL_DELIVERED: 'email.delivered',
  EMAIL_OPENED: 'email.opened',
  EMAIL_BOUNCED: 'email.bounced',

  // Signer events
  SIGNER_ADDED: 'signer.added',
  SIGNER_REMOVED: 'signer.removed',
  SIGNER_REMINDED: 'signer.reminded',

  // Consent events
  CONSENT_GIVEN: 'consent.given',
  CONSENT_WITHDRAWN: 'consent.withdrawn',

  // Signature events
  SIGNATURE_STARTED: 'signature.started',
  SIGNATURE_COMPLETED: 'signature.completed',
  SIGNATURE_DECLINED: 'signature.declined',

  // Certificate events
  CERTIFICATE_GENERATED: 'certificate.generated',
  CERTIFICATE_DOWNLOADED: 'certificate.downloaded',

  // Verification events
  VERIFICATION_SUCCESS: 'verification.success',
  VERIFICATION_FAILED: 'verification.failed'
};

/**
 * Actor types for audit events
 */
const ACTOR_TYPES = {
  USER: 'user',      // Authenticated user (sender)
  SIGNER: 'signer',  // Document signer
  SYSTEM: 'system'   // Automated system action
};

/**
 * Create a new audit event
 * @param {Object} eventData - Event data
 * @param {Object} db - Database connection
 * @returns {Promise<Object>} Created event
 */
async function createAuditEvent(eventData, db) {
  const {
    document_id,
    signer_id = null,
    event_type,
    actor_type,
    actor_id = null,
    actor_email = null,
    ip_address = null,
    user_agent = null,
    event_data = {}
  } = eventData;

  // Validate event type
  if (!Object.values(EVENT_TYPES).includes(event_type)) {
    throw new Error(`Invalid event type: ${event_type}`);
  }

  // Validate actor type
  if (!Object.values(ACTOR_TYPES).includes(actor_type)) {
    throw new Error(`Invalid actor type: ${actor_type}`);
  }

  const timestamp = new Date().toISOString();

  // Parse device info from user agent
  const deviceInfo = user_agent ? parseUserAgent(user_agent) : null;

  // Get previous event for hash chain
  const previousEvent = await db.auditEvents.findLatestByDocument(document_id);

  // Generate hash chain
  const hashChain = generateAuditEventHash(previousEvent, {
    event_type,
    event_timestamp: timestamp,
    document_id,
    actor_email,
    ip_address,
    event_data
  });

  // Create event record
  const event = {
    id: uuidv4(),
    document_id,
    signer_id,
    event_type,
    event_timestamp: timestamp,
    actor_type,
    actor_id,
    actor_email,
    ip_address,
    user_agent,
    device_type: deviceInfo?.device,
    browser: deviceInfo ? `${deviceInfo.browser} ${deviceInfo.browserVersion || ''}`.trim() : null,
    os: deviceInfo ? `${deviceInfo.os} ${deviceInfo.osVersion || ''}`.trim() : null,
    previous_hash: hashChain.previous_hash,
    current_hash: hashChain.current_hash,
    event_data,
    created_at: timestamp
  };

  // Save to database
  await db.auditEvents.create(event);

  return event;
}

/**
 * Create audit event from HTTP request
 * Automatically extracts IP and user agent
 *
 * @param {Object} eventData - Event data
 * @param {Object} request - HTTP request object
 * @param {Object} db - Database connection
 * @returns {Promise<Object>} Created event
 */
async function createAuditEventFromRequest(eventData, request, db) {
  return createAuditEvent({
    ...eventData,
    ip_address: eventData.ip_address || getRealClientIP(request),
    user_agent: eventData.user_agent || request.headers['user-agent']
  }, db);
}

// ============ Event Creator Functions ============

/**
 * Document created event
 */
async function documentCreated(documentId, userId, userEmail, documentData, db) {
  return createAuditEvent({
    document_id: documentId,
    event_type: EVENT_TYPES.DOCUMENT_CREATED,
    actor_type: ACTOR_TYPES.USER,
    actor_id: userId,
    actor_email: userEmail,
    event_data: {
      title: documentData.title,
      page_count: documentData.pageCount,
      file_size_bytes: documentData.fileSize,
      signers_count: documentData.signersCount
    }
  }, db);
}

/**
 * Document uploaded event
 */
async function documentUploaded(documentId, userId, userEmail, fileData, db) {
  return createAuditEvent({
    document_id: documentId,
    event_type: EVENT_TYPES.DOCUMENT_UPLOADED,
    actor_type: ACTOR_TYPES.USER,
    actor_id: userId,
    actor_email: userEmail,
    event_data: {
      file_name: fileData.fileName,
      file_hash: fileData.hash,
      file_size_bytes: fileData.size,
      mime_type: fileData.mimeType
    }
  }, db);
}

/**
 * Document sent event
 */
async function documentSent(documentId, userId, userEmail, recipients, db) {
  return createAuditEvent({
    document_id: documentId,
    event_type: EVENT_TYPES.DOCUMENT_SENT,
    actor_type: ACTOR_TYPES.USER,
    actor_id: userId,
    actor_email: userEmail,
    event_data: {
      recipients: recipients.map(r => ({ email: r.email, name: r.name, role: r.role })),
      recipients_count: recipients.length
    }
  }, db);
}

/**
 * Document viewed event
 */
async function documentViewed(documentId, signerId, signerEmail, request, db) {
  return createAuditEventFromRequest({
    document_id: documentId,
    signer_id: signerId,
    event_type: EVENT_TYPES.DOCUMENT_VIEWED,
    actor_type: ACTOR_TYPES.SIGNER,
    actor_id: signerId,
    actor_email: signerEmail
  }, request, db);
}

/**
 * Document downloaded event
 */
async function documentDownloaded(documentId, actorId, actorEmail, actorType, request, db) {
  return createAuditEventFromRequest({
    document_id: documentId,
    event_type: EVENT_TYPES.DOCUMENT_DOWNLOADED,
    actor_type: actorType,
    actor_id: actorId,
    actor_email: actorEmail
  }, request, db);
}

/**
 * Document completed event
 */
async function documentCompleted(documentId, finalHash, db) {
  return createAuditEvent({
    document_id: documentId,
    event_type: EVENT_TYPES.DOCUMENT_COMPLETED,
    actor_type: ACTOR_TYPES.SYSTEM,
    event_data: {
      final_hash: finalHash,
      completed_at: new Date().toISOString()
    }
  }, db);
}

/**
 * Document voided event
 */
async function documentVoided(documentId, userId, userEmail, reason, db) {
  return createAuditEvent({
    document_id: documentId,
    event_type: EVENT_TYPES.DOCUMENT_VOIDED,
    actor_type: ACTOR_TYPES.USER,
    actor_id: userId,
    actor_email: userEmail,
    event_data: {
      reason,
      voided_at: new Date().toISOString()
    }
  }, db);
}

/**
 * Email sent event
 */
async function emailSent(documentId, signerId, signerEmail, messageId, db) {
  return createAuditEvent({
    document_id: documentId,
    signer_id: signerId,
    event_type: EVENT_TYPES.EMAIL_SENT,
    actor_type: ACTOR_TYPES.SYSTEM,
    actor_email: signerEmail,
    event_data: {
      message_id: messageId,
      recipient_email: signerEmail
    }
  }, db);
}

/**
 * Email delivered event
 */
async function emailDelivered(documentId, signerId, signerEmail, messageId, db) {
  return createAuditEvent({
    document_id: documentId,
    signer_id: signerId,
    event_type: EVENT_TYPES.EMAIL_DELIVERED,
    actor_type: ACTOR_TYPES.SYSTEM,
    actor_email: signerEmail,
    event_data: {
      message_id: messageId
    }
  }, db);
}

/**
 * Email opened event (tracking pixel)
 */
async function emailOpened(documentId, signerId, signerEmail, request, db) {
  return createAuditEventFromRequest({
    document_id: documentId,
    signer_id: signerId,
    event_type: EVENT_TYPES.EMAIL_OPENED,
    actor_type: ACTOR_TYPES.SIGNER,
    actor_id: signerId,
    actor_email: signerEmail
  }, request, db);
}

/**
 * Signature started event
 */
async function signatureStarted(documentId, signerId, signerEmail, request, db) {
  return createAuditEventFromRequest({
    document_id: documentId,
    signer_id: signerId,
    event_type: EVENT_TYPES.SIGNATURE_STARTED,
    actor_type: ACTOR_TYPES.SIGNER,
    actor_id: signerId,
    actor_email: signerEmail
  }, request, db);
}

/**
 * Signature completed event
 */
async function signatureCompleted(documentId, signerId, signerEmail, signatureData, request, db) {
  return createAuditEventFromRequest({
    document_id: documentId,
    signer_id: signerId,
    event_type: EVENT_TYPES.SIGNATURE_COMPLETED,
    actor_type: ACTOR_TYPES.SIGNER,
    actor_id: signerId,
    actor_email: signerEmail,
    event_data: {
      signature_type: signatureData.type, // draw, type, upload
      signature_hash: signatureData.hash,
      fields_signed: signatureData.fields,
      time_spent_seconds: signatureData.timeSpent
    }
  }, request, db);
}

/**
 * Signature declined event
 */
async function signatureDeclined(documentId, signerId, signerEmail, reason, request, db) {
  return createAuditEventFromRequest({
    document_id: documentId,
    signer_id: signerId,
    event_type: EVENT_TYPES.SIGNATURE_DECLINED,
    actor_type: ACTOR_TYPES.SIGNER,
    actor_id: signerId,
    actor_email: signerEmail,
    event_data: {
      decline_reason: reason
    }
  }, request, db);
}

/**
 * Certificate generated event
 */
async function certificateGenerated(documentId, certificateId, certificateHash, db) {
  return createAuditEvent({
    document_id: documentId,
    event_type: EVENT_TYPES.CERTIFICATE_GENERATED,
    actor_type: ACTOR_TYPES.SYSTEM,
    event_data: {
      certificate_id: certificateId,
      certificate_hash: certificateHash
    }
  }, db);
}

/**
 * Verification success event
 */
async function verificationSuccess(documentId, verifiedHash, request, db) {
  return createAuditEventFromRequest({
    document_id: documentId,
    event_type: EVENT_TYPES.VERIFICATION_SUCCESS,
    actor_type: ACTOR_TYPES.SYSTEM,
    event_data: {
      verified_hash: verifiedHash
    }
  }, request, db);
}

/**
 * Verification failed event
 */
async function verificationFailed(documentId, expectedHash, actualHash, request, db) {
  return createAuditEventFromRequest({
    document_id: documentId,
    event_type: EVENT_TYPES.VERIFICATION_FAILED,
    actor_type: ACTOR_TYPES.SYSTEM,
    event_data: {
      expected_hash: expectedHash,
      actual_hash: actualHash,
      reason: 'Hash mismatch'
    }
  }, request, db);
}

/**
 * Get all audit events for a document
 * @param {string} documentId - Document UUID
 * @param {Object} db - Database connection
 * @returns {Promise<Array>} Audit events
 */
async function getAuditTrail(documentId, db) {
  const events = await db.auditEvents.findByDocumentId(documentId);

  return events.sort((a, b) =>
    new Date(a.event_timestamp) - new Date(b.event_timestamp)
  );
}

/**
 * Verify audit trail integrity (hash chain)
 * @param {string} documentId - Document UUID
 * @param {Object} db - Database connection
 * @returns {Promise<Object>} Verification result
 */
async function verifyAuditTrailIntegrity(documentId, db) {
  const events = await getAuditTrail(documentId, db);

  if (events.length === 0) {
    return { valid: true, eventCount: 0 };
  }

  let previousHash = 'GENESIS';
  const errors = [];

  for (let i = 0; i < events.length; i++) {
    const event = events[i];

    // Check previous hash matches
    if (event.previous_hash !== previousHash) {
      errors.push({
        eventIndex: i,
        eventId: event.id,
        eventType: event.event_type,
        expectedPreviousHash: previousHash,
        actualPreviousHash: event.previous_hash
      });
    }

    // Recalculate current hash
    const expectedHash = generateAuditEventHash(
      i > 0 ? events[i - 1] : null,
      {
        event_type: event.event_type,
        event_timestamp: event.event_timestamp,
        document_id: event.document_id,
        actor_email: event.actor_email,
        ip_address: event.ip_address,
        event_data: event.event_data
      }
    );

    if (event.current_hash !== expectedHash.current_hash) {
      errors.push({
        eventIndex: i,
        eventId: event.id,
        eventType: event.event_type,
        expectedCurrentHash: expectedHash.current_hash,
        actualCurrentHash: event.current_hash
      });
    }

    previousHash = event.current_hash;
  }

  return {
    valid: errors.length === 0,
    eventCount: events.length,
    errors: errors.length > 0 ? errors : undefined
  };
}

/**
 * Export audit trail as CSV
 * @param {string} documentId - Document UUID
 * @param {Object} db - Database connection
 * @returns {Promise<string>} CSV string
 */
async function exportAuditTrailCSV(documentId, db) {
  const events = await getAuditTrail(documentId, db);

  const headers = [
    'Timestamp',
    'Event Type',
    'Actor Email',
    'IP Address',
    'Browser',
    'OS',
    'Details'
  ];

  const rows = events.map(event => [
    event.event_timestamp,
    event.event_type,
    event.actor_email || '',
    event.ip_address || '',
    event.browser || '',
    event.os || '',
    JSON.stringify(event.event_data || {})
  ]);

  const csvLines = [
    headers.join(','),
    ...rows.map(row => row.map(cell =>
      `"${String(cell).replace(/"/g, '""')}"`
    ).join(','))
  ];

  return csvLines.join('\n');
}

module.exports = {
  EVENT_TYPES,
  ACTOR_TYPES,
  createAuditEvent,
  createAuditEventFromRequest,

  // Specific event creators
  documentCreated,
  documentUploaded,
  documentSent,
  documentViewed,
  documentDownloaded,
  documentCompleted,
  documentVoided,
  emailSent,
  emailDelivered,
  emailOpened,
  signatureStarted,
  signatureCompleted,
  signatureDeclined,
  certificateGenerated,
  verificationSuccess,
  verificationFailed,

  // Retrieval and verification
  getAuditTrail,
  verifyAuditTrailIntegrity,
  exportAuditTrailCSV
};
