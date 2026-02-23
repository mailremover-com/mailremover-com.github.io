/**
 * SignSimple.io - IP Address Capture Utility
 * Extracts real client IP from requests behind proxies/CDNs
 *
 * Compliant with:
 * - ESIGN Act audit trail requirements
 * - GDPR (with anonymization support)
 */

const UAParser = require('ua-parser-js');

/**
 * Get the real client IP address from a request
 * Handles Cloudflare, Nginx, AWS ALB, and other common proxy setups
 *
 * @param {Object} request - HTTP request object (Express, Fastify, etc.)
 * @returns {string|null} Client IP address or null if not determinable
 */
function getRealClientIP(request) {
  const headers = request.headers || {};

  // Priority order for IP extraction
  const ipSources = [
    // 1. Cloudflare
    headers['cf-connecting-ip'],

    // 2. True-Client-IP (Akamai, Cloudflare Enterprise)
    headers['true-client-ip'],

    // 3. X-Real-IP (Nginx default configuration)
    headers['x-real-ip'],

    // 4. X-Forwarded-For (standard proxy header)
    // Take the FIRST (leftmost) IP, which is the original client
    getFirstForwardedIP(headers['x-forwarded-for']),

    // 5. AWS ALB
    headers['x-amzn-trace-id'] ? extractIPFromAWSTrace(headers['x-amzn-trace-id']) : null,

    // 6. Direct connection fallbacks
    request.connection?.remoteAddress,
    request.socket?.remoteAddress,
    request.info?.remoteAddress, // Hapi.js
    request.ip // Express.js (when trust proxy is set)
  ];

  for (const ip of ipSources) {
    if (ip && isValidIP(ip)) {
      return normalizeIP(ip);
    }
  }

  return null;
}

/**
 * Extract the first IP from X-Forwarded-For header
 * Format: "client, proxy1, proxy2"
 *
 * @param {string} forwardedFor - X-Forwarded-For header value
 * @returns {string|null} First IP address
 */
function getFirstForwardedIP(forwardedFor) {
  if (!forwardedFor) return null;

  const ips = forwardedFor.split(',').map(ip => ip.trim());
  return ips[0] || null;
}

/**
 * Extract IP from AWS ALB trace ID
 * Format: "Root=1-67891233-abcdef123456789012345678;Self=1-67891234-abcdef"
 *
 * @param {string} traceId - X-Amzn-Trace-Id header
 * @returns {string|null} IP if found
 */
function extractIPFromAWSTrace(traceId) {
  // AWS trace ID doesn't contain IP directly, return null
  // IP comes from X-Forwarded-For with ALB
  return null;
}

/**
 * Validate IP address format (IPv4 or IPv6)
 *
 * @param {string} ip - IP address to validate
 * @returns {boolean} True if valid
 */
function isValidIP(ip) {
  if (!ip || typeof ip !== 'string') return false;

  // Handle IPv6-mapped IPv4 addresses
  const cleanIP = ip.replace(/^::ffff:/, '');

  // IPv4 regex
  const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;

  // IPv6 regex (simplified - covers most common formats)
  const ipv6Regex = /^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$/;

  return ipv4Regex.test(cleanIP) || ipv6Regex.test(ip);
}

/**
 * Normalize IP address format
 * - Removes IPv6 prefix for IPv4-mapped addresses
 * - Trims whitespace
 *
 * @param {string} ip - IP address to normalize
 * @returns {string} Normalized IP
 */
function normalizeIP(ip) {
  if (!ip) return ip;

  // Remove IPv6 prefix for IPv4-mapped addresses
  // ::ffff:192.168.1.1 -> 192.168.1.1
  return ip.replace(/^::ffff:/, '').trim();
}

/**
 * Get all Cloudflare-specific headers from request
 * Useful for enhanced logging and debugging
 *
 * @param {Object} request - HTTP request object
 * @returns {Object} Cloudflare headers
 */
function getCloudflareHeaders(request) {
  const headers = request.headers || {};

  return {
    ip: headers['cf-connecting-ip'] || null,
    country: headers['cf-ipcountry'] || null,
    ray: headers['cf-ray'] || null,
    visitor: headers['cf-visitor'] ? JSON.parse(headers['cf-visitor']) : null,
    ipCity: headers['cf-ipcity'] || null,
    ipContinent: headers['cf-ipcontinent'] || null,
    ipLatitude: headers['cf-iplat'] || null,
    ipLongitude: headers['cf-iplon'] || null,
    isBot: headers['cf-is-bot'] === 'true'
  };
}

