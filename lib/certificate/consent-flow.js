/**
 * SignSimple.io - ESIGN Consent Flow
 * Handles electronic signature disclosure and consent recording
 *
 * Compliant with:
 * - ESIGN Act (15 U.S.C. 7001 et seq.)
 * - UETA
 * - eIDAS Regulation (EU 910/2014)
 */

const { sha256 } = require('./hash-utils');
const { getRealClientIP, parseUserAgent } = require('./ip-capture');

// Current version of disclosure (increment when disclosure text changes)
const DISCLOSURE_VERSION = '1.0';

/**
 * ESIGN Act Electronic Signature Disclosure
 * This text must be shown to all signers before they can sign
 */
const ESIGN_DISCLOSURE = `
ELECTRONIC SIGNATURE DISCLOSURE AND CONSENT

Before you proceed to sign electronically, please read this disclosure carefully.

CONSENT TO USE ELECTRONIC SIGNATURES

By clicking "I Agree" below, you consent to:

1. Signing documents electronically using SignSimple.io
2. Receiving documents and notices electronically
3. Using electronic signatures in place of handwritten signatures

LEGAL EFFECT OF ELECTRONIC SIGNATURES

Under the federal Electronic Signatures in Global and National Commerce Act (ESIGN Act, 15 U.S.C. 7001 et seq.) and applicable state law (Uniform Electronic Transactions Act), electronic signatures have the same legal effect as handwritten signatures when all parties consent to conduct business electronically.

By signing electronically, you agree that your electronic signature is the legal equivalent of your manual/handwritten signature.

YOUR RIGHT TO OBTAIN PAPER COPIES

You have the right to receive a paper copy of any document you sign electronically. To request a paper copy, you may:

- Download and print the document from your SignSimple.io account
- Contact the sender to request a paper copy
- Email support@signsimple.io for assistance

There is no fee for requesting paper copies.

YOUR RIGHT TO WITHDRAW CONSENT

You may withdraw your consent to receive documents electronically at any time. To withdraw consent:

- Do not sign the document
- Close this window and contact the sender directly
- Email support@signsimple.io

Withdrawing consent will not affect the validity of any documents you have already signed electronically.

HARDWARE AND SOFTWARE REQUIREMENTS

To access and retain electronic documents, you need:

- A computer or mobile device with internet access
- A current web browser (Chrome, Firefox, Safari, or Edge)
- Software to view PDF documents (e.g., Adobe Reader)
- A printer or storage device to retain copies
- A valid email address to receive notifications

You confirm that you meet these requirements by proceeding.

UPDATING YOUR CONTACT INFORMATION

You are responsible for keeping your email address current. If your email changes, please update it in your account settings or contact the sender.
`.trim();

/**
 * Hardware and Software Requirements (detailed version)
 */
const HARDWARE_SOFTWARE_REQUIREMENTS = `
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

By proceeding, you confirm that you currently have access to the hardware and software listed above and will be able to access and retain the documents you sign.
`.trim();

/**
 * Right to Paper Copy Disclosure
 */
const PAPER_COPY_DISCLOSURE = `
YOUR RIGHT TO PAPER COPIES

At any time, you may request a paper copy of any document you have signed electronically. To obtain a paper copy:

Option 1: Self-Service
- Log into your SignSimple.io account
- Navigate to "My Documents"
- Click "Download" on any document
- Print the downloaded PDF

Option 2: Request from Sender
- Contact the sender directly
- Request a paper copy of the signed document
- The sender may mail or email you a copy

Option 3: Contact Support
- Email support@signsimple.io
- Subject: Paper Copy Request
- Include the document name and your email address

Cost: There is no charge for paper copies.

Timeframe: Paper copies will be provided within 5 business days of request.
`.trim();

/**
 * Get complete disclosure for display
 * @returns {Object} Disclosure content and metadata
 */
