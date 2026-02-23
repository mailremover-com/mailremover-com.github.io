/**
 * SignSimple.io - Certificate of Completion Generator
 * Generates legally-binding PDF certificates for signed documents
 *
 * Compliant with:
 * - ESIGN Act (15 U.S.C. 7001 et seq.)
 * - UETA
 * - eIDAS Regulation (EU 910/2014)
 */

const { PDFDocument, StandardFonts, rgb } = require('pdf-lib');
const { v4: uuidv4 } = require('uuid');
const fs = require('fs').promises;
const path = require('path');

const { sha256, generateCertificateHash } = require('./hash-utils');
const { parseUserAgent, formatDeviceForDisplay } = require('./ip-capture');

// Configuration
const CONFIG = {
  pageWidth: 612,   // Letter size width (8.5")
  pageHeight: 792,  // Letter size height (11")
  margin: 50,
  lineHeight: 14,
  fontSize: {
    title: 16,
    sectionHeader: 12,
    normal: 10,
    small: 9,
    hash: 8
  },
  colors: {
    black: rgb(0, 0, 0),
    darkGray: rgb(0.2, 0.2, 0.2),
    gray: rgb(0.4, 0.4, 0.4),
    lightGray: rgb(0.6, 0.6, 0.6),
    lineColor: rgb(0.8, 0.8, 0.8)
  }
};

/**
 * Gather all data needed for certificate generation
 * @param {string} documentId - Document UUID
 * @param {Object} db - Database connection/ORM
 * @returns {Promise<Object>} Certificate data object
 */
async function gatherCertificateData(documentId, db) {
  // Fetch all required data in parallel
  const [document, signers, auditEvents] = await Promise.all([
    db.documents.findById(documentId),
    db.signers.findByDocumentId(documentId),
    db.auditEvents.findByDocumentId(documentId)
  ]);

  if (!document) {
    throw new Error(`Document not found: ${documentId}`);
  }

  if (document.status !== 'completed') {
    throw new Error(`Document not completed. Status: ${document.status}`);
  }

  // Get the sender (document creator)
  const sender = await db.users.findById(document.created_by);

  // Parse device info for each signer
  const signersWithDeviceInfo = signers.map(signer => ({
    ...signer,
    deviceInfo: parseUserAgent(signer.signature_user_agent)
  }));

  // Format audit events
  const formattedEvents = auditEvents
    .sort((a, b) => new Date(a.event_timestamp) - new Date(b.event_timestamp))
    .map(event => ({
      timestamp: event.event_timestamp,
      type: event.event_type,
      actor: event.actor_email,
      ip: event.ip_address,
      description: formatEventDescription(event)
    }));

  // Generate certificate metadata
  const certificateId = uuidv4();
  const generatedAt = new Date().toISOString();
  const verificationUrl = `https://signsimple.io/verify/${document.id}`;

  // Build certificate data object
  const certificateData = {
    certificate: {
      id: certificateId,
      generated_at: generatedAt,
      verification_url: verificationUrl
    },
    document: {
      id: document.id,
      title: document.title,
      status: document.status,
      original_hash: document.original_hash,
      final_hash: document.final_hash,
      created_at: document.created_at,
      completed_at: document.completed_at,
      page_count: document.page_count || 1,
      sender: {
        name: sender?.name || 'Unknown',
        email: sender?.email || 'Unknown'
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
        ip_address: signer.consent_ip_address?.toString()
      },
      signature: {
        timestamp: signer.signed_at,
        ip_address: signer.signature_ip_address?.toString(),
        device: signer.deviceInfo
      }
    })),
    audit_trail: formattedEvents
  };

  // Generate hash of certificate data for tamper-evidence
  certificateData.certificate.hash = generateCertificateHash(certificateData);

  return certificateData;
}

/**
 * Format audit event into human-readable description
 * @param {Object} event - Audit event object
 * @returns {string} Formatted description
 */
