/**
 * SignSimple.io - Certificate of Completion Module
 * Complete implementation for legally-binding electronic signatures
 *
 * Compliant with:
 * - ESIGN Act (15 U.S.C. 7001 et seq.)
 * - UETA (Uniform Electronic Transactions Act)
 * - eIDAS Regulation (EU 910/2014)
 *
 * @module certificate
 */

const hashUtils = require('./hash-utils');
const ipCapture = require('./ip-capture');
const generateCertificate = require('./generate-certificate');
const consentFlow = require('./consent-flow');
const auditEvents = require('./audit-events');

module.exports = {
  // Hash utilities for document integrity
  hash: {
    sha256: hashUtils.sha256,
    sha256File: hashUtils.sha256File,
    sha256Buffer: hashUtils.sha256Buffer,
    generateHashChain: hashUtils.generateHashChain,
    verifyDocumentHash: hashUtils.verifyDocumentHash,
    verifyBufferHash: hashUtils.verifyBufferHash,
    generateCertificateHash: hashUtils.generateCertificateHash,
    hashDisclosureText: hashUtils.hashDisclosureText,
    sha256BrowserCode: hashUtils.sha256BrowserCode
  },

  // IP address and device capture
  ip: {
    getRealClientIP: ipCapture.getRealClientIP,
    getClientInfo: ipCapture.getClientInfo,
    parseUserAgent: ipCapture.parseUserAgent,
    anonymizeIP: ipCapture.anonymizeIP,
    isPrivateIP: ipCapture.isPrivateIP,
    getCloudflareHeaders: ipCapture.getCloudflareHeaders,
    formatDeviceForDisplay: ipCapture.formatDeviceForDisplay
  },

  // Certificate generation
  certificate: {
    gatherCertificateData: generateCertificate.gatherCertificateData,
    generateCertificatePDF: generateCertificate.generateCertificatePDF,
    createAndSaveCertificate: generateCertificate.createAndSaveCertificate,
    appendCertificateToDocument: generateCertificate.appendCertificateToDocument,
    verifyCertificate: generateCertificate.verifyCertificate
  },

  // ESIGN consent flow
  consent: {
    DISCLOSURE_VERSION: consentFlow.DISCLOSURE_VERSION,
    ESIGN_DISCLOSURE: consentFlow.ESIGN_DISCLOSURE,
    HARDWARE_SOFTWARE_REQUIREMENTS: consentFlow.HARDWARE_SOFTWARE_REQUIREMENTS,
    PAPER_COPY_DISCLOSURE: consentFlow.PAPER_COPY_DISCLOSURE,
    getDisclosure: consentFlow.getDisclosure,
    getConsentCheckboxHTML: consentFlow.getConsentCheckboxHTML,
    recordConsent: consentFlow.recordConsent,
    checkExistingConsent: consentFlow.checkExistingConsent,
    withdrawConsent: consentFlow.withdrawConsent,
    validateConsent: consentFlow.validateConsent,
    getConsentSummary: consentFlow.getConsentSummary
  },

  // Audit trail events
  audit: {
    EVENT_TYPES: auditEvents.EVENT_TYPES,
    ACTOR_TYPES: auditEvents.ACTOR_TYPES,
    createAuditEvent: auditEvents.createAuditEvent,
    createAuditEventFromRequest: auditEvents.createAuditEventFromRequest,
    getAuditTrail: auditEvents.getAuditTrail,
    verifyAuditTrailIntegrity: auditEvents.verifyAuditTrailIntegrity,
    exportAuditTrailCSV: auditEvents.exportAuditTrailCSV,

    // Specific event creators
    events: {
      documentCreated: auditEvents.documentCreated,
      documentUploaded: auditEvents.documentUploaded,
      documentSent: auditEvents.documentSent,
      documentViewed: auditEvents.documentViewed,
      documentDownloaded: auditEvents.documentDownloaded,
      documentCompleted: auditEvents.documentCompleted,
      documentVoided: auditEvents.documentVoided,
      emailSent: auditEvents.emailSent,
      emailDelivered: auditEvents.emailDelivered,
      emailOpened: auditEvents.emailOpened,
      signatureStarted: auditEvents.signatureStarted,
      signatureCompleted: auditEvents.signatureCompleted,
      signatureDeclined: auditEvents.signatureDeclined,
      certificateGenerated: auditEvents.certificateGenerated,
      verificationSuccess: auditEvents.verificationSuccess,
      verificationFailed: auditEvents.verificationFailed
    }
  }
};
