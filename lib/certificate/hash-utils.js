/**
 * SignSimple.io - Hash Utilities
 * SHA-256 implementation for document integrity verification
 *
 * Compliant with:
 * - ESIGN Act (15 U.S.C. 7001 et seq.)
 * - UETA
 * - eIDAS Regulation (EU 910/2014)
 */

const crypto = require('crypto');
const fs = require('fs');
const { promisify } = require('util');

const readFile = promisify(fs.readFile);

/**
 * Generate SHA-256 hash from a Buffer or string
 * @param {Buffer|string} data - Data to hash
 * @returns {string} Uppercase hex SHA-256 hash
 */
function sha256(data) {
  const hash = crypto.createHash('sha256');

  if (Buffer.isBuffer(data)) {
    hash.update(data);
  } else if (typeof data === 'string') {
    hash.update(data, 'utf8');
  } else {
    throw new Error('Unsupported data type for hashing. Expected Buffer or string.');
  }

  return hash.digest('hex').toUpperCase();
}

/**
 * Generate SHA-256 hash from a file
 * @param {string} filePath - Path to file
 * @returns {Promise<string>} Uppercase hex SHA-256 hash
 */
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
 * Generate SHA-256 hash from a Buffer (async wrapper for consistency)
 * @param {Buffer} buffer - Buffer to hash
 * @returns {Promise<string>} Uppercase hex SHA-256 hash
 */
async function sha256Buffer(buffer) {
  return sha256(buffer);
}

/**
 * Generate hash chain for multi-signer documents
 * Each signature creates a new hash that includes the previous hash
 *
 * @param {string} previousHash - Hash of previous state (or original doc hash)
 * @param {Object} signatureData - Signature event data
 * @returns {string} New hash in the chain
 */
function generateHashChain(previousHash, signatureData) {
  // Ensure consistent ordering for reproducible hashes
  const dataToHash = previousHash + JSON.stringify(signatureData, Object.keys(signatureData).sort());
  return sha256(dataToHash);
}

/**
 * Verify document integrity by comparing hashes
 * @param {string} filePath - Path to document file
 * @param {string} expectedHash - Expected SHA-256 hash
 * @returns {Promise<Object>} Verification result
 */
async function verifyDocumentHash(filePath, expectedHash) {
  const actualHash = await sha256File(filePath);
  const normalizedExpected = expectedHash.toUpperCase();

  return {
    valid: actualHash === normalizedExpected,
    actualHash,
    expectedHash: normalizedExpected,
    timestamp: new Date().toISOString()
  };
}

/**
 * Verify buffer integrity by comparing hashes
 * @param {Buffer} buffer - Document buffer
 * @param {string} expectedHash - Expected SHA-256 hash
 * @returns {Object} Verification result
 */
function verifyBufferHash(buffer, expectedHash) {
  const actualHash = sha256(buffer);
  const normalizedExpected = expectedHash.toUpperCase();

  return {
    valid: actualHash === normalizedExpected,
    actualHash,
    expectedHash: normalizedExpected,
    timestamp: new Date().toISOString()
  };
}

/**
 * Generate hash for certificate tamper-evidence
 * Creates a hash of all certificate data for verification
 *
 * @param {Object} certificateData - Complete certificate data object
 * @returns {string} Certificate hash
 */
function generateCertificateHash(certificateData) {
  // Create a copy without the hash field itself
  const dataForHashing = { ...certificateData };
  if (dataForHashing.certificate) {
    delete dataForHashing.certificate.hash;
  }

  // Sort keys recursively for consistent hashing
  const sortedData = JSON.stringify(dataForHashing, (key, value) => {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return Object.keys(value).sort().reduce((sorted, key) => {
        sorted[key] = value[key];
        return sorted;
      }, {});
    }
    return value;
  });

  return sha256(sortedData);
}

/**
 * Generate hash of consent disclosure text
 * Used to prove which version of disclosure was shown to signer
 *
 * @param {string} disclosureText - Full disclosure text
 * @returns {string} Hash of disclosure
 */
function hashDisclosureText(disclosureText) {
  return sha256(disclosureText.trim());
}

/**
 * Generate audit event hash for hash chain
 * Each audit event includes a hash linking to the previous event
 *
 * @param {Object} previousEvent - Previous audit event (or null for first)
 * @param {Object} currentEventData - Current event data
 * @returns {Object} Event with hash chain data
 */
function generateAuditEventHash(previousEvent, currentEventData) {
  const previousHash = previousEvent?.current_hash || 'GENESIS';

  const eventForHashing = {
    previous_hash: previousHash,
    event_type: currentEventData.event_type,
    event_timestamp: currentEventData.event_timestamp,
    document_id: currentEventData.document_id,
    actor_email: currentEventData.actor_email,
    ip_address: currentEventData.ip_address,
    event_data: currentEventData.event_data
  };

  const currentHash = sha256(JSON.stringify(eventForHashing, Object.keys(eventForHashing).sort()));

  return {
    previous_hash: previousHash,
    current_hash: currentHash
  };
}

/**
 * Browser-compatible SHA-256 using Web Crypto API
 * Include this in client-side code for document hashing
 *
 * @example
 * // Browser usage:
 * const hash = await sha256Browser(fileInput.files[0]);
 */
const sha256BrowserCode = `
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
`;

module.exports = {
  sha256,
  sha256File,
  sha256Buffer,
  generateHashChain,
  verifyDocumentHash,
  verifyBufferHash,
  generateCertificateHash,
  hashDisclosureText,
  generateAuditEventHash,
  sha256BrowserCode
};