function formatEventDescription(event) {
  const descriptions = {
    'document.created': `Document created by ${event.actor_email}`,
    'document.uploaded': `Document uploaded by ${event.actor_email}`,
    'document.sent': `Document sent for signing`,
    'document.viewed': `Document viewed by ${event.actor_email}`,
    'document.downloaded': `Document downloaded by ${event.actor_email}`,
    'document.completed': `All signatures complete - Document COMPLETED`,
    'document.voided': `Document voided by ${event.actor_email}`,
    'document.expired': `Document expired`,
    'email.sent': `Signing request email sent to ${event.actor_email}`,
    'email.delivered': `Email delivered to ${event.actor_email}`,
    'email.opened': `Email opened by ${event.actor_email}`,
    'email.bounced': `Email bounced for ${event.actor_email}`,
    'signer.added': `Signer added: ${event.actor_email}`,
    'signer.removed': `Signer removed: ${event.actor_email}`,
    'signer.reminded': `Reminder sent to ${event.actor_email}`,
    'consent.given': `ESIGN consent given by ${event.actor_email}`,
    'consent.withdrawn': `ESIGN consent withdrawn by ${event.actor_email}`,
    'signature.started': `Signing started by ${event.actor_email}`,
    'signature.completed': `Signature completed by ${event.actor_email}`,
    'signature.declined': `Signature declined by ${event.actor_email}`,
    'certificate.generated': `Certificate of Completion generated`,
    'certificate.downloaded': `Certificate downloaded`,
    'verification.success': `Document verification successful`,
    'verification.failed': `Document verification failed`
  };

  let description = descriptions[event.event_type] || event.event_type;

  // Add IP address if available
  if (event.ip_address) {
    description += ` (${event.ip_address})`;
  }

  return description;
}

/**
 * Generate Certificate of Completion PDF
 * @param {Object} certificateData - Complete certificate data object
 * @returns {Promise<Uint8Array>} PDF bytes
 */