function getDisclosure() {
  return {
    version: DISCLOSURE_VERSION,
    main: ESIGN_DISCLOSURE,
    hardwareSoftware: HARDWARE_SOFTWARE_REQUIREMENTS,
    paperCopy: PAPER_COPY_DISCLOSURE,
    hash: sha256(ESIGN_DISCLOSURE + HARDWARE_SOFTWARE_REQUIREMENTS + PAPER_COPY_DISCLOSURE)
  };
}

/**
 * Get HTML for consent checkbox UI
 * @param {string} senderEmail - Email of document sender (for paper copy contact)
 * @returns {string} HTML string
 */
function getConsentCheckboxHTML(senderEmail = 'the sender') {
  return `
<div class="consent-checkboxes">
  <label class="consent-item">
    <input type="checkbox" id="consent-esign" name="consent-esign" required>
    <span>I have read and agree to the <a href="#disclosure" target="_blank">Electronic Signature Disclosure</a>. I consent to use electronic signatures and understand that my electronic signature has the same legal effect as a handwritten signature.</span>
  </label>

  <label class="consent-item">
    <input type="checkbox" id="consent-requirements" name="consent-requirements" required>
    <span>I confirm that I have access to the required hardware and software to view, sign, and retain electronic documents.</span>
  </label>

  <label class="consent-item">
    <input type="checkbox" id="consent-paper-rights" name="consent-paper-rights" required>
    <span>I understand my right to receive paper copies and my right to withdraw consent at any time.</span>
  </label>
</div>
`.trim();
}

/**
 * Record consent given by a signer
 * @param {string} signerId - Signer UUID
 * @param {Object} request - HTTP request object
 * @param {Object} consentData - Consent checkbox states
 * @param {Object} db - Database connection
 * @returns {Promise<Object>} Consent record
 */
async function recordConsent(signerId, request, consentData, db) {
  const timestamp = new Date().toISOString();
  const ipAddress = getRealClientIP(request);
  const userAgent = request.headers['user-agent'];
  const deviceInfo = parseUserAgent(userAgent);
  const disclosure = getDisclosure();

  // Validate all required consents are given
  const requiredConsents = ['esign', 'requirements', 'paperRights'];
  const missingConsents = requiredConsents.filter(key => !consentData[key]);

  if (missingConsents.length > 0) {
    throw new Error(`Missing required consents: ${missingConsents.join(', ')}`);
  }

  // Get signer to find document ID
  const signer = await db.signers.findById(signerId);
  if (!signer) {
    throw new Error(`Signer not found: ${signerId}`);
  }

  // Create consent record
  const consentRecord = {
    signer_id: signerId,
    document_id: signer.document_id,
    consent_given: true,
    consent_timestamp: timestamp,
    consent_ip_address: ipAddress,
    consent_user_agent: userAgent,
    consent_version: disclosure.version,
    disclosure_text_hash: disclosure.hash,
    consents: {
      esign_disclosure: consentData.esign === true,
      hardware_software: consentData.requirements === true,
      paper_copy_rights: consentData.paperRights === true
    },
    device_info: deviceInfo
  };

  // Update signer record
  await db.signers.update(signerId, {
    consent_given: true,
    consent_timestamp: timestamp,
    consent_ip_address: ipAddress,
    consent_user_agent: userAgent
  });

  // Create audit event
  await db.auditEvents.create({
    document_id: signer.document_id,
    signer_id: signerId,
    event_type: 'consent.given',
    event_timestamp: timestamp,
    actor_type: 'signer',
    actor_id: signerId,
    actor_email: signer.email,
    ip_address: ipAddress,
    user_agent: userAgent,
    device_type: deviceInfo.device,
    browser: `${deviceInfo.browser} ${deviceInfo.browserVersion || ''}`.trim(),
    os: `${deviceInfo.os} ${deviceInfo.osVersion || ''}`.trim(),
    event_data: {
      consent_version: disclosure.version,
      disclosure_hash: disclosure.hash,
      consents: consentRecord.consents
    }
  });

  return consentRecord;
}