/**
 * Parse User-Agent string into structured device information
 *
 * @param {string} userAgent - User-Agent header value
 * @returns {Object} Parsed device information
 */
function parseUserAgent(userAgent) {
  if (!userAgent) {
    return {
      browser: 'Unknown',
      browserVersion: null,
      os: 'Unknown',
      osVersion: null,
      device: 'unknown',
      raw: null
    };
  }

  const parser = new UAParser(userAgent);
  const result = parser.getResult();

  return {
    browser: result.browser.name || 'Unknown',
    browserVersion: result.browser.version || null,
    os: result.os.name || 'Unknown',
    osVersion: result.os.version || null,
    device: result.device.type || 'desktop', // desktop, mobile, tablet
    deviceVendor: result.device.vendor || null,
    deviceModel: result.device.model || null,
    raw: userAgent
  };
}

/**
 * Get complete client information from request
 * Combines IP, device, and location data
 *
 * @param {Object} request - HTTP request object
 * @returns {Object} Complete client information
 */
function getClientInfo(request) {
  const headers = request.headers || {};

  return {
    ip: getRealClientIP(request),
    userAgent: headers['user-agent'] || null,
    device: parseUserAgent(headers['user-agent']),
    cloudflare: getCloudflareHeaders(request),
    referer: headers['referer'] || headers['referrer'] || null,
    acceptLanguage: headers['accept-language'] || null,
    timestamp: new Date().toISOString()
  };
}

/**
 * Anonymize IP address for GDPR compliance
 * Zeros out the last portion of the IP address
 *
 * IPv4: 192.168.1.100 -> 192.168.1.0
 * IPv6: 2001:0db8:85a3::8a2e -> 2001:0db8:85a3::0
 *
 * @param {string} ip - IP address to anonymize
 * @returns {string} Anonymized IP
 */
function anonymizeIP(ip) {
  if (!ip) return ip;

  const normalizedIP = normalizeIP(ip);

  if (normalizedIP.includes(':')) {
    // IPv6: Zero out last 80 bits (last 5 groups)
    const parts = normalizedIP.split(':');
    const anonymized = parts.slice(0, 3).concat(['0', '0', '0', '0', '0']).slice(0, 8);
    return anonymized.join(':');
  } else {
    // IPv4: Zero out last octet
    const parts = normalizedIP.split('.');
    parts[3] = '0';
    return parts.join('.');
  }
}

/**
 * Check if IP is a private/internal address
 * Private IPs should be flagged in audit trails
 *
 * @param {string} ip - IP address to check
 * @returns {boolean} True if private IP
 */
function isPrivateIP(ip) {
  const normalizedIP = normalizeIP(ip);

  // IPv4 private ranges
  const privateRanges = [
    /^10\./,                          // 10.0.0.0/8
    /^172\.(1[6-9]|2[0-9]|3[0-1])\./, // 172.16.0.0/12
    /^192\.168\./,                     // 192.168.0.0/16
    /^127\./,                          // 127.0.0.0/8 (loopback)
    /^169\.254\./,                     // 169.254.0.0/16 (link-local)
    /^0\./                             // 0.0.0.0/8
  ];

  for (const range of privateRanges) {
    if (range.test(normalizedIP)) {
      return true;
    }
  }

  // IPv6 private ranges
  if (normalizedIP.includes(':')) {
    const ipv6Private = [
      /^::1$/,          // Loopback
      /^fe80:/i,        // Link-local
      /^fc00:/i,        // Unique local
      /^fd00:/i         // Unique local
    ];

    for (const range of ipv6Private) {
      if (range.test(normalizedIP)) {
        return true;
      }
    }
  }

  return false;
}

/**
 * Format device info for display in certificate
 *
 * @param {Object} deviceInfo - Parsed device info object
 * @returns {string} Formatted device string
 */
function formatDeviceForDisplay(deviceInfo) {
  if (!deviceInfo) return 'Unknown Device';

  const browser = deviceInfo.browserVersion
    ? `${deviceInfo.browser} ${deviceInfo.browserVersion}`
    : deviceInfo.browser;

  const os = deviceInfo.osVersion
    ? `${deviceInfo.os} ${deviceInfo.osVersion}`
    : deviceInfo.os;

  return `${browser} on ${os}`;
}

module.exports = {
  getRealClientIP,
  getFirstForwardedIP,
  isValidIP,
  normalizeIP,
  getCloudflareHeaders,
  parseUserAgent,
  getClientInfo,
  anonymizeIP,
  isPrivateIP,
  formatDeviceForDisplay
};