async function generateCertificatePDF(certificateData) {
  const pdfDoc = await PDFDocument.create();

  // Embed fonts
  const fonts = {
    regular: await pdfDoc.embedFont(StandardFonts.Helvetica),
    bold: await pdfDoc.embedFont(StandardFonts.HelveticaBold),
    mono: await pdfDoc.embedFont(StandardFonts.Courier)
  };

  let page = pdfDoc.addPage([CONFIG.pageWidth, CONFIG.pageHeight]);
  let y = CONFIG.pageHeight - CONFIG.margin;

  // Helper to add new page if needed
  const ensureSpace = (needed) => {
    if (y < needed + CONFIG.margin) {
      page = pdfDoc.addPage([CONFIG.pageWidth, CONFIG.pageHeight]);
      y = CONFIG.pageHeight - CONFIG.margin;
    }
  };

  // Helper functions
  const drawText = (text, x, options = {}) => {
    const font = options.font || fonts.regular;
    const size = options.size || CONFIG.fontSize.normal;
    const color = options.color || CONFIG.colors.black;

    page.drawText(text, { x, y, size, font, color });
    return size + 4;
  };

  const drawLine = () => {
    page.drawLine({
      start: { x: CONFIG.margin, y },
      end: { x: CONFIG.pageWidth - CONFIG.margin, y },
      thickness: 0.5,
      color: CONFIG.colors.lineColor
    });
  };

  const drawSectionHeader = (title) => {
    ensureSpace(50);
    drawText(title, CONFIG.margin, { font: fonts.bold, size: CONFIG.fontSize.sectionHeader });
    y -= 5;
    drawLine();
    y -= 20;
  };

  // ========== HEADER ==========
  const headerX = CONFIG.pageWidth / 2 - 45;
  drawText('SIGNSIMPLE.IO', headerX, { font: fonts.bold, size: 14 });
  y -= 25;

  const titleX = CONFIG.pageWidth / 2 - 85;
  drawText('CERTIFICATE OF COMPLETION', titleX, { font: fonts.bold, size: CONFIG.fontSize.title });
  y -= 15;
  drawLine();
  y -= 30;

  // ========== DOCUMENT INFO ==========
  const doc = certificateData.document;

  drawText(`Document Title: ${doc.title}`, CONFIG.margin, { font: fonts.bold, size: 11 });
  y -= 15;
  drawText(`Document ID: ${doc.id}`, CONFIG.margin, { size: 10, color: CONFIG.colors.gray });
  y -= 15;
  drawText(`Status: ${doc.status.toUpperCase()}`, CONFIG.margin, { font: fonts.bold, size: 10 });
  y -= 25;

  // ========== DOCUMENT INTEGRITY ==========
  drawSectionHeader('DOCUMENT INTEGRITY');

  drawText('Original Document Hash (SHA-256):', CONFIG.margin, { size: 9 });
  y -= 12;
  drawText(doc.original_hash || 'N/A', CONFIG.margin, {
    font: fonts.mono,
    size: CONFIG.fontSize.hash,
    color: CONFIG.colors.darkGray
  });
  y -= 18;

  drawText('Signed Document Hash (SHA-256):', CONFIG.margin, { size: 9 });
  y -= 12;
  drawText(doc.final_hash || 'N/A', CONFIG.margin, {
    font: fonts.mono,
    size: CONFIG.fontSize.hash,
    color: CONFIG.colors.darkGray
  });
  y -= 18;

  drawText(`Certificate Generated: ${certificateData.certificate.generated_at}`, CONFIG.margin, { size: 9 });
  y -= 30;

  // ========== SIGNING PARTIES ==========
  drawSectionHeader('SIGNING PARTIES');

  for (const signer of certificateData.signers) {
    ensureSpace(120);

    drawText(signer.name, CONFIG.margin, { font: fonts.bold, size: 10 });
    y -= 14;

    const indent = CONFIG.margin + 15;
    drawText(`Email: ${signer.email}`, indent, { size: 9 });
    y -= 12;
    drawText(`Role: ${signer.role.toUpperCase()}`, indent, { size: 9 });
    y -= 12;
    drawText(`Status: ${signer.status.toUpperCase()}`, indent, { size: 9 });
    y -= 12;

    if (signer.signature?.timestamp) {
      drawText(`Signed At: ${signer.signature.timestamp}`, indent, { size: 9 });
      y -= 12;
      drawText(`IP Address: ${signer.signature.ip_address || 'N/A'}`, indent, { size: 9 });
      y -= 12;
      drawText(`Device: ${formatDeviceForDisplay(signer.signature.device)}`, indent, { size: 9 });
      y -= 12;
    }

    if (signer.consent?.given) {
      drawText(`Consent Given: Yes, at ${signer.consent.timestamp}`, indent, { size: 9 });
      y -= 12;
    }

    y -= 10;
    drawLine();
    y -= 15;
  }

  // ========== AUDIT TRAIL ==========
  ensureSpace(100);
  drawSectionHeader('AUDIT TRAIL');

  for (const event of certificateData.audit_trail) {
    ensureSpace(20);

    const timestamp = event.timestamp
      .replace('T', ' ')
      .replace(/\.\d{3}Z$/, ' UTC')
      .replace('Z', ' UTC');

    const text = `${timestamp} - ${event.description}`;

    // Truncate long lines
    const maxLength = 85;
    const displayText = text.length > maxLength ? text.substring(0, maxLength) + '...' : text;

    drawText(displayText, CONFIG.margin, { size: 8 });
    y -= 12;
  }

  y -= 20;

  // ========== LEGAL NOTICE ==========
  ensureSpace(150);
  drawSectionHeader('LEGAL NOTICE');

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
    drawText(line, CONFIG.margin, { size: CONFIG.fontSize.small });
    y -= 12;
  }

  y -= 20;
  drawLine();
  y -= 20;

  // ========== FOOTER ==========
  ensureSpace(60);

  drawText(`Certificate ID: ${certificateData.certificate.id}`, CONFIG.margin, {
    size: 9,
    color: CONFIG.colors.gray
  });
  y -= 12;
  drawText(`Certificate Hash: ${certificateData.certificate.hash}`, CONFIG.margin, {
    size: 7,
    font: fonts.mono,
    color: CONFIG.colors.lightGray
  });
  y -= 12;
  drawText(`Generated: ${certificateData.certificate.generated_at}`, CONFIG.margin, {
    size: 9,
    color: CONFIG.colors.gray
  });
  y -= 12;
  drawText('SignSimple.io - https://signsimple.io', CONFIG.margin, {
    size: 9,
    color: CONFIG.colors.gray
  });

  // Save and return PDF bytes
  const pdfBytes = await pdfDoc.save();
  return pdfBytes;
}