/**
 * Check if signer has already given consent
 * @param {string} signerId - Signer UUID
 * @param {Object} db - Database connection
 * @returns {Promise<Object|null>} Existing consent or null
 */
async function checkExistingConsent(signerId, db) {
  const signer = await db.signers.findById(signerId);

  if (!signer) {
    throw new Error(`Signer not found: ${signerId}`);
  }

  if (signer.consent_given) {
    return {
      given: true,
      timestamp: signer.consent_timestamp,
      ipAddress: signer.consent_ip_address
    };
  }

  return null;
}

/**
 * Withdraw consent (signer opts out before signing)
 * @param {string} signerId - Signer UUID
 * @param {Object} request - HTTP request object
 * @param {Object} db - Database connection
 * @returns {Promise<Object>} Withdrawal record
 */
async function withdrawConsent(signerId, request, db) {
  const timestamp = new Date().toISOString();
  const ipAddress = getRealClientIP(request);
  const userAgent = request.headers['user-agent'];

  const signer = await db.signers.findById(signerId);
  if (!signer) {
    throw new Error(`Signer not found: ${signerId}`);
  }

  // Note: We don't actually remove consent record, we just add an event
  // This preserves the audit trail

  // Create audit event
  await db.auditEvents.create({
    document_id: signer.document_id,
    signer_id: signerId,
    event_type: 'consent.withdrawn',
    event_timestamp: timestamp,
    actor_type: 'signer',
    actor_id: signerId,
    actor_email: signer.email,
    ip_address: ipAddress,
    user_agent: userAgent,
    event_data: {
      original_consent_timestamp: signer.consent_timestamp
    }
  });

  // Update signer status
  await db.signers.update(signerId, {
    status: 'declined',
    declined_at: timestamp,
    decline_reason: 'Consent withdrawn'
  });

  return {
    withdrawn: true,
    timestamp,
    signerId
  };
}

/**
 * Validate consent is still valid (not expired, same session)
 * @param {string} signerId - Signer UUID
 * @param {Object} request - HTTP request object
 * @param {Object} db - Database connection
 * @returns {Promise<Object>} Validation result
 */
async function validateConsent(signerId, request, db) {
  const signer = await db.signers.findById(signerId);

  if (!signer) {
    return { valid: false, reason: 'Signer not found' };
  }

  if (!signer.consent_given) {
    return { valid: false, reason: 'No consent recorded' };
  }

  // Check if consent is recent (within 24 hours for extra security)
  const consentTime = new Date(signer.consent_timestamp);
  const now = new Date();
  const hoursSinceConsent = (now - consentTime) / (1000 * 60 * 60);

  if (hoursSinceConsent > 24) {
    // Consent is old, but still valid for signing
    // Just flag it for potential re-confirmation
    return {
      valid: true,
      stale: true,
      hoursSinceConsent: Math.round(hoursSinceConsent),
      timestamp: signer.consent_timestamp
    };
  }

  return {
    valid: true,
    stale: false,
    timestamp: signer.consent_timestamp,
    ipAddress: signer.consent_ip_address
  };
}

/**
 * Get consent summary for certificate
 * @param {string} signerId - Signer UUID
 * @param {Object} db - Database connection
 * @returns {Promise<Object>} Consent summary
 */
async function getConsentSummary(signerId, db) {
  const signer = await db.signers.findById(signerId);

  if (!signer) {
    return null;
  }

  return {
    given: signer.consent_given || false,
    timestamp: signer.consent_timestamp,
    ipAddress: signer.consent_ip_address?.toString(),
    version: DISCLOSURE_VERSION
  };
}

module.exports = {
  // Disclosure text
  DISCLOSURE_VERSION,
  ESIGN_DISCLOSURE,
  HARDWARE_SOFTWARE_REQUIREMENTS,
  PAPER_COPY_DISCLOSURE,

  // Functions
  getDisclosure,
  getConsentCheckboxHTML,
  recordConsent,
  checkExistingConsent,
  withdrawConsent,
  validateConsent,
  getConsentSummary
};