/**
 * Create certificate and save to storage
 * @param {string} documentId - Document UUID
 * @param {Object} db - Database connection
 * @param {Object} storage - Storage service (local, S3, etc.)
 * @returns {Promise<Object>} Certificate result
 */
async function createAndSaveCertificate(documentId, db, storage) {
  // Gather all certificate data
  const certificateData = await gatherCertificateData(documentId, db);

  // Generate PDF
  const pdfBytes = await generateCertificatePDF(certificateData);

  // Determine storage path
  const fileName = `certificate_${certificateData.certificate.id}.pdf`;
  const filePath = `certificates/${documentId}/${fileName}`;

  // Save to storage
  await storage.save(filePath, Buffer.from(pdfBytes));

  // Save certificate record to database
  await db.certificates.create({
    id: certificateData.certificate.id,
    document_id: documentId,
    certificate_hash: certificateData.certificate.hash,
    certificate_data: certificateData,
    pdf_path: filePath,
    generated_at: certificateData.certificate.generated_at,
    generated_by: 'system',
    verification_url: certificateData.certificate.verification_url
  });

  // Create audit event
  await db.auditEvents.create({
    document_id: documentId,
    event_type: 'certificate.generated',
    event_timestamp: new Date().toISOString(),
    actor_type: 'system',
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
    certificateHash: certificateData.certificate.hash,
    pdfPath: filePath,
    pdfBytes: Buffer.from(pdfBytes),
    verificationUrl: certificateData.certificate.verification_url
  };
}

/**
 * Append certificate to signed document (optional - creates combined PDF)
 * @param {Buffer} signedDocBytes - Signed document PDF bytes
 * @param {Buffer} certificateBytes - Certificate PDF bytes
 * @returns {Promise<Buffer>} Combined PDF bytes
 */
async function appendCertificateToDocument(signedDocBytes, certificateBytes) {
  // Load the signed document
  const signedDoc = await PDFDocument.load(signedDocBytes);

  // Load the certificate
  const certificateDoc = await PDFDocument.load(certificateBytes);

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

  return Buffer.from(combinedBytes);
}

/**
 * Verify certificate integrity
 * @param {string} certificateId - Certificate UUID
 * @param {Object} db - Database connection
 * @returns {Promise<Object>} Verification result
 */
async function verifyCertificate(certificateId, db) {
  const certificate = await db.certificates.findById(certificateId);

  if (!certificate) {
    return {
      valid: false,
      error: 'Certificate not found'
    };
  }

  // Recalculate hash from stored data
  const recalculatedHash = generateCertificateHash(certificate.certificate_data);

  // Compare with stored hash
  const isValid = recalculatedHash === certificate.certificate_hash;

  // Update verification count
  await db.certificates.update(certificateId, {
    verified_count: certificate.verified_count + 1,
    last_verified_at: new Date().toISOString()
  });

  return {
    valid: isValid,
    certificateId: certificate.id,
    documentId: certificate.document_id,
    generatedAt: certificate.generated_at,
    storedHash: certificate.certificate_hash,
    calculatedHash: recalculatedHash,
    verifiedAt: new Date().toISOString()
  };
}

module.exports = {
  gatherCertificateData,
  generateCertificatePDF,
  createAndSaveCertificate,
  appendCertificateToDocument,
  verifyCertificate,
  formatEventDescription
};
